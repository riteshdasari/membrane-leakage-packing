"""Serial matched retimed baseline routes, gated by all four exact RTL variants.

This imports safely without launching tools. Both tops use the same 219-FF
registered OOC fixture and 6 ns target as the original guard-add trial. Core
resources exclude those FFs; occupied core/fixture slice sets overlap. Raw-port
timing is a separate budget audit. No board Fmax, power, memory bandwidth, host,
or complete neuron-update latency follows from this primitive experiment.
"""
from pathlib import Path
import argparse
import ctypes
import hashlib
import json
import os
import re
import subprocess
import time

P = Path(__file__).resolve().parent
R = P / 'results'
ORIGINAL_RESULTS = P.parent / 'results'
VIVADO = Path('C:/AMDDesignTools/2025.2/Vivado/bin/vivado.bat')
FUNCTIONAL_SOURCES = ['guard_add_retime.sv', 'tb_guard_add_retime.sv',
                      'check_guard_add_retime.py', 'check_guard_add_retime_snn.py',
                      '../guard_add.sv', '../check_guard_add.py']
SOURCES = FUNCTIONAL_SOURCES + ['guard_add_retime_timing.sv',
                                'route_guard_add_retime.tcl', 'run_guard_add_retime_route.py']
TOPS = dict(top_guard_add_retime_hybrid=2, top_guard_add_retime_lut=3)
VARIANTS = dict(top_guard_add_retime_hybrid=0, top_guard_add_retime_lut=1)
SUITES = ['retime_main_0_checks.json', 'retime_main_1_checks.json',
          'retime_models_0_checks.json', 'retime_models_1_checks.json']
MODEL_INPUTS = ['adaptive_delta_model_25_1/expected.npz', 'adaptive_delta_model_input.json']
REFERENCE_CORE_SHA = 'f89019a87185b046a95819f70cf0c9d83f2fe20ee0a5a0e253a2702e9629a907'


def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def hashes():
    return {name: sha(P / name) for name in SOURCES}


def free():
    class Memory(ctypes.Structure):
        _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong),
                    ('total', ctypes.c_ulonglong), ('free', ctypes.c_ulonglong),
                    ('rest', ctypes.c_ulonglong * 5)]
    memory = Memory()
    memory.length = ctypes.sizeof(memory)
    assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory))
    return memory.free / 2**30


def functional(top, pin):
    assert top in TOPS, ('Unknown matched retimed baseline top', top)
    assert pin['../guard_add.sv'] == REFERENCE_CORE_SHA, 'Measured original reference core changed'
    expected = [0, 1, 2, 3]
    source_pins = {name: pin[name] for name in FUNCTIONAL_SOURCES}
    model_pins = {name: sha(ORIGINAL_RESULTS / name) for name in MODEL_INPUTS}
    evidence = {}
    for name in SUITES:
        data = json.loads((R / name).read_text())
        assert data['source_hashes'] == source_pins, (name, 'Functional source pins differ')
        assert data['tested_variants'] == data['expected_variants'] == expected, name
        assert data['reference_variants'] == [2, 3], name
        assert sorted(row['variant'] for row in data['rows']) == expected, name
        assert data['frames'] > 0 and data['acceptance_to_handshake_advances'] == 4, name
        assert data['backpressure'] == name.endswith('_1_checks.json'), name
        assert data['outputs_byte_identical'] is True and data['matched_original_stimulus'] is True, name
        tag = name.removesuffix('_checks.json')
        stimulus = f'{tag}/stream_stim.txt'
        assert data['stimulus_file'] == stimulus and sha(R / stimulus) == data['stimulus_sha256'], name
        original_tag = tag.replace('retime_', 'guard_add_', 1)
        assert sha(ORIGINAL_RESULTS / original_tag / 'stream_stim.txt') == data['stimulus_sha256'], name
        if name.startswith('retime_models_'):
            assert data['model_input_sha256'] == model_pins and data['frames'] == 9216, name
            neurons = 635904
        else:
            assert data['model_input_sha256'] is None, name
            neurons = 811511
        assert len({row['output_sha256'] for row in data['rows']}) == 1, name
        for row in data['rows']:
            assert row['mismatches'] == 0 and row['neurons'] == neurons, (name, row)
            engine = 2 if row['variant'] in (0, 2) else 3
            assert row['reference_engine'] == engine, (name, row)
            assert row['narrow_requests'] == row['copy_requests'] == 0, (name, row)
            assert row['arithmetic_issues'] == (row['requests'] if engine == 2 else 0), (name, row)
            assert row['latency_checks'] == row['requests'] > 0, (name, row)
            assert sha(R / tag / f"stream_out{row['variant']}.txt") == row['output_sha256'], (name, row['variant'])
            if name == 'retime_models_0_checks.json':
                assert row['clocks'] == row['requests'] + 4, (name, row)
        evidence[name] = sha(R / name)

    name = 'retime_snn_checks.json'
    data = json.loads((R / name).read_text())
    assert data['source_hashes'] == source_pins, 'SNN replay source pins differ'
    assert data['reconstruction_script_sha256'] == pin['check_guard_add_retime_snn.py']
    assert data['tested_variants'] == expected
    assert data['functional_check_sha256'] == {
        name: evidence[name] for name in ('retime_models_0_checks.json', 'retime_models_1_checks.json')}
    assert data['reference_hashes'] == dict(ledger=model_pins[MODEL_INPUTS[1]],
                                          raw_membranes=model_pins[MODEL_INPUTS[0]])
    assert sorted((row['variant'], row['backpressure']) for row in data['rows']) == [
        (variant, backpressure) for variant in expected for backpressure in (False, True)]
    for row in data['rows']:
        assert row['state_mismatches'] == row['spike_mismatches'] == 0 and row['neurons'] == 635904, row
        assert len(row['model_rows']) == 3 and sorted(model['seed'] for model in row['model_rows']) == [0, 1, 2], row
        assert all(model['images'] == 48 and model['spike_counts_matched'] for model in row['model_rows']), row
    output_paths = {str(Path('results') / f'retime_models_{backpressure}' / f'stream_out{variant}.txt')
                    for variant in expected for backpressure in (0, 1)}
    assert set(data['output_hashes']) == output_paths, 'Expected eight SNN replay outputs'
    for path, stamp in data['output_hashes'].items():
        assert sha(P / path) == stamp, (path, 'SNN replay output pin differs')
    evidence[name] = sha(R / name)
    return evidence


def util(path, need_slices=True):
    report = path.read_text()
    def get(label):
        match = re.search(r'\|\s*' + re.escape(label) + r'\*?\s*\|\s*([\d.]+)', report)
        assert match, (path, label)
        return int(float(match[1]))
    occupied = re.search(r'\|\s*Slice\s*\|\s*([\d.]+)', report)
    if need_slices:
        assert occupied, (path, 'Slice')
    return dict(LUT=get('Slice LUTs'), FF=get('Slice Registers'), DSP=get('DSPs'),
                RAMB18=get('RAMB18'), RAMB36=get('RAMB36/FIFO*'),
                occupied_slices=int(float(occupied[1])) if occupied else None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tops', nargs='+')
    parser.add_argument('--target', type=float, default=6.0)
    parser.add_argument('--min-free-gib', type=float, default=2.3)
    args = parser.parse_args()
    assert args.target == 6.0 and args.min_free_gib >= 2.3
    R.mkdir(exist_ok=True)
    pin = hashes()
    assert pin['../guard_add.sv'] == REFERENCE_CORE_SHA
    summary = R / 'retime_hardware.json'
    rows = json.loads(summary.read_text()) if summary.exists() else []
    for top in args.tops:
        assert hashes() == pin, 'Queue sources changed'
        checks = functional(top, pin)
        provenance = hashlib.sha256(json.dumps(dict(
            top=top, engine=TOPS[top], variant=VARIANTS[top], target_ns=args.target, sources=pin, checks=checks,
            part='xc7a100tcsg324-1', hd_clk_src='BUFGCTRL_X0Y0'), sort_keys=True).encode()).hexdigest()
        previous = next((row for row in rows if row['top'] == top
                         and row['provenance_sha256'] == provenance), None)
        if previous:
            artifact_pins = previous['route_artifact_sha256']
            assert artifact_pins and all(sha(P / name) == stamp for name, stamp in artifact_pins.items()), 'Saved route artifacts changed'
            print('Already complete', top, flush=True)
            continue
        memory = free()
        print(top, 'free GiB', round(memory, 2), flush=True)
        assert memory > args.min_free_gib, 'Insufficient free RAM'
        temporary = R / 'retime_tmp'
        temporary.mkdir(exist_ok=True)
        env = os.environ.copy()
        env['TEMP'] = str(temporary)
        env['TMP'] = str(temporary)
        pre = R / f'{top}_synth'
        pre_pin = pre / 'provenance.txt'
        # A stale checkpoint cannot authorize resume of this fresh attempt.
        if pre_pin.exists():
            pre_pin.unlink()
        started = time.time()
        retried = False
        for attempt in range(2):
            assert hashes() == pin, 'Source changed before Vivado'
            suffix = '_resume' if attempt else ''
            log = R / f'{top}{suffix}_build.log'
            command = [str(VIVADO), '-mode', 'batch', '-log', f'results/{top}{suffix}_vivado.log',
                       '-journal', f'results/{top}{suffix}_vivado.jou', '-source', 'route_guard_add_retime.tcl',
                       '-tclargs', top, str(args.target), provenance, 'resume' if attempt else 'fresh']
            with log.open('w') as output:
                result = subprocess.run(subprocess.list2cmdline(command), shell=True, cwd=P,
                                        env=env, stdout=output, stderr=subprocess.STDOUT)
            if result.returncode == 0:
                break
            failure = log.read_text()
            valid_resume = (pre / 'design.dcp').exists() and pre_pin.exists() and pre_pin.read_text().strip() == provenance
            if attempt == 0 and 'ERROR: [Synth 20-411]' in failure and valid_resume:
                retried = True
                continue
            raise RuntimeError(failure[-5000:])
        assert hashes() == pin and functional(top, pin) == checks, 'Source/evidence changed during route'
        assert f'GUARD_ADD_RETIME_TIMING_ROUTED {top}' in log.read_text(), 'Missing route completion marker'
        dest = R / f'{top}_route'
        assert (dest / 'provenance.txt').read_text().splitlines()[0] == provenance
        full, core = util(dest / 'util.rpt'), util(dest / 'core_util.rpt', False)
        accounting = {key: int(value) for key, value in (
            line.split() for line in (dest / 'fixture_accounting.txt').read_text().splitlines())}
        assert accounting['launch_FF'] == 138 and accounting['capture_FF'] == 81 and accounting['fixture_FF'] == 219
        assert full['FF'] - core['FF'] == 219 and full['LUT'] == core['LUT'] and full['DSP'] == core['DSP'] == (1 if TOPS[top] == 2 else 0)
        assert full['occupied_slices'] == accounting['full_occupied_slices']
        core['occupied_slices_reported'] = core['occupied_slices']
        core['occupied_slices'] = accounting['core_slices_touched']
        slack = list(map(float, (dest / 'slack.txt').read_text().splitlines()))
        boundary = list(map(float, (dest / 'boundary_slack.txt').read_text().splitlines()))
        assert len(slack) == len(boundary) == 2
        row = dict(top=top, engine=TOPS[top], variant=VARIANTS[top], target_ns=args.target, core=core, full_fixture=full,
                   fixture_overhead=dict(LUT=0, FF=219, DSP=0), slice_accounting=accounting,
                   WNS_ns=slack[0], WHS_ns=slack[1], boundary_WNS_ns=boundary[0], boundary_WHS_ns=boundary[1],
                   source_sha256=pin, functional_check_sha256=checks, provenance_sha256=provenance,
                   route_artifact_sha256={str(path.relative_to(P)): sha(path)
                                          for folder in (pre, dest) for path in sorted(folder.rglob('*')) if path.is_file()},
                   hd_clk_src='BUFGCTRL_X0Y0', retried_checkpoint=retried,
                   seconds=round(time.time() - started, 1),
                   scope='Exact retimed fixed guard-add baseline in matched 219-FF registered OOC fixture; '
                         'same always-six operation and four-advance contract; '
                         'no board, memory, power or complete neuron-update measurement')
        rows = [old for old in rows if old['top'] != top] + [row]
        summary.write_text(json.dumps(rows, indent=2))
        print(json.dumps(row), flush=True)


if __name__ == '__main__':
    main()
