"""Run one root-coordinated frozen matched original LUT diagnostic variant."""
from pathlib import Path
import argparse
import json
import re
import shutil
import sys

sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent
sys.path.insert(0, str(P))
from verify_eof_only_sdf_derivative_v1 import verify
sys.path.insert(0, str(P.parent.parent / 'selective_energy_trial'))
import run_selective_energy as b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', action='store_true')
    ap.add_argument('--variant', choices=['raw', 'balanced'], required=True)
    ap.add_argument('--attempt', default='a0')
    args = ap.parse_args()
    assert args.run and re.fullmatch(r'[a-zA-Z0-9_-]+', args.attempt)
    prepared = P / 'eof_repair_control_v2'
    prep = json.loads((prepared / 'preparation.json').read_text())
    for section in ['source_sha256', 'prepared_sha256']:
        b.verify(prep[section])
    certificate = verify(prep['certificate'])
    wd = prepared / f'run_{args.variant}_{args.attempt}'
    assert not wd.exists(), 'Retain every diagnostic attempt'
    wd.mkdir()
    for name in ['monitor.sv', 'CARRY4_vendor.v', 'run.tcl']:
        shutil.copyfile(prepared / name, wd / name)
    netlist = prepared / ('routed_raw.v' if args.variant == 'raw' else 'routed_EOF_only_balanced.v')
    stamps = b.pins([Path(__file__), prepared / 'preparation.json',
                     *[Path(p) for p in prep['source_sha256']],
                     *[Path(p) for p in prep['prepared_sha256']], *list(wd.glob('*.*'))])
    b.write(wd / 'provenance.json', stamps)
    commands = [
        [b.VIVADO / 'bin/xvlog.bat', '-d', 'XIL_TIMING', wd / 'CARRY4_vendor.v'],
        [b.VIVADO / 'bin/xvlog.bat', '-sv', '-d', 'ENGINE_ID=2', '-d',
         'DUT_TOP=top_sequential_leak_e2', netlist, wd / 'monitor.sv'],
        [b.VIVADO / 'bin/xvlog.bat', b.VIVADO / 'data/verilog/src/glbl.v'],
        [b.VIVADO / 'bin/xelab.bat', '-mt', 'off', '-debug', 'all', '-maxdelay',
         '-transport_int_delays', '-pulse_r', '0', '-pulse_int_r', '0', '-pulse_e', '0',
         '-pulse_int_e', '0', '-L', 'work', '-L', 'simprims_ver', '-L', 'secureip',
         '-L', 'unisims_ver', 'tb_sequential_energy_replay', 'glbl', '-s', 'sim'],
        [b.VIVADO / 'bin/xsim.bat', 'sim', '-testplusarg', f'TRACE={prep["trace"]}',
         '-testplusarg', f'ROWS={prep["rows"]}', '-testplusarg', 'ROI_FIRST=3',
         '-testplusarg', f'ROI_LAST={prep["rows"]}', '-tclbatch', wd / 'run.tcl']]
    logs = []
    for index, command in enumerate(commands):
        argv = [str(item).replace('\\', '/') for item in command]
        assert not any(item in argv for item in ['-notimingchecks', '-nospecify', '-sdfnowarn', '-sdfnoerror'])
        try:
            log = b.job(argv, wd, f'tool_{index}', stamps, 1.2)
        except AssertionError:
            log = wd / f'tool_{index}.log'
            if index != 4 or not log.is_file() or not re.search(r'REPLAY mismatch E2 row\d+', log.read_text(errors='replace')):
                raise
        logs.append(log)
    elaboration = logs[3].read_text(errors='replace')
    output = logs[4].read_text(errors='replace')
    accepted = [line for line in elaboration.splitlines() if 'SDF backannotation was successful' in line]
    expected_name = 'routed.sdf' if args.variant == 'raw' else 'original_EOF_only_balanced.sdf'
    annotations = len(accepted) == 1 and expected_name in accepted[0]
    mismatches = re.findall(r'REPLAY mismatch E2 row(\d+) got([^ ]+) expected([^\s]+)', output)
    passing = re.findall(r'FRONTIER_ROUTE_REPLAY PASS E2 ROWS (\d+) CHECKED (\d+) VALID_ROWS (\d+)', output)
    full = len(passing) == 1 and tuple(map(int, passing[0])) == (prep['rows'], prep['rows'], prep['valid_rows'])
    gates = dict(work_CARRY4_binding='Compiling module work.CARRY4' in elaboration,
                 original_full_SDF_annotation_accepted=annotations,
                 no_elaboration_warning_or_error=not re.search(r'\b(?:WARNING|ERROR):', elaboration),
                 no_runtime_timing_warning_or_error=not re.search(r'\b(?:WARNING|ERROR):|[Tt]iming [Vv]iolation', output),
                 raw_or_certified_derivative_structure_expected=(args.variant == 'raw' or certificate['appended_closing_parentheses'] == 3),
                 every_original_known_trace_row_passed=full,
                 no_replay_mismatch=not mismatches)
    if all(gates.values()) and args.variant == 'balanced':
        status = 'pass_full_original_known_row_replay_with_EOF_only_derivative'
    elif all(gates.values()):
        status = 'raw_full_replay_passed_but_raw_SDF_structure_invalid'
    elif mismatches and all(value for key, value in gates.items()
                            if key not in ['every_original_known_trace_row_passed', 'no_replay_mismatch']):
        status = 'retained_numerical_replay_failure_under_matched_control'
    else:
        status = 'rejected_annotation_timing_or_replay_gate_incomplete'
    result = dict(status=status, diagnostic_only=True, variant=args.variant,
                  gates=gates, rows_requested=prep['rows'], complete_trace_pass=full,
                  replay_mismatches=[dict(row=int(row), got=got, expected=expected) for row, got, expected in mismatches],
                  original_row914_failure=any(int(row) == 914 for row, _, _ in mismatches),
                  certificate_reverification=certificate,
                  original_netlist_and_raw_SDF_modified=False,
                  balanced_derivative_changes='Append three EOF structural closes; replace exactly one SDF filename argument',
                  original_monitor_and_primitive_unchanged=True, timing_checks_disabled=False,
                  energy_acceptance=False, physical_hardware_correctness_proven=False,
                  paired_raw_vs_balanced_causal_conclusion_requires_both_attempts=True,
                  annotation_success_lines=accepted, artifact_sha256=b.pins(logs))
    b.write(wd / 'diagnostic.json', result)
    b.verify(stamps)
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
