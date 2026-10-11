"""Publish the completed matched fixed-baseline retiming trial after --ready.

Importing this module and invoking it without --ready do not run HDL tools,
write reports, or alter measured sources. Publication requires both current
6 ns routes, four full exact suites, saved SNN reconstruction, and unchanged
original and layout publications. Evidence is hashed in streamed 1 MiB chunks.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import math
import sys

# Safe imports must not create files alongside immutable measured sources.
sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent
R = P / 'results'
ORIGINAL = P.parent
LAYOUT = ORIGINAL / 'layout_trial'
O = P.parents[2] / 'outputs'
STEM = 'guarded_membrane_baseline_retime_trial'
for directory in (P, ORIGINAL, LAYOUT):
    sys.path.insert(0, str(directory))
import run_guard_add_retime_route as route
import publish_guard_add_trial as baseline
import publish_guard_add_layout_trial as layout

VARIANT_TO_ENGINE = {0: 2, 1: 3, 2: 2, 3: 3}
LABELS = {2: 'Retimed native DSP4 plus two LUT additions',
          3: 'Retimed six LUT additions'}
RESOURCE_KEYS = ('LUT', 'FF', 'DSP')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return route.sha(path)


def stamp(path):
    path = path.resolve()
    return dict(path=str(path), bytes=path.stat().st_size, sha256=sha(path))


def verify_entries(entries):
    """Recheck a completed publication without modifying its files."""
    for entry in entries:
        path = Path(entry['path'])
        assert path.is_file(), ('Missing pinned evidence', path)
        assert path.stat().st_size == entry['bytes'], ('Pinned evidence size changed', path)
        assert sha(path) == entry['sha256'], ('Pinned evidence hash changed', path)


def publication(stem, source, checks, hardware, source_key):
    paths = [O / (stem + suffix) for suffix in ('.md', '.summary.json', '.manifest.json')]
    assert all(path.is_file() for path in paths), ('Missing completed publication', stem)
    manifest, summary = read(paths[2]), read(paths[1])
    assert manifest[source_key] == source and summary['source_sha256'] == source, stem
    assert summary['functional_check_sha256'] == checks, stem
    assert {row['top']: row for row in summary['hardware']} == {
        row['top']: row for row in hardware.values()}, (stem, 'Published route rows differ')
    entries = manifest['evidence'] + manifest['deliverables']
    verify_entries(entries)
    deliverables = {Path(entry['path']).resolve() for entry in manifest['deliverables']}
    assert deliverables == {path.resolve() for path in paths[:2]}, stem
    return dict(paths=paths, pins=[stamp(path) for path in paths],
                evidence=entries, summary=summary)


def passes(row):
    return row['WNS_ns'] >= 0 and row['WHS_ns'] >= 0


def vector(row):
    return ' / '.join(f"{row['core'][key]} {key}" for key in RESOURCE_KEYS)


def difference(a, b):
    return {key: a['core'][key] - b['core'][key] for key in RESOURCE_KEYS}


def differences_text(values):
    return ' / '.join(f'{values[key]:+d} {key}' for key in RESOURCE_KEYS)


def link(path, label):
    return f'[{label}](<{path.resolve().as_posix()}>)'


def validate_routes(source, checks):
    rows = read(R / 'retime_hardware.json')
    assert len(rows) == 2 and {row['top'] for row in rows} == set(route.TOPS), 'Both current routes are required'
    result = {}
    for row in rows:
        top = row['top']
        engine, variant = route.TOPS[top], route.VARIANTS[top]
        assert row['engine'] == engine and row['variant'] == variant and row['target_ns'] == 6.0, top
        assert row['source_sha256'] == source and row['functional_check_sha256'] == checks, top
        assert row['hd_clk_src'] == 'BUFGCTRL_X0Y0', top
        expected = hashlib.sha256(json.dumps(dict(
            top=top, engine=engine, variant=variant, target_ns=6.0,
            sources=source, checks=checks, part='xc7a100tcsg324-1',
            hd_clk_src='BUFGCTRL_X0Y0'), sort_keys=True).encode()).hexdigest()
        assert row['provenance_sha256'] == expected, top
        pre, dest = (R / (top + suffix) for suffix in ('_synth', '_route'))
        assert (pre / 'provenance.txt').read_text().strip() == expected, top
        assert (dest / 'provenance.txt').read_text().splitlines()[0] == expected, top
        for name in baseline.REPORTS:
            assert (dest / name).is_file(), (top, name)
        for name in ('util.rpt', 'hierarchical_util.rpt', 'design.dcp', 'provenance.txt'):
            assert (pre / name).is_file(), (top, name)
        artifact_paths = {str(path.relative_to(P)): path for folder in (pre, dest)
                          for path in sorted(folder.rglob('*')) if path.is_file()}
        pins = row['route_artifact_sha256']
        assert pins and set(pins) == set(artifact_paths), (top, 'Checkpoint/report coverage differs')
        for name, path in artifact_paths.items():
            assert sha(path) == pins[name], (top, name, 'Routed artifact changed')
        suffix = '_resume' if row['retried_checkpoint'] else ''
        log = R / (top + suffix + '_build.log')
        assert f'GUARD_ADD_RETIME_TIMING_ROUTED {top}' in log.read_text(), top
        accounting = {key: int(value) for key, value in (
            line.split() for line in (dest / 'fixture_accounting.txt').read_text().splitlines())}
        assert accounting['launch_FF'] == 138 and accounting['capture_FF'] == 81, top
        assert accounting['fixture_FF'] == 219, top
        full, core = route.util(dest / 'util.rpt'), route.util(dest / 'core_util.rpt', False)
        core['occupied_slices_reported'] = core['occupied_slices']
        core['occupied_slices'] = accounting['core_slices_touched']
        assert row['core'] == core and row['full_fixture'] == full, top
        assert row['slice_accounting'] == accounting, top
        assert full['FF'] - core['FF'] == 219 and full['LUT'] == core['LUT'], top
        assert full['DSP'] == core['DSP'] == (1 if engine == 2 else 0), top
        assert full['occupied_slices'] == accounting['full_occupied_slices'], top
        assert row['fixture_overhead'] == {'LUT': 0, 'FF': 219, 'DSP': 0}, top
        assert core['RAMB18'] == core['RAMB36'] == full['RAMB18'] == full['RAMB36'] == 0, top
        for name, keys in [('slack.txt', ('WNS_ns', 'WHS_ns')),
                           ('boundary_slack.txt', ('boundary_WNS_ns', 'boundary_WHS_ns'))]:
            values = list(map(float, (dest / name).read_text().splitlines()))
            assert len(values) == 2 and all(math.isfinite(value) for value in values), top
            assert all(math.isclose(value, row[key], rel_tol=0, abs_tol=1e-9)
                       for value, key in zip(values, keys)), (top, name)
        result[engine] = row
    assert set(result) == {2, 3}
    return result


def validate():
    source = route.hashes()
    assert len(source) == 9 and source['../guard_add.sv'] == route.REFERENCE_CORE_SHA
    evidence = None
    for top in route.TOPS:
        current = route.functional(top, source)
        assert evidence is None or current == evidence, 'Matched tops use different functional gates'
        evidence = current
    old = baseline.validate()
    layouts = layout.validate()
    assert layouts['original']['source_sha256'] == old['source_sha256']
    assert layouts['original']['functional_check_sha256'] == old['functional_check_sha256']
    assert source['../guard_add.sv'] == old['source_sha256']['guard_add.sv']
    old_pub = publication(baseline.STEM, old['source_sha256'], old['functional_check_sha256'],
                          old['hardware'], 'current_source_sha256')
    layout_pub = publication(layout.STEM, layouts['source'], layouts['checks'],
                             layouts['hardware'], 'source_sha256')
    adaptive = layouts['hardware'][1]
    assert {key: adaptive['core'][key] for key in RESOURCE_KEYS} == {'LUT': 130, 'FF': 247, 'DSP': 1}
    adaptive_clocks = old['model_rows'][0]['supplied_window_clocks']
    assert adaptive_clocks == layout_pub['summary']['findings']['unchanged_model_clocks'] == 115758
    suites = {name: read(R / name) for name in route.SUITES}
    checked_outputs = 0
    for name, suite in suites.items():
        reference = old['suites'][name.replace('retime_', 'guard_add_', 1)]
        assert suite['frames'] == reference['frames'] and suite['backpressure'] == reference['backpressure'], name
        assert suite['stimulus_sha256'] == reference['stimulus_sha256'], name
        for row in suite['rows']:
            engine = VARIANT_TO_ENGINE[row['variant']]
            prior = next(item for item in reference['rows'] if item['engine'] == engine)
            for key in ('requests', 'neurons', 'arithmetic_issues', 'narrow_requests', 'copy_requests',
                        'clocks', 'input_stall_checks', 'output_stall_checks', 'latency_checks',
                        'mismatches', 'output_sha256'):
                assert row[key] == prior[key], (name, row['variant'], key)
            assert row['mismatches'] == 0
            if name == 'retime_models_0_checks.json':
                assert row['requests'] == 110592 and row['clocks'] == 110596, row
            checked_outputs += row['neurons']
    assert checked_outputs == 11579320
    snn = read(R / 'retime_snn_checks.json')
    for row in snn['rows']:
        engine = VARIANT_TO_ENGINE[row['variant']]
        prior = next(item for item in old['snn']['rows'] if item['engine'] == engine
                     and item['backpressure'] == row['backpressure'])
        for key in ('neurons', 'state_mismatches', 'spike_mismatches', 'model_rows'):
            assert row[key] == prior[key], ('SNN replay differs', row['variant'], key)
    hardware = validate_routes(source, evidence)
    assert route.hashes() == source and baseline.q.hashes() == old['source_sha256']
    assert layout.route.hashes() == layouts['source'], 'Layout source changed during validation'
    return dict(source=source, checks=evidence, original=old, layout=layouts,
                original_publication=old_pub, layout_publication=layout_pub,
                suites=suites, snn=snn, hardware=hardware,
                adaptive=adaptive, adaptive_clocks=adaptive_clocks,
                checked_outputs=checked_outputs)


def findings(data):
    a, ac = data['adaptive'], data['adaptive_clocks']
    old, hw = data['original'], data['hardware']
    comparisons = {}
    for engine, row in hw.items():
        clocks = old['model_rows'][engine]['supplied_window_clocks']
        assert clocks == 110596
        comparable = passes(a) and passes(row)
        prior = old['hardware'][engine]
        # Equal work and target period cancel in these ratios. These are ideal
        # core-only service densities, not measured replication or system rates.
        ff_ratio = clocks * row['core']['FF'] / (ac * a['core']['FF']) - 1 if comparable else None
        old_ff_ratio = clocks * prior['core']['FF'] / (ac * a['core']['FF']) - 1 \
            if passes(a) and passes(prior) else None
        ff_break_even = a['core']['FF'] * ac / clocks
        dominates = comparable and clocks < ac and all(
            row['core'][key] <= a['core'][key] for key in RESOURCE_KEYS)
        one_ff_tradeoff = comparable and clocks < ac and row['core']['LUT'] < a['core']['LUT'] \
            and row['core']['DSP'] == a['core']['DSP'] and row['core']['FF'] == a['core']['FF'] + 1
        comparisons[engine] = dict(core=row['core'], registered_timing_pass=passes(row),
            change_vs_original_fixed=difference(row, prior),
            adaptive_minus_retimed=difference(a, row),
            supplied_window_clocks=clocks,
            adaptive_clock_increase=ac / clocks - 1,
            adaptive_service_rate_change=clocks / ac - 1 if comparable else None,
            adaptive_ff_normalized_service_change=ff_ratio,
            adaptive_ff_normalized_service_change_vs_original_fixed=old_ff_ratio,
            fixed_ff_break_even_for_adaptive_ff_normalized_service=ff_break_even,
            minimum_integer_fixed_ff_for_adaptive_ff_normalized_gain=math.floor(ff_break_even) + 1,
            rate_comparison_supported_at_common_target=comparable,
            retimed_resource_vector_and_schedule_dominates_adaptive=dominates,
            hybrid_faster_and_fewer_luts_at_one_extra_ff=one_ff_tradeoff)
    native = old['hardware'][1]
    native_clocks = old['model_rows'][1]['supplied_window_clocks']
    return dict(adaptive_variant=1, adaptive_core=a['core'], adaptive_supplied_window_clocks=ac,
        adaptive_registered_timing_pass=passes(a), retimed=comparisons,
        adaptive_minus_native4=difference(a, native),
        adaptive_clock_reduction_vs_native4=1 - ac / native_clocks,
        adaptive_service_rate_change_vs_native4=native_clocks / ac - 1
            if passes(a) and passes(native) else None,
        ff_normalization='Equal-work supplied-window service at 6 ns per core FF; '
                         'ratio = fixed_clocks * fixed_FF / (adaptive_clocks * adaptive_FF) - 1. '
                         'Excludes fixture FFs and does not measure replicated placement or memory supply.',
        overall_win_claim=False,
        research_question_resolved=False)


def report(data, result):
    a, old = data['adaptive'], data['original']
    lines = ['# Guarded membrane-addition fixed-baseline retiming trial', '',
        'This trial gives the fixed hybrid and LUT implementations the input-stage computation already used by the lean adaptive layout. '
        'All kernels still compute exact signed 11-bit membrane U plus signed 11-bit current I into a signed 12-bit sum, '
        'retain lane order, backpressure and reset behavior, and retire after four advancing clocks.', '',
        '## Measured facts', '',
        'The retimed hybrid registers the first four U/I operands and the two exact signed 12-bit LUT sums at acceptance. '
        'The DSP operands, DSP result, and output retain the original stage positions; the extra sums advance through matching registers. '
        'The retimed LUT kernel registers all six exact signed 12-bit sums at acceptance. '
        'These are registration-boundary changes, with unchanged always-six request policies and full integer domain. '
        'The original comparisons were valid for their implementations; this trial strengthens the baselines by applying a legal optimization equally.', '',
        'All routes use Vivado 2025.2, xc7a100tcsg324-1, a 6 ns target, the same clock-source constraint, retained core hierarchy, '
        'and the identical registered OOC fixture. Core counts exclude 219 fixture FFs (138 launch + 81 capture). '
        'Core slice sets and fixture slice sets overlap; occupied slices are not additive.', '']
    for engine, row in data['hardware'].items():
        item = result['retimed'][engine]
        status = 'passes registered setup and hold' if passes(row) else 'fails registered setup or hold'
        lines += [f"- {LABELS[engine]}: {vector(row)}; change from its original fixed baseline "
            f"{differences_text(item['change_vs_original_fixed'])}. Registered WNS {row['WNS_ns']:+.3f} ns / "
            f"WHS {row['WHS_ns']:+.3f} ns; {status}. Core touches {row['core']['occupied_slices']} slices, "
            f"full fixture occupies {row['full_fixture']['occupied_slices']} slices. "
            f"Separate raw-port WNS {row['boundary_WNS_ns']:+.3f} ns / WHS {row['boundary_WHS_ns']:+.3f} ns."]
    lines += ['', f"The immutable adaptive V1 layout remains {vector(a)}, with registered WNS {a['WNS_ns']:+.3f} ns / "
        f"WHS {a['WHS_ns']:+.3f} ns and {data['adaptive_clocks']:,} saved-trace service clocks. "
        'It uses offset-binary fields, the measured wide-lane permutation, and encoded operands captured at acceptance. '
        'Its six-versus-four policy still tests actual U and I for signed7 fit, with the same ordered zero-current identity-copy priority. '
        'Membrane storage and the externally declared integer operation remain full signed11; only the temporary DSP layout narrows.', '',
        'Original matched resource references, revalidated from their saved publications:', '']
    for engine in range(4):
        row = old['hardware'][engine]
        lines.append(f"- {baseline.LABELS[engine]}: {vector(row)}, "
                     f"{old['model_rows'][engine]['supplied_window_clocks']:,} supplied-window service clocks; "
                     f"registered WNS {row['WNS_ns']:+.3f} ns / WHS {row['WHS_ns']:+.3f} ns.")
    lines += ['', 'The two retimed kernels each retain 110,592 requests and 110,596 service clocks on the 635,904-neuron saved trace. '
        'Their retired output hashes, request counts, arithmetic-issue counts, stalls and latency checks match the directly instantiated original E2/E3 references. '
        'No schedule improvement is attributed to retiming.', '',
        f"Four full suites check {data['checked_outputs']:,} scalar outputs across stress and model inputs, four variants, and two backpressure settings. "
        'This is repeated checking of 811,511 stress additions and 635,904 model additions, not an exhaustive six-neuron input space. '
        'Within each suite all four output files are byte-identical and match the original corresponding fixed-engine hash, with zero mismatches. '
        'Tests cover exact signed sums, ordering, four-advance latency, unavailable poisoned tails, stalled-output stability, and reset cancellation.', '',
        'Saved reconstruction matches states, spikes, output spike counts and sampled classifications for 144 images across three seeds. '
        'Leakage at beta=231/256 and threshold/subtractive reset execute in Python; addition executes in RTL. '
        'The reference uses a changed leakage coefficient, so this establishes replay equivalence to that saved reference, '
        'not preservation of original trained-model accuracy or a complete SNN RTL implementation.', '',
        '## Research interpretation', '',
        'Adaptive format selection is a real functional capability: it obtains six DSP additions from eligible actual values and retains a full-range four-lane fallback. '
        'Against native fixed4 with the same ordered identity-copy opportunity, the adaptive schedule uses '
        f"{100*result['adaptive_clock_reduction_vs_native4']:.2f}% fewer saved-trace service clocks for "
        f"{differences_text(result['adaptive_minus_native4'])}. "
        'This is a bounded resource/service tradeoff against that baseline, rather than an overall winner claim.', '']
    if result['adaptive_service_rate_change_vs_native4'] is not None:
        lines += [f"Both members pass registered timing at 6 ns; the ideal supplied-window service rate is "
            f"{100*result['adaptive_service_rate_change_vs_native4']:.2f}% higher than native fixed4 on this trace.", '']
    else:
        lines += ['At least one member fails the common registered target, so the native-four schedule comparison alone does not establish an achievable service-rate gain.', '']
    for engine, item in result['retimed'].items():
        lines += [f"Against {LABELS[engine].lower()}, adaptive V1 uses "
            f"{differences_text(item['adaptive_minus_retimed'])} and "
            f"{100*item['adaptive_clock_increase']:.2f}% more service clocks."]
        if item['rate_comparison_supported_at_common_target']:
            lines += [f"At the common passing 6 ns target, its ideal supplied-window service rate changes by "
                f"{100*item['adaptive_service_rate_change']:+.2f}%, and its service per core FF changes by "
                f"{100*item['adaptive_ff_normalized_service_change']:+.2f}%. "
                'The latter divides the equal-work service rate by core FF count; it excludes the fixture and assumes no shared memory or routing limit. '
                'It is not a measurement of replicated kernels or application throughput.']
            if engine == 2:
                lines += [f"Under this FF-only normalization, adaptive V1 improves on the fixed hybrid only when the hybrid uses more than "
                    f"{item['fixed_ff_break_even_for_adaptive_ff_normalized_service']:.2f} core FFs "
                    f"(at least {item['minimum_integer_fixed_ff_for_adaptive_ff_normalized_gain']} integer FFs), "
                    'before common integration overhead. This condition alone is not an area or application-throughput advantage; LUT and DSP costs still apply.']
        else:
            lines += ['At least one member fails registered setup or hold at 6 ns; service-rate and FF-normalized rate comparisons are withheld.']
        if item['retimed_resource_vector_and_schedule_dominates_adaptive']:
            lines += ['This retimed implementation has no larger LUT, FF or DSP component and a shorter trace schedule; it is stronger within this measured cohort.']
        elif item['hybrid_faster_and_fewer_luts_at_one_extra_ff']:
            lines += ['The hybrid uses fewer LUTs and the same DSP count, with a shorter schedule, at the cost of one extra FF. '
                      'The adaptive one-FF saving does not establish a practical benefit over this hybrid.']
        else:
            lines += ['The resource vectors remain a tradeoff; this experiment supplies no universal area or throughput advantage.']
        lines.append('')
    lines += ['LUT and FF costs remain relevant even when adaptation is the proposed contribution: classification, format selection, exact reconstruction and pipeline storage implement that functionality. '
        'The fixed hybrid and LUT kernels provide the same full-range ordered result without a fit-based scheduler and can be better practical baselines. '
        'More work inside the DSP alone is not an application benefit. A useful adaptive claim needs a concrete workload or resource constraint where the complete measured kernel improves service or fits a budget better than strong fixed alternatives.', '',
        'This result does not invalidate the membrane-aware adaptive-packing research question. It distinguishes a demonstrable native-four tradeoff from an unestablished advantage over strong always-six implementations. '
        'A fixed six-lane residue/high-part DSP reconstruction remains unmeasured; no best-fixed-packing or first-ever mechanism claim follows.', '',
        'Registered setup/hold and raw-port timing are separate. Raw ports use a declared 1 ns setup / 0.1 ns minimum budget; '
        'negative raw-port hold slack is not production interface closure. The OOC target and slack do not establish board Fmax. '
        'The fixture is a timing fixture rather than a production handshake adapter, and retained hierarchy limits inference about a fully integrated implementation.', '',
        'Memory supply, gather/scatter, state memory, host time, threshold/reset hardware, power, energy and true burst-arrival latency remain unmeasured. '
        'No FireFly accelerator was reproduced; these are matched local arithmetic kernels.', '',
        'Evidence: ' + ', '.join([link(R / 'retime_hardware.json', 'current fixed routes'),
            link(R / 'retime_snn_checks.json', 'saved replay'), link(P / 'guard_add_retime.sv', 'retimed core'),
            link(O / (layout.STEM + '.summary.json'), 'immutable adaptive layout'),
            link(O / (STEM + '.manifest.json'), 'source/output/checkpoint manifest')]) + '.', '']
    return '\n'.join(lines)


def assets(data):
    files = {P / name for name in route.SOURCES} | {Path(__file__), R / 'retime_hardware.json', R / 'retime_snn_checks.json'}
    for name in route.SUITES:
        files.add(R / name)
        directory = R / name.removesuffix('_checks.json')
        files.add(directory / 'stream_stim.txt')
        files |= {directory / f'stream_out{variant}.txt' for variant in VARIANT_TO_ENGINE}
        files |= {directory / f'tool_{index}.log' for index in range(4)}
    for row in data['hardware'].values():
        files |= {P / name for name in row['route_artifact_sha256']}
        for suffix in ('', '_resume'):
            for ending in ('_build.log', '_vivado.log', '_vivado.jou'):
                path = R / (row['top'] + suffix + ending)
                if path.exists():
                    files.add(path)
    for key in ('original_publication', 'layout_publication'):
        files |= set(data[key]['paths'])
        files |= {Path(entry['path']) for entry in data[key]['evidence']}
    # The two completed publications already pin the original/layout source,
    # mathematical screen, testsets, model references, logs and six old routes.
    resolved = sorted({path.resolve() for path in files}, key=str)
    assert all(path.is_file() for path in resolved), 'Publication asset missing'
    return resolved


def recheck(data, entries):
    assert route.hashes() == data['source'], 'Retimed source changed during publication'
    for top in route.TOPS:
        assert route.functional(top, data['source']) == data['checks'], 'Current functional evidence changed'
    assert baseline.q.hashes() == data['original']['source_sha256'], 'Original source changed'
    assert baseline.q.functional(baseline.TOPS[0], data['original']['source_sha256']) == \
        data['original']['functional_check_sha256'], 'Original functional evidence changed'
    assert layout.route.hashes() == data['layout']['source'], 'Layout source changed'
    for top in layout.route.TOPS:
        assert layout.route.functional(top, data['layout']['source']) == data['layout']['checks'], 'Layout functional evidence changed'
    verify_entries(entries)
    for key in ('original_publication', 'layout_publication'):
        verify_entries(data[key]['pins'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ready', action='store_true', help='Validate completed routes/replay and write the separate report.')
    args = parser.parse_args()
    if not args.ready:
        print('Publisher prepared; no report written. Use --ready after both current routes and all exact suites/replay finish.')
        return
    data = validate()
    result = findings(data)
    report_text = report(data, result)
    entries = [stamp(path) for path in assets(data)]
    recheck(data, entries)
    now = datetime.now(timezone.utc).isoformat()
    summary = dict(created_utc=now, status='Completed exact matched fixed-baseline retiming trial',
        findings=result, source_sha256=data['source'], functional_check_sha256=data['checks'],
        hardware=[data['hardware'][engine] for engine in (2, 3)],
        adaptive_layout_hardware=data['adaptive'],
        original_reference_hardware=[data['original']['hardware'][engine] for engine in range(4)],
        original_publication_sha256={entry['path']: entry['sha256'] for entry in data['original_publication']['pins']},
        layout_publication_sha256={entry['path']: entry['sha256'] for entry in data['layout_publication']['pins']},
        checked_scalar_outputs=data['checked_outputs'], distinct_input_sets=2,
        input_scalar_pairs=dict(stress=811511, models=635904), repeated_variant_and_stall_inputs=True,
        reference_variant_to_original_engine=VARIANT_TO_ENGINE,
        model_images=144, model_seeds=3, beta_q8=231, beta=231/256,
        acceptance_to_handshake_advances=4, model_fixed_service_clocks=110596,
        model_adaptive_service_clocks=data['adaptive_clocks'], trained_model_accuracy_preservation_claim=False,
        scope='Exact signed11 U + signed11 I -> signed12; fixed baseline input-stage retiming; '
              'matched registered 6 ns routes; Python leakage/threshold/reset replay')
    O.mkdir(exist_ok=True)
    report_path, summary_path, manifest_path = (O / (STEM + suffix) for suffix in ('.md', '.summary.json', '.manifest.json'))
    report_path.write_text(report_text, encoding='utf-8', newline='')
    summary_path.write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8', newline='')
    manifest = dict(created_utc=now, hash_algorithm='SHA-256, streamed 1 MiB chunks',
        source_sha256=data['source'], evidence=entries,
        deliverables=[stamp(path) for path in (report_path, summary_path)],
        scope='New sources/checks/outputs/SNN reconstruction and two routed DCPs/reports; '
              'immutable original and layout publications and all evidence they reference; no payload duplication',
        exclusions=['Simulator object directories, WDBs and temporary directories.',
                    'No board Fmax, power, host, memory, replicated-kernel placement or true burst-arrival measurement.',
                    'No complete SNN RTL, preservation of original trained accuracy, first-ever or universal fixed-packing claim.'])
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8', newline='')
    print('GUARD ADD BASELINE RETIME TRIAL PUBLISHED', report_path, summary_path, manifest_path, flush=True)


if __name__ == '__main__':
    main()
