"""Validated routed replay and estimated power; no tools without --run.

Separate from the already frozen native runner. Full saved workload only.
"""
from pathlib import Path
import argparse
import json
import re
import sys
sys.dont_write_bytecode = True
import run_selective_energy as common

P,R,BASE,VIVADO = common.P,common.R,common.COMMON,common.VIVADO
sha,read,write,pins,verify,job = common.sha,common.read,common.write,common.pins,common.verify,common.job


def native_data(directory, variant):
    directory = Path(directory).resolve()
    data = read(directory/'native_checks.json')
    assert data['status'] == 'pass' and data['clock_period_ns'] == 6
    for name, stamp in data['source_hashes'].items():
        assert sha(P/name) == stamp
    row, = [row for row in data['rows'] if row['core_variant'] == variant]
    assert row['status']=='pass' and row['requests']==110592 and row['neurons']==635904
    assert row['service_clocks']==(110596 if variant==2 else 110710)
    assert sha(row['trace_file'])==row['trace_sha256']
    assert sha(row['retirement_file'])==row['retirement_sha256']
    return data,row


def timing_warnings(logs):
    bad=[]
    for path in logs:
        for line in path.read_text(errors='replace').splitlines():
            if re.search(r'\b(Warning|ERROR|Fatal)\b.*(SDF|timing|setup|hold)|Timing violation|\$setuphold|\$recovery|\$recrem|\$width|REPLAY.*mismatch',line,re.I):
                bad.append(dict(file=str(path),line=line))
    return bad


def saif_stats(path, expected_ps):
    # The standard scalar SAIF state times must cover exactly the declared ROI.
    text=path.read_text()
    scale=re.search(r'\(TIMESCALE\s+(\d+)\s+(ps|ns|us|ms|s)\s*\)',text)
    duration=re.search(r'\(DURATION\s+(\d+)\s*\)',text)
    assert scale and duration,'Missing SAIF timescale/duration'
    unit={'ps':1,'ns':1000,'us':1000000,'ms':1000000000,'s':1000000000000}[scale[2]]
    measured=int(scale[1])*unit*int(duration[1])
    assert measured==expected_ps,('SAIF duration',measured,expected_ps)
    records=[]
    pattern=r'\(T0\s+(\d+)\)\s*\(T1\s+(\d+)\)\s*\(TX\s+(\d+)\)(?:\s*\(TZ\s+(\d+)\))?(?:\s*\(TB\s+(\d+)\))?\s*\(TC\s+(\d+)\)'
    for match in re.finditer(pattern,text):
        t0,t1,tx,tz,tb,tc=match.groups()
        assert int(tb or 0)==0,'Unexpected SAIF TB time'
        times=tuple(map(int,(t0,t1,tx,tz or '0')))
        assert sum(times)==int(duration[1]),('Incomplete SAIF state times',times,duration[1])
        records.append((times,int(tc)))
    assert records,'No scalar SAIF activity'
    unknown=[times for times,tc in records if times[2] or times[3]]
    return dict(duration_ps=measured,duration_seconds=measured*1e-12,
        timescale_count=int(scale[1]),timescale_unit=scale[2],scalar_records=len(records),
        unknown_time_records=len(unknown),unknown_time_ticks=sum(x[2]+x[3] for x in unknown),
        aggregate_transition_count=sum(tc for times,tc in records),
        nonzero_transition_records=sum(tc>0 for times,tc in records),saif_sha256=sha(path))


def recover_record(variant,native_dir,replay_dir):
    """Validate completed simulator evidence after a measurement parser repair.

    Only the orchestrator SHA may move to its preserved executed-source copy.
    All simulation, netlist, stimulus, TB and checkpoint pins remain identical.
    """
    common.frozen()
    wd=Path(replay_dir).resolve()
    data,row=native_data(native_dir,variant)
    original_stamps=read(wd/'provenance.json')
    stamps={}
    for name,pin in original_stamps.items():
        path=Path(name)
        if path.resolve()==Path(__file__).resolve() and sha(path)!=pin:
            path=wd/'replay_source.py'
        assert sha(path)==pin,('Changed simulator evidence',name)
        stamps[str(path.resolve())]=pin
    # Preserve the producer version even if a later parser repair is required.
    producer=wd/('record_source_'+sha(__file__)[:12]+'.py')
    if not producer.exists():producer.write_bytes(Path(__file__).read_bytes())
    stamps.update(pins([producer]))
    logs=[wd/f'tool_{index}.log' for index in range(4)]
    for index in range(4):
        meta=read(wd/f'tool_{index}.job.json')
        assert meta['returncode']==0 and sha(logs[index])==meta['log_sha256']
        assert meta['source_sha256']==original_stamps
    log=logs[-1].read_text(errors='replace')
    match=re.search(r'SELECTIVE_ROUTE_REPLAY PASS V(\d+) ROWS (\d+) CHECKED (\d+) VALID_ROWS (\d+) TIME_NS ([\d.]+)',log)
    assert match and tuple(map(int,match.groups()[:3]))==(variant,row['trace_count'],row['trace_count'])
    assert int(match[4])>=110592
    first,last=row['first_accept_trace_index'],row['last_retire_trace_index']
    start_ps=(126+first*6)*1000-1
    duration_ps=(last-first+3)*6000
    end_ps=start_ps+duration_ps
    assert float(match[5])*1000<end_ps
    assert f'SELECTIVE_SAIF_CLOSED START_PS {start_ps} END_PS {end_ps} DURATION_PS {duration_ps}' in log
    assert 'SDF backannotation was successful' in logs[2].read_text()
    diagnostics=timing_warnings(logs+list(wd.glob('*.log')))
    activity=saif_stats(wd/'activity.saif',duration_ps)
    result=dict(status='timing_pass_activity_pending' if not diagnostics else 'invalid',
        variant=variant,native_row=row,native_check_sha256=sha(Path(native_dir)/'native_checks.json'),
        requests=110592,neurons=635904,clock_period_ns=6,
        first_replay_drive_time_ns=126,output_trace_row_offset=2,
        roi_start_ps=start_ps,roi_end_ps=end_ps,roi_duration_ps=duration_ps,
        roi_extra_fixture_cycles=2,saif=activity,timing_diagnostics=diagnostics,
        replay_rows_checked=int(match[3]),valid_rows_checked=int(match[4]),
        source_sha256=stamps,artifact_sha256=pins([wd/'activity.saif',wd/'activity.tcl',*logs]),
        recovered_record_after_parser_repair=True,
        repair='Read simulator TB0 SAIF field; no simulator/source/timing/traffic rerun or modification',
        scope='Mapped timing replay of complete frozen fixture; no power/energy result')
    write(wd/'replay_checks.json',result)
    assert result['status']=='timing_pass_activity_pending',('Invalid timing pilot',wd)
    print('RECOVERED REPLAY RECORD PASS',wd,activity,flush=True)


def replay(variant, attempt, native_dir, export_dir):
    base=common.frozen()
    data,row=native_data(native_dir,variant)
    export_dir=Path(export_dir).resolve()
    verify(read(export_dir/'artifacts.json'))
    netlist,sdf=export_dir/'routed.v',export_dir/'routed.sdf'
    assert f'module top_guard_add_selective_v{variant}' in netlist.read_text()
    assert '$sdf_annotate' in netlist.read_text(), 'Timing netlist lacks SDF annotation'
    wd=common.stage_dir('replay',variant,attempt)
    stamps=base | pins([Path(__file__),P/'tb_selective_route_replay.sv',
        P/'CONTRACT.md',Path(native_dir)/'native_checks.json',Path(row['trace_file']),
        netlist,sdf,export_dir/'artifacts.json'])
    first,last=row['first_accept_trace_index'],row['last_retire_trace_index']
    # First replay falling edge at126ns after #121 startup. Start1ps before
    # launch of useful pins; include two common fixture settling/drain cycles.
    start_ps=(126+first*6)*1000-1
    duration_ps=(last-first+3)*6000
    end_ps=start_ps+duration_ps
    batch=wd/'activity.tcl'
    batch.write_text(f'''run {start_ps} ps
open_saif activity.saif
current_scope /tb_selective_route_replay/dut
log_saif [get_objects -r *]
run {duration_ps} ps
close_saif
puts "SELECTIVE_SAIF_CLOSED START_PS {start_ps} END_PS {end_ps} DURATION_PS {duration_ps}"
quit
''')
    stamps.update(pins([batch]))
    write(wd/'provenance.json',stamps)
    commands=[
        [VIVADO/'bin/xvlog.bat','-sv','-d',f'ROUTE_VARIANT={variant}',
            '-d',f'DUT_TOP=top_guard_add_selective_v{variant}',netlist,P/'tb_selective_route_replay.sv'],
        [VIVADO/'bin/xvlog.bat',VIVADO/'data/verilog/src/glbl.v'],
        [VIVADO/'bin/xelab.bat','-mt','off','-debug','all','-L','simprims_ver',
            '-L','unisims_ver','-L','secureip','tb_selective_route_replay','glbl','-s','sim'],
        [VIVADO/'bin/xsim.bat','sim','-testplusarg',f"TRACE={row['trace_file']}",
            '-testplusarg',f"ROWS={row['trace_count']}",'-testplusarg',f'ROI_FIRST={first}',
            '-testplusarg',f'ROI_LAST={last}','-tclbatch',batch]]
    logs=[]
    for index,command in enumerate(commands):
        # XSim generates Tcl from these arguments; Windows backslashes would
        # become Tcl escapes in source paths and plusargs.
        command=[str(arg).replace('\\','/') for arg in command]
        logs.append(job(command,wd,f'tool_{index}',stamps,2.3))
    log=logs[-1].read_text(errors='replace')
    match=re.search(r'SELECTIVE_ROUTE_REPLAY PASS V(\d+) ROWS (\d+) CHECKED (\d+) VALID_ROWS (\d+) TIME_NS ([\d.]+)',log)
    assert match,('No replay completion',log[-5000:])
    assert tuple(map(int,match.groups()[:3]))==(variant,row['trace_count'],row['trace_count'])
    assert int(match[4])>=110592
    assert float(match[5])*1000<end_ps
    assert f'SELECTIVE_SAIF_CLOSED START_PS {start_ps} END_PS {end_ps} DURATION_PS {duration_ps}' in log
    diagnostics=timing_warnings(logs+list(wd.glob('*.log')))
    activity=saif_stats(wd/'activity.saif',duration_ps)
    result=dict(status='timing_pass_activity_pending' if not diagnostics else 'invalid',
        variant=variant,native_row=row,native_check_sha256=sha(Path(native_dir)/'native_checks.json'),
        requests=110592,neurons=635904,clock_period_ns=6,
        first_replay_drive_time_ns=126,output_trace_row_offset=2,
        roi_start_ps=start_ps,roi_end_ps=end_ps,roi_duration_ps=duration_ps,
        roi_extra_fixture_cycles=2,saif=activity,timing_diagnostics=diagnostics,
        replay_rows_checked=int(match[3]),valid_rows_checked=int(match[4]),
        source_sha256=stamps,artifact_sha256=pins([wd/'activity.saif',batch,*logs]),
        scope='Mapped timing replay of complete frozen fixture; no power/energy result')
    write(wd/'replay_checks.json',result)
    assert result['status']=='timing_pass_activity_pending',('Invalid timing pilot; see replay_checks.json',wd)
    print('REPLAY COMPLETE',variant,wd,activity,flush=True)


def power(variant,attempt,replay_dir):
    base=common.frozen()
    replay_dir=Path(replay_dir).resolve()
    checked=read(replay_dir/'replay_checks.json')
    assert checked['status'] in ('pass','timing_pass_activity_pending') and checked['variant']==variant
    verify(checked['source_sha256']);verify(checked['artifact_sha256'])
    assert saif_stats(replay_dir/'activity.saif',checked['roi_duration_ps'])==checked['saif']
    wd=common.stage_dir('power',variant,attempt)
    stamps=base | pins([Path(__file__),P/'selective_energy_tools.tcl',
        replay_dir/'replay_checks.json',replay_dir/'activity.saif',P/'CONTRACT.md'])
    write(wd/'provenance.json',stamps)
    dcp=BASE/f'results/top_guard_add_selective_v{variant}_route/design.dcp'
    log=job([VIVADO/'bin/vivado.bat','-mode','batch','-log','vivado.log',
        '-journal','vivado.jou','-source',P/'selective_energy_tools.tcl',
        '-tclargs','power',variant,dcp,wd,replay_dir/'activity.saif'],wd,'power',stamps,2.3)
    assert f'SELECTIVE_ENERGY_POWER PASS V{variant}' in log.read_text(errors='replace')
    write(wd/'power_evidence.json',dict(status='reports generated; coverage/precision audit required',
        variant=variant,replay_dir=str(replay_dir),source_sha256=stamps,
        artifact_sha256=pins(path for path in wd.iterdir() if path.is_file()),
        roi_duration_seconds=checked['saif']['duration_seconds'],neurons=635904,
        scope='Vendor OOC estimated power only; no comparative claim before annotation/settings audit'))
    print('POWER REPORTS COMPLETE',variant,wd,flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',action='store_true')
    parser.add_argument('--stage',choices=('replay','power','validate'),default='replay')
    parser.add_argument('--variant',type=int,choices=(2,3),required=True)
    parser.add_argument('--attempt',type=int,default=0)
    parser.add_argument('--native-dir',type=Path)
    parser.add_argument('--export-dir',type=Path)
    parser.add_argument('--replay-dir',type=Path)
    args=parser.parse_args()
    if args.stage=='validate':
        assert args.native_dir and args.replay_dir
        recover_record(args.variant,args.native_dir,args.replay_dir)
        return
    if not args.run:
        print('No tools launched. Replay/power require validated source-bound prior stages.')
        return
    assert args.attempt>=0
    if args.stage=='replay':
        assert args.native_dir and args.export_dir
        replay(args.variant,args.attempt,args.native_dir,args.export_dir)
    else:
        assert args.replay_dir
        power(args.variant,args.attempt,args.replay_dir)


if __name__=='__main__':main()
