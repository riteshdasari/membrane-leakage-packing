"""Bound the official funcsim run after its complete trace; no timing/energy."""
from pathlib import Path
import sys,time,re
sys.dont_write_bytecode=True
import run_frontier_f5 as run
P=Path(__file__).resolve().parent;wd=P/'results/diagnostic_routed_functional_a0'
assert '--run' in sys.argv and not (wd/'diagnostic_checks.json').exists()
stamps=run.read(wd/'functional_provenance.json');run.verify(stamps)
for k in range(3):assert run.read(wd/f'tool_{k}.job.json')['returncode']==0
old=wd/'tool_3.log';assert 'FRONTIER_ROUTE_REPLAY PASS' in old.read_text()
assert not (wd/'tool_3.job.json').exists()
native=P/'results/native_models_0_a0/frontier_checks.json';row=run.read(native)['rows'][5]
batch=wd/'functional_bounded_a1.tcl';assert not batch.exists()
duration_ps=(126+6*(row['trace_count']+3))*1000
batch.write_text(f'run {duration_ps} ps\nputs "BOUNDED_FUNCTIONAL_REPLAY_CLOSED"\nquit\n')
stamps|=run.pins([Path(__file__),batch,old])
run.write(wd/'continuation_provenance.json',dict(source_sha256=stamps,
    retained_interrupted_run=True,cause='Original -R run printed full PASS but the SAIF-oriented testbench intentionally has nofinish and keeps a free-runningclock. New Tcl quits after allsameassertions. No assertionorRTL change.',
    accepted_timing_result=False,accepted_energy=False))
while run.base.free()<=1.25:time.sleep(5)
run.tool([run.base.VIVADO/'bin/xsim.bat','sim','-testplusarg',f'TRACE={row["trace_file"]}',
          '-testplusarg',f'ROWS={row["trace_count"]}','-testplusarg',f'ROI_FIRST={row["first_accept_trace_index"]}',
          '-testplusarg',f'ROI_LAST={row["last_retire_trace_index"]}','-tclbatch',batch],wd,'tool_3_a1',stamps,1.2)
log=(wd/'tool_3_a1.log').read_text()
match=re.search(r'FRONTIER_ROUTE_REPLAY PASS E(\d+) ROWS (\d+) CHECKED (\d+) VALID_ROWS (\d+)',log)
assert match and tuple(map(int,match.groups()[:3]))==(5,row['trace_count'],row['trace_count'])
assert 'BOUNDED_FUNCTIONAL_REPLAY_CLOSED' in log and not re.search(r'Fatal:|Error:',log)
run.verify(stamps)
run.write(wd/'diagnostic_checks.json',dict(status='official_routed_functional_export_matches_full_trace',
    rows_checked=int(match[3]),valid_rows_checked=int(match[4]),
    same_routed_checkpoint_trace_TB_clock_and_assertions=True,accepted_timing_result=False,accepted_energy=False,
    source_sha256=stamps|run.pins([wd/'continuation_provenance.json']),
    artifact_sha256=run.pins([wd/'routed_functional.v',wd/'export.log',wd/'tool_3_a1.log',wd/'tool_3_a1.job.json',*[wd/f'tool_{n}.log' for n in range(3)]]),
    scope='Official mappedfuncsimonly; boundedTcl after completetrace; noSDF/SAIF/poweracceptance, originaltimed failuresretained.'))
print('BOUNDED OFFICIAL FUNCSIM DIAGNOSTIC PASS',flush=True)
