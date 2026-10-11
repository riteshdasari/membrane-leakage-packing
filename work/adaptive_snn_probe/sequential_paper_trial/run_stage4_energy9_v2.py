"""Bounded serial golden-fixture, SDF, SAIF and strict power checks for six leakage cores."""
from pathlib import Path
import importlib.util,json,re,sys,time
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;ROOT=P.parent
sys.path.insert(0,str(ROOT/'selective_energy_trial'))
import run_selective_energy as base
import replay_selective_energy as helpers
sha,read,write,pins,verify=base.sha,base.read,base.write,base.pins,base.verify
def tool(c,wd,label,s,gate=1.2):
    while base.free()<=gate+.15:time.sleep(5)
    return base.job([str(x).replace('\\','/')for x in c],wd,label,s,gate)
def sources():
    prep=read(P/'stage4_energy9_v2_preparation.json');verify(prep['source_sha256'])
    native=read(P/'stage4_native_acceptance_v4.json');assert native['status']=='pass'
    verify(native['source_sha256']);verify(native['artifact_sha256'])
    return prep['source_sha256']|pins([Path(__file__),P/'stage4_native_acceptance_v4.json',ROOT/'selective_energy_trial/replay_selective_energy.py',ROOT/'selective_energy_trial/normalize_saif_names.py'])
def directory(label):
    wd=P/'hardware'/f'{label}_a0';assert not wd.exists();wd.mkdir(parents=True);return wd
def native(e):
    checkfile=P/'hardware/native_actual_s0_a3/acceptance.json';d=read(checkfile)
    assert d['status']=='pass';verify(d['source_sha256']);verify(d['artifact_sha256'])
    row,=[r for r in d['rows']if r['engine']==e];trace=checkfile.parent/f'trace{e}.txt'
    total=sum(1 for _ in trace.open());return checkfile,row,trace,total
def route(e):
    wd=P/'hardware'/f'common9_e{e}_a0';hw=read(wd/'hardware.json')
    assert hw['status']=='pass'and hw['engine']==e;verify(hw['source_sha256']);verify(hw['artifact_sha256']);return wd,hw
def simulation(e,wd,files,stamps,trace,total,first,last,timed=False):
    batch=wd/'activity.tcl';start=126000+first*9000-1;duration=(last-first+3)*9000;end=start+duration
    if timed:
        batch.write_text(f'run {start} ps\nopen_saif activity.saif\ncurrent_scope /tb_sequential_energy_replay/dut\nlog_saif [get_objects -r *]\nrun {duration} ps\nclose_saif\nputs "FRONTIER_SAIF_CLOSED START_PS {start} END_PS {end} DURATION_PS {duration}"\nrun {(total+4)*9000+126000-end} ps\nquit\n')
    else:batch.write_text(f'run {126000+(total+4)*9000} ps\nquit\n')
    stamps=stamps|pins([batch]);write(wd/'provenance.json',stamps)
    options=['-debug','all','-maxdelay','-transport_int_delays','-pulse_r','0','-pulse_int_r','0','-pulse_e','0','-pulse_int_e','0','-L','simprims_ver','-L','secureip']if timed else['-debug','typical']
    top=f'top_sequential_leak_e{e}'
    cmds=[[base.VIVADO/'bin/xvlog.bat','-sv','-d',f'ENGINE_ID={e}','-d',f'DUT_TOP={top}',*files,P/'tb_energy9.sv'],
          [base.VIVADO/'bin/xvlog.bat',base.VIVADO/'data/verilog/src/glbl.v'],
          [base.VIVADO/'bin/xelab.bat','-mt','off',*options,'-L','unisims_ver','tb_sequential_energy_replay','glbl','-s','sim'],
          [base.VIVADO/'bin/xsim.bat','sim','-testplusarg',f'TRACE={trace}','-testplusarg',f'ROWS={total}','-testplusarg',f'ROI_FIRST={first}','-testplusarg',f'ROI_LAST={last}','-tclbatch',batch]]
    logs=[tool(c,wd,f'tool_{i}',stamps)for i,c in enumerate(cmds)]
    log=logs[-1].read_text();m=re.search(r'FRONTIER_ROUTE_REPLAY PASS E(\d+) ROWS (\d+) CHECKED (\d+) VALID_ROWS (\d+)',log)
    assert m and tuple(map(int,m.groups()[:3]))==(e,total,total)
    expected_valid_rows=sum(int(line.split()[9])for line in trace.open())
    assert int(m[4])==expected_valid_rows and expected_valid_rows>0
    roi=re.search(r'REPLAY ROI_START V(\d+) TIME_NS ([\d.]+) ROW (\d+)',log)
    assert roi and int(roi[1])==e and int(roi[3])==first
    assert abs(float(roi[2])*1000-(126000+first*9000))<0.001
    if timed:
        assert f'FRONTIER_SAIF_CLOSED START_PS {start} END_PS {end} DURATION_PS {duration}'in log
        diagnostics=helpers.timing_warnings(logs+list(wd.glob('*.log')));assert not diagnostics,diagnostics
    verify(stamps)
    return dict(source_sha256=stamps,artifact_sha256=pins([batch,*logs]+([wd/'activity.saif']if timed else[])),roi_start_ps=start,roi_end_ps=end,roi_duration_ps=duration,replay_rows_checked=int(m[3]),valid_rows_checked=int(m[4]))
def golden(e):
    check,row,trace,total=native(e);wd=directory(f'golden9_e{e}')
    s=sources()|pins([check,trace,P/'leak_core.sv',P/'leak_dsp.sv',P/'timing.sv'])
    d=simulation(e,wd,[P/'leak_core.sv',P/'leak_dsp.sv',P/'timing.sv'],s,trace,total,row['first_accept'],row['last_retire'])
    write(wd/'golden_checks.json',d|dict(status='pass',engine=e,trace_sha256=sha(trace),scope='Every known direct-core pin row reproduced through RTL launch/capture fixture with offset 2; no timed-waiver'))
    print('STAGE4 GOLDEN FIXTURE PASS',e,flush=True)
def export(e):
    rd,hw=route(e);wd=directory(f'export9_e{e}');s=sources()|pins([rd/'hardware.json',rd/'design.dcp'])
    write(wd/'provenance.json',s)
    log=tool([base.VIVADO/'bin/vivado.bat','-mode','batch','-log','vivado.log','-journal','vivado.jou','-source',P/'export9.tcl','-tclargs',rd/'design.dcp',wd],wd,'export',s,2.3)
    assert 'FRONTIER_EXPORT PASS'in log.read_text()and f'module {hw["top"]}'in(wd/'routed.v').read_text()
    write(wd/'artifacts.json',pins([wd/'routed.v',wd/'routed.sdf',wd/'provenance.json']));print('STAGE4 EXPORT PASS',e,flush=True)
def replay(e):
    rd,hw=route(e);ex=P/'hardware'/f'export9_e{e}_a0';verify(read(ex/'artifacts.json'))
    goldencheck=P/'hardware'/f'golden9_e{e}_a0/golden_checks.json';g=read(goldencheck);assert g['status']=='pass';verify(g['source_sha256']);verify(g['artifact_sha256'])
    check,row,trace,total=native(e);wd=directory(f'replay9_e{e}')
    s=sources()|pins([check,trace,goldencheck,rd/'hardware.json',rd/'design.dcp',ex/'routed.v',ex/'routed.sdf',ex/'artifacts.json'])
    d=simulation(e,wd,[ex/'routed.v'],s,trace,total,row['first_accept'],row['last_retire'],True)
    stats=helpers.saif_stats(wd/'activity.saif',d['roi_duration_ps'])
    write(wd/'replay_checks.json',d|dict(status='timing_pass_activity_pending',engine=e,design_top=hw['top'],native_row=row,native_check_file=str(check),native_check_sha256=sha(check),trace_sha256=sha(trace),trace_count=total,requests=row['requests'],neurons=row['neurons'],clock_period_ns=9,output_trace_row_offset=2,golden_check_file=str(goldencheck),export_artifacts_file=str(ex/'artifacts.json'),hardware_file=str(rd/'hardware.json'),saif=stats,timing_simulation_method='AMD transport, zero pulse error and rejection, slow/max'))
    normalizer=ROOT/'selective_energy_trial/normalize_saif_names.py'
    tool([sys.executable,'-B',normalizer,wd/'activity.saif',wd/'activity_named.saif'],wd,'normalize',s,.1)
    print('STAGE4 SDF REPLAY PASS',e,flush=True)
def power(e):
    rd,hw=route(e);rp=P/'hardware'/f'replay9_e{e}_a0';d=read(rp/'replay_checks.json');assert d['status']=='timing_pass_activity_pending'
    verify(d['source_sha256']);verify(d['artifact_sha256']);wd=directory(f'power9_e{e}');named=rp/'activity_named.saif'
    s=sources()|pins([named,named.with_suffix('.names.json'),rp/'replay_checks.json',rd/'hardware.json',rd/'design.dcp']);write(wd/'provenance.json',s)
    tool([base.VIVADO/'bin/vivado.bat','-mode','batch','-log','vivado.log','-journal','vivado.jou','-source',P/'power9.tcl','-tclargs',e,rd/'design.dcp',named,wd],wd,'annotation',s,2.3)
    write(wd/'evidence.json',dict(status='reports generated; independent audit required',engine=e,design_top=hw['top'],replay_dir=str(rp),hardware_file=str(rd/'hardware.json'),saif_file=str(named),source_sha256=s,artifact_sha256=pins(p for p in wd.iterdir()if p.is_file()),duration_seconds=d['saif']['duration_seconds'],neurons=d['neurons']))
    spec=importlib.util.spec_from_file_location('sequential_power_auditor',P/'audit_power9_v2.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    audit=module.annotation(wd);write(wd/'power_audit.json',audit);print('STAGE4 POWER AUDIT PASS',e,audit['estimated_dynamic_energy_pJ_per_scalar_update'],flush=True)
def main():
    p=P/'stage4_energy9_progress.json';assert not p.exists();state=dict(status='running',stages=[],failures=[],source_sha256=sources())
    for e in range(6):
        for label,fn in(('golden',golden),('export',export),('replay',replay),('power',power)):
            state['current_stage']=[label,e];write(p,state)
            try:fn(e)
            except Exception as exc:
                state['failures'].append(dict(engine=e,stage=label,reason=repr(exc),accepted_energy=False));print('STAGE4 ENERGY RETAINED FAILURE',e,label,repr(exc),flush=True);break
            state['stages'].append([label,e]);write(p,state)
    state['status']='completed_with_retained_failures'if state['failures']else'pass';write(p,state)
if __name__=='__main__':main()
