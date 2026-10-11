"""Run the single prepared output-port control only when root dispatches it."""
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


def observations(text):
    records = []
    fields = ['ORIG_AGE','FLAT_AGE','ALIAS_AGE','ORIG_S','FLAT_S','ALIAS_S',
              'ORIG_CI','FLAT_CI','ALIAS_CI','ORIG_CY','FLAT_CY','ALIAS_CY',
              'ORIG_DI','FLAT_DI','ALIAS_DI','ORIG_O','FLAT_O','ALIAS_O',
              'ORIG_CO','FLAT_CO','ALIAS_CO','EXPECT_O','EXPECT_CO']
    for line in text.splitlines():
        if not line.startswith('PORT_CONTEXT_SNAPSHOT '):
            continue
        tokens = dict(re.findall('('+'|'.join(fields)+r')([^ ]+)', line))
        assert set(tokens) == set(fields)
        binary = [key for key in fields if not key.endswith('AGE')]
        known = all(re.fullmatch('[0-9a-fA-F]+', tokens[key]) for key in binary)
        row = dict(line=line, known=known)
        if known:
            nums = {key:int(tokens[key],16) for key in binary}
            carry = nums['ORIG_CI'] | nums['ORIG_CY']
            expected_o = expected_co = 0
            for bit in range(4):
                s, di = (nums['ORIG_S']>>bit)&1, (nums['ORIG_DI']>>bit)&1
                expected_o |= (s^carry)<<bit
                carry = carry if s else di
                expected_co |= carry<<bit
            assert (expected_o,expected_co) == (nums['EXPECT_O'],nums['EXPECT_CO'])
            row |= dict(same_observed_inputs=all(nums['ORIG_'+key]==nums['FLAT_'+key]==nums['ALIAS_'+key]
                                                   for key in ['S','CI','CY','DI']),
                        all_stable_gt579ps=all(float(tokens[key+'_AGE'])>.579 for key in ['ORIG','FLAT','ALIAS']),
                        original_wrong=(nums['ORIG_O'],nums['ORIG_CO'])!=(expected_o,expected_co),
                        flat_wrong=(nums['FLAT_O'],nums['FLAT_CO'])!=(expected_o,expected_co),
                        concatenation_wrong=(nums['ALIAS_O'],nums['ALIAS_CO'])!=(expected_o,expected_co))
        records.append(row)
    return records


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', action='store_true')
    ap.add_argument('--attempt', default='a0')
    args = ap.parse_args()
    assert args.run and re.fullmatch(r'[a-zA-Z0-9_-]+', args.attempt)
    prepared = P / 'port_context_v1'
    prep = json.loads((prepared / 'preparation.json').read_text())
    for section in ['source_sha256','prepared_sha256']:
        b.verify(prep[section])
    verify(prep['original_SDF_structure_derivative']['certificate'])
    wd = prepared / f'run_zero_{args.attempt}'
    assert not wd.exists(), 'Retain every diagnostic attempt'
    wd.mkdir()
    for name in ['CARRY4_vendor.v','monitor_shadow.sv','original_and_shadow_full.sdf','run.tcl']:
        shutil.copyfile(prepared/name,wd/name)
    rv = P.parent.parent / 'sequential_paper_trial/hardware/export12_e2_a0/routed.v'
    stamps = b.pins([Path(__file__),prepared/'preparation.json',
                     *[Path(p) for p in prep['source_sha256']],*list(wd.glob('*.*'))])
    b.write(wd/'provenance.json',stamps)
    commands = [
      [b.VIVADO/'bin/xvlog.bat','-d','XIL_TIMING',wd/'CARRY4_vendor.v'],
      [b.VIVADO/'bin/xvlog.bat','-sv','-d','ENGINE_ID=2','-d','DUT_TOP=top_sequential_leak_e2',rv,wd/'monitor_shadow.sv'],
      [b.VIVADO/'bin/xvlog.bat',b.VIVADO/'data/verilog/src/glbl.v'],
      [b.VIVADO/'bin/xelab.bat','-mt','off','-debug','all','-maxdelay',
       '-sdfmax','tb_sequential_energy_replay='+str(wd/'original_and_shadow_full.sdf').replace('\\','/'),
       '-transport_int_delays','-pulse_r','0','-pulse_int_r','0','-pulse_e','0','-pulse_int_e','0',
       '-L','work','-L','simprims_ver','-L','secureip','-L','unisims_ver','tb_sequential_energy_replay','glbl','-s','sim'],
      [b.VIVADO/'bin/xsim.bat','sim','-testplusarg',f'TRACE={prep["trace"]}',
       '-testplusarg',f'ROWS={prep["full_trace_rows"]}','-testplusarg','ROI_FIRST=3',
       '-testplusarg',f'ROI_LAST={prep["full_trace_rows"]}','-tclbatch',wd/'run.tcl']]
    logs = []
    for index, command in enumerate(commands):
        argv = [str(item).replace('\\','/') for item in command]
        assert not any(item in argv for item in ['-notimingchecks','-nospecify','-sdfnowarn','-sdfnoerror'])
        try:
            log = b.job(argv,wd,f'tool_{index}',stamps,1.2)
        except AssertionError:
            log = wd/f'tool_{index}.log'
            if index!=4 or not log.is_file() or not re.search(r'REPLAY mismatch E2 row\d+',log.read_text(errors='replace')):
                raise
        logs.append(log)
    elaboration,output = [logs[i].read_text(errors='replace') for i in [3,4]]
    accepted = [line for line in elaboration.splitlines() if 'SDF backannotation was successful' in line]
    gates = dict(work_CARRY4_bound='Compiling module work.CARRY4' in elaboration,
      one_combined_full_SDF_accepted_at_TB_root=len(accepted)==1 and 'original_and_shadow_full.sdf' in accepted[0]
       and 'root module "tb_sequential_energy_replay"' in accepted[0],
      annotation_not_ignored='$sdf_annotate will be ignored' not in elaboration,
      no_compile_or_elaboration_warning_or_error=not any(re.search(r'\b(?:WARNING|ERROR):',p.read_text(errors='replace')) for p in logs[:4]),
      no_runtime_timing_warning_or_error=not re.search(r'\b(?:WARNING|ERROR):|[Tt]iming [Vv]iolation',output),
      positive50ps_settled600ps_canary='CAUSAL_CANARY_PASS POSITIVE50PS_SETTLED600PS checks2' in output,
      old_causal_snapshots_completed='CAUSAL_PROBE_SNAPSHOTS_COMPLETE' in output,
      port_context_snapshots_completed='PORT_CONTEXT_PROBE_SNAPSHOTS_COMPLETE' in output)
    old_observations,old_conclusion = classify(output)
    new_observations = observations(output)
    mismatch = [dict(row=int(row),got=got,expected=expected) for row,got,expected in
        re.findall(r'REPLAY mismatch E2 row(\d+) got([^ ]+) expected([^\s]+)',output)]
    reproduced = any(row['row']==914 for row in mismatch)
    qualified = [row for row in new_observations if row.get('same_observed_inputs') and row.get('all_stable_gt579ps')
                  and row.get('original_wrong') and not row.get('flat_wrong')]
    if not all(gates.values()) or not reproduced or not qualified:
        conclusion = 'Inconclusive: complete annotation, original failure and a correct flat control under matched settled inputs did not all reproduce.'
    elif any(row['concatenation_wrong'] for row in qualified):
        conclusion = 'A concatenated sliced-net O control can also produce a settled discrepancy while the flat O control is correct in this local live-input context. This supports connection-shape sensitivity, not an identified exact event-region cause or repair.'
    else:
        conclusion = 'The concatenated sliced-net O control is correct at every qualifying snapshot. That output connection shape alone is insufficient to reproduce the original settled discrepancy in this local context.'
    passes = re.findall(r'FRONTIER_ROUTE_REPLAY PASS E2 ROWS (\d+) CHECKED (\d+) VALID_ROWS (\d+)',output)
    complete = len(passes)==1 and tuple(map(int,passes[0]))==(prep['full_trace_rows'],prep['full_trace_rows'],prep['valid_rows'])
    result = dict(status='completed_bounded_output_port_control' if all(gates.values()) else 'rejected_incomplete_output_port_control',
       gates=gates,original_row914_failure=reproduced,full_original_known_row_replay_pass=complete,
       replay_mismatches=mismatch,observations=new_observations,previous_observations=old_observations,
       bounded_conclusion=conclusion,previous_conclusion=old_conclusion,artifact_sha256=b.pins(logs),
       annotation_success_lines=accepted,diagnostic_only=True,original_discrepancy_resolved=False,
       hardware_or_energy_acceptance=False,vendor_CARRY4_modified=False,timing_checks_disabled=False,
       original_netlist_and_raw_SDF_modified=False,event_trace_limit='Observer order is not an exact simulator region/delta trace.')
    b.write(wd/'diagnostic.json',result)
    b.verify(stamps)
    print(json.dumps(result,indent=2),flush=True)


if __name__ == '__main__':
    main()
