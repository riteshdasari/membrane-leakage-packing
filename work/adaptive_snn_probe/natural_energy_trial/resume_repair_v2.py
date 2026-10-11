"""Continue strict audits from unchanged complete simulations in a new attempt."""
from pathlib import Path
import importlib.util
import re
import sys
import time
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P))
import run_energy as run
sys.path.insert(0,str(P.parent/'selective_energy_trial'))
import replay_selective_energy as helper
assert '--run'in sys.argv
initial=run.read(P/'completion_progress.json');run.verify(initial['source_sha256'])
extra=run.pins([Path(__file__),Path(helper.__file__),P/'completion_progress.json',
    P/'repair_completion.json',P/'repair_completed_replay_postprocessing.py',P/'prepare_repair_v2.py',
    P/'repair_v2_preparation.json',P/'audit_power_v2.py'])
original_sources=run.sources;run.sources=lambda:original_sources()|extra
spec=importlib.util.spec_from_file_location('strict_energy_v2',P/'audit_power_v2.py')
auditor=importlib.util.module_from_spec(spec);spec.loader.exec_module(auditor)
state=dict(status='recovering_complete_replays',accepted=[],failures=[],source_sha256=run.sources(),
    retained_prior_attempt_sha256=run.sha(P/'repair_completion.json'),
    no_timing_gate_waiver=True,source_restoration=run.read(P/'repair_v2_preparation.json')['source_restoration'])
output=P/'repair_v2_completion.json';assert not output.exists()
def publish():run.write(output,state|dict(unix_time=time.time()))
publish()
for e in range(5):
    wd=run.R/f'replay_e{e}_a0';logfile=wd/'tool_3.log';text=logfile.read_text()
    run.verify(run.read(wd/'provenance.json'))
    fatal=re.search(r'Fatal: ([^\n]+)',text)
    match=re.search(r'FRONTIER_ROUTE_REPLAY PASS E(\d+) ROWS (\d+) CHECKED (\d+) VALID_ROWS (\d+) TIME_NS ([\d.]+)',text)
    if fatal or not match:
        state['failures'].append(dict(engine=e,stage='timed_replay',reason=fatal[1]if fatal else'No complete full-trace PASS',log_file=str(logfile),log_sha256=run.sha(logfile),accepted_energy=False))
        publish();print('RETAINED TIMED FAILURE',e,flush=True);continue
    checkfile=run.R/'native_trace_a0/trace_checks.json';row=run.read(checkfile)['rows'][e]
    assert tuple(map(int,match.groups()[:3]))==(e,row['trace_count'],row['trace_count'])
    first,last=row['first_accept_trace_index'],row['last_retire_trace_index']
    start=126000+first*6000-1;duration=(last-first+3)*6000;end=start+duration
    assert f'FRONTIER_SAIF_CLOSED START_PS {start} END_PS {end} DURATION_PS {duration}'in text
    logs=[wd/f'tool_{n}.log'for n in range(4)]
    assert all(run.read(wd/f'tool_{n}.job.json')['returncode']==0 for n in range(4))
    diagnostics=helper.timing_warnings(logs+list(wd.glob('*.log')));assert not diagnostics,diagnostics
    stats=helper.saif_stats(wd/'activity.saif',duration)
    stamps=run.read(wd/'provenance.json')|extra
    replaycheck=wd/'replay_checks.json'
    if not replaycheck.exists():
        original_failure,=[r for r in initial['failures']if r['engine']==e]
        assert original_failure['stage']=='replay'and 'has no attribute'in original_failure['reason']
        route,hw=run.route_data(e)
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
                note='Completed original simulator bytes independently verified; no timing/functional gate weakened.'))
        run.write(replaycheck,record)
    else:
        record=run.read(replaycheck);run.verify(record['source_sha256']);run.verify(record['artifact_sha256'])
        assert record['replay_rows_checked']==row['trace_count']and record['roi_duration_ps']==duration
    named=wd/'activity_named.saif';norm=run.ROOT/'selective_energy_trial/normalize_saif_names.py'
    if not named.exists():run.tool([sys.executable,'-B',norm,wd/'activity.saif',named],wd,'normalize',stamps|run.pins([norm]),.1)
    names=run.read(named.with_suffix('.names.json'))
    assert names['target_sha256']==run.sha(named)and names['source_sha256']==record['saif']['saif_sha256']
    state['status']=f'power_e{e}';publish()
    try:
        oldpower=run.R/f'power_e{e}_a0'
        if e==0:
            # Vendor reports completed before the transient source hash failed.
            assert oldpower.exists()and run.read(oldpower/'annotation.job.json')['returncode']==0
            powerdir=oldpower
        else:
            route,hw=run.route_data(e);powerdir=run.directory(f'power_v2_e{e}')
            stamps=run.sources()|run.functional()|run.pins([named,named.with_suffix('.names.json'),
                replaycheck,route/'hardware.json',route/'design.dcp'])
            run.write(powerdir/'provenance.json',stamps)
            run.tool([run.base.VIVADO/'bin/vivado.bat','-mode','batch','-log','vivado.log','-journal','vivado.jou',
                '-source',P/'power.tcl','-tclargs',e,route/'design.dcp',named,powerdir],powerdir,'annotation',stamps)
            run.write(powerdir/'evidence.json',dict(status='reports generated; independent audit required',engine=e,
                design_top=hw['top'],replay_dir=str(wd),hardware_file=str(route/'hardware.json'),saif_file=str(named),
                source_sha256=stamps,artifact_sha256=run.pins(p for p in powerdir.iterdir()if p.is_file()),
                duration_seconds=record['saif']['duration_seconds'],neurons=635904))
        checked=auditor.annotation(powerdir)
        assert checked['fixture_FF']==290
        target=powerdir/'power_audit_v2.json';assert not target.exists();run.write(target,checked)
        state['accepted'].append(dict(engine=e,audit_file=str(target),audit_sha256=run.sha(target)))
        print('STRICT U11 ENERGY ACCEPTED',e,checked['estimated_dynamic_energy_pJ_per_scalar_update'],flush=True)
    except Exception as exc:
        state['failures'].append(dict(engine=e,stage='power_or_audit',reason=repr(exc),accepted_energy=False))
        print('RETAINED AUDIT FAILURE',e,repr(exc),flush=True)
    publish()
state['status']='all_energy_audits_passed'if not state['failures']else'completed_with_retained_failures'
publish();print('ENERGY RECOVERY V2 CLOSED',state['status'],[r['engine']for r in state['accepted']],flush=True)
