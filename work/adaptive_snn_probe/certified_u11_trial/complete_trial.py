"""Bounded six native cohorts and five matched routes; sequential RAM gates."""
from pathlib import Path
import sys,time
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P));import run_trial as run
assert '--run'in sys.argv
target=P/'completion.json';assert not target.exists()
state=dict(status='native',completed=[],failures=[],source_sha256=run.sources())
def publish():run.write(target,state|dict(unix_time=time.time()))
publish()
for kind in('main','shift1','shift3'):
    for stall in(0,1):
        run.native(kind,stall,0);state['completed'].append(['native',kind,stall]);publish()
run.native_acceptance();state['status']='routes';publish()
for e in range(5):
    try:row=run.route(e,0)
    except Exception as exc:
        state['failures'].append(dict(engine=e,stage='route',reason=repr(exc)));publish();print('RETAINED CERTIFIED ROUTE FAILURE',e,repr(exc),flush=True)
    else:state['completed'].append(['route',e,row['status']]);publish()
if not state['failures']:run.hardware_acceptance()
state['status']='complete'if not state['failures']else'completed_with_retained_failures';publish()
print('CERTIFIED INTERVAL TRIAL CLOSED',state['status'],flush=True)
