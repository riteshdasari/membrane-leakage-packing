"""Recover only completed full replays after the adapter's helper-import error."""
from pathlib import Path
import re
import sys
import time

sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P))
import run_energy as run
sys.path.insert(0,str(P.parent/'selective_energy_trial'))
import replay_selective_energy as correct_helpers

assert '--run'in sys.argv
progress=P/'completion_progress.json'
while run.read(progress)['status'] not in ('all_energy_audits_passed','completed_with_retained_failures'):
    time.sleep(5)
initial=run.read(progress);run.verify(initial['source_sha256'])
assert not(P/'repair_completion.json').exists()
extra=run.pins([Path(__file__),Path(correct_helpers.__file__),progress])
original_sources=run.sources
run.sources=lambda:original_sources()|extra
state=dict(status='recovering_completed_replays',accepted=[],failures=[],
    initial_completion_sha256=run.sha(progress),source_sha256=run.sources(),
    repair_scope='Correct helper module for timing diagnostics and SAIF statistics only. Existing native, RTL, checkpoint, exported SDF, simulator commands, trace and SAIF bytes remain unchanged.')
def publish():run.write(P/'repair_completion.json',state|dict(unix_time=time.time()))
publish()

for e in range(5):
    wd=run.R/f'replay_e{e}_a0';logfile=wd/'tool_3.log'
    assert logfile.exists(),('No completed simulator result',e)
    run.verify(run.read(wd/'provenance.json'))
    text=logfile.read_text()
    fatal=re.search(r'Fatal: ([^\n]+)',text)
    match=re.search(r'FRONTIER_ROUTE_REPLAY PASS E(\d+) ROWS (\d+) CHECKED (\d+) VALID_ROWS (\d+) TIME_NS ([\d.]+)',text)
    if fatal or not match:
        state['failures'].append(dict(engine=e,stage='timed_replay',reason=fatal[1]if fatal else'No complete full-trace PASS marker',
            log_file=str(logfile),log_sha256=run.sha(logfile),accepted_energy=False));publish()
        print('U11 RETAINED TIMED FAILURE',e,state['failures'][-1]['reason'],flush=True);continue
    original_failure,=[r for r in initial['failures']if r['engine']==e]
    assert original_failure['stage']=='replay'and 'has no attribute'in original_failure['reason']
    assert not(wd/'replay_checks.json').exists()
    route,hw=run.route_data(e);exportdir=run.R/f'export_e{e}_a0'
    run.verify(run.read(exportdir/'artifacts.json'))
    checkfile=run.R/'native_trace_a0/trace_checks.json';data=run.read(checkfile);row=data['rows'][e]
    assert tuple(map(int,match.groups()[:3]))==(e,row['trace_count'],row['trace_count'])
    first,last=row['first_accept_trace_index'],row['last_retire_trace_index']
    start=126000+first*6000-1;duration=(last-first+3)*6000;end=start+duration
    assert f'FRONTIER_SAIF_CLOSED START_PS {start} END_PS {end} DURATION_PS {duration}'in text
    logs=[wd/f'tool_{n}.log'for n in range(4)]
    for n in range(4):assert run.read(wd/f'tool_{n}.job.json')['returncode']==0
    diagnostics=correct_helpers.timing_warnings(logs+list(wd.glob('*.log')))
    assert not diagnostics,diagnostics
    stats=correct_helpers.saif_stats(wd/'activity.saif',duration)
    stamps=run.read(wd/'provenance.json')|extra
    record=dict(status='timing_pass_activity_pending',engine=e,design_top=hw['top'],native_row=row,
        trace_columns=run.COLS,native_check_file=str(checkfile),native_check_sha256=run.sha(checkfile),
        requests=row['requests'],neurons=635904,clock_period_ns=6,first_replay_drive_time_ns=126,
        output_trace_row_offset=2,roi_start_ps=start,roi_end_ps=end,roi_duration_ps=duration,
        roi_extra_fixture_cycles=2,clock_startup_delay_ns=6,
        timing_simulation_method='AMD transport, zero pulse error and rejection, slow/max',
        saif=stats,timing_diagnostics=diagnostics,replay_rows_checked=int(match[3]),valid_rows_checked=int(match[4]),
        functional_check_sha256=run.functional(),source_sha256=stamps,
        artifact_sha256=run.pins([wd/'activity.saif',wd/'activity.tcl',*logs]),
        postprocessing_repair=dict(original_failure=original_failure,repair_source_sha256=extra,
            note='No simulation rerun or weakened gate; completed original simulator artifacts independently checked.'))
    run.write(wd/'replay_checks.json',record)
    norm=run.ROOT/'selective_energy_trial/normalize_saif_names.py'
    run.tool([sys.executable,'-B',norm,wd/'activity.saif',wd/'activity_named.saif'],wd,'normalize',stamps|run.pins([norm]),.1)
    state['status']=f'power_e{e}';publish()
    try:run.power(e)
    except Exception as exc:
        state['failures'].append(dict(engine=e,stage='power_or_audit',reason=repr(exc),accepted_energy=False));publish()
        print('U11 RETAINED POWER/AUDIT FAILURE',e,repr(exc),flush=True)
    else:
        state['accepted'].append(e);publish()
state['status']='all_energy_audits_passed'if not state['failures']else'completed_with_retained_failures'
publish();print('U11 ENERGY POSTPROCESSING REPAIR CLOSED',state['status'],state['accepted'],flush=True)
