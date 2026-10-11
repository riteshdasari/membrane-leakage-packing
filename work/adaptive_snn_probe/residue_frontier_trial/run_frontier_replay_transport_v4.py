"""Full routed slow/max replay with AMD-required transport/pulse settings."""
from pathlib import Path
import argparse
import sys
sys.dont_write_bytecode=True
import run_frontier as run
P=Path(__file__).resolve().parent


def prepare_tb():
    src=P/'tb_frontier_route_replay.sv'
    dst=P/'tb_frontier_route_replay_startup_v2.sv'
    old=' reg clk=0;always #3 clk=~clk;'
    new=(' // Hold clock low for6ns to settle time-zero SDF inputs. First edge9ns;\n'
         ' // subsequent edges retain the original3mod6ns phase and6ns period.\n'
         ' reg clk=0;initial begin #6;forever #3 clk=~clk;end')
    source=src.read_text();assert source.count(old)==1
    wanted=source.replace(old,new)
    if dst.exists():assert dst.read_text()==wanted
    else:dst.write_text(wanted)
    return dst


def replay(engine,attempt,route_dir,export_dir):
    tb=prepare_tb()
    hw=run.route_data(engine,route_dir);run.verify(run.read(export_dir/'artifacts.json'))
    native_check,=list((P/'results').glob('native_models_0_a*/frontier_checks.json'))
    data=run.read(native_check);row,=[r for r in data['rows'] if r['engine']==engine]
    trace=Path(row['trace_file']);assert run.sha(trace)==row['trace_sha256']
    first,last=row['first_accept_trace_index'],row['last_retire_trace_index']
    start=(126+first*6)*1000-1;duration=(last-first+3)*6000;end=start+duration
    wd=run.directory(f'replay_e{engine}',attempt);batch=wd/'activity.tcl'
    batch.write_text(f'''run {start} ps
open_saif activity.saif
current_scope /tb_frontier_route_replay/dut
log_saif [get_objects -r *]
run {duration} ps
close_saif
puts "FRONTIER_SAIF_CLOSED START_PS {start} END_PS {end} DURATION_PS {duration}"
quit
''')
    stamps=run.frozen()|run.sources()|run.functional()|run.pins([Path(__file__),
        P/'tb_frontier_route_replay.sv',tb,trace,native_check,
        export_dir/'routed.v',export_dir/'routed.sdf',export_dir/'artifacts.json',
        route_dir/'hardware.json',route_dir/'design.dcp',batch])
    run.write(wd/'provenance.json',stamps)
    commands=[
        [run.base.VIVADO/'bin/xvlog.bat','-sv','-d',f'ENGINE_ID={engine}','-d',f'DUT_TOP={hw["top"]}',
         export_dir/'routed.v',tb],
        [run.base.VIVADO/'bin/xvlog.bat',run.base.VIVADO/'data/verilog/src/glbl.v'],
        [run.base.VIVADO/'bin/xelab.bat','-mt','off','-debug','all','-maxdelay','-transport_int_delays','-pulse_r','0','-pulse_int_r','0','-pulse_e','0','-pulse_int_e','0','-L','simprims_ver','-L','unisims_ver',
         '-L','secureip','tb_frontier_route_replay','glbl','-s','sim'],
        [run.base.VIVADO/'bin/xsim.bat','sim','-testplusarg',f'TRACE={trace}',
         '-testplusarg',f'ROWS={row["trace_count"]}','-testplusarg',f'ROI_FIRST={first}',
         '-testplusarg',f'ROI_LAST={last}','-tclbatch',batch]]
    logs=[run.tool(command,wd,f'tool_{n}',stamps) for n,command in enumerate(commands)]
    import re
    log=logs[-1].read_text()
    match=re.search(r'FRONTIER_ROUTE_REPLAY PASS E(\d+) ROWS (\d+) CHECKED (\d+) VALID_ROWS (\d+) TIME_NS ([\d.]+)',log)
    assert match and tuple(map(int,match.groups()[:3]))==(engine,row['trace_count'],row['trace_count'])
    assert f'FRONTIER_SAIF_CLOSED START_PS {start} END_PS {end} DURATION_PS {duration}' in log
    diagnostics=run.replay_helpers.timing_warnings(logs+list(wd.glob('*.log')))
    stats=run.replay_helpers.saif_stats(wd/'activity.saif',duration)
    record=dict(status='timing_pass_activity_pending' if not diagnostics else 'invalid',
        engine=engine,design_top=hw['top'],native_row=row,trace_columns=data['trace_columns'],
        native_check_file=str(native_check),native_check_sha256=run.sha(native_check),
        requests=row['requests'],neurons=635904,clock_period_ns=6,first_replay_drive_time_ns=126,
        output_trace_row_offset=2,roi_start_ps=start,roi_end_ps=end,roi_duration_ps=duration,
        roi_extra_fixture_cycles=2,clock_startup_delay_ns=6,timing_simulation_method='AMD transport, zero pulse error and rejection, slow/max',saif=stats,timing_diagnostics=diagnostics,
        replay_rows_checked=int(match[3]),valid_rows_checked=int(match[4]),
        functional_check_sha256=run.functional(),source_sha256=stamps,
        artifact_sha256=run.pins([wd/'activity.saif',batch,*logs]))
    run.write(wd/'replay_checks.json',record)
    assert record['status']=='timing_pass_activity_pending',diagnostics
    run.tool([sys.executable,'-B',run.ENERGY/'normalize_saif_names.py',wd/'activity.saif',wd/'activity_named.saif'],
             wd,'normalize',stamps|run.pins([run.ENERGY/'normalize_saif_names.py']),.1)
    print('REPLAY COMPLETE PULSE V4 COMPLETE',engine,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run',action='store_true')
    parser.add_argument('--engine',type=int,choices=range(6),required=True)
    parser.add_argument('--attempt',type=int,default=3)
    a=parser.parse_args();assert a.run
    replay(a.engine,a.attempt,P/'results'/f'route_e{a.engine}_a0',P/'results'/f'export_e{a.engine}_a0')
