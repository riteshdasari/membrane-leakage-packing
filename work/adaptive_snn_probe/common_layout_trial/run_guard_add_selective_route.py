"""Serial matched selective exact-correction routes, gated by eight full RTL suites.

This imports safely without launching tools. Four tops use the same 219-FF
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
FUNCTIONAL_SOURCES = ['guard_add_selective.sv', 'tb_guard_add_selective.sv',
                      'check_guard_add_selective.py', 'check_guard_add_selective_snn.py',
                      'guard_add_common.sv', '../guard_add.sv', '../check_guard_add.py',
                      '../baseline_retime_trial/guard_add_retime.sv']
SOURCES = FUNCTIONAL_SOURCES + ['guard_add_selective_timing.sv',
                                'route_guard_add_selective.tcl', 'run_guard_add_selective_route.py']
TOPS = {f'top_guard_add_selective_v{variant}': variant for variant in range(4)}
VARIANTS = dict(TOPS)
SUITES = [f'selective_{kind}_p{profile}_{stall}_checks.json'
          for kind in ('main', 'models') for profile in (0, 1) for stall in (0, 1)]
MODEL_INPUTS = ['adaptive_delta_model_25_1/expected.npz', 'adaptive_delta_model_input.json']
REFERENCE_CORE_SHA = 'f89019a87185b046a95819f70cf0c9d83f2fe20ee0a5a0e253a2702e9629a907'
SELECTIVE_CORE_SHA = 'b5c7d724d642b2310c4e447eabccaf965a3aa520aaf2e04c5f93accd5dbb9e48'


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
    assert top in TOPS, ('Unknown matched selective-correction top', top)
    assert pin['../guard_add.sv'] == REFERENCE_CORE_SHA, 'Measured original reference core changed'
    assert pin['guard_add_selective.sv'] == SELECTIVE_CORE_SHA, 'Frozen selective core changed'
    expected = [0, 1, 2, 3]
    source_pins = {name: pin[name] for name in FUNCTIONAL_SOURCES}
    model_pins = {name: sha(ORIGINAL_RESULTS / name) for name in MODEL_INPUTS}
    evidence = {}
    suite_data = {}
    for name in SUITES:
        data = json.loads((R / name).read_text())
        match = re.fullmatch(r'selective_(main|models)_p([01])_([01])_checks.json', name)
        assert match, name
        kind, profile, stall = match[1], int(match[2]), int(match[3])
        neurons = 635904 if kind == 'models' else 811511
        assert data['source_hashes'] == source_pins, (name, 'Functional source pins differ')
        assert data['tested_variants'] == data['expected_variants'] == expected, name
        assert data['tested_core_variants'] == [2*profile, 2*profile+1], name
        assert data['reference_variants'] == [2, 3], name
        assert sorted(row['variant'] for row in data['rows']) == expected, name
        assert data['profile'] == profile and data['backpressure'] == bool(stall), name
        assert data['frames'] > 0 and data['acceptance_to_handshake_preceding_advances'] == 4, name
        assert data['advance_convention'] == (
            'Pre-edge step stored at acceptance; acceptance edge counted, handshake edge not yet counted. '
            'Internal correction freezes do not advance.'), name
        assert data['fixed_outputs_byte_identical'] is True and data['numeric_outputs_order_identical'] is True, name
        assert data['source_frames_match_original_archive'] is True, name
        assert data['operand_domain'] == ('signed11 U, sign-extended signed8 I' if profile else
                                          'signed11 U, signed11 I'), name
        assert data['integer_operation'] == 'exact signed12 U+I', name
        tag = name.removesuffix('_checks.json')
        stimulus = f'{tag}/stream_stim.txt'
        assert data['stimulus_file'] == stimulus and sha(R / stimulus) == data['stimulus_sha256'], name
        original_tag = f'guard_add_{kind}_{stall}'
        assert sha(ORIGINAL_RESULTS / original_tag / 'stream_stim.txt') == data['original_stimulus_sha256'], name
        if profile and kind == 'main':
            assert data['stress_current_transform'] == 'signed8((I+128)%256-128)', name
            assert data['matched_original_stimulus'] is False, name
        else:
            assert data['stress_current_transform'] == 'identity' and data['matched_original_stimulus'] is True, name
            assert data['original_stimulus_sha256'] == data['stimulus_sha256'], name
        if kind == 'models':
            assert data['model_input_sha256'] == model_pins and data['frames'] == 9216, name
            assert data['validation_kind'] == 'saved_model_addition_replay', name
            assert data['expected_exception_jobs'] == 1008 and data['expected_extra_correction_freezes'] == 114, name
        else:
            assert data['model_input_sha256'] is None, name
            assert data['validation_kind'] == 'full_integer_stress', name
        assert len({row['numeric_retirement_sha256'] for row in data['rows']}) == 1, name
        assert len({row['output_sha256'] for row in data['rows'] if row['variant'] != 1}) == 1, name
        fixed_rows = [row for row in data['rows'] if row['variant'] != 1]
        assert len({row['requests'] for row in data['rows']}) == 1, name
        assert len({row['clocks'] for row in fixed_rows}) == 1, name
        for row in data['rows']:
            assert row['mismatches'] == 0 and row['neurons'] == neurons, (name, row)
            variant = row['variant']
            assert row['core_variant'] == (variant+2*profile if variant < 2 else None), (name, row)
            assert row['reference_engine'] == (variant if variant >= 2 else None), (name, row)
            assert row['arithmetic_issues'] == (row['requests'] if row['variant'] != 3 else 0), (name, row)
            assert row['latency_checks'] == row['requests'] > 0, (name, row)
            assert row['correction_steps'] == (data['expected_exception_jobs'] if variant == 1 else 0), (name, row)
            assert row['expected_exception_jobs'] == row['correction_steps'], (name, row)
            assert row['correction_freezes'] == (data['expected_extra_correction_freezes'] if variant == 1 else 0), (name, row)
            assert 0 <= row['max_internal_correction_freeze_run'] <= 5, (name, row)
            assert (row['max_internal_correction_freeze_run'] > 0) == (row['correction_freezes'] > 0), (name, row)
            histogram = {int(k): v for k, v in row['physical_latency_histogram'].items()}
            assert histogram and sum(histogram.values()) == row['requests'] and min(histogram) >= 4, (name, row)
            assert min(histogram) == row['physical_latency_min'] and max(histogram) == row['physical_latency_max'], (name, row)
            if not stall and variant != 1:
                assert histogram == {4: row['requests']}, (name, row)
            if stall:
                assert row['input_stall_checks'] > 0 and row['output_stall_checks'] > 0, (name, row)
            assert sha(R / tag / f'stream_out{variant}.txt') == row['output_sha256'], (name, variant)
            if kind == 'models':
                assert row['requests'] == 110592, (name, row)
                if not stall:
                    assert row['clocks'] == row['requests'] + 4 + row['correction_freezes'], (name, row)
                    assert row['clocks'] == (110710 if variant == 1 else 110596), (name, row)
        evidence[name] = sha(R / name)
        suite_data[name] = data

    # The model currents are independently signed8-certified, so both operand
    # profiles must reproduce the same numerical and physical retirement trace.
    for stall in (0, 1):
        left = suite_data[f'selective_models_p0_{stall}_checks.json']
        right = suite_data[f'selective_models_p1_{stall}_checks.json']
        assert left['stimulus_sha256'] == right['stimulus_sha256']
        for a, b in zip(left['rows'], right['rows']):
            assert a['variant'] == b['variant']
            for key in ('requests', 'neurons', 'clocks', 'correction_steps', 'correction_freezes',
                        'physical_latency_histogram', 'output_sha256', 'numeric_retirement_sha256'):
                assert a[key] == b[key], ('Model profile mismatch', stall, a['variant'], key)

    name = 'selective_snn_checks.json'
    data = json.loads((R / name).read_text())
    assert data['source_hashes'] == source_pins, 'SNN replay source pins differ'
    assert data['reconstruction_script_sha256'] == pin['check_guard_add_selective_snn.py']
    assert data['tested_variants'] == expected
    assert data['tested_profiles'] == [0, 1] and data['tested_core_variants'] == expected
    assert data['functional_check_sha256'] == {
        name: evidence[name] for name in SUITES if name.startswith('selective_models_')}
    assert data['reference_hashes'] == dict(ledger=model_pins[MODEL_INPUTS[1]],
                                          raw_membranes=model_pins[MODEL_INPUTS[0]])
    assert sorted((row['profile'], row['variant'], row['backpressure']) for row in data['rows']) == [
        (profile, variant, backpressure) for profile in (0, 1)
        for variant in expected for backpressure in (False, True)]
    for row in data['rows']:
        assert row['state_mismatches'] == row['spike_mismatches'] == 0 and row['neurons'] == 635904, row
        assert len(row['model_rows']) == 3 and sorted(model['seed'] for model in row['model_rows']) == [0, 1, 2], row
        assert all(model['images'] == 48 and model['spike_counts_matched'] for model in row['model_rows']), row
        assert row['core_variant'] == (2*row['profile']+row['variant'] if row['variant'] < 2 else None), row
    output_paths = {str(Path('results') / f'selective_models_p{profile}_{backpressure}' / f'stream_out{variant}.txt')
                    for profile in (0, 1) for variant in expected for backpressure in (0, 1)}
    assert set(data['output_hashes']) == output_paths, 'Expected sixteen SNN replay outputs'
    for path, stamp in data['output_hashes'].items():
        assert sha(P / path) == stamp, (path, 'SNN replay output pin differs')
    evidence[name] = sha(R / name)
    evidence.update(policy_evidence(pin, model_pins))
    return evidence


def policy_evidence(pin, model_pins):
    """Gate the unchanged policy, model-domain proof, weights and source pins."""
    names = ['screen_common_adaptation.py', 'common_adaptation_policy_results.json',
             'common_i8_current_bounds.json', 'CONTRACT.md']
    stamps = {name: sha(P / name) for name in names}
    policy = json.loads((P / names[1]).read_text())
    certificate = json.loads((P / names[2]).read_text())
    assert policy['script_sha256'] == certificate['script_sha256'] == stamps[names[0]]
    assert policy['contract_sha256'] == stamps['CONTRACT.md']
    assert policy['oracle_sha256'] == pin['../check_guard_add.py']
    assert policy['arithmetic_proof']['full_signed11_pairs'] == 4194304
    assert policy['arithmetic_proof']['mismatches'] == policy['packed_stress']['mismatches'] == 0
    model = policy['models']
    assert model['model_input_sha256'] == certificate['model_input_sha256'] == model_pins
    assert model['frames'] == 9216 and model['scalars'] == 635904 and model['fixed6_windows'] == 110592
    assert model['reference_state_spike_mismatches'] == certificate['failures'] == 0
    artifact = model['static_current_certificate_artifact']
    assert artifact['path'] == names[2] and artifact['sha256'] == stamps[names[2]]
    assert artifact['bytes'] == (P / names[2]).stat().st_size
    assert all(certificate[key] == value for key, value in model['static_current_certificate'].items())
    assert sorted((row['seed'], row['layer']) for row in certificate['rows']) == [
        (seed, layer) for seed in range(3) for layer in range(2)]
    for row in certificate['rows']:
        assert row['all_neuron_binary_spike_currents_fit_signed8'] is True
        assert -128 <= row['minimum_current'] <= row['maximum_current'] <= 127
    weights = {f'model_seed{seed}.npz': sha(ORIGINAL_RESULTS / f'model_seed{seed}.npz') for seed in range(3)}
    assert certificate['weight_files_sha256'] == weights
    for name, stamp in weights.items():
        stamps[f'../results/{name}'] = stamp
    for name, stamp in certificate['prior_bound_artifact_sha256'].items():
        assert sha(P.parent / name) == stamp, (name, 'Archived bound evidence changed')
        stamps[f'../{name}'] = stamp
    variants = model['predicted_fused_global_freeze_variants']
    assert sorted(row['variant'] for row in variants) == [0, 1, 2, 3]
    for row in variants:
        shared = row['variant'] in (1, 3)
        assert row['shared_correction'] == shared
        assert row['current_contract'] == ('signed8' if row['variant'] >= 2 else 'signed11')
        assert row['declared_general_corrector_units'] == (1 if shared else 6)
        assert row['extra_globally_frozen_clocks'] == (114 if shared else 0)
        assert row['exceptional_fallback_jobs'] == (1008 if shared else 0)
        assert row['predicted_service_clocks'] == (110710 if shared else 110596)
        assert row['cycle_model']['service_clocks'] == row['predicted_service_clocks']
        assert row['cycle_model']['global_freeze_clocks'] == row['extra_globally_frozen_clocks']
        assert row['cycle_model']['repeated_or_out_of_order_retirements'] == 0
    assert stamps == {name: sha(P / name) for name in stamps}, 'Policy proof changed while validating'
    return stamps


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
    summary = R / 'selective_hardware.json'
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
        temporary = R / 'selective_tmp'
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
                       '-journal', f'results/{top}{suffix}_vivado.jou', '-source', 'route_guard_add_selective.tcl',
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
        assert f'GUARD_ADD_SELECTIVE_TIMING_ROUTED {top}' in log.read_text(), 'Missing route completion marker'
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
        assert full['FF'] - core['FF'] == 219 and full['LUT'] == core['LUT'] and full['DSP'] == core['DSP'] == 1
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
                   current_contract='signed8' if TOPS[top] >= 2 else 'signed11',
                   shared_correction=TOPS[top] in (1, 3),
                   fixture_overhead=dict(LUT=0, FF=219, DSP=0), slice_accounting=accounting,
                   WNS_ns=slack[0], WHS_ns=slack[1], boundary_WNS_ns=boundary[0], boundary_WHS_ns=boundary[1],
                   source_sha256=pin, functional_check_sha256=checks, provenance_sha256=provenance,
                   route_artifact_sha256={str(path.relative_to(P)): sha(path)
                                          for folder in (pre, dest) for path in sorted(folder.rglob('*')) if path.is_file()},
                   hd_clk_src='BUFGCTRL_X0Y0', retried_checkpoint=retried,
                   seconds=round(time.time() - started, 1),
                   scope='Exact fixed or selective high-part correction in matched 219-FF registered OOC fixture; '
                         'immutable six-lane DSP layout, four preceding pipeline advances; '
                         'shared variants may add physical correction-freeze clocks; '
                         'no board, memory, power or complete neuron-update measurement')
        rows = [old for old in rows if old['top'] != top] + [row]
        summary.write_text(json.dumps(rows, indent=2), encoding='utf-8')
        print(json.dumps(row), flush=True)


if __name__ == '__main__':
    main()
