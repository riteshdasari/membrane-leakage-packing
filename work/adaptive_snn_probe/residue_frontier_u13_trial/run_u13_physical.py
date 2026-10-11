"""Prepared U13 physical validation: root-only serial RAM-gated execution."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import re
import sys
sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent
ENERGY = P.parent/'selective_energy_trial'
COMMON = P.parent/'common_layout_trial'
sys.path.insert(0,str(ENERGY))
import run_selective_energy as base
import replay_selective_energy as replay_helpers
sys.path.insert(0,str(COMMON))
import run_guard_add_selective_route as route_helpers
sha,read,write,pins,verify = base.sha,base.read,base.write,base.pins,base.verify


def frozen():
    manifest=read(P/'rtl_preparation_manifest.json')
    for key in ('source_sha256','prepared_sha256'):verify(manifest[key])
    manifest2=read(P/'physical_preparation_manifest.json')
    for key in ('source_sha256','prepared_sha256'):verify(manifest2[key])
    return manifest['source_sha256']|manifest['prepared_sha256']|manifest2['source_sha256']|manifest2['prepared_sha256']|pins([P/'rtl_preparation_manifest.json',P/'physical_preparation_manifest.json'])


def sources():
    return pins([Path(__file__),P/'CONTRACT.md',P/'guard_add_frontier_u13.sv',
                 P/'guard_add_frontier_u13_timing.sv',P.parent/'guard_add.sv',
                 P/'prepared_algebra_checks.json'])


def directory(stage,attempt):
    path=P/'results'/f'{stage}_a{attempt}'
    assert not path.exists(),('Preserve attempt',path)
    path.mkdir(parents=True)
    return path


def tool(command,wd,label,stamps,gate=2.3):
    return base.job([str(arg).replace('\\','/') for arg in command],wd,label,stamps,gate)


def functional():
    files=[]
    for kind in ('main','models'):
        for stall in (0,1):
            matches=list((P/'results').glob(f'native_{kind}_{stall}_a*/frontier_checks.json'))
            assert len(matches)==1,('Require one successful cohort',kind,stall,matches)
            path=matches[0]
            d=read(path)
            assert d['status']=='pass' and d['kind']==kind and d['backpressure']==bool(stall)
            assert {r['engine'] for r in d['rows']}==set(range(6))
            assert all(r['status']=='pass' for r in d['rows'])
            verify(read(path.parent/'provenance.json'))
            for key in ('source_sha256','candidate_file_sha256'):
                if key in d:verify(d[key])
            files.append(path)
    return pins(files)



def route(engine,attempt):
    checks=functional()
    top=f'top_guard_add_frontier_u13_e{engine}'
    wd=directory(f'route_e{engine}',attempt)
    stamps=frozen()|sources()|checks|pins([P/'route_u13.tcl'])
    provenance=hashlib.sha256(json.dumps(stamps,sort_keys=True).encode()).hexdigest()
    write(wd/'source_provenance.json',stamps)
    command=[base.VIVADO/'bin/vivado.bat','-mode','batch','-log','vivado.log','-journal','vivado.jou',
             '-source',P/'route_u13.tcl','-tclargs',top,6,provenance,'fresh',wd]
    try:log=tool(command,wd,'route',stamps)
    except AssertionError:
        assert 'ERROR: [Synth 20-411]' in (wd/'route.log').read_text(errors='replace')
        assert (wd/'synth/design.dcp').exists()
        assert (wd/'synth/provenance.txt').read_text().strip()==provenance
        command[-2]='resume';command[4]='vivado_resume.log';command[6]='vivado_resume.jou'
        log=tool(command,wd,'route_resume',stamps)
    assert f'FRONTIER_TIMING_ROUTED {top}' in log.read_text()
    core=route_helpers.util(wd/'core_util.rpt',False);full=route_helpers.util(wd/'util.rpt')
    accounting={k:int(v) for k,v in (line.split() for line in (wd/'fixture_accounting.txt').read_text().splitlines())}
    assert accounting['fixture_FF']==full['FF']-core['FF']==338
    assert accounting['launch_FF']==215 and accounting['capture_FF']==123
    assert core['DSP']==full['DSP']==(0 if engine==4 else 1)
    slack=list(map(float,(wd/'slack.txt').read_text().splitlines()))
    boundary=list(map(float,(wd/'boundary_slack.txt').read_text().splitlines()))
    assert len(slack)==len(boundary)==2 and all(map(math.isfinite,slack+boundary))
    value=dict(status='pass' if min(slack)>=0 else 'timing_failed',engine=engine,top=top,
        core=core,full_fixture=full,slice_accounting=accounting,WNS_ns=slack[0],WHS_ns=slack[1],
        boundary_WNS_ns=boundary[0],boundary_WHS_ns=boundary[1],source_sha256=stamps,
        functional_check_sha256=checks,part='xc7a100tcsg324-1',clock_period_ns=6,
        hd_clk_src='BUFGCTRL_X0Y0',artifact_sha256=pins(path for folder in (wd,wd/'synth')
                                                   for path in folder.iterdir() if path.is_file()),
        scope='Matched8-wide registered OOC fixture,338FF excluded; raw-port timing separate')
    write(wd/'hardware.json',value)
    print('ROUTE COMPLETE',engine,core,slack,flush=True)


def route_data(engine,route_dir):
    d=read(route_dir/'hardware.json')
    verify(d['source_sha256']);verify(d['artifact_sha256'])
    assert d['engine']==engine and d['status']=='pass'
    return d


def export(engine,attempt,route_dir):
    d=route_data(engine,route_dir);wd=directory(f'export_e{engine}',attempt)
    stamps=frozen()|sources()|functional()|pins([P/'export_u13.tcl',route_dir/'design.dcp',route_dir/'hardware.json'])
    write(wd/'provenance.json',stamps)
    tool([base.VIVADO/'bin/vivado.bat','-mode','batch','-log','vivado.log','-journal','vivado.jou',
        '-source',P/'export_u13.tcl','-tclargs',route_dir/'design.dcp',wd],wd,'export',stamps)
    assert f'module {d["top"]}' in (wd/'routed.v').read_text() and '$sdf_annotate' in (wd/'routed.v').read_text()
    write(wd/'artifacts.json',pins([wd/'routed.v',wd/'routed.sdf',wd/'provenance.json']))
    print('EXPORT COMPLETE',engine,flush=True)


def replay(engine,attempt,route_dir,export_dir):
    tb=P/'tb_frontier_u13_route_replay.sv'
    hw=route_data(engine,route_dir);verify(read(export_dir/'artifacts.json'))
    native_check,=list((P/'results').glob('native_models_0_a*/frontier_checks.json'))
    data=read(native_check);row,=[r for r in data['rows'] if r['engine']==engine]
    trace=Path(row['trace_file']);assert sha(trace)==row['trace_sha256']
    first,last=row['first_accept_trace_index'],row['last_retire_trace_index']
    start=(126+first*6)*1000-1;duration=(last-first+3)*6000;end=start+duration
    wd=directory(f'replay_e{engine}',attempt);batch=wd/'activity.tcl'
    batch.write_text(f'''run {start} ps
open_saif activity.saif
current_scope /tb_frontier_u13_route_replay/dut
log_saif [get_objects -r *]
run {duration} ps
close_saif
puts "FRONTIER_SAIF_CLOSED START_PS {start} END_PS {end} DURATION_PS {duration}"
quit
''')
    stamps=frozen()|sources()|functional()|pins([Path(__file__),
        P/'tb_frontier_u13_route_replay.sv',tb,trace,native_check,
        export_dir/'routed.v',export_dir/'routed.sdf',export_dir/'artifacts.json',
        route_dir/'hardware.json',route_dir/'design.dcp',batch])
    write(wd/'provenance.json',stamps)
    commands=[
        [base.VIVADO/'bin/xvlog.bat','-sv','-d',f'ENGINE_ID={engine}','-d',f'DUT_TOP={hw["top"]}',
         export_dir/'routed.v',tb],
        [base.VIVADO/'bin/xvlog.bat',base.VIVADO/'data/verilog/src/glbl.v'],
        [base.VIVADO/'bin/xelab.bat','-mt','off','-debug','all','-maxdelay','-transport_int_delays','-pulse_r','0','-pulse_int_r','0','-pulse_e','0','-pulse_int_e','0','-L','simprims_ver','-L','unisims_ver',
         '-L','secureip','tb_frontier_u13_route_replay','glbl','-s','sim'],
        [base.VIVADO/'bin/xsim.bat','sim','-testplusarg',f'TRACE={trace}',
         '-testplusarg',f'ROWS={row["trace_count"]}','-testplusarg',f'ROI_FIRST={first}',
         '-testplusarg',f'ROI_LAST={last}','-tclbatch',batch]]
    logs=[tool(command,wd,f'tool_{n}',stamps) for n,command in enumerate(commands)]
    import re
    log=logs[-1].read_text()
    match=re.search(r'FRONTIER_ROUTE_REPLAY PASS E(\d+) ROWS (\d+) CHECKED (\d+) VALID_ROWS (\d+) TIME_NS ([\d.]+)',log)
    assert match and tuple(map(int,match.groups()[:3]))==(engine,row['trace_count'],row['trace_count'])
    assert f'FRONTIER_SAIF_CLOSED START_PS {start} END_PS {end} DURATION_PS {duration}' in log
    diagnostics=replay_helpers.timing_warnings(logs+list(wd.glob('*.log')))
    stats=replay_helpers.saif_stats(wd/'activity.saif',duration)
    record=dict(status='timing_pass_activity_pending' if not diagnostics else 'invalid',
        engine=engine,design_top=hw['top'],native_row=row,trace_columns=data['trace_columns'],
        native_check_file=str(native_check),native_check_sha256=sha(native_check),
        requests=row['requests'],neurons=635904,clock_period_ns=6,first_replay_drive_time_ns=126,
        output_trace_row_offset=2,roi_start_ps=start,roi_end_ps=end,roi_duration_ps=duration,
        roi_extra_fixture_cycles=2,clock_startup_delay_ns=6,timing_simulation_method='AMD transport, zero pulse error and rejection, slow/max',saif=stats,timing_diagnostics=diagnostics,
        replay_rows_checked=int(match[3]),valid_rows_checked=int(match[4]),
        functional_check_sha256=functional(),source_sha256=stamps,
        artifact_sha256=pins([wd/'activity.saif',batch,*logs]))
    write(wd/'replay_checks.json',record)
    assert record['status']=='timing_pass_activity_pending',diagnostics
    tool([sys.executable,'-B',ENERGY/'normalize_saif_names.py',wd/'activity.saif',wd/'activity_named.saif'],
             wd,'normalize',stamps|pins([ENERGY/'normalize_saif_names.py']),.1)
    print('REPLAY COMPLETE PULSE V4 COMPLETE',engine,flush=True)



def power(engine,attempt,route_dir,replay_dir):
    hw=route_data(engine,route_dir);record=read(replay_dir/'replay_checks.json')
    assert record['status']=='timing_pass_activity_pending' and record['engine']==engine
    verify(record['source_sha256']);verify(record['artifact_sha256'])
    named=replay_dir/'activity_named.saif';normalized=read(named.with_suffix('.names.json'))
    assert normalized['source_sha256']==record['saif']['saif_sha256'] and normalized['target_sha256']==sha(named)
    assert all(normalized[k] for k in ('ordered_numeric_records_unchanged','hierarchy_unchanged','duration_unchanged'))
    wd=directory(f'power_e{engine}',attempt)
    stamps=frozen()|sources()|functional()|pins([P/'annotation_u13.tcl',named,named.with_suffix('.names.json'),
        ENERGY/'normalize_saif_names.py',replay_dir/'replay_checks.json',route_dir/'hardware.json',route_dir/'design.dcp'])
    write(wd/'provenance.json',stamps)
    log=tool([base.VIVADO/'bin/vivado.bat','-mode','batch','-log','vivado.log','-journal','vivado.jou',
        '-source',P/'annotation_u13.tcl','-tclargs',engine,route_dir/'design.dcp',named,wd],wd,'annotation',stamps)
    assert f'FRONTIER_ANNOTATION_POWER PASS E{engine}' in log.read_text()
    write(wd/'evidence.json',dict(status='reports generated; annotation audit required',engine=engine,
        design_top=hw['top'],replay_dir=str(replay_dir),hardware_file=str(route_dir/'hardware.json'),
        saif_file=str(named),source_sha256=stamps,artifact_sha256=pins(path for path in wd.iterdir() if path.is_file()),
        duration_seconds=record['saif']['duration_seconds'],neurons=635904))
    print('POWER COMPLETE',engine,flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',action='store_true');parser.add_argument('--stage',required=True,choices=('route','export','replay','power'))
    parser.add_argument('--kind',choices=('main','models'),default='models');parser.add_argument('--stall',type=int,choices=(0,1),default=0)
    parser.add_argument('--engine',type=int,choices=range(6),default=0);parser.add_argument('--attempt',type=int,default=0)
    parser.add_argument('--route-dir',type=Path);parser.add_argument('--export-dir',type=Path);parser.add_argument('--replay-dir',type=Path)
    args=parser.parse_args();assert args.run,'Explicit --run required'
    r=(args.route_dir or P/'results'/f'route_e{args.engine}_a0').resolve()
    x=(args.export_dir or P/'results'/f'export_e{args.engine}_a0').resolve()
    s=(args.replay_dir or P/'results'/f'replay_e{args.engine}_a0').resolve()
    if args.stage=='route':route(args.engine,args.attempt)
    elif args.stage=='export':export(args.engine,args.attempt,r)
    elif args.stage=='replay':replay(args.engine,args.attempt,r,x)
    else:power(args.engine,args.attempt,r,s)


if __name__=='__main__':main()
