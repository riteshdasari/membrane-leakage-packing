"""Matched default/O0 XSim diagnostic; frozen original evidence stays read-only."""
from pathlib import Path
import argparse, json, re, shutil, sys
sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent
ISO = P.parent
sys.path.insert(0, str(ISO))
from verify_eof_only_sdf_derivative_v1 import verify
from run_shadow_context_v3 import classify
sys.path.insert(0, str(ISO.parent.parent / 'selective_energy_trial'))
import run_selective_energy as b

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', action='store_true')
    ap.add_argument('--o0', action='store_true')
    ap.add_argument('--attempt', default='a0')
    a = ap.parse_args()
    assert a.run and re.fullmatch(r'[A-Za-z0-9_-]+', a.attempt)
    prepared = ISO / 'shadow_context_v5'
    prep = b.read(prepared / 'preparation.json')
    b.verify(prep['source_sha256']); b.verify(prep['prepared_sha256'])
    verify(prep['original_SDF_structure_derivative']['certificate'])
    wd = P / ('run_o0_' if a.o0 else 'run_default_') / a.attempt
    assert not wd.exists(), 'Preserve every diagnostic attempt'
    wd.mkdir(parents=True)
    names = ['CARRY4_vendor.v', 'monitor_shadow.sv', 'original_and_shadow_full.sdf', 'run.tcl']
    for name in names:
        shutil.copyfile(prepared / name, wd / name)
    rv = ISO.parent.parent / 'sequential_paper_trial/hardware/export12_e2_a0/routed.v'
    stamps = b.pins([Path(__file__), prepared / 'preparation.json', rv, Path(prep['trace']),
                     *[Path(p) for p in prep['source_sha256']], *[wd / n for n in names]])
    b.write(wd / 'provenance.json', stamps)
    cmds = [
        [b.VIVADO / 'bin/xvlog.bat', '-d', 'XIL_TIMING', wd / 'CARRY4_vendor.v'],
        [b.VIVADO / 'bin/xvlog.bat', '-sv', '-d', 'ENGINE_ID=2', '-d',
         'DUT_TOP=top_sequential_leak_e2', rv, wd / 'monitor_shadow.sv'],
        [b.VIVADO / 'bin/xvlog.bat', b.VIVADO / 'data/verilog/src/glbl.v'],
        [b.VIVADO / 'bin/xelab.bat', '-mt', 'off', '-debug', 'all', '-maxdelay',
         '-sdfmax', 'tb_sequential_energy_replay=' + str(wd / 'original_and_shadow_full.sdf').replace('\\', '/'),
         '-transport_int_delays', '-pulse_r', '0', '-pulse_int_r', '0', '-pulse_e', '0',
         '-pulse_int_e', '0', '-L', 'work', '-L', 'simprims_ver', '-L', 'secureip',
         '-L', 'unisims_ver', 'tb_sequential_energy_replay', 'glbl', '-s', 'sim'],
        [b.VIVADO / 'bin/xsim.bat', 'sim', '-testplusarg', 'TRACE=' + prep['trace'],
         '-testplusarg', 'ROWS=' + str(prep['full_trace_rows']), '-testplusarg', 'ROI_FIRST=3',
         '-testplusarg', 'ROI_LAST=' + str(prep['full_trace_rows']), '-tclbatch', wd / 'run.tcl']
    ]
    if a.o0:
        cmds[3].insert(1, '--O0')
    logs = []
    for index, cmd in enumerate(cmds):
        argv = [str(x).replace('\\', '/') for x in cmd]
        assert not any(x in argv for x in ['-notimingchecks', '-nospecify', '-sdfnowarn', '-sdfnoerror'])
        b.write(wd / 'progress.json', {'stage': index, 'argv': argv, 'o0': a.o0, 'diagnostic_only': True})
        try:
            log = b.job(argv, wd, 'tool_' + str(index), stamps, 1.2)
        except AssertionError:
            log = wd / ('tool_' + str(index) + '.log')
            if index != 4 or not log.is_file() or 'REPLAY mismatch E2 row' not in log.read_text(errors='replace'):
                raise
        logs.append(log)
    elab, output = [logs[i].read_text(errors='replace') for i in [3, 4]]
    accepted = [l for l in elab.splitlines() if 'SDF backannotation was successful' in l]
    gates = {'work_CARRY4_bound': 'Compiling module work.CARRY4' in elab,
             'one_full_annotation': len(accepted) == 1 and 'original_and_shadow_full.sdf' in accepted[0],
             'annotation_not_ignored': '$sdf_annotate will be ignored' not in elab,
             'no_elaboration_warning': not re.search(r'\b(?:WARNING|ERROR):', elab),
             'no_runtime_timing_warning': not re.search(r'\b(?:WARNING|ERROR):|[Tt]iming [Vv]iolation', output),
             'delayed_canary_pass': 'CAUSAL_CANARY_PASS POSITIVE50PS_SETTLED600PS' in output,
             'snapshots_complete': 'CAUSAL_PROBE_SNAPSHOTS_COMPLETE' in output}
    observations, conclusion = classify(output)
    mismatches = re.findall(r'REPLAY mismatch E2 row(\d+) got([^ ]+) expected([^\s]+)', output)
    passes = re.findall(r'FRONTIER_ROUTE_REPLAY PASS E2 ROWS (\d+) CHECKED (\d+) VALID_ROWS (\d+)', output)
    complete = len(passes) == 1 and tuple(map(int, passes[0])) == (prep['full_trace_rows'], prep['full_trace_rows'], prep['valid_rows'])
    result = {'status': 'completed_optimization_diagnostic' if all(gates.values()) else 'rejected_diagnostic',
              'gates': gates, 'disable_simulator_optimizations': a.o0, 'commands': cmds,
              'observations': observations, 'bounded_conclusion': conclusion,
              'replay_mismatches': [{'row': int(r), 'got': g, 'expected': e} for r,g,e in mismatches],
              'full_original_known_row_replay_pass': complete, 'diagnostic_only': True,
              'hardware_or_energy_acceptance': False, 'artifact_sha256': b.pins(logs)}
    # JSON strings avoid serialization of Path objects in the command record.
    result['commands'] = [[str(x).replace('\\', '/') for x in cmd] for cmd in cmds]
    b.verify(stamps); b.write(wd / 'diagnostic.json', result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('commands','observations','artifact_sha256')}, indent=2), flush=True)

if __name__ == '__main__': main()
