"""Strict additive audit of error-limit control and original fixed16 probe."""
from pathlib import Path
import json,re,sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parent.parent));sys.path.insert(0,str(P.parent));sys.path.insert(0,str(P.parent.parent/'width16'))
import prepare_fixed16_final_report_v1 as e
import sdf_structure_audit_v1 as parser
import certify_energy_export
from audit_fixed16_E2_stress_failure_a0 import decode


def jobs(wd,expected_status):
    d=e.read(wd/'diagnostic.json',{expected_status});p=e.read(wd/'provenance.json')
    text=[];job=[]
    for i in range(5):
        j=e.read(wd/f'tool_{i}.job.json')
        assert j['source_sha256']==p and j['returncode']==0
        t=e.bind(wd/f'tool_{i}.log',j['log_sha256']).read_text()
        assert not re.search(r'\b(?:WARNING|ERROR):|[Tt]iming [Vv]iolation',t)
        assert not any(x in j['argv'] for x in ['-notimingchecks','-nospecify','-sdfnowarn','-sdfnoerror'])
        text.append(t);job.append(j)
    return d,text,job


def normalized(job,wd):
    wd=str(wd.resolve()).replace('\\','/')
    return [[x.replace(wd,'<RUN>') for x in j['argv']] for j in job]


def snapshot(line):
    labels=['UPSTREAM_CI','EXPECT_CO','PARENT_O','EXPECT_O','D14','Q14','CII','CYI','DII','AGE','CLK','ROW','SI','DI','CI','CY','CO','FB','CE','S','O','T']
    tokens=dict(re.findall(r'\b('+'|'.join(labels)+r')([^ ]+)',line))
    assert set(tokens)==set(labels)
    known=all(re.fullmatch('[0-9a-fA-F]+',tokens[k]) for k in labels if k not in ['T','ROW','AGE'])
    assert known
    nums={k:int(tokens[k],16) for k in labels if k not in ['T','ROW','AGE']}
    carry=nums['CII']|nums['CYI'];eo=ec=0
    for k in range(4):
        s,di=(nums['SI']>>k)&1,(nums['DII']>>k)&1
        eo|=(s^carry)<<k;carry=carry if s else di;ec|=carry<<k
    assert (eo,ec)==(nums['EXPECT_O'],nums['EXPECT_CO'])
    assert (nums['S'],nums['DI'],nums['CI'],nums['CY'])==(nums['SI'],nums['DII'],nums['CII'],nums['CYI'])
    assert nums['CI']==nums['UPSTREAM_CI']
    assert nums['PARENT_O']==(nums['O']&7)
    return dict(line=line,time_ns=float(tokens['T']),row=int(tokens['ROW']),age_ns=float(tokens['AGE']),
      values=nums,cell_O_wrong=nums['O']!=eo,cell_CO_wrong=nums['CO']!=ec,
      O1_wrong=((nums['O']>>1)&1)!=((eo>>1)&1))


def main():
    target=P/'pending_closure_independent_audit_v2.json';md=P/'pending_closure_independent_audit_v2.md'
    assert not target.exists() and not md.exists()
    previous=e.read(P/'signed12_controls_independent_audit_v1.json',{'audited_signed12_optimization_and_connected_CI_intervention'})
    for path,pin in previous['evidence_sha256'].items():e.bind(path,pin)
    base=P/'run_default_/a0';error=P/'run_default_error_/a0'
    bd,bt,bj=jobs(base,'completed_optimization_diagnostic')
    ed,et,ej=jobs(error,'rejected_diagnostic')
    a,b=normalized(bj,base),normalized(ej,error)
    changes=[]
    for flag in ['-pulse_e','-pulse_int_e']:
        i=b[3].index(flag)+1;assert a[3][i]=='0' and b[3][i]=='100'
        changes.append(dict(stage=3,flag=flag,old='0',new='100'));b[3][i]='0'
    assert a==b
    for name in ['monitor_shadow.sv','CARRY4_vendor.v','original_and_shadow_full.sdf','run.tcl']:
        assert (base/name).read_bytes()==(error/name).read_bytes()
    assert ed['replay_mismatches']==[dict(row=5,got='6c0XxxX6',expected='6c02e016')]
    assert ed['gates']['snapshots_complete'] is False
    assert all(v for k,v in ed['gates'].items() if k!='snapshots_complete')
    assert 'Time: 218 ns' in et[4]
    wd=P/'run_signed16_probe/a0';d,t,j=jobs(wd,'completed_observation_only_signed16_probe')
    assert all(d['gates'].values()) and d['original_failure_reproduced']
    assert d['replay_mismatches']==[dict(row=2175,got='6c00da80c8',expected='6c00da00c8')]
    g,x=decode(d['replay_mismatches'][0]['got']),decode(d['replay_mismatches'][0]['expected'])
    assert g['lane0_signed16']-x['lane0_signed16']==16384 and g['lane1_signed16']==x['lane1_signed16']
    assert all(g[k]==x[k] for k in ['in_ready','take','out_valid','out_count','narrow_mode'])
    prep=e.read(P/'signed16_probe_prepared/preparation.json',{'prepared_observation_only_signed16_probe_not_run'})
    W=P.parent.parent/'width16';export=W/'hardware/export12_ottt_e2_ottt_stress_a0_e2'
    certified=certify_energy_export.verify(export)
    assert certified['status']=='pass_exact_derived_export_reproduction'
    sfile=e.bind(export/'routed.sdf');s=sfile.read_text()
    roots,opened,_=parser.parse(s);assert not opened and len(roots)==1
    c,=[c for c in roots[0].direct('CELL') if parser.instance(c,s)[0].replace('\\','')=='fixture/core/lut.lane[0].r_reg[15]_i_4']
    cell=s[c.start:c.end]
    iopaths=[x.strip() for x in cell.splitlines() if '(IOPATH ' in x]
    assert len(iopaths)==12
    pathvalues=[float(n) for line in iopaths for n in re.findall(r'(?<!\w)[0-9]+\.[0-9]+',line)]
    max_io=max(pathvalues);min_io=min(pathvalues)
    assert max_io==579 and min_io==148
    relevant=[line.strip() for line in s.splitlines() if '(INTERCONNECT ' in line and any(x in line for x in [
      r'lut\.lane\[0\]\.r_reg\[15\]_i_4/O[1]',
      r'lut\.lane\[0\]\.r_reg\[12\]_i_2/CO[3] fixture/core/lut\.lane\[0\]\.r_reg\[15\]_i_4/CI',
      r'lut\.lane\[0\]\.r\[14\]_i_1/O fixture/core/lut\.lane\[0\]\.r_reg\[14\]/D'])]
    assert len(relevant)==3
    assert any('(636.2:776.2:776.2)' in line for line in relevant)
    observed=[snapshot(line) for line in t[4].splitlines() if line.startswith('FIXED16_SNAPSHOT ')]
    assert len(observed)==len(d['snapshots'])
    stable_wrong=[r for r in observed if r['O1_wrong'] and r['age_ns']>max_io/1000]
    assert len(stable_wrong)>=8
    before,=[r for r in stable_wrong if r['time_ns']==26237.999]
    after,=[r for r in stable_wrong if r['time_ns']==26239.0]
    assert before['values']['D14']==1 and before['values']['Q14']==0
    assert after['values']['D14']==after['values']['Q14']==1
    assert all(r['values'][k]==0 for r in stable_wrong for k in ['S','DI','CI','CY','SI','DII','CII','CYI','CO','FB','EXPECT_O','EXPECT_CO'])
    assert all(r['values']['O']==r['values']['PARENT_O']==2 for r in stable_wrong)
    events=[]
    for line in t[4].splitlines():
        m=re.match(r'FIXED16_EVENT T([^ ]+) ROW(\d+) SIGNAL([^ ]+) BIT(\d+) VALUE([01xz])',line)
        if m:events.append(dict(time_ns=m[1],row=int(m[2]),signal=m[3],bit=int(m[4]),value=m[5]))
    ci=[r for r in events if r['signal']=='CI_port']
    upstream=[{**r,'signal':'CI_port'} for r in events if r['signal']=='CI_upstream']
    assert ci==upstream
    last_input=[r for r in events if r['signal'] in ['CI_port','CY_port','S_port','DI_port']][-1]
    assert last_input['time_ns']=='26231.113' and last_input['signal']=='CI_port' and last_input['value']=='0'
    final_o1=[r for r in events if r['signal']=='O' and r['bit']==1][-1]
    assert final_o1['time_ns']=='26231.493' and final_o1['value']=='1'
    q1=[r for r in events if r['signal']=='Q14' and r['value']=='1']
    assert q1==[dict(time_ns='26238.362',row=2176,signal='Q14',bit=0,value='1')]
    bench=(wd/'monitor.sv').read_bytes().decode();original=(W/'tb_energy16_12.sv').read_bytes().decode()
    assert bench[:bench.index(' // Observation only.')].rstrip()==original.rsplit('endmodule',1)[0].rstrip()
    assert not any(token in bench for token in ['force ', 'release '])
    assert (wd/'CARRY4_vendor.v').read_bytes()==(P.parent/'CARRY4_vendor.v').read_bytes()
    assert (wd/'run.tcl').read_text()=='run 26271 ns\nquit\n'
    assert not (wd/'activity.saif').exists()
    for flag in ['-pulse_r','-pulse_int_r','-pulse_e','-pulse_int_e']:
        assert j[3]['argv'][j[3]['argv'].index(flag)+1]=='0'
    assert '-maxdelay' in j[3]['argv'] and '-transport_int_delays' in j[3]['argv']
    e.bind(Path(__file__))
    record=dict(status='audited_pending_LUT_closure_signed16_cell_output_inconsistency',
      signed12_previous_audit_sha=e.sha(P/'signed12_controls_independent_audit_v1.json'),
      error_limit_control=dict(matched_changes_only=changes,status='rejected_incomplete_snapshot_diagnostic',
        first_failure_row=5,time_ns=218,got='6c0XxxX6',expected='6c02e016',accepted_as_remedy=False),
      signed16=dict(all_observation_gates_pass=True,original_first_failure_reproduced=True,
        unchanged_full_native_trace=True,unchanged_original_comparison=True,
        certified_export=certified,target_CELL_iopaths=iopaths,min_target_IOPATH_ps=min_io,
        max_target_IOPATH_ps=max_io,relevant_interconnect_SDF_records=relevant,
        stable_wrong_snapshots=stable_wrong,all_snapshots=observed,CI_port_and_upstream_event_sequences_identical=True,
        CI_events=ci,last_observed_cell_input_event=last_input,final_observed_O1_event=final_o1,Q14_rise_event=q1[0],
        first_failure_decoded=dict(got=g,expected=x),
        observed_causal_chain='Original timed CARRY4 O[1] is1 despite settled Boolean inputs requiring0. Its connected parent bit22 is1; downstream D14 is1 before26238ns capture and Q14 rises to1 at26238.362ns; retained row2175 output differs by2^14. This localizes the observed numerical error to the primitive output/timing-model path before the final output LUT/FF.',
        scheduling_cause='Not uniquely established. Logged timestamps do not expose simulator event regions, pending path-event provenance or cancellation. An old event overtaking a newer one is a hypothesis, not a demonstrated event trace.',
        physical_minmax_arc_interpretation='Exported IOPATH min:typ:max numerical values span148..579ps; simulation explicitly selects max. Relevant output interconnect is636.2:776.2:776.2ps. The wrong pre-capture snapshot is6.886ns after the last observed input event, beyond both bounded delays. No physical FPGA defect is inferred.'),
      no_complete_original_E2_replay_fix=True,no_E2_energy_acceptance=True,
      diagnostic_only=True,original_accepted_artifacts_modified=False,vendor_jobs_launched_by_auditor=False,
      further_control_proposed='A pin-local CI intervention would require a fresh derivative netlist splitting the target CI through a dedicated buffer/conditional wire and a matched no-intervention baseline. This would test trigger sufficiency in that derivative context only. It is not necessary to identify the observed wrong-output location, and is not prepared or launched here.',
      checked_hash_count=len(e.PINS),evidence_sha256=e.PINS)
    target.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    md.write_text('The original signed16 OTTT E2 failure is reproduced with unchanged certified netlist/SDF and original full-stream comparison, plus observation-only probes. All annotation, vendor binding, source/hash and timing gates pass.\n\n'
      'The numerical error is localized to the original timed CARRY4 output: at 26237.999 ns its inputs S/DI/CI/CY, internal feedback and independent Boolean result are all zero, yet O is 2 and the connected parent O is 2. Inputs have been stable for 6.886 ns; the maximum target IOPATH is 579 ps and the O[1]-to-bit14-LUT interconnect is 776.2 ps. D14 is 1 before the 26238 ns capture, and Q14 rises to 1 at 26238.362 ns. The same wrong output remains through 26256.001 ns. Row 2175 at 26258 ns then has low lane 16484 instead of 100 (+16384), while the other lane and all controls match. This directly connects the settled primitive output inconsistency to the retained result error.\n\n'
      'The last observed input transition is CI falling at 26231.113 ns; O[1] later rises at 26231.493 ns and remains wrong. CI port and upstream event sequences match. These timestamps do not identify pending-event provenance, simulator regions or cancellation; an older scheduled event overtaking a correct event remains a hypothesis. The observation establishes the failing timed primitive-output location, not a physical FPGA bug or a complete replay repair.\n\n'
      'The separate matched error-limit-only control changes pulse_e and pulse_int_e from 0 to 100 while keeping both rejection limits 0. It fails early at row 5, 218 ns, with unknown output 6c0XxxX6 instead of 6c02e016. Annotation/canary gates pass but the later snapshots never complete, so the control is rejected and provides no remedy.\n\n'
      'The signed12 independent audit remains preserved: disabling optimization did not fix row 914; connected-CI masking removed that first discrepancy but left row 2836 failing, with force/net-collapse caveats. No original E2 energy or full replay is accepted. All original routes, exports, evidence and accepted comparison gates remain unchanged. No additional vendor job was launched by this audit.\n',encoding='utf-8')
    print(json.dumps(dict(status=record['status'],checked_hash_count=record['checked_hash_count'],stable_wrong_snapshots=len(stable_wrong),observed_chain=record['signed16']['observed_causal_chain']),indent=2))


if __name__=='__main__':main()
