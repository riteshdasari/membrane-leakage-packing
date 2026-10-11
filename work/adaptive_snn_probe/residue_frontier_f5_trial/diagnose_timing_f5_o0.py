"""Fresh unoptimized timing elaboration; bounded diagnostic, never energy."""
from pathlib import Path
import sys
sys.dont_write_bytecode=True
import run_frontier_f5 as run
P=Path(__file__).resolve().parent
target=P/'results/timing_diagnostic_f5_o0_a0'
assert not target.exists();target.mkdir()
export=P/'results/export_e5_a1'
run.verify(run.read(export/'artifacts.json'))
native=P/'results/native_models_0_a0/frontier_checks.json'
row=run.read(native)['rows'][5]
batch=target/'wave.tcl'
batch.write_text('''open_vcd waveform.vcd
current_scope /tb_frontier_route_replay
log_vcd [get_objects -r *]
run 9000 ns
close_vcd
puts "SHORT_O0_REPLAY_FINISHED"
quit
''')
stamps=run.frozen()|run.sources()|run.functional()|run.pins([
    Path(__file__),native,export/'artifacts.json',export/'routed.v',export/'routed.sdf',
    P/'tb_frontier_route_replay.sv',Path(row['trace_file']),batch])
run.write(target/'provenance.json',stamps)
commands=[
 [run.base.VIVADO/'bin/xvlog.bat','-sv','-d','ENGINE_ID=5','-d','DUT_TOP=top_guard_add_frontier_f5_e5',export/'routed.v',P/'tb_frontier_route_replay.sv'],
 [run.base.VIVADO/'bin/xvlog.bat',run.base.VIVADO/'data/verilog/src/glbl.v'],
 [run.base.VIVADO/'bin/xelab.bat','-mt','off','-O0','-debug','all','-maxdelay','-transport_int_delays',
  '-pulse_r','0','-pulse_int_r','0','-pulse_e','0','-pulse_int_e','0',
  '-L','simprims_ver','-L','unisims_ver','-L','secureip','tb_frontier_route_replay','glbl','-s','sim'],
 [run.base.VIVADO/'bin/xsim.bat','sim','-testplusarg',f'TRACE={row["trace_file"]}',
  '-testplusarg',f'ROWS={row["trace_count"]}','-testplusarg',f'ROI_FIRST={row["first_accept_trace_index"]}',
  '-testplusarg',f'ROI_LAST={row["last_retire_trace_index"]}','-tclbatch',batch]]
for n,command in enumerate(commands):run.tool(command,target,f'tool_{n}',stamps,1.2)
run.verify(stamps)
run.write(target/'evidence.json',dict(scope='Short unoptimized waveform diagnostic only; no energy acceptance',
 source_sha256=stamps,artifact_sha256=run.pins([target/'waveform.vcd',target/'tool_3.log'])))
print('SHORT O0 F5 DIAGNOSTIC CAPTURED',flush=True)
