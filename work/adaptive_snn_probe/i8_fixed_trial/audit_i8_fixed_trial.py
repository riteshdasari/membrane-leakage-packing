"""Independent read-only checks for the matched signed8-current trial.

No simulator, synthesis, route, model download or file mutation is performed.
Use --functional for stream arithmetic/provenance checks, --routes for source,
report and fixture checks, and --publication to rehash the final manifest.
The functional audit uses Python integer addition and independently parses the
stimulus, instead of importing the layout oracle or the experiment checker.
"""
from pathlib import Path
from contextlib import ExitStack
import argparse
import hashlib
import json
import math
import re

P = Path(__file__).resolve().parent
R = P / 'results'
COMMON = P.parent / 'common_layout_trial'
ORIGINAL_R = P.parent / 'results'
OUTPUTS = P.parents[2] / 'outputs'
VARIANTS = [0, 1, 2, 3]
FUNCTIONAL_SOURCES = [
    'guard_add_i8_fixed.sv', 'tb_guard_add_i8_fixed.sv',
    'check_guard_add_i8_fixed.py', 'check_guard_add_i8_fixed_snn.py',
    '../common_layout_trial/guard_add_selective.sv',
    '../baseline_retime_trial/guard_add_retime.sv',
    '../guard_add.sv', '../check_guard_add.py',
]
ROUTE_SOURCES = FUNCTIONAL_SOURCES + [
    'guard_add_i8_fixed_timing.sv', 'route_guard_add_i8_fixed.tcl',
    'run_guard_add_i8_fixed_route.py', 'CONTRACT.md',
    '../common_layout_trial/common_i8_current_bounds.json',
    '../common_layout_trial/screen_common_adaptation.py',
]
FROZEN = {
    'guard_add_i8_fixed.sv': '1dbc500f27eb02f963474698ce754d87c5ed23ff1c9c9885282cca5d9f733420',
    'guard_add_i8_fixed_timing.sv': '6300175f4058b534f401685eb6aaf17987fae2f61b8d94a32b95d5f3e396bcd0',
    'route_guard_add_i8_fixed.tcl': 'a6b2ecaebdbbe2739a497245b5ae4c2a8055843638d39241c1e7951ad3312833',
    '../common_layout_trial/guard_add_selective.sv': 'b5c7d724d642b2310c4e447eabccaf965a3aa520aaf2e04c5f93accd5dbb9e48',
    '../baseline_retime_trial/guard_add_retime.sv': '0409a89ead96866abee93ee4829210eb093d682a886a847bbf22557e1bd14efc',
    '../guard_add.sv': 'f89019a87185b046a95819f70cf0c9d83f2fe20ee0a5a0e253a2702e9629a907',
    '../check_guard_add.py': '1c7212164c029217679c8348427204c80b855c99b5b4b16d05ecdcf8f53aa834',
}
CERT_SHA = '56e7108c543591468036defcdde54eb6189a064264396d8d4a5a05fe24f7c0ec'


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1048576), b''):
            digest.update(chunk)
    return digest.hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def source_pins(names):
    pins = {name: sha(P / name) for name in names}
    for name, stamp in FROZEN.items():
        if name in pins:
            assert pins[name] == stamp, ('Frozen source changed', name)
    return pins


def signed11(word):
    assert 0 <= word < 2048
    return word - 2048 if word >= 1024 else word


def same_file(left, right):
    with left.open('rb') as first, right.open('rb') as second:
        while True:
            block = first.read(1048576)
            assert block == second.read(1048576), ('Bytes differ', left, right)
            if not block:
                break


def compare_stimulus(current, original, model):
    """Check U/header identity and independently apply the declared stress map."""
    with current.open() as new, original.open() as old:
        frames = int(new.readline())
        assert frames == int(old.readline()) > 0
        neurons = 0
        for _ in range(frames):
            header = tuple(map(int, new.readline().split()))
            assert len(header) == 2 and header == tuple(map(int, old.readline().split()))
            count, gap = header
            assert 1 <= count <= 4096 and gap >= 0
            for _ in range(count):
                u_new, i_new = (int(word, 16) for word in new.readline().split())
                u_old, i_old = (int(word, 16) for word in old.readline().split())
                old_i = signed11(i_old)
                desired_i = old_i if model else ((old_i + 128) % 256) - 128
                assert u_new == u_old and i_new == (desired_i & 2047)
                assert -128 <= signed11(i_new) <= 127
                neurons += 1
        assert not new.read().strip() and not old.read().strip()
    return frames, neurons


def expected_windows(stimulus):
    with stimulus.open() as stream:
        frames = int(stream.readline())
        for fid in range(frames):
            count, gap = map(int, stream.readline().split())
            assert 1 <= count <= 4096 and gap >= 0
            for pos in range(0, count, 6):
                lanes = min(6, count - pos)
                packed = 0
                for lane in range(lanes):
                    u, current = (signed11(int(word, 16)) for word in stream.readline().split())
                    assert -128 <= current <= 127
                    answer = u + current
                    assert -1152 <= answer <= 1150
                    packed |= (answer & 4095) << (12 * lane)
                yield fid, pos, lanes, packed
        assert not stream.read().strip()


def certificate():
    path = COMMON / 'common_i8_current_bounds.json'
    assert sha(path) == CERT_SHA
    data = read(path)
    assert data['failures'] == 0
    assert sorted((row['seed'], row['layer']) for row in data['rows']) == [
        (seed, layer) for seed in range(3) for layer in range(2)]
    for row in data['rows']:
        assert row['all_neuron_binary_spike_currents_fit_signed8'] is True
        assert -128 <= row['minimum_current'] <= row['maximum_current'] <= 127
    assert sha(COMMON / 'screen_common_adaptation.py') == data['script_sha256']
    for name, stamp in data['weight_files_sha256'].items():
        assert sha(ORIGINAL_R / name) == stamp
    for name, stamp in data['model_input_sha256'].items():
        assert sha(ORIGINAL_R / name) == stamp
    for name, stamp in data['prior_bound_artifact_sha256'].items():
        assert sha(P.parent / name) == stamp
    return data


def functional():
    pins = source_pins(FUNCTIONAL_SOURCES)
    model_pins = certificate()['model_input_sha256']
    checked = 0
    suites = {}
    for kind in ('main', 'models'):
        for stall in (0, 1):
            tag = f'i8_fixed_{kind}_{stall}'
            path = R / f'{tag}_checks.json'
            data = read(path)
            assert data['source_hashes'] == pins
            assert data['tested_variants'] == data['expected_variants'] == VARIANTS
            assert data['profile'] == 1 and data['backpressure'] == bool(stall)
            assert data['reference_variants'] == [2, 3]
            assert data['acceptance_to_handshake_preceding_advances'] == 4
            assert data['integer_operation'] == 'exact signed12 U+I'
            assert data['operand_domain'] == 'signed11 U, sign-extended signed8 I'
            assert all(data[key] is True for key in (
                'fixed_outputs_byte_identical', 'outputs_byte_identical',
                'numeric_outputs_order_identical', 'physical_clock_columns_identical',
                'matched_archived_fixed_retirement', 'source_frames_match_original_archive'))
            assert data['stress_current_transform'] == (
                'identity' if kind == 'models' else 'signed8((I+128)%256-128)')
            assert data['model_input_sha256'] == (model_pins if kind == 'models' else None)
            assert data['stimulus_file'] == f'{tag}/stream_stim.txt'
            stimulus = R / data['stimulus_file']
            assert sha(stimulus) == data['stimulus_sha256']
            original = Path(data['original_stimulus_file'])
            assert sha(original) == data['original_stimulus_sha256']
            assert original.resolve() == (ORIGINAL_R / f'guard_add_{kind}_{stall}/stream_stim.txt').resolve()
            frames, neurons = compare_stimulus(stimulus, original, kind == 'models')
            assert data['frames'] == frames
            assert neurons == (635904 if kind == 'models' else 811511)
            assert data['matched_original_stimulus'] == (kind == 'models')
            archived = COMMON / 'results' / f'selective_{kind}_p1_{stall}'
            same_file(stimulus, archived / 'stream_stim.txt')
            archived_check = read(archived.parent / (archived.name + '_checks.json'))
            for name, stamp in archived_check['source_hashes'].items():
                assert sha(COMMON / name) == stamp
            archive_pin = data['archive_reference']
            for key in ('check', 'stimulus', 'output'):
                assert sha(P.parent / archive_pin[f'{key}_file']) == archive_pin[f'{key}_sha256']
            assert archive_pin['local_variant'] == 0 and archive_pin['frozen_core_variant'] == 2
            assert sorted(row['variant'] for row in data['rows']) == VARIANTS
            rows = {row['variant']: row for row in data['rows']}
            assert len({row['output_sha256'] for row in rows.values()}) == 1
            assert len({row['numeric_retirement_sha256'] for row in rows.values()}) == 1
            assert len({row['clocks'] for row in rows.values()}) == 1
            outputs = [R / tag / f'stream_out{variant}.txt' for variant in VARIANTS]
            same_file(outputs[0], archived / 'stream_out0.txt')
            for variant, output in zip(VARIANTS, outputs):
                assert sha(output) == rows[variant]['output_sha256']
                same_file(output, outputs[0])
                row = rows[variant]
                assert row['mismatches'] == row['correction_steps'] == row['correction_freezes'] == 0
                assert row['neurons'] == neurons and row['latency_checks'] == row['requests'] > 0
                assert row['directed_boundary_cases'] == 12
                assert row['arithmetic_issues'] == (0 if variant == 1 else row['requests'])
                if stall:
                    assert row['input_stall_checks'] > 0 and row['output_stall_checks'] > 0
                assert (row['core_engine'], row['reference_core_variant'], row['reference_engine']) == {
                    0: (2, None, None), 1: (3, None, None),
                    2: (None, 2, None), 3: (None, None, 2),
                }[variant]
            requests = 0
            first_accept = last_retire = None
            previous_accept = previous_retire = -1
            numeric = hashlib.sha256()
            latency_histogram = {}
            with ExitStack() as stack:
                streams = [stack.enter_context(output.open()) for output in outputs]
                for fid, pos, lanes, desired in expected_windows(stimulus):
                    lines = [stream.readline() for stream in streams]
                    assert lines[0] and all(line == lines[0] for line in lines)
                    words = lines[0].split()
                    assert len(words) == 8
                    actual_fid, actual_pos, actual_lanes, placeholder = map(int, words[:4])
                    packed = int(words[4], 16)
                    accepted, retired, mode = map(int, words[5:])
                    assert (actual_fid, actual_pos, actual_lanes, packed) == (fid, pos, lanes, desired)
                    assert placeholder == mode == 0
                    assert accepted > previous_accept and retired > previous_retire
                    assert retired - accepted >= 4
                    if not stall:
                        assert retired - accepted == 4
                    latency = retired - accepted
                    latency_histogram[str(latency)] = latency_histogram.get(str(latency), 0) + 1
                    numeric.update(f'{fid} {pos} {lanes} {packed:018x}\n'.encode('ascii'))
                    previous_accept, previous_retire = accepted, retired
                    if first_accept is None:
                        first_accept = accepted
                    last_retire = retired
                    requests += 1
                assert all(not stream.read().strip() for stream in streams)
            for row in rows.values():
                assert row['requests'] == requests
                assert row['clocks'] == last_retire - first_accept + 1
                assert row['numeric_retirement_sha256'] == numeric.hexdigest()
                assert row['physical_latency_histogram'] == latency_histogram
                assert row['physical_latency_min'] == min(map(int, latency_histogram))
                assert row['physical_latency_max'] == max(map(int, latency_histogram))
            if kind == 'models' and not stall:
                assert requests == 110592 and rows[0]['clocks'] == 110596
            assert 'GUARD_ADD_I8_FIXED PASS' in (R / tag / 'tool_3.log').read_text()
            checked += neurons * 4
            suites[path.name] = sha(path)
            print('FUNCTIONAL PASS', tag, neurons, 'pairs per variant', requests, 'requests')
    assert checked == 11579320
    snn_path = R / 'i8_fixed_snn_checks.json'
    snn = read(snn_path)
    assert snn['source_hashes'] == pins and snn['tested_variants'] == VARIANTS
    assert snn['reconstruction_script_sha256'] == pins['check_guard_add_i8_fixed_snn.py']
    assert snn['functional_check_sha256'] == {
        name: suites[name] for name in ('i8_fixed_models_0_checks.json', 'i8_fixed_models_1_checks.json')}
    assert snn['reference_hashes'] == dict(
        ledger=model_pins['adaptive_delta_model_input.json'],
        raw_membranes=model_pins['adaptive_delta_model_25_1/expected.npz'])
    assert sorted((row['variant'], row['backpressure']) for row in snn['rows']) == [
        (variant, backpressure) for variant in VARIANTS for backpressure in (False, True)]
    for row in snn['rows']:
        assert row['neurons'] == 635904 and row['state_mismatches'] == row['spike_mismatches'] == 0
        assert row['spike_counts_matched'] is True and row['classifications_matched'] is True
        assert sorted(model['seed'] for model in row['model_rows']) == [0, 1, 2]
        assert all(model['images'] == 48 and model['spike_counts_matched'] is True
                   and model['classifications_matched'] is True
                   for model in row['model_rows'])
    for name, stamp in snn['output_hashes'].items():
        assert sha(P / name) == stamp
    assert len(snn['output_hashes']) == 8
    assert source_pins(FUNCTIONAL_SOURCES) == pins
    print('SNN PIN AUDIT PASS: eight saved integer-reference replays; no new trained-accuracy claim')
    return checked


def util(path):
    text = path.read_text()
    labels = {'LUT': 'Slice LUTs', 'FF': 'Slice Registers', 'DSP': 'DSPs',
              'RAMB18': 'RAMB18', 'RAMB36': 'RAMB36/FIFO*'}
    result = {}
    for key, label in labels.items():
        match = re.search(r'\|\s*' + re.escape(label) + r'\*?\s*\|\s*([\d.]+)', text)
        assert match, (path, label)
        result[key] = int(float(match[1]))
    return result


def routes():
    pins = source_pins(ROUTE_SOURCES)
    summary = read(R / 'i8_fixed_hardware.json')
    expected = {'top_guard_add_i8_fixed_hybrid': (2, 0), 'top_guard_add_i8_fixed_lut': (3, 1)}
    assert len(summary) == 2 and {row['top'] for row in summary} == set(expected)
    for row in summary:
        engine, variant = expected[row['top']]
        assert (row['engine'], row['variant']) == (engine, variant)
        assert row['source_sha256'] == pins
        assert row['target_ns'] == 6.0 and row['hd_clk_src'] == 'BUFGCTRL_X0Y0'
        checks = row['functional_check_sha256']
        assert set(checks) == {
            f'i8_fixed_{kind}_{stall}_checks.json'
            for kind in ('main', 'models') for stall in (0, 1)
        } | {'i8_fixed_snn_checks.json'}
        for name, stamp in checks.items():
            path = P / name if name.startswith('../') else R / name
            assert sha(path) == stamp
        desired = hashlib.sha256(json.dumps(dict(
            top=row['top'], engine=engine, variant=variant, target_ns=6.0,
            sources=pins, checks=checks, part='xc7a100tcsg324-1',
            hd_clk_src='BUFGCTRL_X0Y0'), sort_keys=True).encode()).hexdigest()
        assert row['provenance_sha256'] == desired
        pre = R / (row['top'] + '_synth')
        dest = R / (row['top'] + '_route')
        assert (pre / 'provenance.txt').read_text().strip() == desired
        provenance_lines = (dest / 'provenance.txt').read_text().splitlines()
        assert provenance_lines[0] == desired
        assert dict(line.split(maxsplit=1) for line in provenance_lines[1:]) == {
            'TOP': row['top'], 'TARGET_NS': '6.0', 'VIVADO': '2025.2',
            'HD_CLK_SRC': 'BUFGCTRL_X0Y0'}
        artifacts = {str(path.relative_to(P)): path for folder in (pre, dest)
                     for path in folder.rglob('*') if path.is_file()}
        assert set(row['route_artifact_sha256']) == set(artifacts)
        for name, stamp in row['route_artifact_sha256'].items():
            assert sha(P / name) == stamp
        full, core = util(dest / 'util.rpt'), util(dest / 'core_util.rpt')
        for key in core:
            assert row['core'][key] == core[key] and row['full_fixture'][key] == full[key]
        assert full['FF'] - core['FF'] == 219
        assert full['LUT'] == core['LUT'] and full['DSP'] == core['DSP'] == (1 if variant == 0 else 0)
        assert all(counts['RAMB18'] == counts['RAMB36'] == 0 for counts in (full, core))
        assert row['fixture_overhead'] == {'LUT': 0, 'FF': 219, 'DSP': 0}
        accounting = dict((key, int(value)) for key, value in (
            line.split() for line in (dest / 'fixture_accounting.txt').read_text().splitlines()))
        assert accounting == row['slice_accounting']
        assert (accounting['launch_FF'], accounting['capture_FF'], accounting['fixture_FF']) == (138, 81, 219)
        assert accounting['core_slices_touched'] + accounting['fixture_slices_touched'] \
            - accounting['shared_slices'] == accounting['full_occupied_slices']
        for file, names in [('slack.txt', ('WNS_ns', 'WHS_ns')),
                            ('boundary_slack.txt', ('boundary_WNS_ns', 'boundary_WHS_ns'))]:
            values = list(map(float, (dest / file).read_text().splitlines()))
            assert len(values) == 2 and all(math.isfinite(value) for value in values)
            assert all(math.isclose(value, row[name], rel_tol=0, abs_tol=1e-9)
                       for value, name in zip(values, names))
        suffix = '_resume' if row['retried_checkpoint'] else ''
        if row['retried_checkpoint']:
            assert row['resume_helper_sha256'] == sha(P / 'resume_i8_fixed_route.py')
            assert row['resume_checkpoint_sha256'] == sha(pre / 'design.dcp')
        assert f"GUARD_ADD_I8_FIXED_TIMING_ROUTED {row['top']}" in (
            R / (row['top'] + suffix + '_build.log')).read_text()
        print('ROUTE PIN AUDIT PASS', row['top'], row['core'], row['WNS_ns'], row['WHS_ns'])
    assert source_pins(ROUTE_SOURCES) == pins


def publication():
    stem = 'membrane_i8_fixed_comparison_trial'
    manifest = read(OUTPUTS / (stem + '.manifest.json'))
    entries = manifest['evidence'] + manifest['deliverables']
    total = 0
    unique = set()
    for entry in entries:
        path = Path(entry['path'])
        assert path.resolve() not in unique
        unique.add(path.resolve())
        assert path.is_file() and path.stat().st_size == entry['bytes']
        assert sha(path) == entry['sha256']
        total += entry['bytes']
    assert {Path(entry['path']).resolve() for entry in manifest['deliverables']} == {
        (OUTPUTS / (stem + suffix)).resolve() for suffix in ('.md', '.summary.json')}
    assert P / 'audit_i8_fixed_trial.py' in unique and P / 'audit_notes.md' in unique
    print('PUBLICATION MANIFEST PASS', len(entries), 'files', total, 'bytes')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--functional', action='store_true')
    parser.add_argument('--routes', action='store_true')
    parser.add_argument('--publication', action='store_true')
    args = parser.parse_args()
    if not any((args.functional, args.routes, args.publication)):
        print('No tools launched; select completed evidence with --functional, --routes or --publication.')
        return
    if args.functional:
        functional()
    if args.routes:
        routes()
    if args.publication:
        publication()


if __name__ == '__main__':
    main()
