"""Official funcsim export of the same routed checkpoint, diagnostic only.

Wait for the current serialized physical queue to finish. This deliberately
produces no timing/SAIF/power acceptance and never replaces the failed SDF run.
"""
from pathlib import Path
import sys,time,re
sys.dont_write_bytecode=True
import run_frontier_f5 as run
P=Path(__file__).resolve().parent
assert '--run' in sys.argv
progress=P.parent/'residue_frontier_u13_trial/results/completion_progress.json'
while run.read(progress)['status'] not in ('all_checks_passed','completed_with_retained_failures'):time.sleep(5)
wd=P/'results/diagnostic_routed_functional_a0';assert not wd.exists();wd.mkdir()
native=P/'results/native_models_0_a0/frontier_checks.json';row=run.read(native)['rows'][5]
checkpoint=P/'results/route_e5_a0/design.dcp'
script=wd/'export_funcsim.tcl'
script.write_text('''set_param general.maxThreads 1
open_checkpoint [lindex $argv 0]
write_verilog -mode funcsim -force [lindex $argv 1]
puts "ROUTED_FUNCSIM_EXPORTED"
''')
stamps=run.frozen()|run.sources()|run.functional()|run.pins([Path(__file__),script,native,
    checkpoint,P/'results/route_e5_a0/hardware.json',P/'tb_frontier_route_replay.sv',Path(row['trace_file'])])
run.write(wd/'provenance.json',stamps)
while run.base.free()<=2.3:time.sleep(5)
run.tool([run.base.VIVADO/'bin/vivado.bat','-mode','batch','-log','vivado.log','-journal','vivado.jou',
          '-source',script,'-tclargs',checkpoint,wd/'routed_functional.v'],wd,'export',stamps)
text=(wd/'routed_functional.v').read_text();assert '$sdf_annotate' not in text
stamps|=run.pins([wd/'routed_functional.v'])
run.write(wd/'functional_provenance.json',stamps)
commands=[
 [run.base.VIVADO/'bin/xvlog.bat','-sv','-d','ENGINE_ID=5','-d','DUT_TOP=top_guard_add_frontier_f5_e5',wd/'routed_functional.v',P/'tb_frontier_route_replay.sv'],
 [run.base.VIVADO/'bin/xvlog.bat',run.base.VIVADO/'data/verilog/src/glbl.v'],
 [run.base.VIVADO/'bin/xelab.bat','-mt','off','-debug','typical','-L','unisims_ver','-L','secureip',
  'tb_frontier_route_replay','glbl','-s','sim'],
 [run.base.VIVADO/'bin/xsim.bat','sim','-testplusarg',f'TRACE={row["trace_file"]}',
  '-testplusarg',f'ROWS={row["trace_count"]}','-testplusarg',f'ROI_FIRST={row["first_accept_trace_index"]}',
  '-testplusarg',f'ROI_LAST={row["last_retire_trace_index"]}','-R']]
for n,command in enumerate(commands):
    while run.base.free()<=1.2:time.sleep(5)
    run.tool(command,wd,f'tool_{n}',stamps,1.2)
log=(wd/'tool_3.log').read_text()
match=re.search(r'FRONTIER_ROUTE_REPLAY PASS E(\d+) ROWS (\d+) CHECKED (\d+) VALID_ROWS (\d+)',log)
assert match and tuple(map(int,match.groups()[:3]))==(5,row['trace_count'],row['trace_count'])
run.verify(stamps)
run.write(wd/'diagnostic_checks.json',dict(status='official_routed_functional_export_matches_full_trace',
    rows_checked=int(match[3]),valid_rows_checked=int(match[4]),
    same_routed_checkpoint_trace_TB_clock_and_assertions=True,
    accepted_timing_result=False,accepted_energy=False,source_sha256=stamps,
    artifact_sha256=run.pins([wd/'routed_functional.v',wd/'export.log',*[wd/f'tool_{n}.log' for n in range(4)]]),
    scope='Mapped functional comparison only, official funcsim netlist. No SDF/SAIF. Preserved SDF failure and strict timing/power acceptance requirements remain unchanged.'))
print('OFFICIAL ROUTED FUNCTIONAL DIAGNOSTIC PASS; TIMING/ENERGY STILL UNACCEPTED',flush=True)
