"""Strict new leakage trace/SDF audit; physical-net checks imported as source from frozen predecessor."""
from pathlib import Path
from collections import deque
import importlib.util,json,re,sys
import xml.etree.ElementTree as ET
P=Path(__file__).resolve().parent;OLD=P.parent/'selective_energy_trial'
ROOT='tb_sequential_energy_replay/dut';SCALARS=17408;PERIOD_PS=6000
AUDIT_SHA='d4cc05920fb7a2beada60d125bc885b39ad9eefd1a6aac68bb26cc258aa9ddf2'
NORMALIZER_SHA='81d84539f84354b317e452de0f4ffe3858f4a32afa54baea37416497d1d7ff07'
path=OLD/'audit_selective_energy.py'
import hashlib
assert hashlib.sha256(path.read_bytes()).hexdigest()==AUDIT_SHA
spec=importlib.util.spec_from_file_location('frozen_physical_saif_parser',path)
prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
read,sha,verify=prior.read,prior.sha,prior.verify
def replay(directory):
    directory=Path(directory);d=read(directory/'replay_checks.json');e=d['engine']
    assert d['status']=='timing_pass_activity_pending'and e in range(6)
    verify(d['source_sha256']);verify(d['artifact_sha256'])
    native=read(P/'stage4_native_acceptance_v4.json');assert native['status']=='pass'
    verify(native['source_sha256']);verify(native['artifact_sha256'])
    checkfile=Path(d['native_check_file']);check=read(checkfile)
    assert sha(checkfile)==d['native_check_sha256']and check['status']=='pass'and check['kind']=='actual'and check['stall']==0
    verify(check['source_sha256']);verify(check['artifact_sha256'])
    row,=[r for r in check['rows']if r['engine']==e];assert row==d['native_row']
    trace=checkfile.parent/f'trace{e}.txt';assert sha(trace)==d['trace_sha256']
    queue=deque();requests=retired=neurons=retired_neurons=0;first=last=None
    for index,line in enumerate(trace.open()):
        f=line.split();assert len(f)==15 and int(f[0])==index
        v=[int(x,16 if j in(5,6,11)else 10)for j,x in enumerate(f)]
        _,rst,iv,ready,av,U,B,ir,take,ov,count,data,mode,accept,retire=v
        assert 0<=av<=2 and accept==int(iv and ir and av>0)and retire==int(ov and ready)
        if accept:
            assert not rst and 1<=take<=av
            want=0
            for k in range(take):
                u=(U>>(12*k))&4095;u=u-4096 if u&2048 else u;b=(B>>(9*k))&511
                assert b<=256;want|=(-((-u*b)//256)&4095)<<(12*k)
            queue.append((take,want));requests+=1;neurons+=take
            if first is None:first=index
        if retire:
            assert queue and(count,data)==queue.popleft();retired+=1;retired_neurons+=count;last=index
    total=index+1
    assert not queue and requests==retired==row['requests']and neurons==retired_neurons==SCALARS
    assert(first,last)==(row['first_accept'],row['last_retire'])and total==d['replay_rows_checked']==d['trace_count']
    start=126000+6000*first-1;duration=6000*(last-first+3)
    assert(d['roi_start_ps'],d['roi_duration_ps'],d['roi_end_ps'])==(start,duration,start+duration)
    assert d['output_trace_row_offset']==2 and d['clock_period_ns']==6
    golden=read(Path(d['golden_check_file']));assert golden['status']=='pass'
    verify(golden['source_sha256']);verify(golden['artifact_sha256'])
    exported=Path(d['export_artifacts_file']);verify(read(exported));producer=read(exported.parent/'provenance.json');verify(producer)
    for name in ('routed.v','routed.sdf'):
        p=str(exported.parent/name);assert producer.get(p,sha(p))==d['source_sha256'][p]==read(exported)[p]==sha(p)
    hardware_file=Path(d['hardware_file']);hardware=read(hardware_file);assert hardware['status']=='pass'
    dcp=str(hardware_file.parent/'design.dcp');assert producer[dcp]==d['source_sha256'][dcp]==sha(dcp)
    text='\n'.join(p.read_text(errors='replace')for p in directory.glob('*.log'))
    assert 'SDF backannotation was successful'in text and f'root module "{ROOT}"'in text
    assert not re.search(r'\b(?:Warning|ERROR|Fatal)\b.*(?:SDF|timing|setup|hold)|Timing violation|\$setuphold|\$recovery|\$recrem|\$width|REPLAY.*mismatch',text,re.I)
    assert f'FRONTIER_ROUTE_REPLAY PASS E{e} ROWS {total} CHECKED {total}'in text
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
    assert records[ROOT+'/clk']==(duration//2,duration//2,0,0,0,duration//3000)
    return dict(status='pass',engine=e,design_top=d['design_top'],duration_ps=duration,scalar_updates=neurons,requests=requests,retirements=retired,clock_transitions=duration//3000,raw_unknown_time_records=unknown,scope='New leakage trace, golden fixture, exact routed/SDF replay and SAIF interval audit')
