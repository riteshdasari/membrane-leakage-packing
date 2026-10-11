"""Fresh golden/export/certified-SDF/SAIF/power pipeline for shared GLIF MCM."""
from pathlib import Path
import argparse,importlib.util,json,re,sys,time
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;W=P.parent;ROOT=W.parent.parent
sys.path.insert(0,str(ROOT/'selective_energy_trial'))
import run_selective_energy as b
import replay_selective_energy as helpers
TOP='top_sequential_leak16_glif_mcm';ENGINE=9;ARGS=None



def wait_memory(threshold):
 budget_file=P/'operational_budget_v1.json'
 assert b.sha(budget_file)=='0f2f4a6ff959619b8d6f7bbc6081a8506d18bdff5677f025483ebac637dc4019'
 b.verify(b.read(budget_file)['source_sha256'])
 deadline=time.monotonic()+600
 while b.free()<=threshold:
  assert time.monotonic()<deadline,('Bounded memory wait expired',threshold,b.free())
  print('MEMORY WAIT free GiB',round(b.free(),3),'required',threshold,flush=True)
  time.sleep(5)

def tool(command,wd,label,stamps,gate=1.2):
 wait_memory(gate+.15)
 return b.job([str(x).replace('\\','/')for x in command],wd,label,stamps,gate)


def sources():
 prep=b.read(P/'preparation.json');b.verify(prep['source_sha256'])
 energy=b.read(P/'energy_preparation.json');assert energy['status']=='prepared_new_measurement_no_vendor_launch';b.verify(energy['source_sha256'])
 native=b.read(ARGS.native_acceptance);assert native['status']=='pass' and native['B']==16 and native['stall']==0 and native['capture']==1
 assert native['cohort']=='actual_glif' and native['label']=='shared_GLIF_checkpoint_MCM_LUT2'
 b.verify(native['source_sha256']);b.verify(native['artifact_sha256'])
 rd,hw=route();return prep['source_sha256']|energy['source_sha256']|native['source_sha256']|native['artifact_sha256']|hw['source_sha256']|hw['artifact_sha256']|b.pins([Path(__file__),P/'preparation.json',P/'energy_preparation.json',ARGS.native_acceptance,rd/'hardware.json'])


def path(label):return P/'hardware'/f'{label}12_glif_mcm_{ARGS.attempt}'


def directory(label):
 wd=path(label);assert not wd.exists();wd.mkdir(parents=True);return wd


def native():
 checkfile=Path(ARGS.native_acceptance).resolve();d=b.read(checkfile)
 assert d['status']=='pass'and d['B']==16 and d['stall']==0 and d['capture']==1 and d['cohort']=='actual_glif'
 assert d['label']=='shared_GLIF_checkpoint_MCM_LUT2'
 b.verify(d['source_sha256']);b.verify(d['artifact_sha256'])
 trace=checkfile.parent/'trace.txt';assert d['artifact_sha256'][str(trace)]==b.sha(trace)
 total=sum(1 for _ in trace.open());return checkfile,d['fields'],trace,total


def route():
 wd=Path(ARGS.route_directory).resolve();hw=b.read(wd/'hardware.json')
 assert hw['status']=='pass'and hw['B']==16 and hw['clock_period_ns']==12 and hw['top']==TOP and hw['label']=='shared_GLIF_checkpoint_MCM_LUT2'
 assert hw['part']=='xc7a100tcsg324-1'and hw['latency_advancing_edges']==2
 assert(hw['slice_accounting']['launch_FF'],hw['slice_accounting']['capture_FF'],hw['slice_accounting']['fixture_FF'])==(55,39,94)
 assert hw['core']['DSP']==hw['full_fixture']['DSP']==0 and hw['full_fixture']['FF']-hw['core']['FF']==94
 assert all(hw[k]>=0 for k in('WNS_ns','WHS_ns','boundary_WNS_ns','boundary_WHS_ns'))
 b.verify(hw['source_sha256']);b.verify(hw['artifact_sha256']);return wd,hw


def simulation(wd,files,stamps,trace,total,first,last,timed=False):
 batch=wd/'activity.tcl';start=132000+first*12000-1;duration=(last-first+3)*12000;end=start+duration
 if timed:
  batch.write_text(f'run {start} ps\nopen_saif activity.saif\ncurrent_scope /tb_sequential_energy_replay16/dut\nlog_saif [get_objects -r *]\nrun {duration} ps\nclose_saif\nputs "FRONTIER_SAIF_CLOSED START_PS {start} END_PS {end} DURATION_PS {duration}"\nrun {(total+4)*12000+132000-end} ps\nquit\n')
 else:batch.write_text(f'run {132000+(total+4)*12000} ps\nquit\n')
 stamps=stamps|b.pins([batch]);b.write(wd/'provenance.json',stamps)
 options=['-debug','all','-maxdelay','-transport_int_delays','-pulse_r','0','-pulse_int_r','0','-pulse_e','0','-pulse_int_e','0','-L','simprims_ver','-L','secureip']if timed else['-debug','typical']
 commands=[[b.VIVADO/'bin/xvlog.bat','-sv','-d',f'ENGINE_ID={ENGINE}','-d',f'DUT_TOP={TOP}',*files,P/'tb_energy_glif_mcm.sv'],
           [b.VIVADO/'bin/xvlog.bat',b.VIVADO/'data/verilog/src/glbl.v'],
           [b.VIVADO/'bin/xelab.bat','-mt','off',*options,'-L','unisims_ver','tb_sequential_energy_replay16','glbl','-s','sim'],
           [b.VIVADO/'bin/xsim.bat','sim','-testplusarg',f'TRACE={trace}','-testplusarg',f'ROWS={total}',
            '-testplusarg',f'ROI_FIRST={first}','-testplusarg',f'ROI_LAST={last}','-tclbatch',batch]]
 logs=[tool(cmd,wd,f'tool_{i}',stamps)for i,cmd in enumerate(commands)]
 txt=logs[-1].read_text();m=re.search(r'FRONTIER_ROUTE_REPLAY PASS E(\d+) ROWS (\d+) CHECKED (\d+) VALID_ROWS (\d+)',txt)
 assert m and tuple(map(int,m.groups()[:3]))==(ENGINE,total,total)
 valid=sum(int(line.split()[9])for line in trace.open());assert int(m[4])==valid and valid>0
 roi=re.search(r'REPLAY ROI_START V(\d+) TIME_NS ([\d.]+) ROW (\d+)',txt)
 assert roi and int(roi[1])==ENGINE and int(roi[3])==first and abs(float(roi[2])*1000-(132000+first*12000))<.001
 if timed:
  assert f'FRONTIER_SAIF_CLOSED START_PS {start} END_PS {end} DURATION_PS {duration}'in txt
  warnings=helpers.timing_warnings(logs+list(wd.glob('*.log')));assert not warnings,warnings
 b.verify(stamps)
 return dict(source_sha256=stamps,artifact_sha256=b.pins([batch,*logs]+([wd/'activity.saif']if timed else[])),
             roi_start_ps=start,roi_end_ps=end,roi_duration_ps=duration,replay_rows_checked=int(m[3]),valid_rows_checked=int(m[4]))


def golden():
 check,fields,trace,total=native();wd=directory('golden')
 stamps=sources()|b.pins([check,trace,P/'leak_glif_mcm.sv',P/'timing_glif_mcm.sv'])
 d=simulation(wd,[P/'leak_glif_mcm.sv',P/'timing_glif_mcm.sv'],stamps,trace,total,fields['first'],fields['last'])
 b.write(wd/'golden_checks.json',d|dict(status='pass',B=16,engine=ENGINE,design_top=TOP,trace_sha256=b.sha(trace),scope='All known new-core pin rows reproduced through exactly matched94FF fixture; offset2'))
 print('GLIF_MCM ENERGY GOLDEN PASS',flush=True)


def export():
 rd,hw=route();wd=directory('export_raw');stamps=sources()|b.pins([rd/'hardware.json',rd/'design.dcp'])
 b.write(wd/'provenance.json',stamps)
 log=tool([b.VIVADO/'bin/vivado.bat','-mode','batch','-log','vivado.log','-journal','vivado.jou','-source',P/'export_energy_glif_mcm.tcl','-tclargs',rd/'design.dcp',wd],wd,'export',stamps,1.6)
 assert 'FRONTIER_EXPORT PASS'in log.read_text() and f'module {TOP}'in(wd/'routed.v').read_text()
 b.write(wd/'artifacts.json',b.pins([wd/'routed.v',wd/'routed.sdf',wd/'provenance.json']))
 spec=importlib.util.spec_from_file_location('glif_mcm_create_certified_export',W/'certify_energy_export.py')
 binder=importlib.util.module_from_spec(spec);spec.loader.exec_module(binder)
 binder.create(wd,path('export'),rd/'hardware.json',stamps)
 print('GLIF_MCM ENERGY RAW EXPORT + EOF CERTIFICATE PASS',flush=True)


def replay():
 rd,hw=route();ex=path('export');b.verify(b.read(ex/'artifacts.json'))
 spec=importlib.util.spec_from_file_location('glif_mcm_verify_export',W/'certify_energy_export.py');binder=importlib.util.module_from_spec(spec);spec.loader.exec_module(binder);binder.verify(ex)
 goldenfile=path('golden')/'golden_checks.json';g=b.read(goldenfile);assert g['status']=='pass';b.verify(g['source_sha256']);b.verify(g['artifact_sha256'])
 check,fields,trace,total=native();wd=directory('replay')
 stamps=sources()|b.pins([check,trace,goldenfile,rd/'hardware.json',rd/'design.dcp',ex/'routed.v',ex/'routed.sdf',ex/'artifacts.json'])
 d=simulation(wd,[ex/'routed.v'],stamps,trace,total,fields['first'],fields['last'],True)
 stats=helpers.saif_stats(wd/'activity.saif',d['roi_duration_ps'])
 b.write(wd/'replay_checks.json',d|dict(status='timing_pass_activity_pending',B=16,engine=ENGINE,design_top=TOP,
      native_fields=fields,native_check_file=str(check),native_check_sha256=b.sha(check),native_trace_file=str(trace),trace_sha256=b.sha(trace),trace_count=total,
      requests=fields['requests'],neurons=fields['scalars'],clock_period_ns=12,output_trace_row_offset=2,
      golden_check_file=str(goldenfile),export_artifacts_file=str(ex/'artifacts.json'),hardware_file=str(rd/'hardware.json'),
      cohort_expectation_file=str((W/'domain_acceptance_glif_v2.json').resolve()),saif=stats,
      timing_simulation_method='AMD transport, zero pulse error and rejection, slow/max; no timing-check waiver; certified EOF-only SDF structure'))
 tool([sys.executable,'-B',ROOT/'selective_energy_trial/normalize_saif_names.py',wd/'activity.saif',wd/'activity_named.saif'],wd,'normalize',stamps,.1)
 print('GLIF_MCM ENERGY COMPLETE SDF REPLAY PASS',flush=True)


def power():
 rd,hw=route();rp=path('replay');d=b.read(rp/'replay_checks.json');assert d['status']=='timing_pass_activity_pending'
 b.verify(d['source_sha256']);b.verify(d['artifact_sha256']);wd=directory('power');named=rp/'activity_named.saif'
 stamps=sources()|b.pins([named,named.with_suffix('.names.json'),rp/'replay_checks.json',rd/'hardware.json',rd/'design.dcp']);b.write(wd/'provenance.json',stamps)
 tool([b.VIVADO/'bin/vivado.bat','-mode','batch','-log','vivado.log','-journal','vivado.jou','-source',P/'power_energy_glif_mcm.tcl','-tclargs',ENGINE,rd/'design.dcp',named,wd],wd,'annotation',stamps,1.6)
 b.write(wd/'evidence.json',dict(status='reports generated; independent audit required',B=16,engine=ENGINE,design_top=TOP,
      replay_dir=str(rp),hardware_file=str(rd/'hardware.json'),saif_file=str(named),source_sha256=stamps,
      artifact_sha256=b.pins(p for p in wd.iterdir()if p.is_file()),duration_seconds=d['saif']['duration_seconds'],neurons=d['neurons']))
 spec=importlib.util.spec_from_file_location('glif_mcm_strict_power_auditor',P/'audit_energy_glif_mcm.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 audit=module.annotation(wd);b.write(wd/'power_audit.json',audit)
 print('GLIF_MCM ENERGY INDEPENDENT POWER AUDIT PASS',audit['estimated_dynamic_energy_pJ_per_scalar_update'],flush=True)


def main():
 global ARGS
 ap=argparse.ArgumentParser();ap.add_argument('--native-acceptance',required=True);ap.add_argument('--route-directory',required=True)
 ap.add_argument('--steps',default='golden,export,replay,power');ap.add_argument('--attempt',required=True);ARGS=ap.parse_args()
 assert re.fullmatch(r'[a-zA-Z0-9_-]+',ARGS.attempt)
 ARGS.native_acceptance=Path(ARGS.native_acceptance).resolve()
 funcs=dict(golden=golden,export=export,replay=replay,power=power);steps=ARGS.steps.split(',');assert len(set(steps))==len(steps)and all(s in funcs for s in steps)
 progress=P/f'energy_{ARGS.attempt}_{"_".join(steps)}_progress.json';assert not progress.exists()
 state=dict(status='running',B=16,engine=ENGINE,top=TOP,clock_ns=12,stages=[],failures=[],source_sha256=sources());b.write(progress,state)
 for stage in steps:
  state['current_stage']=stage;b.write(progress,state)
  try:funcs[stage]()
  except Exception as exc:
   state['failures'].append(dict(stage=stage,reason=repr(exc),accepted_energy=False));print('GLIF_MCM ENERGY RETAINED FAILURE',stage,repr(exc),flush=True);break
  state['stages'].append(stage);b.write(progress,state)
 state['status']='completed_with_retained_failures'if state['failures']else'pass';b.write(progress,state)


if __name__=='__main__':main()
