"""Publish the completed guard-add primitive trial after explicit --ready.

This reads current exact checks and all four routed fixtures; it never launches
RTL tools or modifies their sources. Large outputs/checkpoints are hashed in
chunks. The optional earlier masked snapshot is verified but remains unrouted.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import math

import run_guard_add_route as q

P = Path(__file__).resolve().parent
R = P / 'results'
O = P.parents[1] / 'outputs'
STEM = 'guarded_membrane_addition_trial'
TOPS = ['top_guard_add_adaptive', 'top_guard_add_fixed4',
        'top_guard_add_hybrid6', 'top_guard_add_lut6']
FINAL_CORE_SHA256 = 'f89019a87185b046a95819f70cf0c9d83f2fe20ee0a5a0e253a2702e9629a907'
LABELS = {0: 'Adaptive guarded DSP', 1: 'Native DSP four-lane + identity copies',
          2: 'Native DSP four-lane + two LUT lanes', 3: 'Six LUT lanes'}
REPORTS = ['util.rpt', 'hierarchical_util.rpt', 'core_util.rpt', 'timing.rpt',
           'paths_max.rpt', 'paths_min.rpt', 'launch_paths_max.rpt',
           'launch_paths_min.rpt', 'capture_paths_max.rpt', 'capture_paths_min.rpt',
           'slack.txt', 'design.dcp', 'fixture_accounting.txt', 'slice_sites.txt',
           'provenance.txt', 'boundary_timing.rpt', 'input_paths_max.rpt',
           'input_paths_min.rpt', 'output_paths_max.rpt', 'output_paths_min.rpt',
           'boundary_slack.txt']


def sha(path):
    return q.sha(path)


def read(path):
    return json.loads(path.read_text())


def link(path, label=None):
    return f'[{label or path.name}](<{path.resolve().as_posix()}>)'


def pct(value):
    return f'{100 * value:.2f}%'


def vector(row):
    core = row['core']
    return f"{core['LUT']} LUT / {core['FF']} FF / {core['DSP']} DSP"


def delta_vector(a, b):
    return ', '.join(f"{a['core'][key] - b['core'][key]:+d} {key}"
                     for key in ('LUT', 'FF', 'DSP'))


def close(a, b):
    return math.isclose(a, b, abs_tol=1e-9)


def validate():
    pin = q.hashes()
    assert pin['guard_add.sv'] == FINAL_CORE_SHA256, 'Expected final unmasked payload-capture source'
    # This gate checks all four engines, all four suites, all 16 outputs and
    # all eight SNN replay outputs. Top names are checked separately below.
    checks = q.functional(TOPS[0], pin)
    hardware = read(R / 'guard_add_hardware.json')
    assert len(hardware) == 4 and {row['top'] for row in hardware} == set(TOPS)
    ordered = {q.ENGINES[row['top'].removeprefix('top_guard_add_')]: row for row in hardware}
    for engine, row in ordered.items():
        assert row['target_ns'] == 6.0 and row['source_sha256'] == pin
        assert row['functional_check_sha256'] == checks
        assert row['hd_clk_src'] == 'BUFGCTRL_X0Y0'
        expected_provenance = hashlib.sha256(json.dumps(dict(
            top=row['top'], target_ns=6.0, sources=pin, checks=checks,
            part='xc7a100tcsg324-1', hd_clk_src='BUFGCTRL_X0Y0'), sort_keys=True).encode()).hexdigest()
        assert row['provenance_sha256'] == expected_provenance
        dest = R / f"{row['top']}_route"
        assert (dest / 'provenance.txt').read_text().splitlines()[0] == expected_provenance
        for filename in REPORTS:
            assert (dest / filename).is_file(), (dest, filename)
        full, core = q.util(dest / 'util.rpt'), q.util(dest / 'core_util.rpt', False)
        accounting = {key: int(value) for key, value in (
            line.split() for line in (dest / 'fixture_accounting.txt').read_text().splitlines())}
        core['occupied_slices_reported'] = core['occupied_slices']
        core['occupied_slices'] = accounting['core_slices_touched']
        assert row['full_fixture'] == full and row['core'] == core and row['slice_accounting'] == accounting
        assert accounting['launch_FF'] == 138 and accounting['capture_FF'] == 81 and accounting['fixture_FF'] == 219
        assert full['FF'] - core['FF'] == 219 and full['LUT'] == core['LUT'] and full['DSP'] == core['DSP']
        assert full['occupied_slices'] == accounting['full_occupied_slices']
        assert row['fixture_overhead'] == dict(LUT=0, FF=219, DSP=0)
        assert core['DSP'] == (0 if engine == 3 else 1), (engine, core)
        slack = list(map(float, (dest / 'slack.txt').read_text().splitlines()))
        boundary = list(map(float, (dest / 'boundary_slack.txt').read_text().splitlines()))
        assert len(slack) == len(boundary) == 2
        assert close(slack[0], row['WNS_ns']) and close(slack[1], row['WHS_ns'])
        assert close(boundary[0], row['boundary_WNS_ns']) and close(boundary[1], row['boundary_WHS_ns'])
        pre = R / f"{row['top']}_synth"
        assert (pre / 'design.dcp').is_file() and (pre / 'provenance.txt').read_text().strip() == expected_provenance

    suites = {name: read(R / name) for name in q.MAIN_CHECKS}
    assert {suite['rows'][0]['neurons'] for name, suite in suites.items() if 'main_' in name} == {811511}
    assert {suite['rows'][0]['neurons'] for name, suite in suites.items() if 'models_' in name} == {635904}
    for kind in ('main', 'models'):
        a, b = (suites[f'guard_add_{kind}_{stall}_checks.json'] for stall in (0, 1))
        assert a['stimulus_sha256'] == b['stimulus_sha256'], kind
        assert all(row['neurons'] == (811511 if kind == 'main' else 635904) for suite in (a, b) for row in suite['rows'])
    tested_scalar_sums = sum(row['neurons'] for suite in suites.values() for row in suite['rows'])
    assert tested_scalar_sums == 11579320
    snn = read(R / 'guard_add_snn_checks.json')
    ledger = read(R / q.MODEL_INPUTS[1])
    assert len(ledger['metadata']) == 3 and all(len(model['labels']) == 48 for model in ledger['metadata'])

    screen = read(R / 'guard_add_workload_screen.json')
    assert sha(P / 'screen_guard_add_models.py') == screen['script_sha256']
    assert screen['model_input_sha256'] == {
        str(Path('results') / name): sha(R / name) for name in q.MODEL_INPUTS}
    assert screen['reference_state_mismatches'] == screen['reference_spike_mismatches'] == 0
    assert screen['frames'] == 9216 and screen['neurons'] == 635904
    model_rows = {row['engine']: row for row in screen['models']}
    assert set(model_rows) == set(range(4))
    for name in ('guard_add_models_0_checks.json', 'guard_add_models_1_checks.json'):
        for row in suites[name]['rows']:
            screened = model_rows[row['engine']]
            for key in ('requests', 'neurons', 'narrow_requests'):
                assert row[key] == screened[key], (name, row['engine'], key)
            assert screened['supplied_window_clocks'] == screened['requests'] + 4
            if not suites[name]['backpressure']:
                assert row['clocks'] == screened['supplied_window_clocks']
    for engine, row in model_rows.items():
        assert row['changing_dsp_additions'] + row['changing_lut_additions'] == 589568
        if engine == 3:
            assert row['changing_per_dsp_issue'] is None
        else:
            assert close(row['changing_per_dsp_issue'], row['changing_dsp_additions'] / row['requests'])
    return dict(source_sha256=pin, functional_check_sha256=checks, hardware=ordered,
                suites=suites, snn=snn, screen=screen, model_rows=model_rows,
                tested_scalar_sums=tested_scalar_sums)


def snapshot_metadata(directory):
    """Pin an optional earlier evidence directory without assigning route metrics."""
    if directory is None:
        return None
    directory = directory.resolve()
    assert directory.is_dir(), directory
    metadata_file = directory / 'manifest.json'
    saved = read(metadata_file)
    assert saved['routed'] is False
    assert saved['source_hashes']['guard_add.sv'] == '4d098563a894c15ad7852a022be722e71217b143a7624a478c2c5bd4f237af30'
    for name, stamp in saved['artifact_hashes'].items():
        path = (directory / name).resolve()
        assert path.is_relative_to(directory) and path.is_file(), path
        assert path.stat().st_size == stamp['bytes'] and sha(path) == stamp['sha256'], path
    for name, stamp in saved['source_hashes'].items():
        assert sha(directory / 'sources' / name) == stamp, name
    for name, stamp in saved['functional_check_sha256'].items():
        assert sha(directory / 'results' / name) == stamp, name
    for name in q.MAIN_CHECKS:
        suite = read(directory / 'results' / name)
        assert suite['source_hashes'] == {n: saved['source_hashes'][n] for n in q.FUNCTIONAL_SOURCES}
        assert suite['tested_engines'] == suite['expected_engines'] == list(range(4))
        assert suite['acceptance_to_handshake_advances'] == 4
        assert all(row['mismatches'] == 0 and row['latency_checks'] == row['requests'] > 0
                   for row in suite['rows'])
    snn = read(directory / 'results' / 'guard_add_snn_checks.json')
    assert len(snn['rows']) == 8 and all(row['state_mismatches'] == row['spike_mismatches'] == 0
                                        for row in snn['rows'])
    return dict(path=str(directory), scope='Earlier masked arithmetic/control evidence; no routed hardware results',
                routed=False, metadata_files=[str(metadata_file)], validated_archived_artifacts=len(saved['artifact_hashes']),
                source_sha256={str(path.relative_to(directory)): sha(path)
                               for path in directory.rglob('*.sv')},
                manifest_sha256={str(metadata_file.relative_to(directory)): sha(metadata_file)})


def findings(data):
    h, m = data['hardware'], data['model_rows']
    a, native, hybrid, lut = h[0], h[1], h[2], h[3]
    base_clocks, adaptive_clocks = m[1]['supplied_window_clocks'], m[0]['supplied_window_clocks']
    reduction = 1 - adaptive_clocks / base_clocks
    useful_ratio = m[0]['changing_per_dsp_issue'] / m[1]['changing_per_dsp_issue'] - 1
    closure = {engine: row['WNS_ns'] >= 0 and row['WHS_ns'] >= 0 for engine, row in h.items()}
    primary = (f"Against the native four-lane DSP with the same identity-copy policy, the adaptive kernel uses "
               f"{adaptive_clocks:,} rather than {base_clocks:,} supplied-window clocks ({pct(reduction)} fewer). "
               f"Its measured core is {vector(a)} versus {vector(native)} ({delta_vector(a, native)}).")
    if closure[0] and closure[1]:
        primary += ' Both pass registered setup and hold at the common 6 ns target, so this is a supported primitive service-clock tradeoff for the replayed trace.'
    else:
        primary += ' At least one member of this comparison fails registered timing at 6 ns; the schedule reduction alone does not establish an achievable latency benefit.'
    practical = (f"The always-six hybrid and LUT kernels need {m[2]['supplied_window_clocks']:,} supplied-window clocks; "
                 f"the adaptive schedule is {pct(adaptive_clocks / m[2]['supplied_window_clocks'] - 1)} longer. "
                 f"Their cores are {vector(hybrid)} and {vector(lut)}, respectively. "
                 f"Adaptive differences are {delta_vector(a, hybrid)} versus hybrid and {delta_vector(a, lut)} versus LUT6.")
    lower_vector_hybrid = all(hybrid['core'][key] <= a['core'][key] for key in ('LUT', 'FF', 'DSP'))
    if lower_vector_hybrid and closure[0] and closure[2]:
        practical += ' The hybrid has no larger resource component and a shorter trace schedule, so it remains the stronger practical implementation in this measured cohort.'
    elif (closure[0] and closure[2] and hybrid['core']['LUT'] < a['core']['LUT']
          and hybrid['core']['DSP'] == a['core']['DSP']
          and 0 < hybrid['core']['FF'] - a['core']['FF'] <= 1):
        practical += (' The hybrid uses fewer LUTs and the same DSP count for a shorter schedule, at the cost of one extra FF. '
                      'The adaptive one-FF saving alone does not establish a useful practical advantage over this hybrid.')
    else:
        practical += ' These resource vectors and timing margins must be judged together; this trial does not establish a universal area or latency win over the always-six implementations.'
    return dict(primary=primary, practical=practical, model_clock_reduction_vs_native4=reduction,
                changing_dsp_additions_per_issue_gain_vs_native4=useful_ratio,
                registered_timing_pass=closure, overall_win_claim=False)


def report(data, conclusion, snapshot):
    h, m = data['hardware'], data['model_rows']
    text = [
        '# Guarded membrane-plus-current addition trial', '',
        conclusion['primary'], '', conclusion['practical'], '',
        'The operation is exact signed 11-bit membrane U plus signed 11-bit synaptic current I, returning a signed 12-bit sum. '
        'This ordered addition primitive changes the DSP arithmetic format according to the actual operand values; it is distinct from the earlier leakage multiplication trial.', '',
        'The compared mechanisms are:', '',
        '- E0 uses a DSP with immutable ONE48 mode. When all presented U and I values fit signed 7 bits, it can add five or six neurons in six 8-bit fields with guard bits. Otherwise it uses four 12-bit guarded fields. Sign metadata reconstructs the exact signed sums.',
        '- E0 and E1 share the ordered identity-copy optimization for zero-current fifth/sixth lanes. A copy that consumes the whole window is preferred; a partial fifth copy does not prevent E0 from accepting an eligible six-lane narrow request.',
        '- E1 uses the DSP\'s native FOUR12 mode for four full-range additions plus eligible identity copies. E2 uses the same native four lanes plus two LUT additions and accepts all six. E3 uses six LUT additions and accepts all six.', '',
        f"All four are placed and routed for xc7a100tcsg324-1 at 6 ns with Vivado 2025.2 and one thread. "
        'Core resources exclude the identical 219 preserved fixture FFs (138 launch + 81 capture). '
        'The fixture registers raw U, I, availability, valid, ready and reset, and captures every output unconditionally. It is a timing fixture, not a working production handshake wrapper. '
        'Retained hierarchy prevents optimization across the core boundary and limits conclusions about a fully integrated design.', '',
        'The final measured resource and timing vectors are:', '',
    ]
    for engine in range(4):
        row = h[engine]
        status = 'passes registered setup/hold' if conclusion['registered_timing_pass'][engine] else 'fails registered setup or hold'
        text.append(f"- E{engine} {LABELS[engine]}: core {vector(row)}; full fixture "
                    f"{row['full_fixture']['LUT']} LUT / {row['full_fixture']['FF']} FF / {row['full_fixture']['DSP']} DSP, "
                    f"{row['full_fixture']['occupied_slices']} occupied slices. Registered WNS {row['WNS_ns']:+.3f} ns, "
                    f"WHS {row['WHS_ns']:+.3f} ns; {status}. Separate raw-port audit WNS "
                    f"{row['boundary_WNS_ns']:+.3f} ns / WHS {row['boundary_WHS_ns']:+.3f} ns. "
                    f"Model {m[engine]['requests']:,} requests, {m[engine]['supplied_window_clocks']:,} supplied-window clocks.")
    text += ['', 'Occupied core and fixture slice sets overlap, so touched-slice counts cannot be added or subtracted as independent area. '
             'The separate raw-port audit uses declared 1 ns setup and 0.1 ns minimum budgets; any negative port hold slack is not production interface closure. '
             'No maximum operating frequency is inferred from target minus WNS.', '',
             'The trace accounting helps explain the primary comparison:', '',
             f"- The saved 635,904-neuron trace contains 589,568 changing additions (I ≠ 0). E0 and E1 perform all of them in the DSP: "
             f"{m[0]['changing_per_dsp_issue']:.6f} versus {m[1]['changing_per_dsp_issue']:.6f} changing additions per issue "
             f"({pct(conclusion['changing_dsp_additions_per_issue_gain_vs_native4'])} higher for E0). This is semantic work per issued request, not clock utilization, switching, power or energy.",
             f"- E0 uses {m[0]['narrow_requests']:,} narrow requests and copies {m[0]['copied_neurons']:,} neurons; E1 copies "
             f"{m[1]['copied_neurons']:,}. Different grouping changes the number of copies without changing the exact scalar results.",
             f"- E2 performs {m[2]['changing_dsp_additions']:,} changing additions in the DSP and {m[2]['changing_lut_additions']:,} in LUTs; "
             f"E3 performs all {m[3]['changing_lut_additions']:,} in LUTs. Their shorter always-six schedules remain necessary practical comparisons.",
             '- The workload screen field named issued_dsp_lane_capacity counts the issued valid lane operations for this screen; it is not a denominator for physical lane utilization, because unused tail capacity is excluded.', '',
             f"The four current checksets cover {data['tested_scalar_sums']:,} checked scalar outputs: 811,511 stress inputs and 635,904 saved model inputs, "
             'each replayed across four engines with and without backpressure. These are repeated inputs across configurations, not unique exhaustive multi-neuron cases. '
             'All output, ordering, tail, reset-cancellation, stall-stability and four-advancing-clock checks pass. There is no exhaustive claim over all combinations of four signed 11-bit operand pairs.', '',
             'The independent saved SNN replay matches every reference state, spike, output spike count and sampled classification for three seeds with 48 images each (144 images total). '
             'It computes leakage in Python using beta = 231/256 (Q8 coefficient 231), adds membrane/current in RTL, then applies threshold and subtractive reset in Python. '
             'This reference uses a changed leakage coefficient; it does not establish preservation of the models\' original trained accuracy, new training, or a full SNN RTL implementation.', '',
             'The final measured source retains the presented payload in its input registers. Earlier masking of unconsumed payload lanes was verified separately, '
             'but that snapshot was not routed. No measured area or timing improvement is attributed to removing the mask.']
    if snapshot:
        text += ['', 'Optional earlier masked evidence: ' + link(Path(snapshot['metadata_files'][0]), 'snapshot manifest') + '. It has no hardware measurements.']
    text += ['', 'A further fixed alternative remains unmeasured: six guarded 7-bit residue additions in ONE48 with exact high-part reconstruction in fabric. '
             'For each signed 11-bit operand, U = 128 hU + rU and I = 128 hI + rI with unsigned 7-bit residues. '
             'The DSP can compute six residue sums without interlane carry; fabric high-part addition and the residue carry recover each full signed 12-bit sum. '
             'This stateless design differs from the earlier persistent spill/carry recovery experiments. Its resource and timing cost is unknown here, '
             'so the native-four comparison cannot establish superiority over fixed packing generally or the best one-DSP implementation.', '',
             'Memory supply, gather/scatter, a state memory controller, threshold/reset hardware, burst arrival latency, host performance, board timing and power remain outside this primitive trial. '
             'FireFly accelerator results were not reproduced or compared by RTL here. The fixed DSP and LUT kernels are local implementations of this same addition operation; exact mechanism novelty remains unproved.', '',
             'Evidence: ' + ', '.join([link(R / 'guard_add_hardware.json', 'four route results'),
                                      link(R / 'guard_add_snn_checks.json', 'SNN replay'),
                                      link(R / 'guard_add_workload_screen.json', 'work accounting'),
                                      link(P / 'guard_add.sv', 'current core'),
                                      link(O / (STEM + '.manifest.json'), 'source/report/checkpoint manifest')]) + '.', '']
    return '\n'.join(text)


def evidence_files(snapshot):
    files = {P / name for name in q.SOURCES}
    files |= {Path(__file__), P / 'screen_guard_add_models.py', R / 'guard_add_workload_screen.json',
              R / 'guard_add_hardware.json', R / 'guard_add_snn_checks.json'}
    files |= {R / name for name in q.MAIN_CHECKS + q.MODEL_INPUTS}
    for name in q.MAIN_CHECKS:
        directory = R / name.removesuffix('_checks.json')
        files.add(directory / 'stream_stim.txt')
        files |= {directory / f'stream_out{engine}.txt' for engine in range(4)}
        files |= {directory / f'tool_{index}.log' for index in range(4)}
    for top in TOPS:
        files |= {R / f'{top}_route' / name for name in REPORTS}
        pre = R / f'{top}_synth'
        files |= {pre / name for name in ('util.rpt', 'hierarchical_util.rpt', 'design.dcp', 'provenance.txt')}
        for suffix in ('', '_resume'):
            for ending in ('_build.log', '_vivado.log', '_vivado.jou'):
                path = R / f'{top}{suffix}{ending}'
                if path.exists():
                    files.add(path)
    if snapshot:
        files |= {path for path in Path(snapshot['path']).rglob('*') if path.is_file()}
    for path in files:
        assert path.is_file(), ('Missing evidence asset', path)
    return sorted(files, key=lambda path: str(path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ready', action='store_true', help='Validate completed evidence and write the separate report.')
    parser.add_argument('--masked-snapshot', type=Path, default=None,
                        help='Optional earlier masked evidence directory; never treated as routed.')
    args = parser.parse_args()
    if not args.ready:
        print('Publisher prepared. No report written; use --ready after all current four routes and exact replay complete.')
        return
    data = validate()
    snapshot_path = args.masked_snapshot
    automatic_snapshot = R / 'guard_add_masked_4d098563a894'
    if snapshot_path is None and automatic_snapshot.is_dir():
        snapshot_path = automatic_snapshot
    snapshot = snapshot_metadata(snapshot_path)
    conclusion = findings(data)
    report_text = report(data, conclusion, snapshot)
    assets = evidence_files(snapshot)
    manifest_entries = [dict(path=str(path.resolve()), bytes=path.stat().st_size, sha256=sha(path)) for path in assets]
    assert q.hashes() == data['source_sha256'], 'Current source changed during publication'
    for name, stamp in data['functional_check_sha256'].items():
        assert sha(R / name) == stamp, 'Functional evidence changed during publication'
    now = datetime.now(timezone.utc).isoformat()
    summary = dict(created_utc=now, status='completed primitive trial', findings=conclusion,
                   source_sha256=data['source_sha256'], functional_check_sha256=data['functional_check_sha256'],
                   hardware=[data['hardware'][engine] for engine in range(4)],
                   model_work_accounting=data['screen']['models'],
                   checked_scalar_outputs=data['tested_scalar_sums'], distinct_input_sets=2,
                   input_scalar_pairs=dict(stress=811511, models=635904),
                   repeated_engine_and_stall_configurations=True,
                   scope='signed11 membrane-plus-current addition -> signed12; Python leakage/threshold/reset replay',
                   model_images=144, model_seeds=3, beta_q8=231, beta=231/256,
                   trained_model_accuracy_preservation_claim=False, masked_snapshot=snapshot)
    O.mkdir(exist_ok=True)
    report_path, summary_path = O / (STEM + '.md'), O / (STEM + '.summary.json')
    report_path.write_text(report_text, encoding='utf-8', newline='')
    summary_path.write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8', newline='')
    manifest = dict(created_utc=now, hash_algorithm='SHA-256, streamed 1 MiB chunks',
                    scope='Current source/check/output/SNN replay and four 6 ns OOC route checkpoints/reports',
                    current_source_sha256=data['source_sha256'], evidence=manifest_entries,
                    deliverables=[dict(path=str(path), bytes=path.stat().st_size, sha256=sha(path))
                                  for path in (report_path, summary_path)],
                    masked_snapshot=snapshot,
                    exclusions=['Simulator object directories, WDBs and temporary directories.',
                                'No board Fmax, power, host, memory or complete burst latency measurement.'])
    manifest_path = O / (STEM + '.manifest.json')
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8', newline='')
    print('GUARD ADD TRIAL PUBLISHED', report_path, summary_path, manifest_path, flush=True)


if __name__ == '__main__':
    main()
