"""Finish interrupted reporting/routes and RAM-gated power jobs in new attempts."""
from pathlib import Path
import sys,time,hashlib,json,re,traceback
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;W=P/'residue_frontier_u13_trial';A=P/'adaptive_natural_lut_trial'
sys.path.insert(0,str(W))
import run_u13_physical as run
import audit_u13_power as audit
assert '--run' in sys.argv
progress=W/'results/remaining_power_completion.json';assert not progress.exists()
state=dict(status='finishing_adaptive_LUT_route',routes=[],powers=[],failures=[],
           source_sha256=run.pins([Path(__file__)]))
def publish():run.write(progress,state|dict(unix_time=time.time()))
publish()
def wait_ram(floor):
    while run.base.free()<=floor+.05:time.sleep(5)
# The initial route wrote a valid synthesis checkpoint before Synth20-411.
# Its first resume was interrupted. Keep both and launch a separately named
# resume with exactly the same checkpoint/source identity.
wd=A/'route_a0';previous=run.read(wd/'route.job.json')
assert previous['returncode']!=0 and 'ERROR: [Synth 20-411]' in (wd/'route.log').read_text()
current=previous['source_sha256'];run.verify(current)
assert (wd/'synth/design.dcp').exists()
provenance=hashlib.sha256(json.dumps(current,sort_keys=True).encode()).hexdigest()
assert (wd/'synth/provenance.txt').read_text().strip()==provenance
run.write(wd/'continuation_provenance.json',dict(source_sha256=current|run.pins([Path(__file__),wd/'route.log',wd/'route.job.json',wd/'synth/design.dcp']),
    retained_interrupted_resume_log=str(wd/'route_resume.log'),
    scope='New named resume from unchanged verified synthesis checkpoint; originalfailed/partiallogs preserved.'))
command=[run.base.VIVADO/'bin/vivado.bat','-mode','batch','-log','vivado_resume_a1.log','-journal','vivado_resume_a1.jou',
    '-source',A/'route.tcl','-tclargs','top_adaptive_natural_lut',6,provenance,'resume',wd]
wait_ram(2.3);run.tool(command,wd,'route_resume_a1',current)
c=run.route_helpers.util(wd/'core_util.rpt',False);full=run.route_helpers.util(wd/'util.rpt')
assert c['DSP']==0 and full['FF']-c['FF']==338
slack=list(map(float,(wd/'slack.txt').read_text().splitlines()));run.verify(current)
run.write(wd/'hardware.json',dict(status='pass' if min(slack)>=0 else 'timing_failed',core=c,
    full_fixture=full,fixture_FF=338,WNS_ns=slack[0],WHS_ns=slack[1],clock_period_ns=6,
    latency_advancing_edges=1,source_sha256=current|run.pins([wd/'continuation_provenance.json']),
    artifact_sha256=run.pins(p for p in wd.iterdir() if p.is_file()),
    scope='Same membranepolicy directLUT; resource/STAonly, no acceptedoneedgeSDF/energy. Interruptedresume preserved.'))
state['routes'].append('adaptive_natural_LUT');publish()
print('ADAPTIVE NATURAL LUT ROUTE CLOSED',c,slack,flush=True)
state['status']='serial_power';publish()
# All four numerical replays are already complete; only fresh power jobs are
# needed. Earlier power directories for0/1 contain only a RAM-gated start.
for engine in (3,4,0,1):
    replay_attempt=1 if engine in (3,4) else 0
    replay_dir=W/'results'/f'replay_e{engine}_a{replay_attempt}'
    assert run.read(replay_dir/'replay_checks.json')['status']=='timing_pass_activity_pending'
    try:
        wait_ram(2.3)
        run.power(engine,1,W/'results'/f'route_e{engine}_a0',replay_dir)
        pd=W/'results'/f'power_e{engine}_a1'
        run.tool([sys.executable,'-B',W/'audit_u13_power.py','--power-dir',pd,'--output',pd/'power_audit.json'],
                 pd,'audit',run.pins([Path(__file__),W/'audit_u13_power.py']),.1)
        assert run.read(pd/'power_audit.json')['status']=='pass'
        state['powers'].append(engine);publish()
    except Exception as exc:
        state['failures'].append(dict(stage='power',engine=engine,error=repr(exc),traceback=traceback.format_exc()))
        publish();print('RETAINED POWER FAILURE',engine,repr(exc),flush=True)
# Finish the mutable RAM-retry progress ledger while preserving the interrupted
# snapshot verbatim. The separate new completion file carries all fresh jobs.
rp=W/'results/ram_retry_progress.json'
snapshot=W/'results/ram_retry_interrupted_state.json';assert not snapshot.exists()
snapshot.write_bytes(rp.read_bytes());retry=run.read(rp)
assert retry['status']=='waiting_for_serial_power_slot' and retry['replays']==[3,4]
retry['powers']=[e for e in (3,4) if e in state['powers']]
retry['failures']+=[f for f in state['failures'] if f['engine'] in (3,4)]
retry['status']='all_checks_passed' if retry['powers']==[3,4] else 'completed_with_retained_failures'
retry['source_sha256']|=run.pins([Path(__file__),snapshot])
retry['completion_continuation_file']=str(progress)
run.write(rp,retry|dict(unix_time=time.time()))
state['status']='all_checks_passed' if not state['failures'] else 'completed_with_retained_failures'
publish();print('INTERRUPTED HARDWARE QUEUE CLOSED',state['status'],flush=True)
