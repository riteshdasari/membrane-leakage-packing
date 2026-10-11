"""Serial, source-pinned native/route/replay/power stages for one isolated core."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import sys
sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent
ENERGY = P.parent/'selective_energy_trial'
COMMON = P.parent/'common_layout_trial'
sys.path.insert(0, str(ENERGY))
import run_selective_energy as base
import replay_selective_energy as replay_helpers
sys.path.insert(0, str(COMMON))
import run_guard_add_selective_route as route_helpers
TOP = 'top_guard_add_selective_isolated_v3'
sha, read, write, pins, verify = base.sha, base.read, base.write, base.pins, base.verify
NATIVE = ENERGY/'results/native_models_0_a1'


def frozen():
    return base.frozen() | pins([P.parents[2]/'outputs'/('membrane_selective_energy_trial'+suffix)
                               for suffix in ('.md', '.summary.json', '.manifest.json')])


def directory(stage, attempt):
    path = P/'results'/f'{stage}_a{attempt}'
    assert not path.exists(), ('Preserve attempt', path)
    path.mkdir(parents=True)
    return path


def tool(command, wd, label, stamps, gate=2.3):
    return base.job([str(x).replace('\\','/') for x in command], wd, label, stamps, gate)


def functional():
    files = []
    for suite in ('main', 'models'):
        for stall in (0, 1):
            path = P/'results'/f'native_{suite}_{stall}_a0'/'comparison_checks.json'
            data = read(path)
            assert data['status'] == 'pass' and data['kind'] == suite and data['backpressure'] == bool(stall)
            verify(data['source_sha256']); verify(data['candidate_file_sha256'])
            verify(read(path.parent/'provenance.json'))
            assert sha(data['log_file']) == data['log_sha256']
            assert sha(data['archived_check_file']) == data['archived_check_sha256']
            if suite == 'models' and stall == 0:
                assert data['trace']['matched_all_eighteen_columns']
            files.append(path)
    return pins(files)


def native(suite, stall, attempt):
    wd = directory(f'native_{suite}_{stall}', attempt)
    archive = COMMON/'results'/f'selective_{suite}_p1_{stall}'
    shutil.copyfile(archive/'stream_stim.txt', wd/'stream_stim.txt')
    stamps = frozen() | pins([Path(__file__), P/'CONTRACT.md', P/'guard_add_selective_isolated.sv',
        P/'tb_operand_isolation_compare.sv', P/'verify_operand_isolation.py',
        COMMON/'guard_add_selective.sv', COMMON/'tb_guard_add_selective.sv',
        COMMON.parent/'guard_add.sv', COMMON.parent/'baseline_retime_trial/guard_add_retime.sv',
        archive/'stream_out1.txt', COMMON/'results'/f'selective_{suite}_p1_{stall}_checks.json',
        wd/'stream_stim.txt'])
    write(wd/'provenance.json', stamps)
    commands = [
        [base.VIVADO/'bin/xvlog.bat','-sv','-d',f'STALL={stall}','-d','PROFILE=1',
         '-d',f'CAPTURE_TRACE={int(suite=="models" and stall==0)}','-d','ISOLATE_POLICY=1',
         COMMON/'guard_add_selective.sv', P/'guard_add_selective_isolated.sv',
         COMMON.parent/'guard_add.sv', COMMON.parent/'baseline_retime_trial/guard_add_retime.sv',
         COMMON/'tb_guard_add_selective.sv', P/'tb_operand_isolation_compare.sv'],
        [base.VIVADO/'bin/xvlog.bat', base.VIVADO/'data/verilog/src/glbl.v'],
        [base.VIVADO/'bin/xelab.bat','-mt','off','-debug','typical','-L','unisims_ver',
         'tb_operand_isolation_compare','glbl','-s','sim'],
        [base.VIVADO/'bin/xsim.bat','sim','-R']]
    for n, command in enumerate(commands): tool(command, wd, f'tool_{n}', stamps, 1.2)
    tool([sys.executable,'-B',P/'verify_operand_isolation.py','--directory',wd,
          '--kind',suite,'--stall',stall,'--policy',1,'--output',wd/'comparison_checks.json'], wd, 'verify', stamps, .1)
    print('NATIVE COMPLETE', suite, stall, flush=True)


def route(attempt):
    checks = functional()
    wd = directory('route', attempt)
    stamps = frozen() | checks | pins([Path(__file__), P/'CONTRACT.md',
        P/'guard_add_selective_isolated.sv', P/'guard_add_selective_isolated_timing.sv',
        P/'route_operand_isolation.tcl', COMMON.parent/'guard_add.sv'])
    provenance = hashlib.sha256(json.dumps(stamps, sort_keys=True).encode()).hexdigest()
    write(wd/'source_provenance.json', stamps)
    command = [base.VIVADO/'bin/vivado.bat','-mode','batch','-log','vivado.log','-journal','vivado.jou',
               '-source',P/'route_operand_isolation.tcl','-tclargs',TOP,6,provenance,'fresh',wd]
    try:
        log = tool(command, wd, 'route', stamps)
    except AssertionError:
        failed = (wd/'route.log').read_text(errors='replace')
        assert 'ERROR: [Synth 20-411]' in failed
        assert (wd/'synth/design.dcp').exists()
        assert (wd/'synth/provenance.txt').read_text().strip() == provenance
        command[-2] = 'resume'
        command[4] = 'vivado_resume.log'; command[6] = 'vivado_resume.jou'
        log = tool(command, wd, 'route_resume', stamps)
    assert f'GUARD_ADD_SELECTIVE_TIMING_ROUTED {TOP}' in log.read_text()
    core = route_helpers.util(wd/'core_util.rpt', False)
    full = route_helpers.util(wd/'util.rpt')
    accounting = {k:int(v) for k,v in (line.split() for line in (wd/'fixture_accounting.txt').read_text().splitlines())}
    assert accounting['fixture_FF'] == full['FF']-core['FF'] == 219
    assert accounting['launch_FF']==138 and accounting['capture_FF']==81
    assert core['DSP']==full['DSP']==1
    slack = list(map(float, (wd/'slack.txt').read_text().splitlines()))
    boundary = list(map(float, (wd/'boundary_slack.txt').read_text().splitlines()))
    value = dict(status='pass' if min(slack)>=0 else 'timing_failed', top=TOP,
        core=core, full_fixture=full, slice_accounting=accounting,
        WNS_ns=slack[0], WHS_ns=slack[1], boundary_WNS_ns=boundary[0], boundary_WHS_ns=boundary[1],
        source_sha256=stamps, functional_check_sha256=checks, part='xc7a100tcsg324-1',
        clock_period_ns=6, hd_clk_src='BUFGCTRL_X0Y0',
        artifact_sha256=pins(path for folder in (wd, wd/'synth') for path in folder.iterdir() if path.is_file()),
        scope='Same registered OOC fixture; core counts exclude219FF; raw-port timing separate')
    write(wd/'hardware.json', value)
    print('ROUTE COMPLETE', json.dumps({k:value[k] for k in ('status','core','WNS_ns','WHS_ns')}), flush=True)


def route_data(route_dir):
    hardware = read(route_dir/'hardware.json')
    verify(hardware['source_sha256']); verify(hardware['artifact_sha256'])
    assert hardware['status'] == 'pass' and hardware['top'] == TOP
    return hardware


def export(attempt, route_dir):
    route_data(route_dir)
    wd = directory('export', attempt)
    stamps = frozen() | functional() | pins([Path(__file__), P/'export_operand_isolation.tcl',
        route_dir/'hardware.json', route_dir/'design.dcp'])
    write(wd/'provenance.json', stamps)
    tool([base.VIVADO/'bin/vivado.bat','-mode','batch','-log','vivado.log','-journal','vivado.jou',
        '-source',P/'export_operand_isolation.tcl','-tclargs',route_dir/'design.dcp',wd], wd, 'export', stamps)
    assert f'module {TOP}' in (wd/'routed.v').read_text() and '$sdf_annotate' in (wd/'routed.v').read_text()
    write(wd/'artifacts.json', pins([wd/'routed.v',wd/'routed.sdf',wd/'provenance.json']))
    print('EXPORT COMPLETE', wd, flush=True)


def replay(attempt, export_dir, route_dir):
    route_data(route_dir)
    verify(read(export_dir/'artifacts.json'))
    data, row = replay_helpers.native_data(NATIVE, 3)
    wd = directory('replay', attempt)
    first, last = row['first_accept_trace_index'], row['last_retire_trace_index']
    start = (126+first*6)*1000-1; duration = (last-first+3)*6000; end = start+duration
    batch = wd/'activity.tcl'
    batch.write_text(f'''run {start} ps
open_saif activity.saif
current_scope /tb_selective_route_replay/dut
log_saif [get_objects -r *]
run {duration} ps
close_saif
puts "SELECTIVE_SAIF_CLOSED START_PS {start} END_PS {end} DURATION_PS {duration}"
quit
''')
    stamps = frozen() | functional() | pins([Path(__file__), ENERGY/'replay_selective_energy.py',
        ENERGY/'tb_selective_route_replay.sv', NATIVE/'native_checks.json', Path(row['trace_file']),
        export_dir/'routed.v',export_dir/'routed.sdf',export_dir/'artifacts.json',
        route_dir/'hardware.json',route_dir/'design.dcp',batch])
    write(wd/'provenance.json', stamps)
    commands = [
        [base.VIVADO/'bin/xvlog.bat','-sv','-d','ROUTE_VARIANT=3','-d',f'DUT_TOP={TOP}',
         export_dir/'routed.v',ENERGY/'tb_selective_route_replay.sv'],
        [base.VIVADO/'bin/xvlog.bat',base.VIVADO/'data/verilog/src/glbl.v'],
        [base.VIVADO/'bin/xelab.bat','-mt','off','-debug','all','-L','simprims_ver','-L','unisims_ver',
         '-L','secureip','tb_selective_route_replay','glbl','-s','sim'],
        [base.VIVADO/'bin/xsim.bat','sim','-testplusarg',f"TRACE={row['trace_file']}",
         '-testplusarg',f"ROWS={row['trace_count']}",'-testplusarg',f'ROI_FIRST={first}',
         '-testplusarg',f'ROI_LAST={last}','-tclbatch',batch]]
    logs = [tool(command,wd,f'tool_{n}',stamps) for n,command in enumerate(commands)]
    log = logs[-1].read_text()
    match = re.search(r'SELECTIVE_ROUTE_REPLAY PASS V(\d+) ROWS (\d+) CHECKED (\d+) VALID_ROWS (\d+) TIME_NS ([\d.]+)',log)
    assert match and tuple(map(int,match.groups()[:3])) == (3,row['trace_count'],row['trace_count'])
    assert f'SELECTIVE_SAIF_CLOSED START_PS {start} END_PS {end} DURATION_PS {duration}' in log
    diagnostics = replay_helpers.timing_warnings(logs+list(wd.glob('*.log')))
    stats = replay_helpers.saif_stats(wd/'activity.saif',duration)
    record = dict(status='timing_pass_activity_pending' if not diagnostics else 'invalid',
        variant=3, design_top=TOP, native_row=row, native_check_sha256=sha(NATIVE/'native_checks.json'),
        requests=110592,neurons=635904,clock_period_ns=6,first_replay_drive_time_ns=126,
        output_trace_row_offset=2,roi_start_ps=start,roi_end_ps=end,roi_duration_ps=duration,
        roi_extra_fixture_cycles=2,saif=stats,timing_diagnostics=diagnostics,
        replay_rows_checked=int(match[3]),valid_rows_checked=int(match[4]),
        functional_check_sha256=functional(),source_sha256=stamps,
        artifact_sha256=pins([wd/'activity.saif',batch,*logs]))
    write(wd/'replay_checks.json',record)
    assert record['status']=='timing_pass_activity_pending'
    print('REPLAY COMPLETE', wd, stats, flush=True)


def power(attempt, replay_dir, route_dir):
    route_data(route_dir)
    record=read(replay_dir/'replay_checks.json')
    assert record['status']=='timing_pass_activity_pending' and record['design_top']==TOP
    verify(record['source_sha256']); verify(record['artifact_sha256'])
    saif=replay_dir/'activity_named.saif'
    normalized=read(saif.with_suffix('.names.json'))
    assert normalized['source_sha256']==record['saif']['saif_sha256']
    assert normalized['target_sha256']==sha(saif)
    assert all(normalized[key] for key in ('ordered_numeric_records_unchanged','hierarchy_unchanged','duration_unchanged'))
    wd=directory('power',attempt)
    stamps=frozen() | functional() | pins([Path(__file__), P/'annotation_operand_isolation.tcl', ENERGY/'annotation_power_audit.tcl',
        ENERGY/'normalize_saif_names.py', saif, saif.with_suffix('.names.json'),
        replay_dir/'replay_checks.json', route_dir/'hardware.json', route_dir/'design.dcp'])
    write(wd/'provenance.json',stamps)
    log=tool([base.VIVADO/'bin/vivado.bat','-mode','batch','-log','vivado.log','-journal','vivado.jou',
        '-source',P/'annotation_operand_isolation.tcl','-tclargs',3,route_dir/'design.dcp',saif,wd],wd,'annotation',stamps)
    assert 'SELECTIVE_ANNOTATION_POWER PASS V3' in log.read_text()
    write(wd/'evidence.json',dict(status='reports generated; annotation audit required',variant=3,
        design_top=TOP,replay_dir=str(replay_dir),saif_file=str(saif),source_sha256=stamps,
        artifact_sha256=pins(path for path in wd.iterdir() if path.is_file()),
        duration_seconds=record['saif']['duration_seconds'],neurons=635904))
    print('POWER COMPLETE',wd,flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',action='store_true')
    parser.add_argument('--stage',choices=('native','route','export','replay','power'),required=True)
    parser.add_argument('--suite',choices=('main','models'),default='models')
    parser.add_argument('--stall',type=int,choices=(0,1),default=0)
    parser.add_argument('--attempt',type=int,default=0)
    parser.add_argument('--route-dir',type=Path,default=P/'results/route_a0')
    parser.add_argument('--export-dir',type=Path,default=P/'results/export_a0')
    parser.add_argument('--replay-dir',type=Path,default=P/'results/replay_a0')
    args=parser.parse_args()
    if not args.run: print('No tools launched; explicit --run and source/evidence gates required'); return
    args.route_dir=args.route_dir.resolve();args.export_dir=args.export_dir.resolve();args.replay_dir=args.replay_dir.resolve()
    if args.stage=='native':native(args.suite,args.stall,args.attempt)
    elif args.stage=='route':route(args.attempt)
    elif args.stage=='export':export(args.attempt,args.route_dir)
    elif args.stage=='replay':replay(args.attempt,args.export_dir,args.route_dir)
    else:power(args.attempt,args.replay_dir,args.route_dir)


if __name__=='__main__':main()
