"""Freeze an explicit-path, hash-bound scientific report after root completes jobs.

No vendor tools, model inference, latest/best selection, manuscript edits or
silent missing-gate substitution. This performs integrity/accounting checks on
previous independent audit receipts; it does not rerun the physical SAIF audit
or infer publication strength from a pass. Absent/rejected evidence is retained.
"""
from pathlib import Path
from fractions import Fraction
from decimal import Decimal
import argparse
import datetime
import hashlib
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
import numpy as np

sys.dont_write_bytecode = True
C = Path(__file__).resolve().parent
W = C / 'width16'
S = C.parent / 'sequential_paper_trial'
BENCH = C / 'benchmarks'
PINS = {}
CACHE = {}
ISSUES = []
HASH = re.compile(r'^[0-9a-fA-F]{64}$')


def sha(path):
    path = Path(path).resolve()
    info = path.stat()
    key = (str(path), info.st_size, info.st_mtime_ns)
    if key not in CACHE:
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1 << 20), b''):
                digest.update(chunk)
        CACHE[key] = digest.hexdigest()
    return CACHE[key]


def bind(path, expected=None):
    path = Path(path).resolve()
    current = sha(path)
    PINS[str(path)] = current
    assert expected is None or current == expected, ('Hash mismatch', str(path), expected, current)
    return path


def references(value, origin):
    """Independently bind declared path/hash pairs and absolute hash maps."""
    if isinstance(value, list):
        for child in value:
            references(child, origin)
        return
    if not isinstance(value, dict):
        return
    # Export manifests and provenance files can themselves be a plain map.
    for filename, pin in value.items():
        if isinstance(filename, str) and Path(filename).is_absolute() and isinstance(pin, str) and HASH.fullmatch(pin):
            bind(filename, pin)
    for key in ['source_sha256', 'artifact_sha256', 'source_artifact_sha256', 'sha256', 'pins']:
        stamps = value.get(key)
        if isinstance(stamps, dict):
            for filename, pin in stamps.items():
                if isinstance(pin, str) and HASH.fullmatch(pin):
                    path = Path(filename)
                    if not path.is_absolute():
                        path = origin.parent / path
                    bind(path, pin)
    if isinstance(value.get('path'), str) and isinstance(value.get('sha256'), str) and HASH.fullmatch(value['sha256']):
        bind(value['path'], value['sha256'])
    if isinstance(value.get('file'), str) and isinstance(value.get('sha256'), str) and HASH.fullmatch(value['sha256']):
        bind(value['file'], value['sha256'])
    for key, pin in value.items():
        if key.endswith('_sha256') and isinstance(pin, str) and HASH.fullmatch(pin):
            stem = key[:-7]
            for alternative in [stem + '_file', stem + '_path', stem, stem + '_manifest']:
                filename = value.get(alternative)
                if isinstance(filename, str) and Path(filename).is_file():
                    bind(filename, pin)
                    break
    for child in value.values():
        references(child, origin)


def read(path, status=None):
    path = bind(path)
    value = json.loads(path.read_text(encoding='utf-8-sig'))
    references(value, path)
    if status is not None:
        assert value.get('status') in status, (str(path), value.get('status'))
    return value


def stage(name, path, callback):
    path = Path(path).resolve()
    if not path.is_file():
        issue = dict(stage=name, category='absent_gate', path=str(path), accepted=False)
        ISSUES.append(issue)
        return dict(status='absent', path=str(path), accepted=False)
    try:
        value = callback(path)
        return dict(status='verified', path=str(path), sha256=sha(path), accepted=True, evidence=value)
    except Exception as error:
        issue = dict(stage=name, category='rejected_or_incomplete_gate', path=str(path),
                     reason=repr(error), accepted=False)
        ISSUES.append(issue)
        try:
            context = json.loads(path.read_text(encoding='utf-8-sig'))
        except Exception as parse_error:
            context = dict(unreadable_or_partial_JSON=repr(parse_error))
        return dict(status='rejected_or_incomplete', path=str(path), sha256=sha(path), accepted=False,
                    reason=repr(error), saved_record_context_only=context)


def route(path, engine):
    d = read(path, {'pass'})
    assert d['B'] == 16 and d['engine'] == engine and d['clock_period_ns'] == 12
    assert d['part'] == 'xc7a100tcsg324-1' and d['latency_advancing_edges'] == 2
    assert d['fixture_FF'] == 94
    assert d['slice_accounting']['launch_FF'] == 55 and d['slice_accounting']['capture_FF'] == 39
    assert d['full_fixture']['FF'] - d['core']['FF'] == 94
    assert d['full_fixture']['LUT'] == d['core']['LUT'] and d['full_fixture']['DSP'] == d['core']['DSP']
    for name in ['WNS_ns', 'WHS_ns', 'boundary_WNS_ns', 'boundary_WHS_ns']:
        assert math.isfinite(d[name]) and d[name] >= 0
    if engine in (0, 1, 4, 5, 8):
        assert d['core']['DSP'] == 1
    if engine in (2, 6, 7):
        assert d['core']['DSP'] == 0
    if engine == 3:
        assert d['core']['DSP'] == 2
    return dict(file=str(Path(path).resolve()), sha256=sha(path), core=d['core'],
                WNS_ns=d['WNS_ns'], WHS_ns=d['WHS_ns'], full_fixture=d['full_fixture'])


def all_routes(path, e7):
    manifest = read(path, {'pass'})
    assert manifest['B'] == 16 and manifest['period_ns'] == 12
    assert set(manifest['selected_routes']) == {str(i) for i in range(7)}
    selected = {key: route(Path(folder) / 'hardware.json', int(key))
                for key, folder in manifest['selected_routes'].items()}
    selected['7'] = route(e7, 7)
    a, b = selected['5']['core'], selected['1']['core']
    return dict(selected=selected, E5_vs_E1=dict(same_DSP_count=a['DSP'] == b['DSP'],
                LUT_reduction_fraction=1 - a['LUT'] / b['LUT'],
                FF_reduction_fraction=1 - a['FF'] / b['FF'],
                adaptive_core=a, fixed_split_core=b),
                scope='Core fabric resources; common94FF fixture excluded. DSPs and fabric resources are separately reported.')


def power(item, routes):
    file = bind(item['power_audit_file'], item['power_audit_sha256'])
    saved = read(file, {'pass'})
    engine = saved['engine']
    selected = routes[str(engine)]
    bind(saved['routed_hardware_file'], saved['routed_hardware_sha256'])
    assert Path(saved['routed_hardware_file']).resolve() == Path(selected['file']).resolve()
    assert saved['routed_hardware_sha256'] == selected['sha256']
    assert saved['core_resources'] == selected['core']
    assert saved['clock_period_ns'] == 12 and saved['fixture_FF'] == 94
    assert saved['physical_activity_unknown_records'] == 0
    # Bind the independent detailed audit's own source and export certificate.
    auditor = item.get('auditor_file')
    if auditor:
        bind(auditor, saved['auditor_sha256'])
    else:
        candidates = [W / 'ottt_representative/audit_power16_rep3_12_certified.py',
                      W / 'lutceil_e7/audit_power16_lutceil_12_certified.py', W / 'audit_power16_12_certified.py']
        matched = [p for p in candidates if p.is_file() and sha(p) == saved['auditor_sha256']]
        assert len(matched) == 1
        bind(matched[0], saved['auditor_sha256'])
    certificate = saved.get('certified_export_audit')
    assert certificate and certificate['status'] == 'pass_exact_derived_export_reproduction'
    read(certificate['export_binding_file'], {'pass_exact_annotation_path_binding'})
    read(certificate['SDF_structure_certificate_file'], {'pass_certified_additive_SDF_structure_derivative'})
    interval = saved['native_interval_audit']
    duration, count = interval['duration_ps'], interval['scalar_updates']
    assert isinstance(duration, int) and duration > 0 and isinstance(count, int) and count > 0
    assert interval['requests'] == interval['retirements'] and interval['requests'] > 0
    xml = bind(file.parent / 'power_xpe.xml', saved['power_xpe_sha256'])
    root = ET.parse(xml).getroot()
    supplies = root.findall('ENVIRONMENT/VOLTAGESOURCES/SOURCE')
    watts = sum((Fraction(Decimal(s.attrib['voltage'])) * Fraction(Decimal(s.attrib['icc']))
                 for s in supplies), Fraction(0))
    exact = watts * duration / count
    assert math.isclose(float(watts), saved['dynamic_power_W'], rel_tol=1e-12, abs_tol=1e-12)
    assert math.isclose(float(exact), saved['estimated_dynamic_energy_pJ_per_scalar_update'], rel_tol=1e-12, abs_tol=1e-9)
    if 'scalar_updates' in item:
        assert count == item['scalar_updates'] and duration == item['ROI_duration_ps']
    assert math.isclose(saved['dynamic_energy_J'], float(watts) * duration * 1e-12, rel_tol=1e-12, abs_tol=1e-30)
    # Transitively hash-bind the detailed audit inputs. The previously accepted
    # physical audit is not repeated a third time inside this report generator.
    evidence = read(file.parent / 'evidence.json')
    replay = read(Path(evidence['replay_dir']) / 'replay_checks.json', {'timing_pass_activity_pending'})
    native = read(replay['native_check_file'], {'pass'})
    read(replay['golden_check_file'], {'pass'})
    expectation = read(replay['cohort_expectation_file'])
    cohort = expectation['cohorts'][native['cohort']]
    assert cohort['operations'] == count
    expected_operand_file = bind(cohort['expected_outputs_file'])
    export = Path(replay['export_artifacts_file'])
    read(export)
    read(export.parent / 'provenance.json')
    return dict(power_audit_file=str(file), power_audit_sha256=sha(file), engine=engine,
                routed_hardware_file=selected['file'], routed_hardware_sha256=selected['sha256'],
                core=saved['core_resources'], dynamic_power_W=float(watts), duration_ps=duration,
                scalar_updates=count, requests=interval['requests'], retirements=interval['retirements'],
                estimated_fixture_dynamic_pJ_per_scalar=float(exact),
                serialized_exact_energy_fraction=dict(numerator=exact.numerator, denominator=exact.denominator),
                scope=saved['scope'], cohort=native['cohort'], certified_export=certificate,
                expected_operand_file=str(expected_operand_file), expected_operand_sha256=sha(expected_operand_file),
                annotation_reproduction_scope='Integrity/accounting recheck of previously independently reproduced physical audit; no fresh vendor or full-SAIF rerun.')


def selected_energy(path, routes):
    record = read(path)
    assert record['B'] == 16 and record['clock_ns'] == 12 and record['fixture_FF'] == 94
    accepted = {}
    for key, item in record.get('accepted_power', {}).items():
        try:
            outcome = power(item, routes)
            workload, engine = key.split('/e')
            assert outcome['engine'] == int(engine)
            assert outcome['cohort'] == ('actual_glif' if workload == 'glif' else 'actual128')
            assert workload in ('glif', 'ottt')
            accepted[key] = outcome
        except Exception as error:
            ISSUES.append(dict(stage='selected_energy', category='power_receipt_rejected', key=key,
                               reason=repr(error), accepted=False))
    required = {f'glif/e{e}' for e in (0, 1, 3, 4, 5, 7)} | {f'ottt/e{e}' for e in (0, 1, 3, 4, 5, 6)}
    missing = sorted(required - set(accepted))
    all_missing = sorted((required | {'glif/e2', 'ottt/e2'}) - set(accepted))
    assert record.get('primary_comparison_status') == 'pass' and not missing, ('Primary energy incomplete', missing)
    return dict(accepted_power=accepted, missing_primary=missing, missing_all_attempted=all_missing,
                all_attempted_complete=not all_missing and record.get('all_attempted_control_status') == 'pass',
                retained_failures=record.get('retained_failures', []), evidence_issues=record.get('evidence_issues', []),
                GLIF_scope='Bounded representative64 arithmetic capture after common zero filtering',
                OTTT_scope='Deliberately selected stress/coverage capture; separate from representative OTTT below')


def rep_energy(path, routes):
    record = read(path, {'pass_representative_OTTT_selected_energy'})
    assert record['B'] == 16 and record['clock_ns'] == 12 and record['fixture_FF'] == 94
    assert set(record['accepted_energy']) == {'1', '5', '6'} and not record['failures']
    powers = {key: power(item, routes) for key, item in record['accepted_energy'].items()}
    assert all(item['cohort'] == 'actual_ottt_representative' for item in powers.values())
    assert len({item['scalar_updates'] for item in powers.values()}) == 1
    return dict(accepted_power=powers, scope='Bounded representative64 OTTT arithmetic windows; beta128 shift control mandatory',
                retained_failures=record['failures'])


def glif(path):
    reference = read(path, {'pass'})
    full = read(S / 'stage2_results.json', {'complete_integer_neuron_public_test'})
    packed = read(S / 'stage3_results.json', {'pass_exact_packed_feedback_and_stream_screen'})
    read(S / 'stage3_acceptance.json', {'pass_and_proceed_to_RTL'})
    assert reference['samples'] == full['samples'] == 10000 and packed['samples'] == 64
    with np.load(S / 'stage2_logits.npz') as integer, np.load(S / 'stage3_logits.npz') as p:
        with np.load(C.parent / 'public_model_trial/full_test_logits_v3.npz') as floating:
            correct = int((integer['logits'].argmax(1) == integer['labels']).sum())
            fc = int((floating['logits'].argmax(1) == integer['labels']).sum())
            changed = int((integer['logits'].argmax(1) != floating['logits'].argmax(1)).sum())
        assert np.array_equal(p['logits'], integer['logits'][:64])
    assert (correct, fc, changed) == (reference['correct'], reference['float_correct'], reference['class_disagreements'])
    assert packed['all_logits_bit_identical_to_integer_reference'] and packed['state_spike_arithmetic_mismatches'] == 0
    assert all(-32768 <= endpoint <= 32767 for key in ['observed_old_state_range', 'observed_next_state_range'] for endpoint in reference[key])
    total = packed['total']
    adaptive, fixed = total['issues']['adaptive_post'], total['issues']['fixed_split2']
    return dict(model='Published GLIF ResNet18/CIFAR10 T2', full_samples=10000,
                float_correct=fc, integer_correct=correct, conversion_changed_predictions=changed,
                exact_feedback_samples=64, exact_feedback_raw_updates=total['raw_operations'],
                packing_state_spike_mismatches=0, packing_logits_bit_equal=True,
                arithmetic_updates=total['arithmetic_operations'], adaptive_issues=adaptive, fixed_split_issues=fixed,
                adaptive_issue_penalty_fraction=adaptive / fixed - 1,
                useful_operations_per_adaptive_issue=total['arithmetic_operations'] / adaptive,
                narrow_fraction=total['narrow9_arithmetic_operations'] / total['arithmetic_operations'],
                observed_signed16_bounds_fit=True, accuracy_scope='Integer-neuron conversion with FP32 synapse/BN/readout; exact packing preserves that declared integer neuron.')


def arithmetic(path):
    record = read(path, {'pass_mathematics_and_stimulus_preparation_no_RTL_run'})
    prior = read(S / 'stage3_algebra.json', {'pass'})
    assert record['arithmetic_mismatches'] == prior['failures'] == 0
    assert record['signed16_scalar_cases'] == record['signed16_fixed_split_cases'] == 16842752
    assert record['shift128_cases'] == 65536 and prior['postcorrected_pairs'] == 67371008
    bind(S / 'stage3_algebra.json', record['original_unchanged_narrow_pair_proof_sha256'])
    prep = read(W / 'preparation_v2.json', {'prepared_uncompiled_unrouted_v2'})
    assert prep['B'] == 16 and prep['full_U_domain'] == [-32768, 32767]
    assert prep['narrow_U_domain'] == [-256, 255] and prep['coefficient_domain'] == [0, 256]
    return dict(signed16_scalar_cases=record['signed16_scalar_cases'],
                signed16_fixed_split_cases=record['signed16_fixed_split_cases'],
                exact_narrow_pair_cases=prior['postcorrected_pairs'], shift128_cases=record['shift128_cases'],
                arithmetic_mismatches=0,
                scope='Exhaustive declared integer arithmetic; source/domain binding. Native protocol, model feedback and routed timing are separate gates.')


def model_runs(path, kind, selected_run=None):
    record = read(path)
    if kind == 'ottt':
        assert record['status'] == 'full_evaluation_passed'
        bind(BENCH / 'verify_ottt_benchmarks.py', record['audit_source_sha256'])
        read(bind(BENCH / 'ottt_source_manifest.json', record['source_manifest_sha256']))
        chosen = ['cifar10_T6_n64_a2', 'cifar10_full10000_a0']
    else:
        assert record['status'] == 'bounded_results_audited'
        bind(BENCH / 'verify_bntt_benchmarks.py', record['auditor_sha256'])
        chosen = [selected_run]
    outcomes = {}
    for name in chosen:
        checked = record['runs'][name]
        assert checked['status'] == 'passed'
        result_file = bind(BENCH / name / 'results.json', checked['result_sha256'])
        logits_file = bind(BENCH / name / 'logits.npz', checked['logits_sha256'])
        result = read(result_file)
        with np.load(logits_file) as arrays:
            assert np.isfinite(arrays['float']).all() and np.isfinite(arrays['integer']).all()
            labels = arrays['labels']
            correct = {key: int((arrays[key].argmax(1) == labels).sum()) for key in ('float', 'integer')}
            assert correct == {key: checked['correct'][key] for key in ('float', 'integer')}
            if 'packed' in arrays.files:
                assert np.array_equal(arrays['integer'], arrays['packed'])
                assert result['state_mismatches'] == result['spike_mismatches'] == 0
            changed = int((arrays['integer'].argmax(1) != arrays['float'].argmax(1)).sum())
        assert result['operation_counts']['packed_mismatches'] == 0
        if kind == 'ottt':
            width = checked['width_acceptance']
            assert width['width'] == 16 and width['old_operand_bounds_fit'] and width['every_post_reset_stored_state_bounds_fit']
            expected_changed = checked['changed_predictions']
            fields = [('checkpoint_sha256', BENCH / 'cifar10_ottta.pth'),
                      ('data_sha256', C.parent / 'public_model_trial/full_test10000.npz'),
                      ('contract_sha256', BENCH / 'ottt_contract.md')]
            fields += [('runner_sha256', BENCH / 'run_ottt_v3.py'), ('integer_sha256', BENCH / 'ottt_integer_v2.py')] if name == chosen[0] else [
                      ('runner_sha256', BENCH / 'run_ottt_stream.py'), ('adapter_sha256', BENCH / 'ottt_integer_v3.py'), ('packing_sha256', BENCH / 'ottt_integer_v2.py')]
        else:
            assert checked['samples'] == 64 and checked['fixed16_hardware_domain_supported']
            expected_changed = checked['changed_integer_vs_float_predictions']
            fields = [(field, BENCH / filename) for field, filename in [
                ('checkpoint_sha256', 'bntt_pretrained_tiny_t30.pth.tar'), ('dataset_sha256', 'tiny-imagenet-200.zip'),
                ('contract_sha256', 'bntt_contract.md'), ('runner_sha256', 'run_bntt.py'),
                ('adapter_sha256', 'bntt_integer.py'), ('packing_sha256', 'ottt_integer_v2.py'),
                ('predeclared_subset_sha256', 'bntt_predeclared_subset.json')]]
        assert changed == expected_changed
        for field, file in fields:
            bind(file, result[field])
        assert all(-32768 <= bounds[key] <= 32767 for bounds in result['range_by_layer'].values()
                   for key in ['old_min', 'old_max', 'state_min', 'state_max'])
        outcomes[name] = checked | dict(result_file=str(result_file), logits_file=str(logits_file),
                                       packing_accuracy_gain_claimed=False)
    return dict(model='Published OTTT vanillaLIF VGG11/CIFAR10 T6' if kind == 'ottt' else 'Published BNTT SNN/TinyImageNet T30',
                runs=outcomes, full_evaluation=(kind == 'ottt'),
                unselected_run_status_context={name: child.get('status') for name, child in record['runs'].items() if name not in chosen},
                coefficient=128 if kind == 'ottt' else 253,
                exact_zero_DSP_constant_control='ceil(U/2)' if kind == 'ottt' else 'ceil(253U/256)=U-floor(3U/256)',
                BNTT_constant_control_hardware_measured=False,
                scope='Full10k classification plus separate64 exact feedback' if kind == 'ottt' else 'Predeclared64 held-out subset, never full TinyImageNet accuracy')


def e8(path, routes):
    record = read(path, {'pass_narrow_domain_cost_ablation'})
    assert record['B'] == 16 and record['legal_E8_signed_bits'] == 9 and record['clock_ns'] == 12 and record['fixture_FF'] == 94
    wide, narrow = route(record['selected_E5_hardware_file'], 5), route(record['selected_E8_hardware_file'], 8)
    assert wide['sha256'] == routes['5']['sha256']
    assert wide['core'] == record['E5_core'] and narrow['core'] == record['E8_core']
    delta = {key: wide['core'][key] - narrow['core'][key] for key in ('LUT', 'FF', 'DSP')}
    assert delta == record['E5_minus_E8_resources']
    assert len(record['native']) == 4
    for native in record['native']:
        read(bind(native['acceptance_file'], native['acceptance_sha256']), {'pass'})
    return dict(E5_core=wide['core'], E8_core=narrow['core'], combined_admission_and_wide_support_cost=delta,
                scope=record['interpretation'], E8_legal_state_bits=9, E8_full16_baseline=False, E8_energy_measured=False)


def e2(path):
    record = read(path)
    bind(C / 'lut_isolation/verify_eof_repair_control_pair_v1.py', record['reviewer_sha256'])
    bind(C / 'lut_isolation/eof_repair_control_v2/preparation.json', record['preparation_sha256'])
    assert record['gates'] and all(record['gates'].values())
    assert record['rows'] == 17413 and record['valid_rows'] == 8704
    for variant in ('raw', 'balanced'):
        child = read(record[variant]['path'])
        assert child['variant'] == variant
    return dict(status=record['status'], replay_resolved=record['original_frozen_replay_resolved'],
                bounded_conclusion=record['bounded_conclusion'], physical_hardware_proven=False,
                historical_signed12_diagnostic_only=True)


def differences(powers, adaptive, baseline):
    if adaptive not in powers or baseline not in powers:
        return None
    a, b = powers[adaptive], powers[baseline]
    assert a['scalar_updates'] == b['scalar_updates']
    assert a['expected_operand_sha256'] == b['expected_operand_sha256']
    value, reference = a['estimated_fixture_dynamic_pJ_per_scalar'], b['estimated_fixture_dynamic_pJ_per_scalar']
    return dict(adaptive_pJ=value, baseline_pJ=reference,
                energy_change_fraction=value / reference - 1 if reference else None,
                energy_saving_fraction=1 - value / reference if reference else None,
                scalar_updates=a['scalar_updates'], scope='Vendor-estimated full94FFfixture dynamic energy, not board or whole-neuron energy')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for option in ('selected-energy', 'ottt-representative-closure', 'bntt-acceptance', 'e8-closure', 'e2-verdict', 'output-prefix'):
        ap.add_argument('--' + option, required=True)
    ap.add_argument('--routes', default=str(W / 'route_resolved_acceptance_a1.json'))
    ap.add_argument('--e7-route', default=str(W / 'lutceil_e7/hardware/route12_e7_close_a0/hardware.json'))
    ap.add_argument('--ottt-acceptance', default=str(BENCH / 'benchmark_acceptance.json'))
    ap.add_argument('--glif-stage2', default=str(S / 'stage2_acceptance.json'))
    ap.add_argument('--bntt-run', default='tiny_T30_n64_a2')
    ap.add_argument('--prior-work', default=str(C / 'prior_art/targeted_followup/followup_manifest.json'))
    ap.add_argument('--retained-context', action='append', default=[])
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    prefix = Path(args.output_prefix).resolve()
    output, markdown = Path(str(prefix) + '.json'), Path(str(prefix) + '.md')
    assert not output.exists() and not markdown.exists(), 'Retain all frozen reports'
    assert re.fullmatch(r'[a-zA-Z0-9_-]+', args.bntt_run)
    bind(__file__)
    stages = {}
    stages['arithmetic'] = stage('arithmetic', W / 'domain_acceptance_glif_v2.json', arithmetic)
    stages['routes'] = stage('routes', args.routes, lambda p: all_routes(p, args.e7_route))
    routes = stages['routes'].get('evidence', {}).get('selected', {})
    stages['GLIF'] = stage('GLIF', args.glif_stage2, glif)
    stages['OTTT'] = stage('OTTT', args.ottt_acceptance, lambda p: model_runs(p, 'ottt'))
    stages['BNTT'] = stage('BNTT', args.bntt_acceptance, lambda p: model_runs(p, 'bntt', args.bntt_run))
    stages['E8'] = stage('E8', args.e8_closure, lambda p: e8(p, routes))
    stages['main_energy'] = stage('main_energy', args.selected_energy, lambda p: selected_energy(p, routes))
    stages['OTTT_representative_energy'] = stage('OTTT_representative_energy', args.ottt_representative_closure, lambda p: rep_energy(p, routes))
    stages['original_E2_diagnostic'] = stage('original_E2_diagnostic', args.e2_verdict, e2)
    stages['prior_work'] = stage('prior_work', args.prior_work, lambda p: read(p, {'bounded_targeted_followup_complete_method_equivalence_not_closed'}))
    main_powers = stages['main_energy'].get('evidence', {}).get('accepted_power', {})
    rep_powers = stages['OTTT_representative_energy'].get('evidence', {}).get('accepted_power', {})
    comparisons = {f'GLIF_E5_vs_E{e}': differences(main_powers, 'glif/e5', f'glif/e{e}') for e in (1, 3, 4, 7)}
    comparisons |= {f'OTTT_representative_E5_vs_E{e}': differences(rep_powers, '5', str(e)) for e in (1, 6)}
    comparisons = {key: value for key, value in comparisons.items() if value is not None}
    if stages['main_energy']['accepted'] and not stages['main_energy']['evidence']['all_attempted_complete']:
        ISSUES.append(dict(stage='main_energy', category='all_attempted_control_energy_incomplete',
                           missing=stages['main_energy']['evidence']['missing_all_attempted'], accepted=False))
    if stages['original_E2_diagnostic']['accepted'] and not stages['original_E2_diagnostic']['evidence']['replay_resolved']:
        ISSUES.append(dict(stage='original_E2_diagnostic', category='original_numerical_discrepancy_remains_unresolved',
                           reason=stages['original_E2_diagnostic']['evidence']['bounded_conclusion'], accepted=False))
    retained = [stage('retained_context', p, lambda path: read(path)) for p in args.retained_context]
    limitations = [
        'Fixed signed16 storage/interface and unit1/256; signed9 is internal pair eligibility, not workload-specific stored precision.',
        'Actual adjacent membranes and matching coefficients select pair versus full16 singleton after common zero filtering; no exponent, rescaling, rounding approximation, reordering or accuracy gain.',
        'Exactness is relative to declared integer neurons; FP32 synapses/BN/readout remain. Model conversion can change predictions.',
        'GLIF energy is bounded representative64 activity. OTTT representative windows are separate from deliberate wide-value stress evidence.',
        'Estimated dynamic energy includes the common94FF fixture; no board/static/memory/filter/full-accelerator energy or full-neuron latency claim.',
        'OTTTbeta128 has an exact zero-DSP shift control. BNTTbeta253 has an exact shift/add identity; its specific hardware has not been measured.',
        'E8 subtraction measures combined admission and wide fallback cost; it is not isolated controller-only area and E8 is not a full16 baseline.',
        'Generic narrowness-driven dynamic packing, signed correction and exact spill recovery have prior art. No first-ever claim or publication-strength guarantee follows.',
        'Four full-method access gaps remain: Ou2024, CuiICFPT2024, UDP2026 full paper, McKeownSiPS2008 original runtime/overflow details.',
        'Historical signed12 results and any rejected/incomplete timing/activity evidence provide no accepted fixed16 energy.',
        'AdEx, MNIST, DVS-Gesture and FireFly checkpoints/whole accelerators have not been reproduced by these leakage tests.']
    complete = all(s['accepted'] for s in stages.values()) and not ISSUES
    result = dict(status='explicit_evidence_report_complete_with_stated_limits' if complete else 'explicit_evidence_report_with_open_or_failed_gates',
                  generated_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  contract=dict(stored_state_bits=16, scalar_input_bits=16, internal_pair_signed_bits=9,
                                beta_range=[0, 256], unit_denominator=256, operation='ceil(beta*U/256)',
                                part='xc7a100tcsg324-1', period_ns=12, fixture_FF=94),
                  adaptive=True, adaptation='Actual-U signed9 admission and same-coefficient pair; otherwise exact signed16 singleton',
                  candidate_contributions=[
                      'Exact rounded signed membrane-leakage packing/decoder with exhaustive safety conditions.',
                      'Actual-membrane pair admission with full16 fallback while stored precision stays fixed.',
                      'Matched implementation, combined admission-cost ablation, public LIF/GLIF exact feedback, and measured applicability trade-offs.'],
                  novelty_limits='These are scoped candidate contributions. Fixed split arithmetic and generic dynamic narrow-operand packing are established ideas; the bounded review does not prove absence of an equivalent prior method.',
                  stages=stages, energy_comparisons=comparisons, evidence_issues=ISSUES,
                  explicitly_retained_context=retained, quantitative_closure_complete=complete,
                  strong_publication_claim_established=False, first_ever_claim_established=False,
                  limitations=limitations, evidence_sha256=dict(sorted(PINS.items())),
                  verification_scope='Independent hash binding and numerical/resource/accounting checks of explicit accepted receipts; prior physical/native/model executions are not repeated.')
    lines = ['# Fixed16 membrane leakage evidence', '',
             'Adaptive packing selects two signed9 membrane operations or one full signed16 operation from actual membrane values. Stored precision and integer units stay fixed.', '',
             f'Closure: **{result["status"]}**. The report does not certify ISCAS strength or first-ever novelty.', '']
    if stages['routes']['accepted']:
        area = stages['routes']['evidence']
        a, b = area['E5_vs_E1']['adaptive_core'], area['E5_vs_E1']['fixed_split_core']
        lines += [f'E5 uses {a["LUT"]} LUTs, {a["FF"]} fabric FFs and {a["DSP"]} DSP; E1 fixed split uses {b["LUT"]} LUTs, {b["FF"]} FFs and {b["DSP"]} DSP. This is {100*area["E5_vs_E1"]["LUT_reduction_fraction"]:.2f}% fewer LUTs and {100*area["E5_vs_E1"]["FF_reduction_fraction"]:.2f}% fewer FFs under the common16bit/12ns/94FF fixture.', '']
    if stages['arithmetic']['accepted']:
        d = stages['arithmetic']['evidence']
        lines += [f'Zero arithmetic mismatches across {d["exact_narrow_pair_cases"]:,} exhaustive narrow pairs, {d["signed16_scalar_cases"]:,} full16 scalar cases and {d["signed16_fixed_split_cases"]:,} fixed-split cases. Hardware protocol/timing and neural feedback are separately audited.', '']
    if stages['GLIF']['accepted']:
        d = stages['GLIF']['evidence']
        lines += [f'GLIF/CIFAR10: FP32 {d["float_correct"]}/10000, integer {d["integer_correct"]}/10000, {d["conversion_changed_predictions"]} changed predictions from conversion. The64-image packed feedback has zero state/spike mismatches and identical integer logits. E5 uses {d["adaptive_issues"]:,} issues versus E1 {d["fixed_split_issues"]:,} ({100*d["adaptive_issue_penalty_fraction"]:.3f}% more).', '']
    for key in ('OTTT', 'BNTT'):
        if stages[key]['accepted']:
            model = stages[key]['evidence']
            for name, d in model['runs'].items():
                integer, floating = d['correct']['integer'], d['correct']['float']
                lines += [f'{key}/{name}: FP32 {floating}/{d["samples"]}, integer {integer}/{d["samples"]}; exact packing preserves the declared integer outputs. Adaptive issue penalty against fixed two-lane: {100*d["adaptive_issue_overhead_vs_fixed_two_lane_fraction"]:.3f}%. {model["scope"]}.', '']
    if stages['E8']['accepted']:
        d = stages['E8']['evidence']
        delta = d['combined_admission_and_wide_support_cost']
        lines += [f'Combined membrane admission/full16 support adds {delta["LUT"]:+d} LUTs, {delta["FF"]:+d} FFs and {delta["DSP"]:+d} DSPs relative to restricted signed9 E8. This is not controller-only area.', '']
    if comparisons:
        lines += ['Accepted representative energy comparisons:', '']
        for key, d in comparisons.items():
            change = d['energy_change_fraction']
            label = f'{100*abs(change):.2f}% ' + ('lower' if change < 0 else 'higher') if change is not None else 'undefined ratio'
            lines.append(f'- {key}: E5 {d["adaptive_pJ"]:.6f} pJ/scalar; baseline {d["baseline_pJ"]:.6f} pJ/scalar; E5 {label}.')
        lines += ['', 'These are vendor-estimated dynamic values for the common fixture and bounded arithmetic capture.', '']
    if ISSUES:
        lines += ['Open/rejected gates:', ''] + [f'- {d["stage"]}: {d["category"]}; {d.get("reason", d.get("path", ""))}.' for d in ISSUES] + ['']
    if stages['original_E2_diagnostic']['accepted']:
        lines += [stages['original_E2_diagnostic']['evidence']['bounded_conclusion'], '']
    lines += ['Prior-work review remains bounded by four inaccessible full methods. The plausible contribution is the exact rounded leakage decoder, actual-membrane admission, fixed stored precision and measured trade-offs. Neither packing alone nor equal integer accuracy establishes a strong paper.', '',
              'The scope excludes board measurements, memory/filter costs, complete-neuron latency and AdEx. Beta128 shift and beta253 shift/add controls constrain where DSP packing is useful.', '',
              f'All explicit records and SHA256 bindings: `{output}`.', '']
    # Detect changes during report generation; never freeze a mixed snapshot.
    for filename, pin in PINS.items():
        assert sha(filename) == pin, ('Evidence changed while generating report', filename)
    if args.dry_run:
        print(json.dumps(dict(status='checked_not_frozen', final_status=result['status'], stages={k:v['status'] for k,v in stages.items()}, pins=len(PINS), issues=ISSUES), indent=2))
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    markdown.write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps(dict(status=result['status'], report=str(markdown), evidence=str(output), evidence_records=len(PINS), open_gates=len(ISSUES)), indent=2))


if __name__ == '__main__':
    main()
