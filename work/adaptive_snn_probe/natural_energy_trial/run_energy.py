"""Serial, RAM-gated full-trace energy evaluation of the frozen U11 cores."""
from pathlib import Path
from collections import deque
import argparse
import importlib.util
import re
import sys
import time

sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent
ROOT = P.parent
J = ROOT/'natural_u11_trial'
sys.path.insert(0,str(ROOT/'selective_energy_trial'))
import run_selective_energy as base
sys.path.insert(0,str(ROOT/'residue_frontier_trial'))
import run_frontier_replay_transport_v4 as replay_helpers
sys.path.insert(0,str(J))
import run_trial as native
from workload import load_groups, take_for

sha,read,write,pins,verify=base.sha,base.read,base.write,base.pins,base.verify
R=P/'results'
COLS=['idx','running','done','rst','in_valid','out_ready','available','U','I','in_ready',
      'take','out_valid','out_count','out_data','narrow_mode','advance','accepted_thiscycle','retired_thiscycle']

def sources():
    prep=read(P/'source_preparation.json');verify(prep['source_sha256']);verify(prep['generated_sha256'])
    return native.sources()|pins([P/'source_preparation.json',Path(__file__),
        *[P/n for n in ('tb_replay.sv','export.tcl','power.tcl','audit_power.py','CONTRACT.md')],
        ROOT/'selective_energy_trial/normalize_saif_names.py',
        ROOT/'residue_frontier_trial/run_frontier_replay_transport_v4.py'])

def functional():
    return native.functional()|pins([R/'native_trace_a0/trace_checks.json'])

def directory(label,attempt=0):
    wd=R/f'{label}_a{attempt}';assert not wd.exists(),wd;wd.mkdir(parents=True);return wd

def tool(command,wd,label,stamps,gate=2.3):
    command=[str(c).replace('\\','/')for c in command]
    while True:
        while base.free()<=gate+.15:time.sleep(5)
        try:return base.job(command,wd,label,stamps,gate)
        except AssertionError as exc:
            if 'Insufficient free RAM' not in str(exc):raise
            assert not(wd/f'{label}.job.json').exists()
            time.sleep(5)

def capture():
    wd=directory('native_trace');old=J/'results/native_shift3_stall0_a0'
    stamps=sources()|native.functional()|pins([old/n for n in ('native_checks.json','provenance.json','stream_stim.txt','workload.json','reference_ledger.json')])
    verify(read(old/'provenance.json'))
    for name in ('stream_stim.txt','workload.json','reference_ledger.json'):
        (wd/name).write_bytes((old/name).read_bytes())
    stamps.update(pins(wd/n for n in ('stream_stim.txt','workload.json','reference_ledger.json')))
    write(wd/'provenance.json',stamps)
    commands=[
        [base.VIVADO/'bin/xvlog.bat','-sv','-d','STALL=0','-d','CAPTURE_TRACE=1',J/'core.sv',J/'tb_native.sv'],
        [base.VIVADO/'bin/xvlog.bat',base.VIVADO/'data/verilog/src/glbl.v'],
        [base.VIVADO/'bin/xelab.bat','-mt','off','-debug','typical','-L','unisims_ver','tb_natural_u11','glbl','-s','sim'],
        [base.VIVADO/'bin/xsim.bat','sim','-R'],
        [sys.executable,'-B',J/'verify_native.py','--directory',wd,'--kind','shift3','--stall','0']]
    for n,command in enumerate(commands):tool(command,wd,f'tool_{n}',stamps,1.2)
    check=read(wd/'native_checks.json');prior=read(old/'native_checks.json')
    assert check['status']=='pass';groups=load_groups(wd/'stream_stim.txt');log=(wd/'tool_3.log').read_text()
    pattern=(r'FRONTIER E {e} REQUESTS (\d+) RETIREMENTS (\d+) NEURONS (\d+) CLOCKS (\d+) '
             r'INPUT_STALLS (\d+) OUTPUT_STALLS (\d+) MIN_LATENCY (\d+) MAX_LATENCY (\d+) '
             r'TRACE_ROWS (\d+) FIRST_ACCEPT_TRACE (-?\d+) LAST_RETIRE_TRACE (-?\d+)')
    artifacts=dict(check['candidate_file_sha256']);rows=[]
    for e,(row,oldrow)in enumerate(zip(check['rows'],prior['rows'])):
        for key in ('requests','service_clocks','neurons','numeric_retirement_sha256','retirement_sha256'):
            assert row[key]==oldrow[key],(e,key)
        assert (wd/f'frontier_out{e}.txt').read_bytes()==(old/f'frontier_out{e}.txt').read_bytes()
        match=re.search(pattern.format(e=e),log);assert match
        nrows,first,last=map(int,match.groups()[-3:]);trace=wd/f'frontier_trace{e}.txt'
        queue=deque();req=ret=neurons=total=gid=pos=0;actualfirst=actuallast=None
        for index,line in enumerate(trace.open()):
            fields=line.split();assert len(fields)==18 and int(fields[0])==index
            v={k:int(s,16 if k in ('U','I','out_data')else 10)for k,s in zip(COLS,fields)}
            total+=1;assert v['done']==0 and 0<=v['available']<=8
            if not v['running']:continue
            assert v['rst']==0 and v['in_ready']==int(not(v['out_valid']and not v['out_ready']))
            accept=bool(v['in_valid']and v['in_ready']and v['available'])
            retire=bool(v['out_valid']and v['out_ready'])
            assert v['accepted_thiscycle']==accept and v['retired_thiscycle']==retire
            if accept:
                gap,pairs=groups[gid];assert gap==0 and v['available']==min(8,len(pairs)-pos)
                take=take_for(e,pairs,pos);assert v['take']==take
                want=0
                for lane in range(take):
                    u=(v['U']>>(11*lane))&2047;i=(v['I']>>(11*lane))&2047
                    u=u-2048 if u&1024 else u;i=i-2048 if i&1024 else i
                    assert (u,i)==pairs[pos+lane]
                    want|=((u+i)&4095)<<(12*lane)
                queue.append((take,want));req+=1;neurons+=take
                if actualfirst is None:actualfirst=index
                pos+=take
                if pos==len(pairs):gid+=1;pos=0
            if retire:
                assert queue;wantcount,wantdata=queue.popleft()
                assert v['out_count']==wantcount and v['out_data']==wantdata
                ret+=1;actuallast=index
        assert not queue and gid==len(groups)and pos==0
        assert total==nrows and(first,last)==(actualfirst,actuallast)
        assert req==ret==row['requests']and neurons==row['neurons']==635904
        artifacts.update(pins([trace]));rows.append(row|dict(trace_file=str(trace),trace_sha256=sha(trace),
            trace_count=nrows,first_accept_trace_index=first,last_retire_trace_index=last))
    value=check|dict(rows=rows,trace_columns=COLS,source_sha256=stamps,
        candidate_file_sha256=artifacts,scope='Independent full raw-pin capture and exact identical original shift3 native retirements; no SDF or energy yet')
    write(wd/'trace_checks.json',value);print('U11 ENERGY NATIVE TRACE PASS',flush=True)

def route_data(e):
    folder=J/f'results/route_e{e}_a0';d=read(folder/'hardware.json')
    verify(d['source_sha256']);verify(d['artifact_sha256'])
    assert d['status']=='pass'and d['engine']==e and d['clock_period_ns']==6
    return folder,d

def export(e):
    route,hw=route_data(e);wd=directory(f'export_e{e}')
    stamps=sources()|functional()|pins([route/'hardware.json',route/'design.dcp'])
    write(wd/'provenance.json',stamps)
    tool([base.VIVADO/'bin/vivado.bat','-mode','batch','-log','vivado.log','-journal','vivado.jou',
        '-source',P/'export.tcl','-tclargs',route/'design.dcp',wd],wd,'export',stamps)
    assert f'module {hw["top"]}'in(wd/'routed.v').read_text()and '$sdf_annotate'in(wd/'routed.v').read_text()
    write(wd/'artifacts.json',pins([wd/'routed.v',wd/'routed.sdf',wd/'provenance.json']))
    print('U11 ENERGY EXPORT PASS',e,flush=True)

def replay(e):
    route,hw=route_data(e);exportdir=R/f'export_e{e}_a0';verify(read(exportdir/'artifacts.json'))
    checkfile=R/'native_trace_a0/trace_checks.json';data=read(checkfile);row=data['rows'][e]
    trace=Path(row['trace_file']);assert sha(trace)==row['trace_sha256']
    first,last=row['first_accept_trace_index'],row['last_retire_trace_index']
    start=126000+first*6000-1;duration=(last-first+3)*6000;end=start+duration
    wd=directory(f'replay_e{e}');batch=wd/'activity.tcl'
    batch.write_text(f'''run {start} ps
open_saif activity.saif
current_scope /tb_natural_energy_replay/dut
log_saif [get_objects -r *]
run {duration} ps
close_saif
puts "FRONTIER_SAIF_CLOSED START_PS {start} END_PS {end} DURATION_PS {duration}"
quit
''')
    stamps=sources()|functional()|pins([trace,checkfile,batch,route/'hardware.json',route/'design.dcp',
        exportdir/'routed.v',exportdir/'routed.sdf',exportdir/'artifacts.json'])
    write(wd/'provenance.json',stamps)
    commands=[
        [base.VIVADO/'bin/xvlog.bat','-sv','-d',f'ENGINE_ID={e}','-d',f'DUT_TOP={hw["top"]}',exportdir/'routed.v',P/'tb_replay.sv'],
        [base.VIVADO/'bin/xvlog.bat',base.VIVADO/'data/verilog/src/glbl.v'],
        [base.VIVADO/'bin/xelab.bat','-mt','off','-debug','all','-maxdelay','-transport_int_delays',
         '-pulse_r','0','-pulse_int_r','0','-pulse_e','0','-pulse_int_e','0','-L','simprims_ver',
         '-L','unisims_ver','-L','secureip','tb_natural_energy_replay','glbl','-s','sim'],
        [base.VIVADO/'bin/xsim.bat','sim','-testplusarg',f'TRACE={trace}','-testplusarg',f'ROWS={row["trace_count"]}',
         '-testplusarg',f'ROI_FIRST={first}','-testplusarg',f'ROI_LAST={last}','-tclbatch',batch]]
    logs=[tool(command,wd,f'tool_{n}',stamps)for n,command in enumerate(commands)]
    log=logs[-1].read_text();m=re.search(r'FRONTIER_ROUTE_REPLAY PASS E(\d+) ROWS (\d+) CHECKED (\d+) VALID_ROWS (\d+) TIME_NS ([\d.]+)',log)
    assert m and tuple(map(int,m.groups()[:3]))==(e,row['trace_count'],row['trace_count'])
    assert f'FRONTIER_SAIF_CLOSED START_PS {start} END_PS {end} DURATION_PS {duration}'in log
    diagnostics=replay_helpers.timing_warnings(logs+list(wd.glob('*.log')))
    stats=replay_helpers.saif_stats(wd/'activity.saif',duration)
    record=dict(status='timing_pass_activity_pending'if not diagnostics else'invalid',engine=e,design_top=hw['top'],
        native_row=row,trace_columns=COLS,native_check_file=str(checkfile),native_check_sha256=sha(checkfile),
        requests=row['requests'],neurons=635904,clock_period_ns=6,first_replay_drive_time_ns=126,
        output_trace_row_offset=2,roi_start_ps=start,roi_end_ps=end,roi_duration_ps=duration,
        roi_extra_fixture_cycles=2,clock_startup_delay_ns=6,timing_simulation_method='AMD transport, zero pulse error and rejection, slow/max',
        saif=stats,timing_diagnostics=diagnostics,replay_rows_checked=int(m[3]),valid_rows_checked=int(m[4]),
        functional_check_sha256=functional(),source_sha256=stamps,artifact_sha256=pins([wd/'activity.saif',batch,*logs]))
    write(wd/'replay_checks.json',record);assert record['status']=='timing_pass_activity_pending',diagnostics
    norm=ROOT/'selective_energy_trial/normalize_saif_names.py'
    tool([sys.executable,'-B',norm,wd/'activity.saif',wd/'activity_named.saif'],wd,'normalize',stamps|pins([norm]),.1)
    print('U11 ENERGY FULL SDF REPLAY PASS',e,flush=True)

def power(e):
    route,hw=route_data(e);replaydir=R/f'replay_e{e}_a0';d=read(replaydir/'replay_checks.json')
    assert d['status']=='timing_pass_activity_pending';verify(d['source_sha256']);verify(d['artifact_sha256'])
    named=replaydir/'activity_named.saif';norm=read(named.with_suffix('.names.json'))
    assert norm['target_sha256']==sha(named)and norm['source_sha256']==d['saif']['saif_sha256']
    wd=directory(f'power_e{e}');stamps=sources()|functional()|pins([named,named.with_suffix('.names.json'),
        replaydir/'replay_checks.json',route/'hardware.json',route/'design.dcp'])
    write(wd/'provenance.json',stamps)
    tool([base.VIVADO/'bin/vivado.bat','-mode','batch','-log','vivado.log','-journal','vivado.jou',
        '-source',P/'power.tcl','-tclargs',e,route/'design.dcp',named,wd],wd,'annotation',stamps)
    write(wd/'evidence.json',dict(status='reports generated; independent audit required',engine=e,
        design_top=hw['top'],replay_dir=str(replaydir),hardware_file=str(route/'hardware.json'),
        saif_file=str(named),source_sha256=stamps,artifact_sha256=pins(p for p in wd.iterdir()if p.is_file()),
        duration_seconds=d['saif']['duration_seconds'],neurons=635904))
    auditfile=P/'audit_power.py';spec=importlib.util.spec_from_file_location('natural_U11_energy_audit',auditfile)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    checked=module.annotation(wd);write(wd/'power_audit.json',checked)
    print('U11 ENERGY STRICT POWER AUDIT PASS',e,checked['estimated_dynamic_energy_pJ_per_scalar_update'],flush=True)

def all_stages():
    progress=P/'completion_progress.json';assert not progress.exists()
    state=dict(status='native_trace',stages=[],failures=[],source_sha256=sources())
    def publish():write(progress,state|dict(unix_time=time.time()))
    publish();capture();state['stages'].append(['native_trace',None]);publish()
    for e in range(5):
        for stage,fn in (('export',export),('replay',replay),('power',power)):
            state['status']=f'{stage}_e{e}';publish()
            try:fn(e)
            except Exception as exc:
                state['failures'].append(dict(engine=e,stage=stage,reason=repr(exc),accepted_energy=False))
                print('U11 ENERGY RETAINED FAILURE',e,stage,repr(exc),flush=True);publish();break
            state['stages'].append([stage,e]);publish()
    state['status']='all_energy_audits_passed'if not state['failures']else'completed_with_retained_failures';publish()
    print('U11 ENERGY BOUNDED COHORT CLOSED',state['status'],flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--run',action='store_true');ap.add_argument('--stage',choices=('all','native','export','replay','power'),required=True)
    ap.add_argument('--engine',type=int,choices=range(5));args=ap.parse_args();assert args.run
    if args.stage=='all':all_stages()
    elif args.stage=='native':capture()
    else:assert args.engine is not None;globals()[args.stage](args.engine)
