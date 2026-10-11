"""Publish the matched U11/I8 fixed-baseline trial only after --ready.

No HDL tools run here. Sources, four full suites, eight saved SNN replays,
two routes, and immutable prior publication evidence must all validate.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import math
import sys

sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent
R = P / 'results'
O = P.parents[2] / 'outputs'
COMMON = P.parent / 'common_layout_trial'
sys.path.insert(0, str(P))
import run_guard_add_i8_fixed_route as route

STEM = 'membrane_i8_fixed_comparison_trial'
OLD_STEM = 'membrane_selective_correction_trial'
KEYS = ('LUT', 'FF', 'DSP')
LABELS = {0: 'I8 hybrid: FOUR12 DSP plus two LUT sums',
          1: 'I8 LUT-only: six fabric sums',
          2: 'Fixed residue: six DSP low sums plus fabric high recovery',
          3: 'Shared adaptive exact correction (archived I8 V3)'}


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def stamp(path):
    path = path.resolve()
    return dict(path=str(path), bytes=path.stat().st_size, sha256=sha(path))


def verify(entries):
    for entry in entries:
        path = Path(entry['path'])
        assert path.is_file() and path.stat().st_size == entry['bytes'], path
        assert sha(path) == entry['sha256'], ('Changed evidence', path)


def passes(row):
    return row['WNS_ns'] >= 0 and row['WHS_ns'] >= 0


def vector(row):
    return ' / '.join(f"{row['core'][key]} {key}" for key in KEYS)


def delta(a, b):
    return {key: a['core'][key] - b['core'][key] for key in KEYS}


def link(path, label):
    return f'[{label}](<{path.resolve().as_posix()}>)'


def validate_routes(source, checks):
    rows = read(R / 'i8_fixed_hardware.json')
    assert len(rows) == 2 and {row['top'] for row in rows} == set(route.TOPS)
    validated = {}
    for row in rows:
        top = row['top']
        engine, variant = route.TOPS[top], route.VARIANTS[top]
        assert row['engine'] == engine and row['variant'] == variant
        assert row['target_ns'] == 6.0 and row['hd_clk_src'] == 'BUFGCTRL_X0Y0'
        assert row['source_sha256'] == source and row['functional_check_sha256'] == checks
        provenance = hashlib.sha256(json.dumps(dict(
            top=top, engine=engine, variant=variant, target_ns=6.0,
            sources=source, checks=checks, part='xc7a100tcsg324-1',
            hd_clk_src='BUFGCTRL_X0Y0'), sort_keys=True).encode()).hexdigest()
        assert row['provenance_sha256'] == provenance
        pre, dest = (R / (top + suffix) for suffix in ('_synth', '_route'))
        assert (pre / 'provenance.txt').read_text().strip() == provenance
        lines = (dest / 'provenance.txt').read_text().splitlines()
        assert lines[0] == provenance
        assert dict(line.split(maxsplit=1) for line in lines[1:]) == {
            'TOP': top, 'TARGET_NS': '6.0', 'VIVADO': '2025.2',
            'HD_CLK_SRC': 'BUFGCTRL_X0Y0'}
        artifacts = {str(path.relative_to(P)): path for folder in (pre, dest)
                     for path in sorted(folder.rglob('*')) if path.is_file()}
        assert set(row['route_artifact_sha256']) == set(artifacts)
        for name, path in artifacts.items():
            assert sha(path) == row['route_artifact_sha256'][name], path
        suffix = '_resume' if row['retried_checkpoint'] else ''
        if row['retried_checkpoint']:
            assert row['resume_helper_sha256'] == sha(P / 'resume_i8_fixed_route.py')
            assert row['resume_checkpoint_sha256'] == sha(pre / 'design.dcp')
        assert f'GUARD_ADD_I8_FIXED_TIMING_ROUTED {top}' in (
            R / (top + suffix + '_build.log')).read_text()
        accounting = {key: int(value) for key, value in (
            line.split() for line in (dest / 'fixture_accounting.txt').read_text().splitlines())}
        assert accounting['launch_FF'] == 138 and accounting['capture_FF'] == 81
        assert accounting['fixture_FF'] == 219
        assert accounting['core_slices_touched'] + accounting['fixture_slices_touched'] \
            - accounting['shared_slices'] == accounting['full_occupied_slices']
        full, core = route.util(dest / 'util.rpt'), route.util(dest / 'core_util.rpt', False)
        core['occupied_slices_reported'] = core['occupied_slices']
        core['occupied_slices'] = accounting['core_slices_touched']
        assert row['core'] == core and row['full_fixture'] == full
        assert row['slice_accounting'] == accounting
        assert full['FF'] - core['FF'] == 219 and full['LUT'] == core['LUT']
        assert full['DSP'] == core['DSP'] == (1 if engine == 2 else 0)
        assert row['fixture_overhead'] == {'LUT': 0, 'FF': 219, 'DSP': 0}
        assert all(item['RAMB18'] == item['RAMB36'] == 0 for item in (core, full))
        for name, keys in [('slack.txt', ('WNS_ns', 'WHS_ns')),
                           ('boundary_slack.txt', ('boundary_WNS_ns', 'boundary_WHS_ns'))]:
            values = list(map(float, (dest / name).read_text().splitlines()))
            assert len(values) == 2 and all(math.isfinite(value) for value in values)
            assert all(math.isclose(value, row[key], rel_tol=0, abs_tol=1e-9)
                       for value, key in zip(values, keys))
        validated[variant] = row
    assert set(validated) == {0, 1}
    return validated


def validate():
    source = route.hashes()
    checks = route.functional(next(iter(route.TOPS)), source)
    assert all(route.functional(top, source) == checks for top in route.TOPS)
    old_paths = [O / (OLD_STEM + suffix)
                 for suffix in ('.md', '.summary.json', '.manifest.json')]
    old, manifest = read(old_paths[1]), read(old_paths[2])
    verify(manifest['evidence'] + manifest['deliverables'])
    assert {Path(entry['path']).resolve() for entry in manifest['deliverables']} == {
        path.resolve() for path in old_paths[:2]}
    assert old['decode_included'] and old['trained_model_accuracy_preservation_claim'] is False
    old_hw = {row['variant']: row for row in old['hardware']}
    assert old_hw[2]['core']['LUT'] == 43 and old_hw[2]['core']['FF'] == 262
    assert old_hw[2]['core']['DSP'] == 1
    assert old_hw[3]['core']['LUT'] == 147 and old_hw[3]['core']['FF'] == 268
    assert old_hw[3]['core']['DSP'] == 1
    assert sha(COMMON / 'guard_add_selective.sv') == old['source_sha256']['guard_add_selective.sv']
    for name, pin in source.items():
        assert sha(P / name) == pin
    suites = {name: read(R / name) for name in route.SUITES}
    checked = sum(row['neurons'] for suite in suites.values() for row in suite['rows'])
    assert checked == 11579320
    model = suites['i8_fixed_models_0_checks.json']['rows']
    assert all(row['clocks'] == 110596 and row['requests'] == 110592
               and row['neurons'] == 635904 for row in model)
    certificate = read(COMMON / 'common_i8_current_bounds.json')
    assert certificate['failures'] == 0
    assert all(row['all_neuron_binary_spike_currents_fit_signed8'] for row in certificate['rows'])
    hardware = validate_routes(source, checks)
    assert route.hashes() == source
    return dict(source=source, checks=checks, suites=suites,
                snn=read(R / 'i8_fixed_snn_checks.json'), checked_outputs=checked,
                hardware=hardware, old=old, old_hardware=old_hw,
                old_manifest=manifest, old_paths=old_paths,
                certificate=certificate, model_rows=model)


def findings(data):
    fixed, adaptive = data['old_hardware'][2], data['old_hardware'][3]
    model = {row['variant']: row for row in data['model_rows']}
    comparisons = {}
    for variant, baseline in data['hardware'].items():
        change = delta(fixed, baseline)
        supported = passes(fixed) and passes(baseline)
        comparisons[variant] = dict(fixed_minus_matched_baseline=change,
            fixed_relative_resource_change={key: change[key] / baseline['core'][key]
                if baseline['core'][key] else None for key in KEYS},
            both_pass_registered_6ns=supported,
            same_model_clocks=model[variant]['clocks'] == 110596,
            fixed_dominates_resource_vector_at_equal_service=supported
                and all(value <= 0 for value in change.values())
                and any(value < 0 for value in change.values()),
            matched_baseline_dominates_resource_vector_at_equal_service=supported
                and all(value >= 0 for value in change.values())
                and any(value > 0 for value in change.values()))
    return dict(comparisons=comparisons, fixed_core=fixed['core'],
        fixed_model_clocks=110596, adaptive_core=adaptive['core'],
        adaptive_minus_fixed=delta(adaptive, fixed), adaptive_model_clocks=110710,
        adaptive_extra_clocks=114,
        fixed_layout_and_static_current_specialization_are_adaptive=False,
        first_ever_claim=False, universal_best_fixed_claim=False,
        total_area_or_energy_claim=False, trained_accuracy_advantage=False)


def report(data, result):
    hybrid_delta = result['comparisons'][0]['fixed_minus_matched_baseline']
    hybrid_percent = result['comparisons'][0]['fixed_relative_resource_change']
    lines = ['# Matched signed8-current fixed membrane-addition comparison', '',
        f"Against the equally specialized hybrid, the fixed residue implementation changes resources by "
        f"{hybrid_delta['LUT']:+d} LUT ({hybrid_percent['LUT']:+.1%}) and "
        f"{hybrid_delta['FF']:+d} FF ({hybrid_percent['FF']:+.1%}), with the same one DSP and saved service clocks. "
        'LUTs and registers remain separate tradeoff axes; this does not establish a total-area or energy saving.', '',
        'This isolated trial closes the operand-domain gap: every cost comparator supports signed11 membrane U plus statically signed8 current I, producing exact signed12 U+I. '
        'It retains six ordered lanes, four advancing clocks, stalls, reset cancellation and zero output tails. '
        'The fixed residue and adaptive routes are unchanged archived references; only two specialized fixed baselines are newly routed.', '',
        'The hybrid physically stores four eight-bit currents before its FOUR12 DSP additions; the other two sums are computed in fabric at acceptance. '
        'The LUT-only implementation uses eight-bit signed currents in all six fabric additions. '
        'The membrane input remains eleven bits and each output remains twelve bits. Ignored tail payloads can be arbitrary.', '',
        'The archived fixed residue design splits U=128hU+rU and I=128hI+rI. '
        'One DSP adds six pairs of unsigned seven-bit residues in eight-bit fields. '
        'Each residue sum is at most 254, so no carry crosses into another field. '
        'Fabric reconstructs the exact high part hU+hI+carry; in the I8 domain this is hU+carry-sign(I). '
        'Thus the DSP computes six low-part additions, while fabric completes the full-width sums.', '',
        '## Routed core results', '',
        'Vivado 2025.2, xc7a100tcsg324-1, one thread, 6 ns, identical registered OOC fixture. '
        'Core counts exclude 219 fixture FFs. Slice sets overlap. Registered setup/hold and raw-port timing are separate.', '']
    combined = dict(data['hardware'])
    combined[2], combined[3] = data['old_hardware'][2], data['old_hardware'][3]
    for variant, row in combined.items():
        clocks = 110710 if variant == 3 else 110596
        lines.append(f"- {LABELS[variant]}: {vector(row)}; WNS {row['WNS_ns']:+.3f} ns, WHS {row['WHS_ns']:+.3f} ns; "
                     f"registered timing {'passes' if passes(row) else 'fails'}; {clocks:,} saved service clocks.")
    hybrid, lut_only = data['hardware'][0], data['hardware'][1]
    lines.extend(['',
        f"Under the separately declared raw-port budgets, boundary hold slack is "
        f"{hybrid['boundary_WHS_ns']:+.3f} ns for the hybrid and "
        f"{lut_only['boundary_WHS_ns']:+.3f} ns for LUT-only. "
        'These boundary checks do not pass; the passing timing statements above apply to the registered OOC fixture. '
        'A board interface and clock network have not been validated.'])
    lines.extend(['', 'For the fixed residue core relative to each newly specialized baseline:', ''])
    for variant, comparison in result['comparisons'].items():
        values = comparison['fixed_minus_matched_baseline']
        differences = ' / '.join(f'{values[key]:+d} {key}' for key in KEYS)
        if comparison['fixed_dominates_resource_vector_at_equal_service']:
            interpretation = 'The fixed residue resource vector dominates at equal measured service and passing target timing.'
        elif comparison['matched_baseline_dominates_resource_vector_at_equal_service']:
            interpretation = 'The matched baseline resource vector dominates at equal measured service and passing target timing.'
        elif comparison['both_pass_registered_6ns']:
            interpretation = 'This is a resource tradeoff; no total-area or energy ordering is measured.'
        else:
            interpretation = 'A common-target service advantage cannot be claimed because registered timing fails.'
        lines.append(f'- Versus {LABELS[variant]}: {differences}. {interpretation}')
    lines.extend(['',
        'All fixed implementations accept six available updates per issue and use the same saved service clocks. '
        'The current shared adaptive implementation still costs +104 LUT and +6 FF versus its own fixed residue reference, with the same DSP count and 114 extra saved clocks. '
        'This comparator study does not create an adaptive throughput or accuracy benefit. Energy per completed update remains unmeasured.', '',
        '## Exactness and workload contract', '',
        f"Four full RTL suites check {data['checked_outputs']:,} repeated scalar outputs across four implementations, with and without output backpressure. "
        'All retirement files must be byte-identical to the archived profile1 fixed result, including physical clock columns. '
        'Eight SNN replays match the saved states, spikes, spike counts and sampled classes. This is repeated checking, not exhaustive six-neuron combinations.', '',
        'Stress inputs use the same modular signed8-current projection as the archived profile1 trial. This changes the stress domain and is not lossless requantization of arbitrary I11 inputs. '
        'Saved model operands remain unchanged: 635,904 scalar pairs in 110,592 windows, 144 images across three seeds. '
        'The weight certificate bounds all permitted binary-spike currents in [-100,70], which fits signed8. '
        'Other weights, extra currents or nonbinary spike encodings require their own certificate.', '',
        'SNN leakage at beta231, threshold and subtractive reset execute in Python; U+I executes in RTL. '
        'The leakage differs from original training, so equivalence is to the declared saved integer reference, not preservation of original trained-model accuracy.', '',
        '## Contribution boundary', '',
        'Exact guarded SNN addition packing is already described in '
        '[DSP-Packing, Section VII](https://arxiv.org/html/2203.11028#S7). '
        'Packed low-part DSP arithmetic with exact external high-part handling also appears in '
        '[Arithmetic Packing, Sections III-C/III-D](https://arxiv.org/html/2606.11065). '
        'Our fixed candidate is a particular six-lane unsigned-residue mapping with direct high reconstruction and a certified current-width specialization. '
        'Its arithmetic decomposition is not established here as new, and absence of an identical configuration does not prove novelty.', '',
        'This local primitive comparison measures resources, OOC timing and RTL service. It does not measure total weighted area, energy, board Fmax, memory supply, arrival-burst latency or complete SNN-update latency. '
        'No FireFly accelerator RTL is reproduced. Static I8 specialization and fixed six-lane mapping are not runtime adaptation.', '',
        'Evidence: ' + ', '.join([link(P/'guard_add_i8_fixed.sv', 'specialized RTL'),
                                  link(R/'i8_fixed_hardware.json', 'two new routes'),
                                  link(P/'audit_notes.md', 'independent audit'),
                                  link(O/(STEM+'.manifest.json'), 'complete manifest')]) + '.', ''])
    return '\n'.join(lines)


def assets(data):
    files = {P / name for name in data['source']}
    files |= {P / name for name in ('CONTRACT.md', 'hardware_notes.md',
                                  'audit_notes.md', 'audit_i8_fixed_trial.py',
                                  'publish_i8_fixed_trial.py', 'resume_i8_fixed_route.py')}
    files |= set(data['old_paths'])
    files |= {Path(entry['path']) for entry in
              data['old_manifest']['evidence'] + data['old_manifest']['deliverables']}
    files |= {R / 'i8_fixed_hardware.json'}
    for name in data['checks']:
        path = R / name
        files.add(path if path.is_file() else P / name)
    for suite in data['suites'].values():
        files.add(R / suite['stimulus_file'])
        folder = (R / suite['stimulus_file']).parent
        files |= set(folder.glob('stream_out*.txt'))
        files |= set(folder.glob('tool_*.log'))
        files |= {path for path in folder.glob('*.log') if path.is_file()}
    for row in data['hardware'].values():
        for name in row['route_artifact_sha256']:
            files.add(P / name)
        files |= set(R.glob(row['top'] + '*_build.log'))
        files |= set(R.glob(row['top'] + '*_vivado.log'))
        files |= set(R.glob(row['top'] + '*_vivado.jou'))
    resolved = sorted({path.resolve() for path in files}, key=str)
    assert all(path.is_file() for path in resolved)
    return resolved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ready', action='store_true')
    args = parser.parse_args()
    if not args.ready:
        print('No files written. Publication requires four full suites, SNN replay and both routes.')
        return
    data = validate()
    result = findings(data)
    text = report(data, result)
    entries = [stamp(path) for path in assets(data)]
    verify(entries)
    assert route.hashes() == data['source']
    assert route.functional(next(iter(route.TOPS)), data['source']) == data['checks']
    now = datetime.now(timezone.utc).isoformat()
    summary = dict(created_utc=now, status='Completed matched signed8-current fixed comparison',
        source_sha256=data['source'], functional_check_sha256=data['checks'],
        findings=result, hardware=[data['hardware'][v] for v in (0, 1)],
        unchanged_reference_hardware=[data['old_hardware'][v] for v in (2, 3)],
        model_rows=data['model_rows'], suites=data['suites'], snn=data['snn'],
        checked_scalar_outputs=data['checked_outputs'], saved_snn_replays=8,
        input_domain='signed11 U + sign-extended signed8 I -> exact signed12 sum',
        stress_transformation='same archived profile1 modular signed8-current projection',
        saved_model_operands_changed=False, current_certificate=data['certificate'],
        prior_publication_sha256={str(path): sha(path) for path in data['old_paths']},
        scope='Matched fixed arithmetic primitives; no adaptive energy, trained accuracy, board or full system claim')
    paths = [O / (STEM + suffix) for suffix in ('.md', '.summary.json', '.manifest.json')]
    paths[0].write_text(text, encoding='utf-8', newline='')
    paths[1].write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8', newline='')
    manifest = dict(created_utc=now, hash_algorithm='SHA-256 streamed 1 MiB chunks',
        source_sha256=data['source'], evidence=entries,
        deliverables=[stamp(path) for path in paths[:2]],
        exclusions=['Simulator objects, temporary runtime directories, waveforms.',
                    'No first-ever, globally best, energy, trained-accuracy or full-system claim.'])
    paths[2].write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8', newline='')
    print('I8 FIXED TRIAL PUBLISHED', *paths, flush=True)


if __name__ == '__main__':
    main()
