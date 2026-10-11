"""Wait for the active serial route job, then resolve and run checked closure."""
from pathlib import Path
import subprocess,sys,time
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parent.parent/'selective_energy_trial'))
import run_selective_energy as b
stamps=b.pins([Path(__file__),P/'resolve_routes16.py',P/'run_energy_closure_sequence_v2.py'])
out=P/'autoclose_a0.json';assert not out.exists()
state=dict(status='waiting_original_routes',source_sha256=stamps,stages=[]);b.write(out,state)
while not(P/'route_acceptance_a0.json').exists():
    b.verify(stamps);time.sleep(5)
for label,script,argv in [('resolution','resolve_routes16.py',['--attempt','a1']),('energy','run_energy_closure_sequence_v2.py',['--attempt','close_a0','--route-acceptance',str(P/'route_resolved_acceptance_a1.json')])]:
    b.verify(stamps);state['status']='running';state['current_stage']=label;b.write(out,state)
    log=P/f'autoclose_{label}_a0.log';assert not log.exists()
    with log.open('w',encoding='utf-8')as stream:
        rc=subprocess.run([sys.executable,'-B',str(P/script),*argv],cwd=P,stdout=stream,stderr=subprocess.STDOUT).returncode
    record=dict(stage=label,returncode=rc,log=str(log),log_sha256=b.sha(log));state['stages'].append(record);b.write(out,state)
    print('AUTOCLOSE',label,record,flush=True);assert rc==0,record
state['status']='completed_requires_child_gate_audit';b.write(out,state)
