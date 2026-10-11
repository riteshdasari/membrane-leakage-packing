"""Run one matched combined-root shadow/pulse diagnostic, only on root request."""
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
from run_shadow_context_v3 import classify
sys.path.insert(0, str(P.parent.parent / 'selective_energy_trial'))
import run_selective_energy as b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', action='store_true')
    ap.add_argument('--pulse', choices=['0', '100'], required=True)
    ap.add_argument('--attempt', default='a0')
    args = ap.parse_args()
    assert args.run and re.fullmatch(r'[a-zA-Z0-9_-]+', args.attempt)
    prepared = P / 'shadow_context_v5'
    prep = json.loads((prepared / 'preparation.json').read_text())
    for section in ['source_sha256', 'prepared_sha256']:
        b.verify(prep[section])
    verify(prep['original_SDF_structure_derivative']['certificate'])
    wd = prepared / f'run_pulse{args.pulse}_{args.attempt}'
    assert not wd.exists(), 'Retain every diagnostic attempt'
    wd.mkdir()
    for name in ['CARRY4_vendor.v', 'monitor_shadow.sv', 'original_and_shadow_full.sdf', 'run.tcl']:
        shutil.copyfile(prepared / name, wd / name)
    rv = P.parent.parent / 'sequential_paper_trial/hardware/export12_e2_a0/routed.v'
    stamps = b.pins([Path(__file__), prepared / 'preparation.json',
                     *[Path(p) for p in prep['source_sha256']], *list(wd.glob('*.*'))])
    b.write(wd / 'provenance.json', stamps)
    commands = [
        [b.VIVADO / 'bin/xvlog.bat', '-d', 'XIL_TIMING', wd / 'CARRY4_vendor.v'],
        [b.VIVADO / 'bin/xvlog.bat', '-sv', '-d', 'ENGINE_ID=2', '-d',
         'DUT_TOP=top_sequential_leak_e2', rv, wd / 'monitor_shadow.sv'],
        [b.VIVADO / 'bin/xvlog.bat', b.VIVADO / 'data/verilog/src/glbl.v'],
        [b.VIVADO / 'bin/xelab.bat', '-mt', 'off', '-debug', 'all', '-maxdelay',
         '-sdfmax', 'tb_sequential_energy_replay=' + str(wd / 'original_and_shadow_full.sdf').replace('\\', '/'),
         '-transport_int_delays', '-pulse_r', args.pulse, '-pulse_int_r', args.pulse,
         '-pulse_e', args.pulse, '-pulse_int_e', args.pulse, '-L', 'work', '-L',
         'simprims_ver', '-L', 'secureip', '-L', 'unisims_ver', 'tb_sequential_energy_replay', 'glbl', '-s', 'sim'],
        [b.VIVADO / 'bin/xsim.bat', 'sim', '-testplusarg', f'TRACE={prep["trace"]}',
         '-testplusarg', f'ROWS={prep["full_trace_rows"]}', '-testplusarg', 'ROI_FIRST=3',
         '-testplusarg', f'ROI_LAST={prep["full_trace_rows"]}', '-tclbatch', wd / 'run.tcl']]
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
    elaboration, output = [logs[i].read_text(errors='replace') for i in [3, 4]]
    accepted = [line for line in elaboration.splitlines() if 'SDF backannotation was successful' in line]
    gates = dict(work_CARRY4_bound='Compiling module work.CARRY4' in elaboration,
                 one_combined_full_SDF_accepted_at_TB_root=len(accepted) == 1 and 'original_and_shadow_full.sdf' in accepted[0]
                    and 'root module "tb_sequential_energy_replay"' in accepted[0],
                 annotation_not_ignored='$sdf_annotate will be ignored' not in elaboration,
                 no_elaboration_warning_or_error=not re.search(r'\b(?:WARNING|ERROR):', elaboration),
                 no_runtime_timing_warning_or_error=not re.search(r'\b(?:WARNING|ERROR):|[Tt]iming [Vv]iolation', output),
                 positive50ps_settled600ps_canary='CAUSAL_CANARY_PASS POSITIVE50PS_SETTLED600PS' in output,
                 causal_snapshots_completed='CAUSAL_PROBE_SNAPSHOTS_COMPLETE' in output)
    observations, conclusion = classify(output)
    mismatches = re.findall(r'REPLAY mismatch E2 row(\d+) got([^ ]+) expected([^\s]+)', output)
    passes = re.findall(r'FRONTIER_ROUTE_REPLAY PASS E2 ROWS (\d+) CHECKED (\d+) VALID_ROWS (\d+)', output)
    complete = len(passes) == 1 and tuple(map(int, passes[0])) == (prep['full_trace_rows'], prep['full_trace_rows'], prep['valid_rows'])
    result = dict(status='completed_bounded_combined_shadow_diagnostic' if all(gates.values()) else 'rejected_incomplete_or_unverified_combined_shadow_diagnostic',
                  gates=gates, pulse_limit_percent=int(args.pulse),
                  original_netlist_and_raw_SDF_modified=False,
                  combined_SDF_explicit_EOF_completion_and_INSTANCE_relocation=True,
                  vendor_CARRY4_modified=False, timing_checks_disabled=False,
                  original_row914_failure=any(int(row) == 914 for row, _, _ in mismatches),
                  full_original_known_row_replay_pass=complete,
                  replay_mismatches=[dict(row=int(row), got=got, expected=expected) for row, got, expected in mismatches],
                  observations=observations, bounded_conclusion=conclusion,
                  annotation_success_lines=accepted, artifact_sha256=b.pins(logs),
                  diagnostic_only=True, original_discrepancy_resolved=False,
                  hardware_or_energy_acceptance=False,
                  event_trace_limit='Per-bit observer order is not an exact simulator region/delta dump.')
    b.write(wd / 'diagnostic.json', result)
    b.verify(stamps)
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
