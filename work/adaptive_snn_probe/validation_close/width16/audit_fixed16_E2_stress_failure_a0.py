"""Read-only fixed16 E2 stress failure audit; no causal or energy acceptance."""
from pathlib import Path
import collections
import hashlib
import json
import re
import sys

sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parent));sys.path.insert(0,str(P))
import prepare_fixed16_final_report_v1 as evidence
import certify_energy_export


def decode(word):
    n=int(word,16);data=(n>>1)&0xffffffff
    def signed(value):return value-65536 if value&32768 else value
    return dict(word_hex=word,data_hex=f'{data:08x}',lane0_signed16=signed(data&65535),
      lane1_signed16=signed(data>>16),in_ready=(n>>38)&1,take=(n>>36)&3,
      out_valid=(n>>35)&1,out_count=(n>>33)&3,narrow_mode=n&1)


def main():
    target=P/'fixed16_E2_stress_failure_a0.json';md=P/'fixed16_E2_stress_failure_a0.md'
    assert not target.exists() and not md.exists()
    tag='ottt_e2_ottt_stress_a0_e2'
    replay=P/'hardware'/('replay12_'+tag)
    golden=P/'hardware'/('golden12_'+tag)
    export=P/'hardware'/('export12_'+tag)
    raw=P/'hardware'/('export_raw12_'+tag)
    route=P/'hardware/route12_e2_a1/hardware.json'
    progress_path=P/'energy_recovery_ottt_e2_ottt_stress_a0_e2_progress.json'
    parent_log=P/'energy_recovery_OTTT_energy_e2_ottt_stress_a0.log'
    progress=evidence.read(progress_path,{'completed_with_retained_failures'})
    assert progress['B']==16 and progress['engines']==[2]
    assert progress['stages']==[['golden',2],['export',2]]
    assert progress['failures']==[dict(engine=2,stage='replay',reason='AssertionError()',accepted_energy=False)]
    selected=evidence.route(route,2)
    assert selected['core']['LUT']==340 and selected['core']['FF']==88 and selected['core']['DSP']==0
    certified=certify_energy_export.verify(export)
    assert certified['status']=='pass_exact_derived_export_reproduction'
    binding=evidence.read(export/'export_binding_certificate.json')
    certificate=evidence.read(export/'sdf_structure_certificate.json')
    assert binding['hardware_file']==str(route.resolve()) and binding['hardware_sha256']==selected['sha256']
    assert certificate['appended_closing_parentheses']==3
    assert certificate['derivative_structural_audit']['strict_structurally_balanced']
    assert certificate['derivative_structural_audit']['direct_root_cell_count']==704
    for folder in [raw,export]:
        evidence.read(folder/'artifacts.json');evidence.read(folder/'provenance.json')
    evidence.read(raw/'export.job.json');evidence.bind(raw/'export.log')
    assert 'FRONTIER_EXPORT PASS' in (raw/'export.log').read_text()
    golden_check=evidence.read(golden/'golden_checks.json',{'pass'})
    assert (golden_check['B'],golden_check['engine'],golden_check['replay_rows_checked'],golden_check['valid_rows_checked'])==(16,2,7340,3671)
    logs=[];jobs=[]
    for folder in [golden,replay]:
        provenance=evidence.read(folder/'provenance.json')
        group_logs=[];group_jobs=[]
        for i in range(4):
            job=evidence.read(folder/f'tool_{i}.job.json')
            log_path=evidence.bind(folder/f'tool_{i}.log',job['log_sha256'])
            profile=folder/f'tool_{i}.memory_profile.json'
            assert job['source_sha256']=={**provenance,str(profile.resolve()):evidence.sha(profile)}
            assert job['returncode']==0 and Path(job['cwd']).resolve()==folder.resolve()
            assert not any(item in job['argv'] for item in ['-notimingchecks','-nospecify','-sdfnowarn','-sdfnoerror'])
            group_logs.append(log_path.read_text());group_jobs.append(job)
        logs.append(group_logs);jobs.append(group_jobs)
    assert not any(re.search(r'\b(?:WARNING|ERROR):|[Tt]iming [Vv]iolation',text) for group in logs for text in group)
    annotated=[line for line in logs[1][2].splitlines() if 'SDF backannotation was successful' in line]
    assert len(annotated)==1 and '/export12_'+tag+'/routed.sdf' in annotated[0]
    assert 'root module "tb_sequential_energy_replay16/dut"' in annotated[0]
    argv=jobs[1][2]['argv']
    assert '-maxdelay' in argv and '-transport_int_delays' in argv
    for flag in ['-pulse_r','-pulse_int_r','-pulse_e','-pulse_int_e']:
        assert argv.count(flag)==1 and argv[argv.index(flag)+1]=='0'
    trace=P/'hardware/native_actual128_s0_a0/trace2.txt'
    assert f'TRACE={str(trace.resolve()).replace(chr(92),"/")}' in jobs[1][3]['argv']
    assert 'ROWS=7340' in jobs[1][3]['argv']
    failures=[]
    for row,got,expected in re.findall(r'REPLAY mismatch E2 row(\d+) got([^ ]+) expected([^\s]+)',logs[1][3]):
        g,e=decode(got),decode(expected)
        controls=['in_ready','take','out_valid','out_count','narrow_mode']
        assert all(g[key]==e[key] for key in controls)
        failures.append(dict(row=int(row),got=g,expected=e,control_fields_equal=True,
          lane0_error=g['lane0_signed16']-e['lane0_signed16'],lane1_error=g['lane1_signed16']-e['lane1_signed16']))
    assert [row['row'] for row in failures]==[2175,2176]
    assert all(row['lane0_error']==16384 and row['lane1_error']==0 for row in failures)
    assert 'FRONTIER_ROUTE_REPLAY PASS E2' not in logs[1][3]
    assert 'FRONTIER_ROUTE_REPLAY PASS E2 ROWS 7340 CHECKED 7340 VALID_ROWS 3671' in logs[0][3]
    # Rebuild direct-core acceptance/retirement association from recorded valid,
    # ready and take fields; derive leakage independently with Python integers.
    trace_path=evidence.bind(trace)
    queue=collections.deque();by_row={item['row']:item for item in failures}
    native_lines=trace_path.read_text().splitlines()
    assert len(native_lines)==7340
    for line in native_lines:
        f=line.split();row=int(f[0]);u=int(f[5],16);beta=int(f[6],16)
        accept=int(f[2]) and int(f[7]) and int(f[4])>0
        retire=int(f[9]) and int(f[3])
        assert bool(int(f[13]))==bool(accept) and bool(int(f[14]))==bool(retire)
        if accept:queue.append(dict(row=row,u=u,beta=beta,take=int(f[8])))
        if retire:
            assert queue
            operation=queue.popleft()
            if row in by_row:
                scalar=[];packed=0
                for lane in range(operation['take']):
                    a=(operation['u']>>(16*lane))&65535
                    a=a-65536 if a&32768 else a
                    b=(operation['beta']>>(9*lane))&511
                    leak=-((-a*b)//256)
                    scalar.append(dict(U=a,beta=b,scalar_ceil=leak))
                    packed|=(leak&65535)<<(16*lane)
                assert packed==int(f[11],16)==int(by_row[row]['expected']['data_hex'],16)
                by_row[row]['native_accept_row']=operation['row']
                by_row[row]['source_operands']=scalar
    assert not queue
    assert failures[0]['native_accept_row']==2173 and failures[0]['source_operands']==[
      dict(U=200,beta=128,scalar_ceil=100),dict(U=218,beta=128,scalar_ceil=109)]
    saif=evidence.bind(replay/'activity.saif')
    header=saif.read_text()[:500]
    actual_duration,=re.findall(r'\(DURATION\s+(\d+)\)',header)
    assert int(actual_duration)==26090001
    requested_duration=golden_check['roi_duration_ps']
    assert requested_duration==44100000 and int(actual_duration)!=requested_duration
    assert 'FRONTIER_SAIF_CLOSED START_PS 167999 END_PS 44267999 DURATION_PS 44100000' in logs[1][3]
    assert not (replay/'replay_checks.json').exists()
    assert not (P/'hardware'/('power12_'+tag)/'power_audit.json').exists()
    for path in [Path(__file__),parent_log,replay/'activity.tcl',P/'tb_energy16_12.sv']:
        evidence.bind(path)
    record=dict(status='audited_new_fixed16_E2_stress_numerical_replay_failure',B=16,
      workload='OTTT deliberately selected7335-operation stress capture, beta128',
      selected_route=selected,certified_export=certified,
      golden_full_known_row_replay_pass=True,derived_SDF_structurally_balanced=True,
      original_numeric_delays_paths_and_timing_checks_preserved=True,
      all_compile_elaboration_and_simulation_job_returncodes_zero=True,
      derived_DUT_SDF_annotation_success=True,no_compile_or_runtime_timing_warning=True,
      timing_checks_enabled=True,pulse_limit_percent=0,
      observed_failures=failures,first_failure_simulation_time_ns=26258,
      classification='Numerical mismatches in the full signed16 delayed replay. No job-launch, SDF-annotation, syntax, logged timing-violation or resource-exhaustion failure is observed.',
      kernel_or_physical_cause='Not established. No internal cell/event trace was acquired for this new run, and no identity with the historical signed12 carry discrepancy is inferred.',
      actual_partial_SAIF_duration_ps=int(actual_duration),requested_SAIF_duration_ps=requested_duration,
      partial_SAIF_bytes=saif.stat().st_size,
      printed_Tcl_duration_is_completion_proof=False,
      accepted_energy=False,full_known_row_delayed_replay_pass=False,
      all14_controls_acceptance_possible_with_current_evidence=False,
      previously_accepted_primary12_controls_not_replaced_or_waived=True,
      GLIF_E2_status='Not determined by this workload audit; its separate forthcoming attempt must be retained independently.',
      original_files_modified=False,vendor_or_model_jobs_launched=False,process_control_performed=False,
      needed_final_report_update='Retain this optional-control failure explicitly; distinguish accepted primary comparison gates from the failed all14-controls gate. Do not assign E2 energy from its partial SAIF or substitute E7 acceptance for E2.',
      checked_hash_count=len(evidence.PINS),evidence_sha256=evidence.PINS)
    target.write_text(json.dumps(record,indent=2)+'\n')
    md.write_text(
      'The new full signed16 E2 OTTT stress attempt fails numerical delayed replay. Its complete golden replay, certified balanced SDF, original-DUT annotation and all compile/elaboration/simulation job receipts pass their checks. Timing checks remain enabled with slow/max delays and zero pulse limits; no warning or timing-violation lines are observed.\n\n'
      'At the first failure,row2175 at26258ns,the result data is006d4064 instead of006d0064. Decoded signed16 lanes are16484/109 instead of100/109: the low lane differs by+16384 while the other lane and every control field match. Recorded acceptance at row2173 supplies(U,beta)=(200,128) and(218,128), whose independently calculated ceiling leakage values are100 and109. The next failure at row2176 gives16483/74 instead of99/74, again+16384 in the low lane.\n\n'
      'The actual SAIF duration is26090001ps, short of the requested44100000ps. Tcl continues after the first fatal and prints the requested interval before a subsequent failing row; that printed constant does not prove complete capture. No full delayed-replay pass, replay acceptance receipt or power audit exists for this attempt. Its partial SAIF is rejected for energy.\n\n'
      'This records only the new fixed16 observation. Its exact simulator, internal-cell or physical cause remains unmeasured; no common cause with the historical signed12 error is inferred. All original exports, receipts and traces are preserved. The selected route and raw/derived SDF/Verilog certificates are hash-bound in the JSON report.\n\n'
      'Previously accepted primary comparisons retain their own gates, but the all14-controls gate cannot pass with this retained E2 failure. The separate GLIF E2 attempt remains outside this workload audit. Keep both statuses explicit in the final report; E7 acceptance does not repair or replace E2.\n',encoding='utf-8')
    print(json.dumps({key:value for key,value in record.items() if key in ['status','classification','observed_failures','actual_partial_SAIF_duration_ps','requested_SAIF_duration_ps','accepted_energy','checked_hash_count']},indent=2))


if __name__=='__main__':main()
