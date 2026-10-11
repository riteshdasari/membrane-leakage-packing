"""Finish prepared trial without suppressing failures or changing evidence."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import sys,time,traceback
sys.dont_write_bytecode=True
import run_u13_physical as run
import audit_u13_power as audit
P=Path(__file__).resolve().parent
assert '--run' in sys.argv
progress=P/'results/completion_progress.json'
assert not progress.exists()
state=dict(status='waiting_for_native_and_serial_route_slot',routes=[],exports=[],replays=[],powers=[],failures=[])
def publish():run.write(progress,state|dict(unix_time=time.time()))
def native_ready():
    return all((P/'results'/f'native_{kind}_{stall}_a0/frontier_checks.json').exists()
               for kind in ('main','models') for stall in (0,1))
publish()
while not native_ready() or not (P.parent/'trained_reference_native_trial/static_u8_physical/hardware.json').exists():
    time.sleep(5)
run.functional();run.frozen()
stamps=run.frozen()|run.sources()|run.functional()|run.pins([Path(__file__),P/'audit_u13_power.py'])
run.write(P/'results/completion_provenance.json',stamps)
state['status']='serial_route_export';publish()
for engine in (5,2,3,4,0,1):
    try:
        run.route(engine,0);state['routes'].append(engine);publish()
        run.export(engine,0,P/'results'/f'route_e{engine}_a0');state['exports'].append(engine);publish()
    except Exception as exc:
        state['failures'].append(dict(stage='route_export',engine=engine,error=repr(exc),traceback=traceback.format_exc()))
        publish();print('U13 ROUTE/EXPORT FAILED',engine,repr(exc),flush=True)
state['status']='two_replays_serial_power';publish()
def replay(engine):
    run.replay(engine,0,P/'results'/f'route_e{engine}_a0',P/'results'/f'export_e{engine}_a0')
    return engine
with ThreadPoolExecutor(max_workers=2) as pool:
    futures={pool.submit(replay,engine):engine for engine in state['exports']}
    for future in as_completed(futures):
        engine=futures[future]
        try:
            future.result();state['replays'].append(engine);publish()
        except Exception as exc:
            state['failures'].append(dict(stage='replay',engine=engine,error=repr(exc),traceback=traceback.format_exc()))
            publish();print('U13 REPLAY FAILED',engine,repr(exc),flush=True);continue
        try:
            run.power(engine,0,P/'results'/f'route_e{engine}_a0',P/'results'/f'replay_e{engine}_a0')
            directory=P/'results'/f'power_e{engine}_a0'
            run.tool([sys.executable,'-B',P/'audit_u13_power.py','--power-dir',directory,
                      '--output',directory/'power_audit.json'],directory,'audit',stamps,.1)
            checked=run.read(directory/'power_audit.json');assert checked['status']=='pass'
            state['powers'].append(engine);publish()
        except Exception as exc:
            state['failures'].append(dict(stage='power_audit',engine=engine,error=repr(exc),traceback=traceback.format_exc()))
            publish();print('U13 POWER/AUDIT FAILED',engine,repr(exc),flush=True)
run.verify(stamps)
state['status']='all_checks_passed' if not state['failures'] else 'completed_with_retained_failures'
publish();print('U13 TRIAL FINISHED',state['status'],flush=True)
