"""Serial E7 validation and strict main fixed16 energy closure, retained attempts."""
from pathlib import Path
import argparse,subprocess,sys,time
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;ALT=P/'lutceil_e7';ABL=P/'static9_e8';ROOT=P.parent.parent
sys.path.insert(0,str(ROOT/'selective_energy_trial'))
import run_selective_energy as b

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--attempt',required=True);args=ap.parse_args()
    assert args.attempt.replace('_','').isalnum()
    route= b.read(P/'route_acceptance_a0.json')
    assert route['status']=='pass','Resolve retained route failures before this pipeline.'
    b.verify(route['source_sha256']);b.verify(route['artifact_sha256'])
    route_template=str(P/'hardware'/'route12_e{engine}_a0')
    plan=[
      ('E7_general_s0',ALT/'run_native16_lutceil_v2.py',['--cohort','general','--stall','0','--capture','0','--attempt','native_general_s0_'+args.attempt]),
      ('E7_general_s1',ALT/'run_native16_lutceil_v2.py',['--cohort','general','--stall','1','--capture','0','--attempt','native_general_s1_'+args.attempt]),
      ('E7_actual_glif',ALT/'run_native16_lutceil_v2.py',['--cohort','actual_glif','--stall','0','--capture','1','--attempt','native_actual_glif_s0_'+args.attempt]),
      ('E7_route12',ALT/'run_route16_lutceil.py',['--native-acceptance',str(ALT/'hardware'/('native_general_s0_'+args.attempt)/'acceptance.json'),'--attempt',args.attempt]),
      ('E8_pair_s0',ABL/'run_native_static9.py',['--cohort','pair','--stall','0','--capture','0','--attempt','native_pair_s0_'+args.attempt]),
      ('E8_pair_s1',ABL/'run_native_static9.py',['--cohort','pair','--stall','1','--capture','0','--attempt','native_pair_s1_'+args.attempt]),
      ('E8_scalar_s0',ABL/'run_native_static9.py',['--cohort','scalar','--stall','0','--capture','0','--attempt','native_scalar_s0_'+args.attempt]),
      ('E8_scalar_s1',ABL/'run_native_static9.py',['--cohort','scalar','--stall','1','--capture','0','--attempt','native_scalar_s1_'+args.attempt]),
      ('E8_route12',ABL/'run_route_static9.py',['--native-acceptance',str(ABL/'hardware'/('native_pair_s0_'+args.attempt)/'acceptance.json'),'--attempt',args.attempt]),
      ('GLIF_main_energy',P/'run_energy16_12.py',['--workload','glif','--native-acceptance',str(P/'hardware/native_actual_glif_s0_a0/acceptance.json'),'--route-dir-template',route_template,'--engines','5,1,2,0,3,4','--attempt',args.attempt]),
      ('GLIF_E7_energy',ALT/'run_energy16_lutceil_12.py',['--workload','glif','--native-acceptance',str(ALT/'hardware'/('native_actual_glif_s0_'+args.attempt)/'acceptance.json'),'--route-dir-template',str(ALT/'hardware'/('route12_e{engine}_'+args.attempt)),'--engines','7','--attempt',args.attempt]),
      ('OTTT_stress_energy',P/'run_energy16_12.py',['--workload','ottt','--native-acceptance',str(P/'hardware/native_actual128_s0_a0/acceptance.json'),'--route-dir-template',route_template,'--engines','5,1,2,6,0,3,4','--attempt',args.attempt]),
      ('aggregate',P/'aggregate_hardwareclosure.py',['--label','measured_'+args.attempt]),
    ]
    stamps=b.pins([Path(__file__),ROOT/'selective_energy_trial/run_selective_energy.py',b.VIVADO/'data/verilog/src/glbl.v',*(f for _,f,_ in plan)])
    progress=P/f'energy_closure_sequence_{args.attempt}.json';assert not progress.exists()
    state=dict(status='running',B=16,steps=[],failures=[],source_sha256=stamps)
    for label,script,argv in plan:
        b.verify(stamps);state['current_stage']=label;b.write(progress,state)
        log=P/f'energy_closure_{label}_{args.attempt}.log';assert not log.exists()
        start=time.time()
        with log.open('w',encoding='utf-8')as stream:
            rc=subprocess.run([sys.executable,'-B',str(script),*argv],cwd=P,stdout=stream,stderr=subprocess.STDOUT).returncode
        b.verify(stamps)
        record=dict(label=label,returncode=rc,seconds=time.time()-start,log_file=str(log),log_sha256=b.sha(log))
        state['steps'].append(record)
        print('ENERGY CLOSURE STEP',label,'returncode',rc,'seconds',round(record['seconds'],1),flush=True)
        if rc:
            state['failures'].append(record);print(log.read_text(errors='replace')[-2500:],flush=True)
        b.write(progress,state)
    state['status']='completed_with_retained_failures'if state['failures']else'completed_requires_independent_stage_acceptances'
    b.write(progress,state)
if __name__=='__main__':main()
