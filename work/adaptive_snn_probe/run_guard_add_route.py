"""Serial, RAM-gated routes for independently exact-checked guard-add kernels.

The registered OOC fixture has 219 preserved FFs, excluded from core resources.
It is not a production handshake adapter. Main setup/hold timing covers the
registered arithmetic and control paths; raw port budgets are audited separately.
Occupied SLICE sites overlap and are not additive. No board Fmax, power, memory
bandwidth, host latency, or full neuron-update latency follows from these routes.
Importing this module never launches a route or changes an evidence file.
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
V = Path('C:/AMDDesignTools/2025.2/Vivado/bin/vivado.bat')
SOURCES = ['guard_add.sv', 'tb_guard_add.sv', 'check_guard_add.py',
           'check_guard_add_snn.py', 'guard_add_timing.sv',
           'route_guard_add.tcl', 'run_guard_add_route.py']
ENGINES = dict(adaptive=0, fixed4=1, hybrid6=2, lut6=3)
MODEL_INPUTS = ['adaptive_delta_model_25_1/expected.npz',
                'adaptive_delta_model_input.json']
MAIN_CHECKS = ['guard_add_main_0_checks.json', 'guard_add_main_1_checks.json',
               'guard_add_models_0_checks.json', 'guard_add_models_1_checks.json']
FUNCTIONAL_SOURCES = ['guard_add.sv', 'tb_guard_add.sv', 'check_guard_add.py']


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


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
    match = re.fullmatch(r'top_guard_add_(adaptive|fixed4|hybrid6|lut6)', top)
    assert match and match[1] in ENGINES, ('Unknown guard-add top', top)
    evidence = {}
    expected_engines = list(range(4))
    functional_pins = {name: pin[name] for name in FUNCTIONAL_SOURCES}
    model_pins = {name: sha(R / name) for name in MODEL_INPUTS}
    for check in MAIN_CHECKS:
        data = json.loads((R / check).read_text())
        assert data['frames'] > 0 and data['acceptance_to_handshake_advances'] == 4, check
        assert data['tested_engines'] == data['expected_engines'] == expected_engines, check
        assert sorted(row['engine'] for row in data['rows']) == expected_engines, check
        assert data['source_hashes'] == functional_pins, (check, 'Source pin differs')
        assert data['backpressure'] == check.endswith('_1_checks.json'), check
        stimulus = check.removesuffix('_checks.json') + '/stream_stim.txt'
        assert data['stimulus_file'] == stimulus and sha(R / stimulus) == data['stimulus_sha256'], check
        if check.startswith('guard_add_models_'):
            assert data['frames'] == 9216 and data['model_input_sha256'] == model_pins, check
            assert data['validation_kind'] == 'saved_model_addition_replay', check
        else:
            assert data['model_input_sha256'] is None, check
            assert data['validation_kind'] == 'full_integer_stress', check
        for row in data['rows']:
            assert row['mismatches'] == 0 and row['neurons'] > 0, (check, row)
            assert row['latency_checks'] == row['requests'] > 0, (check, row)
            output = R / check.removesuffix('_checks.json') / f"stream_out{row['engine']}.txt"
            assert sha(output) == row['output_sha256'], (check, row['engine'], 'Output pin differs')
            if check == 'guard_add_models_0_checks.json':
                assert row['clocks'] == row['requests'] + 4, (check, row)
        evidence[check] = sha(R / check)

    snn_check = R / 'guard_add_snn_checks.json'
    data = json.loads(snn_check.read_text())
    assert data['source_hashes'] == functional_pins, 'SNN replay source pins differ'
    assert data['reconstruction_script_sha256'] == pin['check_guard_add_snn.py']
    assert data['reference_hashes'] == dict(ledger=model_pins[MODEL_INPUTS[1]],
                                          raw_membranes=model_pins[MODEL_INPUTS[0]])
    assert sorted((row['engine'], row['backpressure']) for row in data['rows']) == [
        (engine, backpressure) for engine in expected_engines for backpressure in (False, True)]
    for row in data['rows']:
        assert row['state_mismatches'] == row['spike_mismatches'] == 0 and row['neurons'] > 0, row
        assert len(row['model_rows']) == 3, row
        assert sorted(model['seed'] for model in row['model_rows']) == [0, 1, 2], row
        assert all(model['spike_counts_matched'] and model['images'] == 48
                   for model in row['model_rows']), row
    expected_outputs = {str(Path('results') / f'guard_add_models_{backpressure}' / f'stream_out{engine}.txt')
                        for backpressure in (0, 1) for engine in expected_engines}
    assert set(data['output_hashes']) == expected_outputs, 'Expected eight SNN replay outputs'
    for name, stamp in data['output_hashes'].items():
        assert sha(P / name) == stamp, (name, 'SNN replay output pin differs')
    evidence[snn_check.name] = sha(snn_check)
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
    summary = R / 'guard_add_hardware.json'
    rows = json.loads(summary.read_text()) if summary.exists() else []
    for top in args.tops:
        assert hashes() == pin, 'Queue source changed'
        checks = functional(top, pin)
        provenance = hashlib.sha256(json.dumps(dict(
            top=top, target_ns=args.target, sources=pin, checks=checks,
            part='xc7a100tcsg324-1', hd_clk_src='BUFGCTRL_X0Y0'), sort_keys=True).encode()).hexdigest()
        if any(row['top'] == top and row['provenance_sha256'] == provenance for row in rows):
            print('Already complete', top, flush=True)
            continue
        memory = free()
        print(top, 'free GiB', round(memory, 2), flush=True)
        assert memory > args.min_free_gib, 'Insufficient free RAM'
        temporary = R / 'guard_add_tmp'
        temporary.mkdir(exist_ok=True)
        env = os.environ.copy()
        env['TEMP'] = str(temporary)
        env['TMP'] = str(temporary)
        pre = R / f'{top}_synth'
        pre_pin = pre / 'provenance.txt'
        # Only a DCP written and pinned by this fresh attempt may be resumed.
        if pre_pin.exists():
            pre_pin.unlink()
        started = time.time()
        retried = False
        for attempt in range(2):
            assert hashes() == pin, 'Source changed before Vivado'
            tail = '_resume' if attempt else ''
            log = R / f'{top}{tail}_build.log'
            command = [str(V), '-mode', 'batch', '-log', f'results/{top}{tail}_vivado.log',
                       '-journal', f'results/{top}{tail}_vivado.jou', '-source', 'route_guard_add.tcl',
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
        assert hashes() == pin and functional(top, pin) == checks, 'Sources/evidence changed during route'
        dest = R / f'{top}_route'
        assert (dest / 'provenance.txt').read_text().splitlines()[0] == provenance
        full = util(dest / 'util.rpt')
        core = util(dest / 'core_util.rpt', False)
        accounting = {key: int(value) for key, value in (
            line.split() for line in (dest / 'fixture_accounting.txt').read_text().splitlines())}
        assert accounting['launch_FF'] == 138 and accounting['capture_FF'] == 81 and accounting['fixture_FF'] == 219
        assert full['FF'] - core['FF'] == 219 and full['LUT'] == core['LUT'] and full['DSP'] == core['DSP']
        assert full['occupied_slices'] == accounting['full_occupied_slices']
        core['occupied_slices_reported'] = core['occupied_slices']
        core['occupied_slices'] = accounting['core_slices_touched']
        slack = list(map(float, (dest / 'slack.txt').read_text().splitlines()))
        boundary = list(map(float, (dest / 'boundary_slack.txt').read_text().splitlines()))
        assert len(slack) == len(boundary) == 2
        row = dict(top=top, target_ns=args.target, core=core, full_fixture=full,
                   fixture_overhead=dict(LUT=0, FF=219, DSP=0), slice_accounting=accounting,
                   WNS_ns=slack[0], WHS_ns=slack[1],
                   boundary_WNS_ns=boundary[0], boundary_WHS_ns=boundary[1],
                   source_sha256=pin, functional_check_sha256=checks, provenance_sha256=provenance,
                   hd_clk_src='BUFGCTRL_X0Y0', retried_checkpoint=retried,
                   seconds=round(time.time() - started, 1),
                   scope='Exact signed membrane-plus-current kernel in registered OOC fixture; '
                         'no board, memory, power or full neuron-update latency measurement')
        rows = [old for old in rows if old['top'] != top] + [row]
        summary.write_text(json.dumps(rows, indent=2))
        print(json.dumps(row), flush=True)


if __name__ == '__main__':
    main()
