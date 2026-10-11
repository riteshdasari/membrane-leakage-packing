"""New attempts for RAM-gated (not numerically failed) U13 replays.

Native XSim compilation/replay uses a 1.2 GiB launch floor, supported by the
retained process samples. Vivado power remains serialized and at 2.3 GiB.
The original completion record and all failed attempt files stay unchanged.
"""
from pathlib import Path
import sys,time,traceback
sys.dont_write_bytecode=True
import run_u13_physical as run
P=Path(__file__).resolve().parent
assert '--run' in sys.argv
progress=P/'results/ram_retry_progress.json'
assert not progress.exists()
stamps=run.frozen()|run.sources()|run.functional()|run.pins([Path(__file__),P/'audit_u13_power.py'])
original_tool=run.tool
def native_tool(command,wd,label,pins,gate=2.3):
    first=Path(str(command[0])).name.lower()
    floor=1.2 if first in ('xvlog.bat','xelab.bat','xsim.bat') else gate
    while run.base.free()<=floor+.05:time.sleep(5)
    return original_tool(command,wd,label,pins,floor)
run.tool=native_tool
state=dict(status='native_replay_retries',engines=[3,4],replays=[],powers=[],failures=[],
           native_launch_floor_GiB=1.2,vivado_launch_floor_GiB=2.3,
           rationale='Prior retained E3 elaboration process-tree RSS peak0.423GiB; observed running XSim trees about0.3GiB. No timing options changed.',
           source_sha256=stamps)
def publish():run.write(progress,state|dict(unix_time=time.time()))
publish()
for engine in (3,4):
    completion=run.read(P/'results/completion_progress.json')
    failures=[x for x in completion['failures'] if x['stage']=='replay' and x['engine']==engine]
    assert len(failures)==1 and 'Insufficient free RAM' in failures[0]['error']
    assert not (P/'results'/f'replay_e{engine}_a0/replay_checks.json').exists()
    try:
        run.replay(engine,1,P/'results'/f'route_e{engine}_a0',P/'results'/f'export_e{engine}_a0')
        state['replays'].append(engine);publish()
    except Exception as exc:
        state['failures'].append(dict(stage='replay',engine=engine,error=repr(exc),traceback=traceback.format_exc()))
        publish();print('U13 RAM RETRY REPLAY FAILED',engine,repr(exc),flush=True)
state['status']='waiting_for_serial_power_slot';publish()
# The existing driver completes its serial power queue first; then the
# serialized natural-latency routes finish. Low-memory replays can overlap.
route_queue=P.parent/'adaptive_natural_lut_trial/route_a0/hardware.json'
while run.read(P/'results/completion_progress.json')['status'] not in ('all_checks_passed','completed_with_retained_failures') or not route_queue.exists():
    time.sleep(5)
state['original_completion_file']=str(P/'results/completion_progress.json')
state['source_sha256']|=run.pins([P/'results/completion_progress.json',route_queue])
state['status']='serial_power_retries';publish()
for engine in state['replays']:
    try:
        run.power(engine,1,P/'results'/f'route_e{engine}_a0',P/'results'/f'replay_e{engine}_a1')
        wd=P/'results'/f'power_e{engine}_a1'
        run.tool([sys.executable,'-B',P/'audit_u13_power.py','--power-dir',wd,
                  '--output',wd/'power_audit.json'],wd,'audit',stamps,.1)
        assert run.read(wd/'power_audit.json')['status']=='pass'
        state['powers'].append(engine);publish()
    except Exception as exc:
        state['failures'].append(dict(stage='power_audit',engine=engine,error=repr(exc),traceback=traceback.format_exc()))
        publish();print('U13 RAM RETRY POWER FAILED',engine,repr(exc),flush=True)
run.verify(state['source_sha256'])
state['status']='all_checks_passed' if not state['failures'] else 'completed_with_retained_failures'
publish();print('U13 RAM RETRY FINISHED',state['status'],flush=True)
