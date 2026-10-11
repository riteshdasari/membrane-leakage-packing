"""Isolate cell-path-delay effects; never an accepted timing/energy run.

The routed netlist, complete SDF, trace, clock and comparison assertions are
unchanged. Cell specify paths/checks are disabled only in this diagnostic.
Interconnect transport is retained. No SAIF or power is produced.
"""
from pathlib import Path
import sys,re
sys.dont_write_bytecode=True
import run_frontier_f5 as run
P=Path(__file__).resolve().parent
wd=P/'results/diagnostic_no_cell_paths_a0';assert not wd.exists();wd.mkdir()
export=P/'results/export_e5_a1'
run.verify(run.read(export/'artifacts.json'))
native=P/'results/native_models_0_a0/frontier_checks.json'
row=run.read(native)['rows'][5]
stamps=run.frozen()|run.sources()|run.functional()|run.pins([
    Path(__file__),native,export/'artifacts.json',export/'routed.v',export/'routed.sdf',
    P/'tb_frontier_route_replay.sv',Path(row['trace_file'])])
run.write(wd/'provenance.json',stamps)
commands=[
 [run.base.VIVADO/'bin/xvlog.bat','-sv','-d','ENGINE_ID=5','-d','DUT_TOP=top_guard_add_frontier_f5_e5',export/'routed.v',P/'tb_frontier_route_replay.sv'],
 [run.base.VIVADO/'bin/xvlog.bat',run.base.VIVADO/'data/verilog/src/glbl.v'],
 [run.base.VIVADO/'bin/xelab.bat','-mt','off','-debug','all','-maxdelay','-nospecify','-notimingchecks',
  '-transport_int_delays','-pulse_r','0','-pulse_int_r','0','-pulse_e','0','-pulse_int_e','0',
  '-L','simprims_ver','-L','unisims_ver','-L','secureip','tb_frontier_route_replay','glbl','-s','sim'],
 [run.base.VIVADO/'bin/xsim.bat','sim','-testplusarg',f'TRACE={row["trace_file"]}',
  '-testplusarg',f'ROWS={row["trace_count"]}','-testplusarg',f'ROI_FIRST={row["first_accept_trace_index"]}',
  '-testplusarg',f'ROI_LAST={row["last_retire_trace_index"]}','-R']]
for n,command in enumerate(commands):run.tool(command,wd,f'tool_{n}',stamps,1.2)
log=(wd/'tool_3.log').read_text()
match=re.search(r'FRONTIER_ROUTE_REPLAY PASS E(\d+) ROWS (\d+) CHECKED (\d+) VALID_ROWS (\d+)',log)
assert match and tuple(map(int,match.groups()[:3]))==(5,row['trace_count'],row['trace_count'])
run.verify(stamps)
run.write(wd/'diagnostic_checks.json',dict(status='diagnostic_functional_comparison_pass',
    rows_checked=int(match[3]),valid_rows_checked=int(match[4]),cell_paths_disabled=True,
    timing_checks_disabled=True,interconnect_transport_retained=True,
    complete_original_SDF_netlist_trace_and_assertions_retained=True,
    accepted_timing_result=False,accepted_energy=False,
    source_sha256=stamps,artifact_sha256=run.pins([wd/f'tool_{n}.log' for n in range(4)]),
    interpretation='Disabling cell paths distinguishes mapped logical/interconnect behavior from the failing cell-delay replay. It is diagnostic evidence only; it cannot validate timing or energy.'))
print('NO-CELL-PATH DIAGNOSTIC MATCHES COMPLETE F5 TRACE; NO ENERGY ACCEPTED',flush=True)
