"""New U11 attempt after a pre-launch RAM gate, preserving the first attempt."""
from pathlib import Path
import sys,time
sys.dont_write_bytecode=True
import run_trial as run
P=Path(__file__).resolve().parent
assert '--run' in sys.argv
previous=P/'results/native_main_stall0_a0'
run.verify(run.read(previous/'provenance.json'))
assert not (previous/'tool_0.job.json').exists() and not (previous/'native_checks.json').exists()
record=P/'ram_gate_continuation.json';assert not record.exists()
run.write(record,dict(source_sha256=run.pins([Path(__file__),previous/'provenance.json',P/'completion_progress.json']),
    retained_failed_attempt=str(previous),failure='Before xvlog launch, free RAM moved to1.18993GiB below1.2GiB gate. No vendor jobexecuted.',
    policy='Wait withmargin and retryonly prelaunch memoryassertions; arithmetic/protocol/toolfailures propagate.'))
original_job=run.job
def safe_job(command,wd,label,stamps,gate):
    while True:
        while run.base.free()<=gate+.15:time.sleep(5)
        try:return original_job(command,wd,label,stamps,gate)
        except AssertionError as exc:
            if 'Insufficient free RAM' not in str(exc):raise
            assert not (wd/f'{label}.job.json').exists()
            time.sleep(5)
run.job=safe_job
progress=P/'completion_resume_progress.json';assert not progress.exists()
state=dict(status='native',native=[],routes=[],source_sha256=run.pins([record,Path(__file__)]))
def publish():run.write(progress,state|dict(unix_time=time.time()))
publish()
for kind in ('main','shift1','shift3'):
    for stall in (0,1):
        attempt=1 if kind=='main' and stall==0 else 0
        run.native(kind,stall,attempt);state['native'].append([kind,stall,attempt]);publish()
run.native_acceptance()
state['status']='waiting_for_serial_route_slot';publish()
slot=run.ROOT/'residue_frontier_u13_trial/results/remaining_power_completion.json'
while not slot.exists() or run.read(slot)['status'] not in ('all_checks_passed','completed_with_retained_failures'):time.sleep(5)
state['status']='serial_route';publish()
for engine in (0,1,2,3,4):
    run.route(engine,0);state['routes'].append(engine);publish()
run.hardware_acceptance();state['status']='all_checks_completed';publish()
print('NATURAL U11 BOUNDED TRIAL COMPLETE',flush=True)
