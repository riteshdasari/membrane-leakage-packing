"""Read-only-source short waveform replay of the retained F5 valid mismatch.

This is diagnostic evidence only. Its short interval never supplies energy.
The original full replay/log/source/snapshot remain untouched.
"""
from pathlib import Path
import shutil
import sys
sys.dont_write_bytecode=True
import run_frontier_f5 as run
P=Path(__file__).resolve().parent
source=P/'results/replay_e5_a1'
target=P/'results/timing_diagnostic_f5_a0'
assert not target.exists();target.mkdir()
shutil.copytree(source/'xsim.dir',target/'xsim.dir')
for name in ('xsim.ini',):
    if (source/name).exists():shutil.copy2(source/name,target/name)
row=run.read(P/'results/native_models_0_a0/frontier_checks.json')['rows'][5]
batch=target/'wave.tcl'
batch.write_text('''open_vcd waveform.vcd
current_scope /tb_frontier_route_replay
log_vcd [get_objects -r *]
run 9000 ns
close_vcd
quit
''')
stamps=run.frozen()|run.sources()|run.functional()|run.pins([
    Path(__file__),P/'run_frontier_replay_transport_v4.py',source/'tool_2.job.json',
    P/'results/export_e5_a1/artifacts.json',Path(row['trace_file']),batch])
run.write(target/'provenance.json',stamps)
run.tool([run.base.VIVADO/'bin/xsim.bat','sim','-testplusarg',f'TRACE={row["trace_file"]}',
    '-testplusarg',f'ROWS={row["trace_count"]}','-testplusarg',f'ROI_FIRST={row["first_accept_trace_index"]}',
    '-testplusarg',f'ROI_LAST={row["last_retire_trace_index"]}','-tclbatch',batch],target,'diagnostic',stamps,1.2)
run.write(target/'evidence.json',dict(scope='Short waveform diagnostic; no energy acceptance',
    source_sha256=stamps,artifact_sha256=run.pins([target/'waveform.vcd',target/'diagnostic.log'])))
print('F5 WAVEFORM DIAGNOSTIC CAPTURED',flush=True)
