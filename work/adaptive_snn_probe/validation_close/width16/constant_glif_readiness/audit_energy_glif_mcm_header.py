"""Strict source/known-pin/full-SDF/activity audit for new shared GLIF MCM."""
from pathlib import Path
from collections import deque
import hashlib,importlib.util,json,re,sys
import xml.etree.ElementTree as ET
import numpy as np
P=Path(__file__).resolve().parent;W=P.parent;OLD=W.parent.parent/'selective_energy_trial'
ROOT='tb_sequential_energy_replay16/dut';PERIOD_PS=12000
AUDIT_SHA='d4cc05920fb7a2beada60d125bc885b39ad9eefd1a6aac68bb26cc258aa9ddf2'
NORMALIZER_SHA='81d84539f84354b317e452de0f4ffe3858f4a32afa54baea37416497d1d7ff07'
path=OLD/'audit_selective_energy.py';assert hashlib.sha256(path.read_bytes()).hexdigest()==AUDIT_SHA
spec=importlib.util.spec_from_file_location('frozen_physical_saif_parser_glif_mcm',path)
prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
read,sha,verify=prior.read,prior.sha,prior.verify
TOP='top_sequential_leak16_glif_mcm'


def replay(directory):
 directory=Path(directory).resolve();d=read(directory/'replay_checks.json');e=d['engine']
 assert d['status']=='timing_pass_activity_pending' and e==9 and d['design_top']==TOP
 verify(d['source_sha256']);verify(d['artifact_sha256'])
 checkfile=Path(d['native_check_file']).resolve();check=read(checkfile)
 assert sha(checkfile)==d['native_check_sha256'] and check['status']=='pass' and check['B']==16 and check['cohort']=='actual_glif'
 assert check['stall']==0 and check['capture']==1 and check['label']=='shared_GLIF_checkpoint_MCM_LUT2'
 verify(check['source_sha256']);verify(check['artifact_sha256'])
 row=check['fields'];assert row==d['native_fields']
 prep=read(P/'preparation.json');verify(prep['source_sha256']);allowed=set(prep['domain']['beta'])
 assert check['beta_domain']==prep['domain']['beta'] and len(allowed)==33
 expectation_path=Path(d['cohort_expectation_file']);expectation=read(expectation_path)
 assert d['source_sha256'][str(expectation_path)]==sha(expectation_path)
 verify(expectation['source_sha256']);cohort=expectation['cohorts']['actual_glif'];verify(cohort['artifact_sha256'])
 actual={key:value for key,value in np.load(cohort['expected_outputs_file']).items()}
 assert row['scalars']==cohort['operations']==262528 and row['requests']==cohort['expected_requests_by_engine'][2]==131328
 ends=np.repeat(np.cumsum(actual['frame_lengths']),actual['frame_lengths'])
 trace=Path(d['native_trace_file']);assert trace==checkfile.parent/'trace.txt' and sha(trace)==d['trace_sha256']
 queue=deque();requests=retired=neurons=retired_neurons=valid_rows=0;first=last=None
 for index,line in enumerate(trace.open()):
  f=line.split();assert len(f)==15 and int(f[0])==index
  v=[int(x,16 if j in(5,6,11)else 10)for j,x in enumerate(f)]
  _,rst,iv,ready,av,U,B,ir,take,ov,count,data,mode,accept,retire=v
  assert 0<=av<=2 and accept==int(iv and ir and av>0) and retire==int(ov and ready) and mode==0
  valid_rows+=ov
  if accept:
   assert not rst and take==av and av==(2 if ends[neurons]-neurons>=2 else 1)
   want=0
   for k in range(av):
    u=(U>>(16*k))&65535;u=u-65536 if u&32768 else u;b=(B>>(9*k))&511
    assert b in allowed and u==int(actual['U'][neurons+k]) and b==int(actual['beta'][neurons+k])
    scalar=-((-u*b)//256);assert scalar==int(actual['expected_leak'][neurons+k])
    want|=(scalar&65535)<<(16*k)
   queue.append((take,want,index));requests+=1;neurons+=take
   if first is None:first=index
  if retire:
   assert queue
   qcount,qdata,qcycle=queue.popleft();assert(count,data,mode)==(qcount,qdata,0)and index-qcycle==2
   retired+=1;retired_neurons+=count;last=index
 total=index+1
 assert not queue and requests==retired==row['requests']==row['retirements'] and neurons==retired_neurons==row['scalars']==cohort['operations']
 assert(first,last)==(row['first'],row['last']) and total==d['replay_rows_checked']==d['trace_count']
 assert valid_rows==d['valid_rows_checked']
 start=132000+12000*first-1;duration=12000*(last-first+3)
 assert(d['roi_start_ps'],d['roi_duration_ps'],d['roi_end_ps'])==(start,duration,start+duration)
 assert d['output_trace_row_offset']==2 and d['clock_period_ns']==12
 golden=read(Path(d['golden_check_file']));assert golden['status']=='pass' and golden['engine']==9 and golden['design_top']==TOP
 verify(golden['source_sha256']);verify(golden['artifact_sha256']);assert golden['trace_sha256']==sha(trace)
 assert golden['replay_rows_checked']==total and golden['valid_rows_checked']==valid_rows
 exported=Path(d['export_artifacts_file']);verify(read(exported));producer=read(exported.parent/'provenance.json');verify(producer)
 for name in ('routed.v','routed.sdf'):
  p=str(exported.parent/name);assert producer.get(p,sha(p))==d['source_sha256'][p]==read(exported)[p]==sha(p)
 hardware_file=Path(d['hardware_file']);hardware=read(hardware_file)
 assert hardware['status']=='pass' and hardware['top']==TOP and hardware['label']=='shared_GLIF_checkpoint_MCM_LUT2'
 dcp=str(hardware_file.parent/'design.dcp');assert producer[dcp]==d['source_sha256'][dcp]==sha(dcp)
 text='\n'.join(p.read_text(errors='replace')for p in directory.glob('*.log'))
 assert text.count('SDF backannotation was successful')>=1 and f'root module "{ROOT}"'in text
 assert not re.search(r'\b(?:Warning|ERROR|Fatal)\b.*(?:SDF|timing|setup|hold)|Timing violation|\$setuphold|\$recovery|\$recrem|\$width|REPLAY.*mismatch',text,re.I)
 assert f'FRONTIER_ROUTE_REPLAY PASS E{e} ROWS {total} CHECKED {total} VALID_ROWS {valid_rows}'in text
 assert f'FRONTIER_SAIF_CLOSED START_PS {start} END_PS {start+duration} DURATION_PS {duration}'in text
 jobs=[read(p)for p in directory.glob('tool_*.job.json')];assert len(jobs)==4 and all(j['returncode']==0 for j in jobs)
 opts,=[j['argv']for j in jobs if Path(j['argv'][0]).name=='xelab.bat']
 assert '-transport_int_delays'in opts and '-maxdelay'in opts
 assert not re.search(r'notimingchecks|nospecify|sdfnoerrors|sdfnowarn',' '.join(opts),re.I)
 for name in('-pulse_r','-pulse_int_r','-pulse_e','-pulse_int_e'):assert opts.count(name)==1 and opts[opts.index(name)+1]=='0'
 raw=directory/'activity.saif';s=raw.read_text();assert re.search(r'\(TIMESCALE\s+1\s+ps\)',s)
 assert int(re.search(r'\(DURATION\s+(\d+)\)',s)[1])==duration
 records=prior.saif_records(raw);unknown=0
 for a,b,x,z,tb,tc in records.values():
  assert a+b+x+z==duration and tb==0;unknown+=bool(x or z)
 assert records[ROOT+'/clk']==(duration//2,duration//2,0,0,0,duration//6000)
 return dict(status='pass',engine=e,design_top=TOP,duration_ps=duration,scalar_updates=neurons,requests=requests,retirements=retired,
       clock_transitions=duration//6000,raw_unknown_time_records=unknown,
       scope='Full captured runtime selected GLIF coefficients, fullsigned16 membranes, fixed independent pair consumption; every known pin row through golden and complete certified full-interconnect SDF replay; exact SAIF ROI')
