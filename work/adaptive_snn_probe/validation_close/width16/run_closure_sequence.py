"""Explicitly invoked serial fixed16 closure, retained stages and source pins."""
from pathlib import Path
import argparse,json,subprocess,sys,time
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;ROOT=P.parent.parent
sys.path.insert(0,str(ROOT/'selective_energy_trial'))
import run_selective_energy as b

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--attempt',required=True);args=ap.parse_args()
    assert args.attempt.replace('_','').isalnum()
    plan=[
      ('shift128_unstalled',P/'run_native16.py',['--cohort','shift128','--stall','0','--capture','0','--attempt','native_shift128_s0_'+args.attempt]),
      ('shift128_stalled',P/'run_native16.py',['--cohort','shift128','--stall','1','--capture','0','--attempt','native_shift128_s1_'+args.attempt]),
      ('actual128',P/'run_native16.py',['--cohort','actual128','--stall','0','--capture','1','--attempt','native_actual128_s0_'+args.attempt]),
      ('actual_glif',P/'run_native16_v2.py',['--cohort','actual_glif','--stall','0','--capture','1','--attempt','native_actual_glif_s0_'+args.attempt]),
      ('routes12',P/'run_routes16.py',['--period','12','--attempt',args.attempt]),
    ]
    stamps=b.pins([Path(__file__),ROOT/'selective_energy_trial/run_selective_energy.py',b.VIVADO/'data/verilog/src/glbl.v',*(f for _,f,_ in plan)])
    progress=P/f'closure_sequence_{args.attempt}.json';assert not progress.exists()
    state=dict(status='running',B=16,steps=[],failures=[],source_sha256=stamps)
    for label,script,argv in plan:
        b.verify(stamps);state['current_stage']=label;b.write(progress,state)
        log=P/f'closure_{label}_{args.attempt}.log';assert not log.exists()
        start=time.time()
        with log.open('w',encoding='utf-8')as f:
            rc=subprocess.run([sys.executable,'-B',str(script),*argv],cwd=P,stdout=f,stderr=subprocess.STDOUT).returncode
        b.verify(stamps)
        record=dict(label=label,returncode=rc,seconds=time.time()-start,log_file=str(log),log_sha256=b.sha(log))
        state['steps'].append(record)
        print('CLOSURE STEP',label,'returncode',rc,'seconds',round(record['seconds'],1),flush=True)
        if rc:
            state['failures'].append(record);print(log.read_text(errors='replace')[-2500:],flush=True)
        b.write(progress,state)
    state['status']='completed_with_retained_failures'if state['failures']else'completed_requires_independent_stage_acceptances'
    b.write(progress,state)
if __name__=='__main__':main()
