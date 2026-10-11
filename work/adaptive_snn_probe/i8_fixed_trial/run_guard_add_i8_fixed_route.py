"""Serial matched statically-I8 fixed routes, gated by all four exact RTL variants.

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
FUNCTIONAL_SOURCES = ['guard_add_i8_fixed.sv', 'tb_guard_add_i8_fixed.sv',
                      'check_guard_add_i8_fixed.py', 'check_guard_add_i8_fixed_snn.py',
                      '../guard_add.sv', '../check_guard_add.py',
                      '../common_layout_trial/guard_add_selective.sv',
                      '../baseline_retime_trial/guard_add_retime.sv']
SOURCES = FUNCTIONAL_SOURCES + ['guard_add_i8_fixed_timing.sv',
                                'route_guard_add_i8_fixed.tcl', 'run_guard_add_i8_fixed_route.py',
                                'CONTRACT.md', '../common_layout_trial/common_i8_current_bounds.json',
                                '../common_layout_trial/screen_common_adaptation.py']
TOPS = dict(top_guard_add_i8_fixed_hybrid=2, top_guard_add_i8_fixed_lut=3)
VARIANTS = dict(top_guard_add_i8_fixed_hybrid=0, top_guard_add_i8_fixed_lut=1)
SUITES = ['i8_fixed_main_0_checks.json', 'i8_fixed_main_1_checks.json',
          'i8_fixed_models_0_checks.json', 'i8_fixed_models_1_checks.json']
MODEL_INPUTS = ['adaptive_delta_model_25_1/expected.npz', 'adaptive_delta_model_input.json']
REFERENCE_CORE_SHA = 'f89019a87185b046a95819f70cf0c9d83f2fe20ee0a5a0e253a2702e9629a907'
SELECTIVE_CORE_SHA = 'b5c7d724d642b2310c4e447eabccaf965a3aa520aaf2e04c5f93accd5dbb9e48'
RETIME_CORE_SHA = '0409a89ead96866abee93ee4829210eb093d682a886a847bbf22557e1bd14efc'
ORACLE_SHA = '1c7212164c029217679c8348427204c80b855c99b5b4b16d05ecdcf8f53aa834'
CURRENT_CERT_SHA = '56e7108c543591468036defcdde54eb6189a064264396d8d4a5a05fe24f7c0ec'


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


def current_certificate(model_pins):
    """Pin the saved-model I8 domain proof and all of its input artifacts."""
    certificate_name = '../common_layout_trial/common_i8_current_bounds.json'
    script_name = '../common_layout_trial/screen_common_adaptation.py'
    stamp = sha(P / certificate_name)
    assert stamp == CURRENT_CERT_SHA, 'Frozen all-spike I8 certificate changed'
    data = json.loads((P / certificate_name).read_text())
    evidence = {certificate_name: stamp, script_name: sha(P / script_name)}
    assert data['script_sha256'] == evidence[script_name]
    assert data['model_input_sha256'] == model_pins and data['failures'] == 0
    assert sorted((row['seed'], row['layer']) for row in data['rows']) == [
        (seed, layer) for seed in range(3) for layer in range(2)]
    for row in data['rows']:
        assert row['all_neuron_binary_spike_currents_fit_signed8'] is True
        assert -128 <= row['minimum_current'] <= row['maximum_current'] <= 127
    for name, stamp in data['weight_files_sha256'].items():
        path = f'../results/{name}'
        assert sha(P / path) == stamp, (path, 'Certified saved weights changed')
        evidence[path] = stamp
    assert sorted(data['weight_files_sha256']) == [f'model_seed{seed}.npz' for seed in range(3)]
    for name, stamp in data['prior_bound_artifact_sha256'].items():
        path = f'../{name}'
        assert sha(P / path) == stamp, (path, 'Prior bound artifact changed')
        evidence[path] = stamp
    assert evidence == {name: sha(P / name) for name in evidence}
    return evidence


def functional(top, pin):
    assert top in TOPS, ('Unknown matched statically-I8 baseline top', top)
    assert pin['../guard_add.sv'] == REFERENCE_CORE_SHA, 'Measured original reference core changed'
    assert pin['../common_layout_trial/guard_add_selective.sv'] == SELECTIVE_CORE_SHA
    assert pin['../baseline_retime_trial/guard_add_retime.sv'] == RETIME_CORE_SHA
    assert pin['../check_guard_add.py'] == ORACLE_SHA
    expected = [0, 1, 2, 3]
    source_pins = {name: pin[name] for name in FUNCTIONAL_SOURCES}
    model_pins = {name: sha(ORIGINAL_RESULTS / name) for name in MODEL_INPUTS}
    evidence = {}
    model_archives = {}
    for name in SUITES:
        data = json.loads((R / name).read_text())
        assert data['source_hashes'] == source_pins, (name, 'Functional source pins differ')
        assert data['tested_variants'] == data['expected_variants'] == expected, name
        assert data['reference_variants'] == [2, 3], name
        assert sorted(row['variant'] for row in data['rows']) == expected, name
        assert data['frames'] > 0 and data['acceptance_to_handshake_preceding_advances'] == 4, name
        assert data['profile'] == 1 and data['tested_core_engines'] == [2, 3], name
        assert data['operand_domain'] == 'signed11 U, sign-extended signed8 I', name
        assert data['integer_operation'] == 'exact signed12 U+I', name
        assert data['advance_convention'] == (
            'Pre-edge step stored at acceptance; acceptance edge counted, handshake edge not yet counted.'), name
        assert data['backpressure'] == name.endswith('_1_checks.json'), name
        assert data['outputs_byte_identical'] is True and data['fixed_outputs_byte_identical'] is True, name
        assert data['numeric_outputs_order_identical'] is True and data['physical_clock_columns_identical'] is True, name
        assert data['source_frames_match_original_archive'] is True and data['matched_archived_fixed_retirement'] is True, name
        tag = name.removesuffix('_checks.json')
        stimulus = f'{tag}/stream_stim.txt'
        assert data['stimulus_file'] == stimulus and sha(R / stimulus) == data['stimulus_sha256'], name
        match = re.fullmatch(r'i8_fixed_(main|models)_([01])_checks.json', name)
        assert match, name
        kind, stall = match[1], int(match[2])
        original_tag = f'guard_add_{kind}_{stall}'
        assert sha(ORIGINAL_RESULTS / original_tag / 'stream_stim.txt') == data['original_stimulus_sha256'], name
        archived = data['archive_reference']
        archived_tag = f'selective_{kind}_p1_{stall}'
        assert archived['check_file'] == str(Path('common_layout_trial') / 'results' / f'{archived_tag}_checks.json'), name
        assert archived['stimulus_file'] == str(Path('common_layout_trial') / 'results' / archived_tag / 'stream_stim.txt'), name
        assert archived['output_file'] == str(Path('common_layout_trial') / 'results' / archived_tag / 'stream_out0.txt'), name
        for artifact, pin_key in (('check_file', 'check_sha256'), ('stimulus_file', 'stimulus_sha256'), ('output_file', 'output_sha256')):
            assert sha(P.parent / archived[artifact]) == archived[pin_key], (name, artifact)
        old_data = json.loads((P.parent / archived['check_file']).read_text())
        assert old_data['profile'] == 1 and old_data['backpressure'] == bool(stall), name
        assert old_data['source_hashes'] == archived['source_hashes'], name
        for path, stamp in archived['source_hashes'].items():
            assert sha(P.parent / 'common_layout_trial' / path) == stamp, (name, path)
        old_row = next(row for row in old_data['rows'] if row['variant'] == 0)
        assert archived['local_variant'] == 0 and archived['frozen_core_variant'] == old_row['core_variant'] == 2, name
        assert old_row['mismatches'] == old_row['correction_freezes'] == old_row['correction_steps'] == 0, name
        assert old_row['output_sha256'] == archived['output_sha256'], name
        assert old_data['stimulus_sha256'] == archived['stimulus_sha256'] == data['stimulus_sha256'], name
        if kind == 'models':
            assert data['model_input_sha256'] == model_pins and data['frames'] == 9216, name
            assert data['validation_kind'] == 'saved_model_addition_replay', name
            assert data['stress_current_transform'] == 'identity' and data['matched_original_stimulus'] is True, name
            assert data['original_stimulus_sha256'] == data['stimulus_sha256'], name
            assert old_data['model_input_sha256'] == model_pins, name
            model_archives[str(stall)] = archived
            neurons = 635904
        else:
            assert data['model_input_sha256'] is None, name
            assert data['validation_kind'] == 'full_integer_stress', name
            assert data['stress_current_transform'] == old_data['stress_current_transform'] == 'signed8((I+128)%256-128)', name
            assert data['matched_original_stimulus'] is False, name
            neurons = 811511
        assert len({row['output_sha256'] for row in data['rows']}) == 1, name
        assert len({row['numeric_retirement_sha256'] for row in data['rows']}) == 1, name
        assert len({row['clocks'] for row in data['rows']}) == 1, name
        for row in data['rows']:
            assert row['mismatches'] == 0 and row['neurons'] == neurons, (name, row)
            variant = row['variant']
            assert row['core_engine'] == (variant+2 if variant < 2 else None), (name, row)
            assert row['reference_core_variant'] == (2 if variant == 2 else None), (name, row)
            assert row['reference_engine'] == (2 if variant == 3 else None), (name, row)
            assert row['arithmetic_issues'] == (row['requests'] if variant != 1 else 0), (name, row)
            assert row['correction_freezes'] == row['correction_steps'] == 0, (name, row)
            assert row['latency_checks'] == row['requests'] > 0, (name, row)
            assert row['directed_boundary_cases'] == 12, (name, row)
            assert sha(R / tag / f'stream_out{variant}.txt') == row['output_sha256'] == archived['output_sha256'], (name, variant)
            histogram = {int(k): value for k, value in row['physical_latency_histogram'].items()}
            assert histogram and sum(histogram.values()) == row['requests'] and min(histogram) >= 4, (name, row)
            assert row['physical_latency_min'] == min(histogram) and row['physical_latency_max'] == max(histogram), (name, row)
            if not stall:
                assert histogram == {4: row['requests']}, (name, row)
            else:
                assert row['input_stall_checks'] > 0 and row['output_stall_checks'] > 0, (name, row)
            for key in ('requests', 'neurons', 'clocks', 'input_stall_checks', 'output_stall_checks',
                        'physical_latency_histogram', 'output_sha256', 'numeric_retirement_sha256'):
                assert row[key] == old_row[key], (name, variant, key)
            if kind == 'models':
                assert row['requests'] == 110592, (name, row)
            if name == 'i8_fixed_models_0_checks.json':
                assert row['clocks'] == row['requests'] + 4, (name, row)
        evidence[name] = sha(R / name)

    name = 'i8_fixed_snn_checks.json'
    data = json.loads((R / name).read_text())
    assert data['source_hashes'] == source_pins, 'SNN replay source pins differ'
    assert data['reconstruction_script_sha256'] == pin['check_guard_add_i8_fixed_snn.py']
    assert data['tested_variants'] == expected
    assert data['tested_profiles'] == [1] and data['tested_core_engines'] == [2, 3]
    assert data['model_input_sha256'] == model_pins
    assert data['archive_references'] == model_archives
    assert data['functional_check_sha256'] == {
        name: evidence[name] for name in ('i8_fixed_models_0_checks.json', 'i8_fixed_models_1_checks.json')}
    assert data['reference_hashes'] == dict(ledger=model_pins[MODEL_INPUTS[1]],
                                          raw_membranes=model_pins[MODEL_INPUTS[0]])
    assert sorted((row['variant'], row['backpressure']) for row in data['rows']) == [
        (variant, backpressure) for variant in expected for backpressure in (False, True)]
    for row in data['rows']:
        assert row['state_mismatches'] == row['spike_mismatches'] == 0 and row['neurons'] == 635904, row
        assert row['spike_counts_matched'] is True and row['classifications_matched'] is True, row
        assert len(row['model_rows']) == 3 and sorted(model['seed'] for model in row['model_rows']) == [0, 1, 2], row
        assert all(model['images'] == 48 and model['spike_counts_matched'] and model['classifications_matched']
                   for model in row['model_rows']), row
    output_paths = {str(Path('results') / f'i8_fixed_models_{backpressure}' / f'stream_out{variant}.txt')
                    for variant in expected for backpressure in (0, 1)}
    assert set(data['output_hashes']) == output_paths, 'Expected eight SNN replay outputs'
    for path, stamp in data['output_hashes'].items():
        assert sha(P / path) == stamp, (path, 'SNN replay output pin differs')
    evidence[name] = sha(R / name)
    current_certificate(model_pins)
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
    summary = R / 'i8_fixed_hardware.json'
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
        temporary = R / 'i8_fixed_tmp'
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
                       '-journal', f'results/{top}{suffix}_vivado.jou', '-source', 'route_guard_add_i8_fixed.tcl',
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
        assert f'GUARD_ADD_I8_FIXED_TIMING_ROUTED {top}' in log.read_text(), 'Missing route completion marker'
        dest = R / f'{top}_route'
        provenance_lines = (dest / 'provenance.txt').read_text().splitlines()
        assert provenance_lines[0] == provenance
        provenance_fields = dict(line.split(maxsplit=1) for line in provenance_lines[1:])
        assert provenance_fields['TOP'] == top and float(provenance_fields['TARGET_NS']) == args.target
        assert provenance_fields['VIVADO'] == '2025.2' and provenance_fields['HD_CLK_SRC'] == 'BUFGCTRL_X0Y0'
        assert pre_pin.read_text().strip() == provenance
        full, core = util(dest / 'util.rpt'), util(dest / 'core_util.rpt', False)
        accounting = {key: int(value) for key, value in (
            line.split() for line in (dest / 'fixture_accounting.txt').read_text().splitlines())}
        assert accounting['launch_FF'] == 138 and accounting['capture_FF'] == 81 and accounting['fixture_FF'] == 219
        assert full['FF'] - core['FF'] == 219 and full['LUT'] == core['LUT'] and full['DSP'] == core['DSP'] == (1 if TOPS[top] == 2 else 0)
        assert full['occupied_slices'] == accounting['full_occupied_slices']
        assert accounting['full_occupied_slices'] == (accounting['core_slices_touched'] +
                                                     accounting['fixture_slices_touched'] - accounting['shared_slices'])
        assert accounting['core_exclusive_slices'] == accounting['core_slices_touched'] - accounting['shared_slices']
        assert accounting['fixture_exclusive_slices'] == accounting['fixture_slices_touched'] - accounting['shared_slices']
        assert all(value >= 0 for value in accounting.values())
        core['occupied_slices_reported'] = core['occupied_slices']
        core['occupied_slices'] = accounting['core_slices_touched']
        slack = list(map(float, (dest / 'slack.txt').read_text().splitlines()))
        boundary = list(map(float, (dest / 'boundary_slack.txt').read_text().splitlines()))
        assert len(slack) == len(boundary) == 2
        row = dict(top=top, engine=TOPS[top], variant=VARIANTS[top], target_ns=args.target, core=core, full_fixture=full,
                   current_contract='signed8', operation='exact signed11 U + signed8 I -> signed12',
                   fixture_overhead=dict(LUT=0, FF=219, DSP=0), slice_accounting=accounting,
                   WNS_ns=slack[0], WHS_ns=slack[1], boundary_WNS_ns=boundary[0], boundary_WHS_ns=boundary[1],
                   source_sha256=pin, functional_check_sha256=checks, provenance_sha256=provenance,
                   route_artifact_sha256={str(path.relative_to(P)): sha(path)
                                          for folder in (pre, dest) for path in sorted(folder.rglob('*')) if path.is_file()},
                   hd_clk_src='BUFGCTRL_X0Y0', retried_checkpoint=retried,
                   seconds=round(time.time() - started, 1),
                   scope='Exact statically-I8 retimed fixed baseline in matched 219-FF registered OOC fixture; '
                         'same always-six operation and four-advance contract; '
                         'no board, memory, power or complete neuron-update measurement')
        rows = [old for old in rows if old['top'] != top] + [row]
        summary.write_text(json.dumps(rows, indent=2))
        print(json.dumps(row), flush=True)


if __name__ == '__main__':
    main()
