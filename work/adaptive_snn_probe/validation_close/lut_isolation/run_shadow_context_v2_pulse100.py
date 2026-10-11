"""Run the prepared in-situ diagnostic only after root coordinates vendor RAM."""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

P = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(P.parent.parent / 'selective_energy_trial'))
import run_selective_energy as b


def classify(text):
    lines = [line for line in text.splitlines() if line.startswith('CAUSAL_SNAPSHOT ')]
    observations = []
    for line in lines:
        tokens = dict(re.findall(r'(ORIG_AGE|SHADOW_AGE|ORIG_S|SHADOW_S|ORIG_CI|SHADOW_CI|ORIG_DI|SHADOW_DI|ORIG_CO|SHADOW_CO|ORIG_FB|SHADOW_FB|ORIG_O|SHADOW_O|EXPECT_O|EXPECT_CO)([^ ]+)', line))
        if not tokens:
            continue
        known = all(re.fullmatch('[0-9a-fA-F]+', tokens[key]) for key in
                    ['ORIG_S', 'SHADOW_S', 'ORIG_CI', 'SHADOW_CI', 'ORIG_DI',
                     'SHADOW_DI', 'ORIG_O', 'SHADOW_O', 'EXPECT_O'])
        observation = {'line': line, 'known': known}
        if known:
            same_inputs = all(int(tokens['ORIG_' + name], 16) == int(tokens['SHADOW_' + name], 16)
                              for name in ['S', 'CI', 'DI'])
            observation.update({'same_observed_inputs': same_inputs,
                                'original_settled_gt_maxdelay': float(tokens['ORIG_AGE']) > .579,
                                'shadow_settled_gt_maxdelay': float(tokens['SHADOW_AGE']) > .579,
                                'original_wrong': int(tokens['ORIG_O'], 16) != int(tokens['EXPECT_O'], 16),
                                'shadow_wrong': int(tokens['SHADOW_O'], 16) != int(tokens['EXPECT_O'], 16)})
        observations.append(observation)
    qualifying = [row for row in observations if row.get('same_observed_inputs')
                  and row['original_settled_gt_maxdelay'] and row['shadow_settled_gt_maxdelay']]
    reproduced = any(row['original_wrong'] for row in qualifying)
    shared = any(row['original_wrong'] and row['shadow_wrong'] for row in qualifying)
    divergent = any(row['original_wrong'] and not row['shadow_wrong'] for row in qualifying)
    if shared:
        conclusion = 'Both contexts show a settled Boolean discrepancy under live original events; exact path/event cause remains unresolved.'
    elif divergent:
        conclusion = 'Original-only settled discrepancy under matching observed inputs implicates context/delta or port-path treatment; not an arithmetic or hardware fix.'
    elif not reproduced:
        conclusion = 'The added diagnostic does not reproduce the settled original failure; possible observer/elaboration sensitivity remains unresolved.'
    else:
        conclusion = 'Insufficient settled observations for a causal distinction.'
    return observations, conclusion


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', action='store_true')
    ap.add_argument('--attempt', default='a0')
    args = ap.parse_args()
    assert args.run, 'No vendor launch without explicit --run and root coordination.'
    assert re.fullmatch('[a-zA-Z0-9_-]+', args.attempt)
    prepared = P / 'shadow_context_v2'
    prep = json.loads((prepared / 'preparation.json').read_text())
    for section in ['source_sha256', 'prepared_sha256']:
        b.verify(prep[section])
    wd = prepared / ('run_' + args.attempt)
    assert not wd.exists(), 'Retain every diagnostic attempt.'
    wd.mkdir()
    for name in ['CARRY4_vendor.v', 'monitor_shadow.sv', 'shadow_paths.sdf', 'run.tcl']:
        shutil.copyfile(prepared / name, wd / name)
    s = P.parent.parent / 'sequential_paper_trial'
    rv = s / 'hardware/export12_e2_a0/routed.v'
    trace = s / 'hardware/native_actual_s0_a3/trace2.txt'
    paths = [Path(__file__), prepared / 'preparation.json', *[Path(name) for name in prep['source_sha256']],
             *list(wd.glob('*.*'))]
    stamps = b.pins(paths)
    b.write(wd / 'provenance.json', stamps)
    commands = [
        [b.VIVADO / 'bin/xvlog.bat', '-d', 'XIL_TIMING', wd / 'CARRY4_vendor.v'],
        [b.VIVADO / 'bin/xvlog.bat', '-sv', '-d', 'ENGINE_ID=2', '-d',
         'DUT_TOP=top_sequential_leak_e2', rv, wd / 'monitor_shadow.sv'],
        [b.VIVADO / 'bin/xvlog.bat', b.VIVADO / 'data/verilog/src/glbl.v'],
        [b.VIVADO / 'bin/xelab.bat', '-mt', 'off', '-debug', 'all', '-maxdelay',
         '-transport_int_delays', '-pulse_r', '100', '-pulse_int_r', '100', '-pulse_e', '100',
         '-pulse_int_e', '100', '-L', 'work', '-L', 'simprims_ver', '-L', 'secureip',
         '-L', 'unisims_ver', 'tb_sequential_energy_replay', 'glbl', '-s', 'sim'],
        [b.VIVADO / 'bin/xsim.bat', 'sim', '-testplusarg', f'TRACE={trace}',
         '-testplusarg', 'ROWS=950', '-testplusarg', 'ROI_FIRST=3', '-testplusarg',
         'ROI_LAST=950', '-tclbatch', wd / 'run.tcl']]
    logs = []
    for index, command in enumerate(commands):
        argv = [str(item).replace('\\', '/') for item in command]
        assert not any(item in argv for item in ['-notimingchecks', '-nospecify', '-sdfnowarn', '-sdfnoerror'])
        if index < 4:
            logs.append(b.job(argv, wd, f'tool_{index}', stamps, 1.2))
        else:
            # A target replay fatal is expected diagnostic evidence. Preserve its
            # exit/job record if this simulator returns a nonzero fatal status.
            try:
                logs.append(b.job(argv, wd, f'tool_{index}', stamps, 1.2))
            except AssertionError:
                log = wd / f'tool_{index}.log'
                if not log.exists() or 'REPLAY mismatch E2 row914' not in log.read_text(errors='replace'):
                    raise
                logs.append(log)
    elaboration = logs[3].read_text(errors='replace')
    text = logs[4].read_text(errors='replace')
    sdf_accepts = [line for line in elaboration.splitlines() if 'SDF backannotation was successful' in line]
    gates = {'work_CARRY4_bound': 'Compiling module work.CARRY4' in elaboration,
             'original_full_SDF_accepted': any('routed.sdf' in line for line in sdf_accepts),
             'shadow_and_canary_SDF_accepted': any('shadow_paths.sdf' in line for line in sdf_accepts),
             'SDF_not_ignored': '$sdf_annotate will be ignored' not in elaboration,
             'elaboration_warnings_or_errors_absent': not re.search(r'\b(?:WARNING|ERROR):', elaboration),
             'positive_228ps_timing_canary': 'CAUSAL_CANARY_PASS' in text,
             'snapshots_completed': 'CAUSAL_PROBE_SNAPSHOTS_COMPLETE' in text}
    observations, conclusion = classify(text)
    result = {'status': 'completed_causal_diagnostic_not_hardware_acceptance' if all(gates.values())
              else 'rejected_incomplete_or_unverified_causal_diagnostic',
              'gates': gates, 'vendor_CARRY4_modified': False,
              'original_netlist_or_SDF_modified': False, 'timing_checks_disabled': False,
              'original_row914_replay_failure': 'REPLAY mismatch E2 row914' in text,
              'observations': observations, 'bounded_conclusion': conclusion,
              'event_trace_limit': 'Per-bit observer order is not an exact simulator region/delta dump.',
              'log_sha256': b.pins(logs),
              'hardware_acceptance': False, 'original_discrepancy_resolved': False}
    b.write(wd / 'diagnostic.json', result)
    b.verify(stamps)
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
