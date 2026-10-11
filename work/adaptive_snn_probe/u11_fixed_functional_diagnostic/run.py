"""Mapped functional diagnosis only; cannot waive the retained timed failure."""
from pathlib import Path
import re,sys,time
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;ROOT=P.parent
sys.path.insert(0,str(ROOT/'natural_energy_trial'));import run_energy as energy
assert '--run'in sys.argv
completed=ROOT/'certified_u11_trial/completion.json'
while energy.read(completed)['status'] not in('complete','completed_with_retained_failures'):time.sleep(5)
assert not(P/'results').exists();wd=P/'results';wd.mkdir()
route,hw=energy.route_data(1)
tracecheck=energy.R/'native_trace_a0/trace_checks.json';row=energy.read(tracecheck)['rows'][1]
trace=Path(row['trace_file']);assert energy.sha(trace)==row['trace_sha256']
timed=energy.R/'replay_e1_a0/tool_3.log';text=timed.read_text()
assert 'REPLAY data mismatch'in text and 'FRONTIER_ROUTE_REPLAY PASS E1'not in text
batch=wd/'replay.tcl';batch.write_text(f'run {6*(row["trace_count"]+5)+200} ns\nquit\n')
stamps=energy.sources()|energy.functional()|energy.pins([Path(__file__),P/'export.tcl',batch,
    ROOT/'natural_energy_trial/tb_replay.sv',route/'design.dcp',route/'hardware.json',trace,tracecheck,timed])
energy.write(wd/'provenance.json',stamps)
energy.tool([energy.base.VIVADO/'bin/vivado.bat','-mode','batch','-log','vivado.log','-journal','vivado.jou',
    '-source',P/'export.tcl','-tclargs',route/'design.dcp',wd],wd,'export',stamps)
net=wd/'mapped_functional.v';assert '$sdf_annotate'not in net.read_text()
stamps|=energy.pins([net]);energy.write(wd/'replay_provenance.json',stamps)
commands=[
 [energy.base.VIVADO/'bin/xvlog.bat','-sv','-d','ENGINE_ID=1','-d',f'DUT_TOP={hw["top"]}',net,ROOT/'natural_energy_trial/tb_replay.sv'],
 [energy.base.VIVADO/'bin/xvlog.bat',energy.base.VIVADO/'data/verilog/src/glbl.v'],
 [energy.base.VIVADO/'bin/xelab.bat','-mt','off','-debug','typical','-L','unisims_ver','tb_natural_energy_replay','glbl','-s','sim'],
 [energy.base.VIVADO/'bin/xsim.bat','sim','-testplusarg',f'TRACE={trace}','-testplusarg',f'ROWS={row["trace_count"]}',
  '-testplusarg',f'ROI_FIRST={row["first_accept_trace_index"]}','-testplusarg',f'ROI_LAST={row["last_retire_trace_index"]}','-tclbatch',batch]]
logs=[energy.tool(c,wd,f'tool_{n}',stamps,1.2)for n,c in enumerate(commands)]
log=logs[-1].read_text();m=re.search(r'FRONTIER_ROUTE_REPLAY PASS E(\d+) ROWS (\d+) CHECKED (\d+) VALID_ROWS (\d+) TIME_NS ([\d.]+)',log)
passed=bool(m)and tuple(map(int,m.groups()[:3]))==(1,row['trace_count'],row['trace_count'])and 'Fatal:'not in log
energy.verify(stamps)
energy.write(P/'acceptance.json',dict(status='mapped_functional_pass'if passed else'mapped_functional_failure',
    engine=1,rows_checked=int(m[3])if m else0,valid_rows_checked=int(m[4])if m else0,
    accepted_timing_result=False,accepted_energy=False,
    unchanged_timed_failure_log=str(timed),unchanged_timed_failure_sha256=energy.sha(timed),
    source_sha256=stamps,artifact_sha256=energy.pins(logs+[net]),
    scope='Official mapped functional netlist comparison of the entire unchanged trace, including known invalid data. Localizes disagreement to timed versus functional simulation if successful; no source of vendor/model discrepancy established and no timing/energy gate waived.'))
print('U11 FIXED MAPPED FUNCTIONAL DIAGNOSTIC',passed,flush=True)
