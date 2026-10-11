"""Root continuation of the bounded five-core U11 trial, serialized vendor jobs."""
from pathlib import Path
import sys,time
sys.dont_write_bytecode=True
import run_trial as run
P=Path(__file__).resolve().parent
assert '--run' in sys.argv
progress=P/'completion_progress.json';assert not progress.exists()
state=dict(status='native',native=[],routes=[],failures=[])
def publish():run.write(progress,state|dict(unix_time=time.time()))
publish()
run.prerequisites()
for kind in ('main','shift1','shift3'):
    for stall in (0,1):
        run.native(kind,stall,0);state['native'].append([kind,stall]);publish()
run.native_acceptance()
state['status']='waiting_for_serial_route_slot';publish()
slot=run.ROOT/'residue_frontier_u13_trial/results/remaining_power_completion.json'
while not slot.exists() or run.read(slot)['status'] not in ('all_checks_passed','completed_with_retained_failures'):
    time.sleep(5)
state['status']='serial_route';publish()
for engine in (0,1,2,3,4):
    run.route(engine,0);state['routes'].append(engine);publish()
run.hardware_acceptance()
state['status']='all_checks_completed';publish()
print('NATURAL U11 BOUNDED TRIAL COMPLETE',flush=True)
