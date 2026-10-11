"""Additive two-workload E2 failure audit; never launch jobs or accept energy."""
from pathlib import Path
import collections
import json
import re
import sys

sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent
sys.path.insert(0, str(P.parent))
sys.path.insert(0, str(P))
import prepare_fixed16_final_report_v1 as evidence
import certify_energy_export
from audit_fixed16_E2_stress_failure_a0 import decode


def audit(workload, attempt, native, rows, valid_rows, expected_failures, expected_duration):
    tag = f'{workload}_e2_{attempt}_a0_e2'
    replay = P / 'hardware' / ('replay12_' + tag)
    golden = P / 'hardware' / ('golden12_' + tag)
    export = P / 'hardware' / ('export12_' + tag)
    raw = P / 'hardware' / ('export_raw12_' + tag)
    route = P / 'hardware/route12_e2_a1/hardware.json'
    progress_path = P / f'energy_recovery_{workload}_e2_{attempt}_a0_e2_progress.json'
    parent_log = P / f'energy_recovery_{workload.upper()}_energy_e2_{attempt}_a0.log'
    progress = evidence.read(progress_path, {'completed_with_retained_failures'})
    assert progress['B'] == 16 and progress['workload'] == workload and progress['engines'] == [2]
    assert progress['stages'] == [['golden', 2], ['export', 2]]
    assert progress['failures'] == [dict(engine=2, stage='replay', reason='AssertionError()', accepted_energy=False)]
    selected = evidence.route(route, 2)
    assert {key: selected['core'][key] for key in ['LUT', 'FF', 'DSP']} == dict(LUT=340, FF=88, DSP=0)
    certified = certify_energy_export.verify(export)
    assert certified['status'] == 'pass_exact_derived_export_reproduction'
    binding = evidence.read(export / 'export_binding_certificate.json')
    certificate = evidence.read(export / 'sdf_structure_certificate.json')
    assert binding['hardware_file'] == str(route.resolve()) and binding['hardware_sha256'] == selected['sha256']
    assert certificate['appended_closing_parentheses'] == 3
    assert certificate['derivative_structural_audit']['strict_structurally_balanced']
    assert certificate['derivative_structural_audit']['direct_root_cell_count'] == 704
    for folder in [raw, export]:
        evidence.read(folder / 'artifacts.json')
        evidence.read(folder / 'provenance.json')
    export_job = evidence.read(raw / 'export.job.json')
    export_log = evidence.bind(raw / 'export.log', export_job['log_sha256'])
    assert export_job['returncode'] == 0 and 'FRONTIER_EXPORT PASS' in export_log.read_text()
    golden_check = evidence.read(golden / 'golden_checks.json', {'pass'})
    assert (golden_check['B'], golden_check['engine'], golden_check['replay_rows_checked'], golden_check['valid_rows_checked']) == (16, 2, rows, valid_rows)
    logs, jobs = [], []
    for folder in [golden, replay]:
        provenance = evidence.read(folder / 'provenance.json')
        group_logs, group_jobs = [], []
        for i in range(4):
            job = evidence.read(folder / f'tool_{i}.job.json')
            log_path = evidence.bind(folder / f'tool_{i}.log', job['log_sha256'])
            profile = folder / f'tool_{i}.memory_profile.json'
            assert job['source_sha256'] == {**provenance, str(profile.resolve()): evidence.sha(profile)}
            assert job['returncode'] == 0 and Path(job['cwd']).resolve() == folder.resolve()
            assert not any(item in job['argv'] for item in ['-notimingchecks', '-nospecify', '-sdfnowarn', '-sdfnoerror'])
            group_logs.append(log_path.read_text())
            group_jobs.append(job)
        logs.append(group_logs)
        jobs.append(group_jobs)
    assert not any(re.search(r'\b(?:WARNING|ERROR):|[Tt]iming [Vv]iolation', text) for group in logs for text in group)
    annotated = [line for line in logs[1][2].splitlines() if 'SDF backannotation was successful' in line]
    assert len(annotated) == 1 and '/export12_' + tag + '/routed.sdf' in annotated[0]
    assert 'root module "tb_sequential_energy_replay16/dut"' in annotated[0]
    argv = jobs[1][2]['argv']
    assert '-maxdelay' in argv and '-transport_int_delays' in argv
    for flag in ['-pulse_r', '-pulse_int_r', '-pulse_e', '-pulse_int_e']:
        assert argv.count(flag) == 1 and argv[argv.index(flag) + 1] == '0'
    trace = P / 'hardware' / native / 'trace2.txt'
    assert f'TRACE={str(trace.resolve()).replace(chr(92), "/")}' in jobs[1][3]['argv']
    assert f'ROWS={rows}' in jobs[1][3]['argv']
    failures = []
    controls = ['in_ready', 'take', 'out_valid', 'out_count', 'narrow_mode']
    matches = re.findall(r'REPLAY mismatch E2 row(\d+) got([^ ]+) expected([^\s]+)\s+Time: ([\d.]+) ns', logs[1][3])
    for row, got, expected, ns in matches:
        g, e = decode(got), decode(expected)
        assert all(g[key] == e[key] for key in controls)
        failures.append(dict(row=int(row), simulation_time_ns=float(ns), got=g, expected=e,
            control_fields_equal=True, lane0_error=g['lane0_signed16'] - e['lane0_signed16'],
            lane1_error=g['lane1_signed16'] - e['lane1_signed16']))
    assert [(item['row'], item['got']['data_hex'], item['expected']['data_hex']) for item in failures] == expected_failures
    assert 'FRONTIER_ROUTE_REPLAY PASS E2' not in logs[1][3]
    assert f'FRONTIER_ROUTE_REPLAY PASS E2 ROWS {rows} CHECKED {rows} VALID_ROWS {valid_rows}' in logs[0][3]
    queue = collections.deque()
    by_row = {item['row']: item for item in failures}
    trace_path = evidence.bind(trace)
    native_lines = trace_path.read_text().splitlines()
    assert len(native_lines) == rows
    for line in native_lines:
        f = line.split()
        row, u, beta = int(f[0]), int(f[5], 16), int(f[6], 16)
        accept = int(f[2]) and int(f[7]) and int(f[4]) > 0
        retire = int(f[9]) and int(f[3])
        assert bool(int(f[13])) == bool(accept) and bool(int(f[14])) == bool(retire)
        if accept:
            queue.append(dict(row=row, u=u, beta=beta, take=int(f[8])))
        if retire:
            assert queue
            operation = queue.popleft()
            if row in by_row:
                scalar, packed = [], 0
                for lane in range(operation['take']):
                    a = (operation['u'] >> (16 * lane)) & 65535
                    a = a - 65536 if a & 32768 else a
                    b = (operation['beta'] >> (9 * lane)) & 511
                    leak = -((-a * b) // 256)
                    scalar.append(dict(U=a, beta=b, scalar_ceil=leak))
                    packed |= (leak & 65535) << (16 * lane)
                assert packed == int(f[11], 16) == int(by_row[row]['expected']['data_hex'], 16)
                by_row[row]['native_accept_row'] = operation['row']
                by_row[row]['source_operands'] = scalar
    assert not queue
    saif = evidence.bind(replay / 'activity.saif')
    with saif.open() as stream:
        header = stream.read(500)
    actual_duration, = re.findall(r'\(DURATION\s+(\d+)\)', header)
    actual_duration = int(actual_duration)
    assert actual_duration == expected_duration
    assert actual_duration != golden_check['roi_duration_ps']
    declared_close = f"FRONTIER_SAIF_CLOSED START_PS {golden_check['roi_start_ps']} END_PS {golden_check['roi_end_ps']} DURATION_PS {golden_check['roi_duration_ps']}"
    assert declared_close in logs[1][3]
    assert not (replay / 'replay_checks.json').exists()
    assert not (P / 'hardware' / ('power12_' + tag) / 'power_audit.json').exists()
    for path in [parent_log, replay / 'activity.tcl']:
        evidence.bind(path)
    return dict(workload=workload, progress_file=str(progress_path.resolve()),
        replay_folder=str(replay.resolve()), selected_route=selected, certified_export=certified,
        full_known_golden_replay_pass=True, full_known_delayed_replay_pass=False,
        all_vendor_job_returncodes_zero=True, certified_original_DUT_SDF_annotation_success=True,
        certified_SDF_704_cells_balanced_with_three_EOF_closures_only=True,
        original_numerical_paths_and_timing_checks_preserved=True, timing_checks_enabled=True,
        max_delay=True, transport_interconnect_delays=True, all_four_pulse_limits_percent=0,
        no_compile_runtime_warning_or_logged_timing_violation=True, observed_failures=failures,
        requested_interval=dict(start_ps=golden_check['roi_start_ps'], end_ps=golden_check['roi_end_ps'], duration_ps=golden_check['roi_duration_ps']),
        actual_partial_SAIF_duration_ps=actual_duration, partial_SAIF_bytes=saif.stat().st_size,
        printed_Tcl_duration_is_completion_proof=False, accepted_energy=False,
        classification='Numerical delayed-replay failure; no observed job-launch, SDF syntax/annotation, logged timing-violation or resource-exhaustion failure.',
        cause='Unresolved. No internal-cell/event trace was acquired for this fixed16 attempt; no identity with the historical signed12 cause is inferred.')


def main():
    target = P / 'fixed16_E2_combined_failures_a0.json'
    md = P / 'fixed16_E2_combined_failures_a0.md'
    assert not target.exists() and not md.exists()
    old_path = P / 'fixed16_E2_stress_failure_a0.json'
    old = evidence.read(old_path, {'audited_new_fixed16_E2_stress_numerical_replay_failure'})
    for path, pin in old['evidence_sha256'].items():
        evidence.bind(path, pin)
    old_md = evidence.bind(P / 'fixed16_E2_stress_failure_a0.md')
    stress = audit('ottt', 'ottt_stress', 'native_actual128_s0_a0', 7340, 3671,
        [(2175, '006d4064', '006d0064'), (2176, '004a4063', '004a0063')], 26090001)
    glif = audit('glif', 'glif_remaining', 'native_actual_glif_s0_a0', 262533, 131328,
        [(5065, '0004e029', '00040029'), (5066, '0002e029', '00020029')], 60770001)
    assert all(item['lane0_error'] == 16384 and item['lane1_error'] == 0 for item in stress['observed_failures'])
    assert all(item['lane0_error'] == -8192 and item['lane1_error'] == 0 for item in glif['observed_failures'])
    assert glif['observed_failures'][0]['native_accept_row'] == 5063
    assert glif['observed_failures'][0]['source_operands'] == [dict(U=124, beta=83, scalar_ceil=41), dict(U=5, beta=162, scalar_ceil=4)]
    evidence.bind(Path(__file__))
    evidence.bind(P / 'tb_energy16_12.sv')
    record = dict(status='audited_both_fixed16_E2_numerical_replay_failures', B=16,
        observed_attempts=dict(OTTT_stress=stress, GLIF_representative=glif),
        both_E2_energy_comparisons_rejected=True, all14_controls_attempted=True,
        all14_controls_pass=False, accepted_primary12_controls_not_replaced_or_waived=True,
        primary12_comparison_acceptance='Separate root-owned selected-evidence verification; this failure audit does not recertify or revoke those independent gates.',
        optimized_LUT_E7_acceptance='Independent evidence; it does not establish the cause of, repair or replace either E2 failure.',
        historical_signed12_causal_identity_established=False, original_files_modified=False,
        vendor_model_jobs_launched=False, process_control_performed=False,
        retained_stress_report=dict(file=str(old_path.resolve()), sha256=evidence.sha(old_path), markdown_file=str(old_md), markdown_sha256=evidence.sha(old_md)),
        checked_hash_count=len(evidence.PINS), evidence_sha256=evidence.PINS)
    target.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    md.write_text(
        'Both new fixed signed16 E2 attempts fail numerical delayed replay and their energy measurements are rejected. Each complete golden replay passes; the original DUT receives successful certified SDF annotation. The selected route has 340 LUTs, 88 core FFs, zero DSPs and positive static timing with the common 94-FF fixture. Both 704-cell SDF derivatives preserve every numerical delay/path/timing check and append only three structural closing parentheses. All vendor receipts return zero; maximum delays, transport interconnect and all four zero pulse limits remain enabled, with no logged warning or timing violation.\n\n'
        'The GLIF attempt first fails at row 5065, at 60,938 ns. Its data is 0004e029 instead of 00040029: signed16 lanes are −8151 and 4 instead of 41 and 4. The low-lane error is −8192; every control field matches. Native acceptance at row 5063 supplied (U, beta) = (124, 83) and (5, 162), whose independently computed ceiling leakage values are 41 and 4. Row 5066 repeats −8151 instead of 41, with the high lane 2 correct, from (124, 83) and (3, 162) at row 5064. The full golden run checks 262,533 rows and 131,328 valid rows. The failing delayed capture has actual SAIF duration 60,770,001 ps, versus 1,575,984,000 ps requested over [167,999, 1,576,151,999] ps.\n\n'
        'The retained OTTT stress attempt first fails at row 2175, at 26,258 ns. Its data is 006d4064 instead of 006d0064: signed16 lanes are 16484 and 109 instead of 100 and 109. The low-lane error is +16384; every control field matches. Native acceptance at row 2173 supplied (200, 128) and (218, 128), giving exact ceilings 100 and 109. Row 2176 repeats +16384 on the low lane, with the high lane correct. Its golden run checks 7,340 rows and 3,671 valid rows. Actual SAIF duration is 26,090,001 ps, versus 44,100,000 ps requested over [167,999, 44,267,999] ps. This stress capture is deliberately selected and is not representative energy evidence.\n\n'
        'Both Tcl scripts continue after the first fatal, close the partial SAIF and print the predeclared requested interval, then encounter the next fatal. Those printed constants do not prove completion. Neither attempt has a delayed-replay acceptance receipt or a power audit; neither partial SAIF is admissible for energy.\n\n'
        'The fixed16 cause remains unresolved. These observations do not establish identity with the historical signed12 carry discrepancy. Previously accepted primary12 comparisons retain their independent gates, but the attempted all14-control gate fails because both E2 comparisons are rejected. Independently accepted optimized LUT E7 evidence does not repair E2 or prove its cause. All original receipts, raw/certified exports, routes and the earlier stress report remain unchanged and are hash-bound in the JSON.\n', encoding='utf-8')
    print(json.dumps(dict(status=record['status'], checked_hash_count=record['checked_hash_count'],
        GLIF_first_failure=glif['observed_failures'][0], both_E2_energy_rejected=True, all14_controls_pass=False), indent=2))


if __name__ == '__main__':
    main()
