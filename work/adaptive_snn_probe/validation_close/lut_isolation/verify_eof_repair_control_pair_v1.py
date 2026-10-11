"""Independent explicit-path verdict for matched raw vs EOF-only LUT replay.

The producer's saved status is not treated as proof: job arguments, source pins,
annotation logs, warnings, full-known-row counts and mismatches are reread.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import sys

sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent
sys.path.insert(0, str(P))
from verify_eof_only_sdf_derivative_v1 import verify
W = P / 'eof_repair_control_v2'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_pins(stamps):
    assert all(sha(name) == stamp for name, stamp in stamps.items())


def one(path, variant, prep):
    path = Path(path).resolve()
    wd = path.parent
    assert path.name == 'diagnostic.json' and wd.parent == W.resolve()
    assert wd.name.startswith('run_' + variant + '_')
    saved = json.loads(path.read_text())
    assert saved['variant'] == variant
    provenance = json.loads((wd / 'provenance.json').read_text())
    check_pins(provenance)
    check_pins(saved['artifact_sha256'])
    assert (wd / 'monitor.sv').read_bytes() == (W / 'monitor.sv').read_bytes()
    assert (wd / 'CARRY4_vendor.v').read_bytes() == (W / 'CARRY4_vendor.v').read_bytes()
    assert (wd / 'run.tcl').read_bytes() == (W / 'run.tcl').read_bytes()
    jobs, logs = [], []
    for index in range(5):
        job_path = wd / f'tool_{index}.job.json'
        log_path = wd / f'tool_{index}.log'
        job = json.loads(job_path.read_text())
        assert Path(job['cwd']).resolve() == wd
        assert job['source_sha256'] == provenance
        assert job['log_sha256'] == sha(log_path)
        assert index == 4 or job['returncode'] == 0
        check_pins(job['source_sha256'])
        jobs.append(job)
        logs.append(log_path.read_text(errors='replace'))
    def normalized(argv):
        result = []
        for token in argv:
            token = token.replace('\\', '/')
            token = token.replace(str(wd).replace('\\', '/'), '<WD>')
            token = token.replace(str((W / 'routed_raw.v').resolve()).replace('\\', '/'), '<NETLIST>')
            token = token.replace(str((W / 'routed_EOF_only_balanced.v').resolve()).replace('\\', '/'), '<NETLIST>')
            result.append(token)
        return result
    commands = [normalized(job['argv']) for job in jobs]
    assert jobs[3]['argv'][1:] == ['-mt', 'off', '-debug', 'all', '-maxdelay',
           '-transport_int_delays', '-pulse_r', '0', '-pulse_int_r', '0', '-pulse_e', '0',
           '-pulse_int_e', '0', '-L', 'work', '-L', 'simprims_ver', '-L', 'secureip',
           '-L', 'unisims_ver', 'tb_sequential_energy_replay', 'glbl', '-s', 'sim']
    runtime = jobs[4]['argv']
    assert f'ROWS={prep["rows"]}' in runtime and f'ROI_LAST={prep["rows"]}' in runtime
    assert 'ROI_FIRST=3' in runtime
    assert 'TRACE=' + prep['trace'].replace('\\', '/') in runtime
    assert not any(option in job['argv'] for job in jobs for option in
                   ['-notimingchecks', '-nospecify', '-sdfnowarn', '-sdfnoerror'])
    annotation = [line for line in logs[3].splitlines() if 'SDF backannotation was successful' in line]
    expected = 'routed.sdf' if variant == 'raw' else 'original_EOF_only_balanced.sdf'
    gates = dict(work_CARRY4_bound='Compiling module work.CARRY4' in logs[3],
                 exactly_one_expected_annotation=len(annotation) == 1 and expected in annotation[0],
                 procedural_annotation_not_ignored='$sdf_annotate will be ignored' not in logs[3],
                 no_compile_or_elaboration_warning=not any(re.search(r'\b(?:WARNING|ERROR):', log) for log in logs[:4]),
                 no_runtime_timing_warning=not re.search(r'\b(?:WARNING|ERROR):|[Tt]iming [Vv]iolation', logs[4]),
                 unchanged_full_monitor_and_primitive=True,
                 original_full_trace_requested=True, active_maxdelay_and_timing_checks=True)
    matches = re.findall(r'REPLAY mismatch E2 row(\d+) got([^ ]+) expected([^\s]+)', logs[4])
    mismatches = [dict(row=int(row), got=got, expected=expected) for row, got, expected in matches]
    passes = re.findall(r'FRONTIER_ROUTE_REPLAY PASS E2 ROWS (\d+) CHECKED (\d+) VALID_ROWS (\d+)', logs[4])
    full = len(passes) == 1 and tuple(map(int, passes[0])) == (prep['rows'], prep['rows'], prep['valid_rows'])
    if matches:
        assert not full
        assert 'Fatal:' in logs[4]
    elif full:
        assert jobs[4]['returncode'] == 0 and 'Fatal:' not in logs[4]
    assert mismatches == saved['replay_mismatches'] and full == saved['complete_trace_pass']
    return dict(path=str(path), producer_status_context_only=saved['status'], gates=gates,
                full_known_row_replay_pass=full, mismatches=mismatches,
                normalized_commands=commands,
                source_receipt_sha256={str(p): sha(p) for p in
                    [path, wd / 'provenance.json', *[wd / f'tool_{i}.{ext}' for i in range(5) for ext in ['log', 'job.json']]]})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--raw', required=True)
    ap.add_argument('--balanced', required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()
    target = Path(args.output).resolve()
    assert not target.exists()
    prep = json.loads((W / 'preparation.json').read_text())
    for section in ['source_sha256', 'prepared_sha256']:
        check_pins(prep[section])
    certificate = verify(prep['certificate'])
    assert certificate['appended_closing_parentheses'] == 3
    raw, balanced = one(args.raw, 'raw', prep), one(args.balanced, 'balanced', prep)
    assert raw['normalized_commands'] == balanced['normalized_commands']
    gates = dict(source_and_artifact_pins_passed=True,
                 all_raw_bytes_tokens_paths_delays_checks_unchanged=True,
                 raw_and_balanced_commands_matched=True,
                 all_raw_annotation_and_timing_gates=all(raw['gates'].values()),
                 all_balanced_annotation_and_timing_gates=all(balanced['gates'].values()))
    if not all(gates.values()):
        status = 'rejected_incomplete_annotation_or_timing_causal_control'
        conclusion = 'An annotation/timing gate failed; no causal resolution is accepted.'
        resolved = False
    elif raw['mismatches'] and balanced['full_known_row_replay_pass']:
        status = 'EOF_only_derivative_resolves_frozen_original_replay'
        conclusion = 'The raw control failed and the EOF-only derivative passed every original known trace row with matched checks and primitive source. This resolves this frozen simulation replay; physical hardware correctness and a primitive/tool defect are not established.'
        resolved = True
    elif raw['mismatches'] and balanced['mismatches']:
        same = raw['mismatches'] == balanced['mismatches']
        status = 'EOF_closure_does_not_resolve_original_numerical_discrepancy'
        conclusion = 'Both controls fail' + (' with the same first mismatch.' if same else ' with different first mismatches.') + ' The syntax defect is real but does not close the numerical discrepancy.'
        resolved = False
    elif raw['full_known_row_replay_pass'] and balanced['full_known_row_replay_pass']:
        status = 'original_failure_not_reproduced_in_matched_control'
        conclusion = 'Both full traces pass in this replay context. Historical causal closure remains incomplete because the raw control did not reproduce its failure.'
        resolved = False
    else:
        status = 'retained_unexplained_control_outcome'
        conclusion = 'The controls do not support resolution; retain both outcomes for further diagnosis.'
        resolved = False
    result = dict(status=status, gates=gates, original_frozen_replay_resolved=resolved,
                  raw=raw, balanced=balanced, certificate_reverification=certificate,
                  rows=prep['rows'], valid_rows=prep['valid_rows'], bounded_conclusion=conclusion,
                  physical_hardware_correctness_proven=False, energy_acceptance=False,
                  original_raw_evidence_modified=False, reviewer_sha256=sha(__file__),
                  preparation_sha256=sha(W / 'preparation.json'))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ['raw', 'balanced']}, indent=2))


if __name__ == '__main__':
    main()
