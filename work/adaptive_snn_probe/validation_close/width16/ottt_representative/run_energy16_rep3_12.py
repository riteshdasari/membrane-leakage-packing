"""Explicitly invoked fixed16 actual-stream golden/SDF/SAIF/power pipeline."""
from pathlib import Path
import argparse,importlib.util,json,re,sys,time
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;ROOT=P.parent.parent.parent
sys.path.insert(0,str(ROOT/'selective_energy_trial'))
import run_selective_energy as base
import replay_selective_energy as helpers
sha,read,write,pins,verify=base.sha,base.read,base.write,base.pins,base.verify
ARGS=None
def tool(command,wd,label,stamps,gate=1.2):
    while base.free()<=gate+.15:time.sleep(5)
    return base.job([str(x).replace('\\','/')for x in command],wd,label,stamps,gate)
def sources():
    prep=read(P/'energy16_preparation_rep3.json');verify(prep['source_sha256']);verify(prep['artifact_sha256'])
    core=read(P/'preparation_rep3.json');verify(core['source_sha256']);verify(core['artifact_sha256'])
    native=read(ARGS.native_acceptance);assert native['status']=='pass' and native['B']==16 and native['stall']==0 and native['capture']==1
    assert native['cohort']=='actual_ottt_representative'
    verify(native['source_sha256']);verify(native['artifact_sha256'])
    return prep['source_sha256']|prep['artifact_sha256']|core['source_sha256']|core['artifact_sha256']|pins([Path(__file__),P/'energy16_preparation_rep3.json',P/'preparation_rep3.json',ARGS.native_acceptance,P/'domain_acceptance_ottt_representative.json',ROOT/'selective_energy_trial/replay_selective_energy.py',ROOT/'selective_energy_trial/normalize_saif_names.py'])
def path(label,e):return P/'hardware'/f'{label}12_{ARGS.workload}_e{e}_{ARGS.attempt}'
def directory(label,e):
    wd=path(label,e);assert not wd.exists();wd.mkdir(parents=True);return wd
def native(e):
    checkfile=Path(ARGS.native_acceptance).resolve();d=read(checkfile)
    assert d['status']=='pass' and d['B']==16 and d['stall']==0 and d['capture']==1
    verify(d['source_sha256']);verify(d['artifact_sha256'])
    row,=[r for r in d['rows']if r['engine']==e];trace=checkfile.parent/f"trace{row['native_index']}.txt"
    total=sum(1 for _ in trace.open());return checkfile,row,trace,total
def route(e):
    wd=Path(ARGS.route_dir_template.format(engine=e)).resolve();hw=read(wd/'hardware.json')
    assert hw['status']=='pass' and hw['B']==16 and hw['engine']==e and hw['clock_period_ns']==12
    assert hw['top']==f'top_sequential_leak16_e{e}'
    assert(hw['slice_accounting']['launch_FF'],hw['slice_accounting']['capture_FF'],hw['slice_accounting']['fixture_FF'])==(55,39,94)
    verify(hw['source_sha256']);verify(hw['artifact_sha256'])
    # Golden copies must be identical to sources of this selected main route.
    for name in('leak_core16.sv','leak_dsp.sv','timing16.sv'):
        original=str((P.parent/name).resolve())
        assert hw['source_sha256'][original]==sha(P/name)==sha(original)
    return wd,hw
def simulation(e,wd,files,stamps,trace,total,first,last,timed=False):
    batch=wd/'activity.tcl';start=132000+first*12000-1;duration=(last-first+3)*12000;end=start+duration
    if timed:
        batch.write_text(f'run {start} ps\nopen_saif activity.saif\ncurrent_scope /tb_sequential_energy_replay16/dut\nlog_saif [get_objects -r *]\nrun {duration} ps\nclose_saif\nputs "FRONTIER_SAIF_CLOSED START_PS {start} END_PS {end} DURATION_PS {duration}"\nrun {(total+4)*12000+132000-end} ps\nquit\n')
    else:batch.write_text(f'run {132000+(total+4)*12000} ps\nquit\n')
    stamps=stamps|pins([batch]);write(wd/'provenance.json',stamps)
    options=['-debug','all','-maxdelay','-transport_int_delays','-pulse_r','0','-pulse_int_r','0','-pulse_e','0','-pulse_int_e','0','-L','simprims_ver','-L','secureip']if timed else['-debug','typical']
    top=f'top_sequential_leak16_e{e}'
    commands=[[base.VIVADO/'bin/xvlog.bat','-sv','-d',f'ENGINE_ID={e}','-d',f'DUT_TOP={top}',*files,P/'tb_energy16_12.sv'],
        [base.VIVADO/'bin/xvlog.bat',base.VIVADO/'data/verilog/src/glbl.v'],
        [base.VIVADO/'bin/xelab.bat','-mt','off',*options,'-L','unisims_ver','tb_sequential_energy_replay16','glbl','-s','sim'],
        [base.VIVADO/'bin/xsim.bat','sim','-testplusarg',f'TRACE={trace}','-testplusarg',f'ROWS={total}','-testplusarg',f'ROI_FIRST={first}','-testplusarg',f'ROI_LAST={last}','-tclbatch',batch]]
    logs=[tool(command,wd,f'tool_{i}',stamps)for i,command in enumerate(commands)]
    text=logs[-1].read_text();match=re.search(r'FRONTIER_ROUTE_REPLAY PASS E(\d+) ROWS (\d+) CHECKED (\d+) VALID_ROWS (\d+)',text)
    assert match and tuple(map(int,match.groups()[:3]))==(e,total,total)
    expected_valid=sum(int(line.split()[9])for line in trace.open());assert int(match[4])==expected_valid and expected_valid>0
    roi=re.search(r'REPLAY ROI_START V(\d+) TIME_NS ([\d.]+) ROW (\d+)',text)
    assert roi and int(roi[1])==e and int(roi[3])==first and abs(float(roi[2])*1000-(132000+first*12000))<.001
    if timed:
        assert f'FRONTIER_SAIF_CLOSED START_PS {start} END_PS {end} DURATION_PS {duration}'in text
        diagnostics=helpers.timing_warnings(logs+list(wd.glob('*.log')));assert not diagnostics,diagnostics
    verify(stamps)
    return dict(source_sha256=stamps,artifact_sha256=pins([batch,*logs]+([wd/'activity.saif']if timed else[])),
        roi_start_ps=start,roi_end_ps=end,roi_duration_ps=duration,replay_rows_checked=int(match[3]),valid_rows_checked=int(match[4]))
def golden(e):
    check,row,trace,total=native(e);wd=directory('golden',e)
    stamps=sources()|pins([check,trace,P/'leak_core16.sv',P/'leak_dsp.sv',P/'timing16.sv'])
    d=simulation(e,wd,[P/'leak_core16.sv',P/'leak_dsp.sv',P/'timing16.sv'],stamps,trace,total,row['first_accept'],row['last_retire'])
    write(wd/'golden_checks.json',d|dict(status='pass',B=16,engine=e,trace_sha256=sha(trace),scope='Every known direct-core row reproduced through matched94FF launch/capture fixture; offset2'))
    print('ENERGY16 GOLDEN PASS',ARGS.workload,e,flush=True)
def export(e):
    rd,hw=route(e);wd=directory('export',e);stamps=sources()|pins([rd/'hardware.json',rd/'design.dcp'])
    write(wd/'provenance.json',stamps)
    log=tool([base.VIVADO/'bin/vivado.bat','-mode','batch','-log','vivado.log','-journal','vivado.jou','-source',P/'export16_12.tcl','-tclargs',rd/'design.dcp',wd],wd,'export',stamps,2.3)
    assert 'FRONTIER_EXPORT PASS'in log.read_text() and f'module {hw["top"]}'in(wd/'routed.v').read_text()
    write(wd/'artifacts.json',pins([wd/'routed.v',wd/'routed.sdf',wd/'provenance.json']));print('ENERGY16 EXPORT PASS',ARGS.workload,e,flush=True)
def replay(e):
    rd,hw=route(e);ex=path('export',e);verify(read(ex/'artifacts.json'))
    goldenfile=path('golden',e)/'golden_checks.json';g=read(goldenfile);assert g['status']=='pass';verify(g['source_sha256']);verify(g['artifact_sha256'])
    check,row,trace,total=native(e);wd=directory('replay',e)
    stamps=sources()|pins([check,trace,goldenfile,rd/'hardware.json',rd/'design.dcp',ex/'routed.v',ex/'routed.sdf',ex/'artifacts.json'])
    d=simulation(e,wd,[ex/'routed.v'],stamps,trace,total,row['first_accept'],row['last_retire'],True)
    stats=helpers.saif_stats(wd/'activity.saif',d['roi_duration_ps'])
    write(wd/'replay_checks.json',d|dict(status='timing_pass_activity_pending',B=16,engine=e,design_top=hw['top'],
        native_row=row,native_trace_file=str(trace),native_check_file=str(check),native_check_sha256=sha(check),trace_sha256=sha(trace),trace_count=total,
        requests=row['requests'],neurons=row['neurons'],clock_period_ns=12,output_trace_row_offset=2,
        golden_check_file=str(goldenfile),export_artifacts_file=str(ex/'artifacts.json'),hardware_file=str(rd/'hardware.json'),
        cohort_expectation_file=str((P/'domain_acceptance_ottt_representative.json').resolve()),saif=stats,
        timing_simulation_method='AMD transport, zero pulse error and rejection, slow/max; no timing-check waiver'))
    tool([sys.executable,'-B',ROOT/'selective_energy_trial/normalize_saif_names.py',wd/'activity.saif',wd/'activity_named.saif'],wd,'normalize',stamps,.1)
    print('ENERGY16 SDF REPLAY PASS',ARGS.workload,e,flush=True)
def power(e):
    rd,hw=route(e);rp=path('replay',e);d=read(rp/'replay_checks.json');assert d['status']=='timing_pass_activity_pending'
    verify(d['source_sha256']);verify(d['artifact_sha256']);wd=directory('power',e);named=rp/'activity_named.saif'
    stamps=sources()|pins([named,named.with_suffix('.names.json'),rp/'replay_checks.json',rd/'hardware.json',rd/'design.dcp']);write(wd/'provenance.json',stamps)
    tool([base.VIVADO/'bin/vivado.bat','-mode','batch','-log','vivado.log','-journal','vivado.jou','-source',P/'power16_12.tcl','-tclargs',e,rd/'design.dcp',named,wd],wd,'annotation',stamps,2.3)
    write(wd/'evidence.json',dict(status='reports generated; independent audit required',B=16,engine=e,design_top=hw['top'],
        replay_dir=str(rp),hardware_file=str(rd/'hardware.json'),saif_file=str(named),source_sha256=stamps,
        artifact_sha256=pins(p for p in wd.iterdir()if p.is_file()),duration_seconds=d['saif']['duration_seconds'],neurons=d['neurons']))
    spec=importlib.util.spec_from_file_location('power16_independent_auditor',P/'audit_power16_rep3_12.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    audit=module.annotation(wd);write(wd/'power_audit.json',audit);print('ENERGY16 POWER AUDIT PASS',ARGS.workload,e,audit['estimated_dynamic_energy_pJ_per_scalar_update'],flush=True)
def main():
    global ARGS
    ap=argparse.ArgumentParser();ap.add_argument('--workload',choices=['ottt_representative'],required=True)
    ap.add_argument('--native-acceptance',required=True);ap.add_argument('--route-dir-template',required=True)
    ap.add_argument('--engines',required=True);ap.add_argument('--steps',default='golden,export,replay,power');ap.add_argument('--attempt',required=True)
    ARGS=ap.parse_args();assert re.fullmatch(r'[a-zA-Z0-9_-]+',ARGS.attempt)and '{engine}'in ARGS.route_dir_template
    engines=list(map(int,ARGS.engines.split(',')));assert len(engines)==len(set(engines))and all(e in(5,1,6)for e in engines)
    if ARGS.workload=='glif':assert all(e<=5 for e in engines)
    funcs={'golden':golden,'export':export,'replay':replay,'power':power};steps=ARGS.steps.split(',');assert all(s in funcs for s in steps)
    progress=P/f'energy12_{ARGS.workload}_{ARGS.attempt}_{"_".join(steps)}_progress.json';assert not progress.exists()
    state=dict(status='running',B=16,workload=ARGS.workload,clock_ns=12,engines=engines,stages=[],failures=[],source_sha256=sources())
    for e in engines:
        for label in steps:
            state['current_stage']=[label,e];write(progress,state)
            try:funcs[label](e)
            except Exception as exc:
                state['failures'].append(dict(engine=e,stage=label,reason=repr(exc),accepted_energy=False));print('ENERGY16 RETAINED FAILURE',ARGS.workload,e,label,repr(exc),flush=True);break
            state['stages'].append([label,e]);write(progress,state)
    state['status']='completed_with_retained_failures'if state['failures']else'pass';write(progress,state)
if __name__=='__main__':main()
