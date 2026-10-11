"""Read-only matched pulse-control audit; preserve unresolved full replay errors."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import sys

sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent
W = P / 'shadow_context_v5'
sys.path.insert(0, str(P))
import sdf_structure_audit_v1 as parser
from verify_eof_only_sdf_derivative_v1 import verify as verify_derivative


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pins(values):
    assert all(sha(path) == pin for path, pin in values.items())


def snapshots(output):
    fields = ['ORIG_AGE', 'SHADOW_AGE', 'ORIG_S', 'SHADOW_S', 'ORIG_CI', 'SHADOW_CI',
              'ORIG_DI', 'SHADOW_DI', 'ORIG_CO', 'SHADOW_CO', 'ORIG_FB', 'SHADOW_FB',
              'ORIG_O', 'SHADOW_O', 'EXPECT_O', 'EXPECT_CO']
    items = []
    for line in output.splitlines():
        if not line.startswith('CAUSAL_SNAPSHOT '):
            continue
        value = dict(re.findall('(' + '|'.join(fields) + r')([^ ]+)', line))
        assert set(value) == set(fields)
        binary_keys = [f for f in fields if not f.endswith('AGE')]
        known = all(re.fullmatch('[0-9a-fA-F]+', value[key]) for key in binary_keys)
        row = dict(line=line, known=known)
        if known:
            numbers = {key: int(value[key], 16) for key in binary_keys}
            carry = numbers['ORIG_CI']  # CYINIT is source-proven constant0.
            expected_o = expected_co = 0
            for bit in range(4):
                s, di = (numbers['ORIG_S'] >> bit) & 1, (numbers['ORIG_DI'] >> bit) & 1
                expected_o |= (s ^ carry) << bit
                carry = carry if s else di
                expected_co |= carry << bit
            assert expected_o == numbers['EXPECT_O'] and expected_co == numbers['EXPECT_CO']
            same = all(numbers['ORIG_' + key] == numbers['SHADOW_' + key] for key in ['S', 'CI', 'DI'])
            settled = float(value['ORIG_AGE']) > .579 and float(value['SHADOW_AGE']) > .579
            row |= dict(same_observed_inputs=same, both_stable_gt579ps=settled,
                        original_wrong=numbers['ORIG_O'] != expected_o,
                        flat_shadow_wrong=numbers['SHADOW_O'] != expected_o,
                        original_O=numbers['ORIG_O'], flat_shadow_O=numbers['SHADOW_O'],
                        expected_O=expected_o, original_age_ns=float(value['ORIG_AGE']),
                        flat_shadow_age_ns=float(value['SHADOW_AGE']))
        items.append(row)
    assert items
    return items


def one(path, pulse, prep):
    path = Path(path).resolve()
    folder = path.parent
    assert folder.parent == W.resolve() and folder.name.startswith(f'run_pulse{pulse}_')
    saved = json.loads(path.read_text())
    assert saved['pulse_limit_percent'] == pulse
    provenance = json.loads((folder / 'provenance.json').read_text())
    pins(provenance)
    pins(saved['artifact_sha256'])
    for name in ['CARRY4_vendor.v', 'monitor_shadow.sv', 'original_and_shadow_full.sdf', 'run.tcl']:
        assert (folder / name).read_bytes() == (W / name).read_bytes()
    jobs, logs, normalized = [], [], []
    for index in range(5):
        job_file, log_file = folder / f'tool_{index}.job.json', folder / f'tool_{index}.log'
        job = json.loads(job_file.read_text())
        assert job['source_sha256'] == provenance and sha(log_file) == job['log_sha256']
        assert Path(job['cwd']).resolve() == folder
        assert job['returncode'] == 0
        argv = [x.replace('\\', '/') for x in job['argv']]
        for forbidden in ['-notimingchecks', '-nospecify', '-sdfnowarn', '-sdfnoerror']:
            assert forbidden not in argv
        normalized.append([x.replace(str(folder).replace('\\', '/'), '<WD>') for x in argv])
        jobs.append(job)
        logs.append(log_file.read_text(errors='replace'))
    argv = jobs[3]['argv']
    for option in ['-pulse_r', '-pulse_int_r', '-pulse_e', '-pulse_int_e']:
        assert argv.count(option) == 1 and argv[argv.index(option) + 1] == str(pulse)
    assert '-maxdelay' in argv and '-transport_int_delays' in argv and '-sdfmax' in argv
    runtime = jobs[4]['argv']
    assert f'ROWS={prep["full_trace_rows"]}' in runtime and f'ROI_LAST={prep["full_trace_rows"]}' in runtime
    assert 'ROI_FIRST=3' in runtime
    annotated = [line for line in logs[3].splitlines() if 'SDF backannotation was successful' in line]
    gates = dict(work_CARRY4_bound='Compiling module work.CARRY4' in logs[3],
                 one_combined_annotation=len(annotated) == 1 and 'original_and_shadow_full.sdf' in annotated[0]
                    and 'root module "tb_sequential_energy_replay"' in annotated[0],
                 annotation_not_ignored='$sdf_annotate will be ignored' not in logs[3],
                 no_compile_or_elaboration_warning=not any(re.search(r'\b(?:WARNING|ERROR):', text) for text in logs[:4]),
                 no_runtime_timing_warning=not re.search(r'\b(?:WARNING|ERROR):|[Tt]iming [Vv]iolation', logs[4]),
                 positive50ps_settled600ps_canary='CAUSAL_CANARY_PASS POSITIVE50PS_SETTLED600PS checks2' in logs[4],
                 snapshots_completed='CAUSAL_PROBE_SNAPSHOTS_COMPLETE' in logs[4])
    mismatch = [dict(row=int(row), got=got, expected=expected) for row, got, expected in
                re.findall(r'REPLAY mismatch E2 row(\d+) got([^ ]+) expected([^\s]+)', logs[4])]
    assert mismatch == saved['replay_mismatches']
    full = re.findall(r'FRONTIER_ROUTE_REPLAY PASS E2 ROWS (\d+) CHECKED (\d+) VALID_ROWS (\d+)', logs[4])
    passed = len(full) == 1 and tuple(map(int, full[0])) == (prep['full_trace_rows'], prep['full_trace_rows'], prep['valid_rows'])
    assert passed == saved['full_original_known_row_replay_pass']
    return dict(path=str(path), sha256=sha(path), pulse_limit_percent=pulse, gates=gates,
                mismatches=mismatch, full_original_known_row_replay_pass=passed,
                observations=snapshots(logs[4]), normalized_commands=normalized,
                artifact_sha256={str(p.resolve()):sha(p) for p in [path, folder/'provenance.json',
                    *[folder/f'tool_{i}.{ext}' for i in range(5) for ext in ['job.json','log']]]})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--zero', required=True)
    ap.add_argument('--hundred', required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()
    target = Path(args.output).resolve()
    assert not target.exists()
    prep = json.loads((W / 'preparation.json').read_text())
    pins(prep['source_sha256']); pins(prep['prepared_sha256'])
    verified = verify_derivative(prep['original_SDF_structure_derivative']['certificate'])
    assert verified['appended_closing_parentheses'] == 3
    original_path = P.parent.parent / 'sequential_paper_trial/hardware/export12_e2_a0/routed.v'
    source = original_path.read_text()
    marker = r'CARRY4 \lut.lane[0].r_reg[11]_i_4'
    assert source.count(marker) == 1
    original_cell = source.split(marker, 1)[1].split(';', 1)[0]
    assert ".CYINIT(1'b0)" in original_cell
    combined_text = (W / 'original_and_shadow_full.sdf').read_text()
    roots, opened, _ = parser.parse(combined_text)
    assert not opened and len(roots[0].direct('CELL')) == 556
    zero, hundred = one(args.zero, 0, prep), one(args.hundred, 100, prep)
    changed = []
    for index, (left, right) in enumerate(zip(zero['normalized_commands'], hundred['normalized_commands'])):
        assert len(left) == len(right)
        for position, (a, b) in enumerate(zip(left, right)):
            if a != b:
                assert index == 3 and position > 0
                option = left[position - 1]
                assert option in ['-pulse_r', '-pulse_int_r', '-pulse_e', '-pulse_int_e'] and (a, b) == ('0', '100')
                changed.append(option)
    assert sorted(changed) == sorted(['-pulse_r', '-pulse_int_r', '-pulse_e', '-pulse_int_e'])
    gates = dict(all_zero_annotation_canary_and_timing_gates=all(zero['gates'].values()),
                 all_hundred_annotation_canary_and_timing_gates=all(hundred['gates'].values()),
                 exactly_four_explicit_pulse_arguments_changed=True,
                 every_other_command_and_source_unchanged=True, original_CYINIT_constant_zero_proven=True)
    qualifying = [r for r in zero['observations'] if r.get('same_observed_inputs') and r.get('both_stable_gt579ps')]
    original_only = any(r['original_wrong'] and not r['flat_shadow_wrong'] for r in qualifying)
    zero_reproduced = any(row['row'] == 914 for row in zero['mismatches'])
    region100 = any(row['row'] == 914 for row in hundred['mismatches'])
    status = 'pass_bounded_pulse_and_context_diagnostic_original_discrepancy_unresolved' if all(gates.values()) else 'rejected_incomplete_pulse_context_comparison'
    conclusions = []
    if zero_reproduced and original_only:
        conclusions.append('The zero-limit combined replay reproduces row914. The original cell has a settled Boolean discrepancy while the flat live-input shadow is correct under matching observed inputs, localizing a context/port-path/event-treatment difference rather than erroneous leakage algebra.')
    if zero_reproduced and not region100 and hundred['mismatches']:
        conclusions.append('Explicit100 limits remove the first row914 failure but leave a later full-replay failure. Simulation behavior is pulse-policy sensitive; the numerical replay is not fixed.')
    elif zero_reproduced and hundred['full_original_known_row_replay_pass']:
        conclusions.append('The100-limit control passes this full trace, but it cannot replace failed zero-limit evidence or establish how command limits override per-cell PATHPULSE values.')
    else:
        conclusions.append('The controls do not establish a complete numerical replay resolution.')
    conclusions.append('Per-bit observer ordering is not an event-region/delta trace; effective short-pulse rejection and a simulator or physical hardware defect remain unproved.')
    result = dict(status=status, gates=gates, zero=zero, hundred=hundred,
                  zero_row914_reproduced=zero_reproduced, zero_original_only_settled_discrepancy=original_only,
                  original_discrepancy_resolved=False, hardware_or_energy_acceptance=False,
                  bounded_conclusions=conclusions,
                  original_raw_evidence_modified=False, timing_checks_waived=False,
                  source_sha256={str(Path(__file__).resolve()):sha(__file__), str(W/'preparation.json'):sha(W/'preparation.json'),
                                 str(original_path):sha(original_path), str(P/'amd_pulse_policy_source_review.md'):sha(P/'amd_pulse_policy_source_review.md')})
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key:value for key,value in result.items() if key not in ['zero','hundred','source_sha256']}, indent=2))


if __name__ == '__main__':
    main()
