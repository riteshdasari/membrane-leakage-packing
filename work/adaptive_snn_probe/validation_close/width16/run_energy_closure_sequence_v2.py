"""Serial fixed16 closure with resolved routes and independent stage gates."""
from pathlib import Path
import argparse,re,subprocess,sys,time
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;ALT=P/'lutceil_e7';ABL=P/'static9_e8';ROOT=P.parent.parent
sys.path.insert(0,str(ROOT/'selective_energy_trial'))
import run_selective_energy as b
RECEIPTS=[]

def accepted(path,status='pass'):
    d=b.read(path);assert d['status']==status,(str(path),d['status'])
    b.verify(d.get('source_sha256',{}));b.verify(d.get('artifact_sha256',{}))
    RECEIPTS.append(dict(path=str(Path(path).resolve()),sha256=b.sha(path),status=status));return d

def template(directory,engine):
    directory=Path(directory);name=re.sub(rf'e{engine}(?=_)','e{engine}',directory.name)
    assert '{engine}'in name;return str(directory.parent/name)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--attempt',required=True);ap.add_argument('--route-acceptance',required=True);args=ap.parse_args()
    assert args.attempt.replace('_','').isalnum()
    routefile=Path(args.route_acceptance).resolve();route=accepted(routefile)
    assert route['B']==16 and route['period_ns']==12 and set(route['selected_routes'])==set(map(str,range(7)))
    for e,directory in route['selected_routes'].items():
        hw=accepted(Path(directory)/'hardware.json');assert hw['engine']==int(e)and hw['B']==16 and hw['clock_period_ns']==12
    scripts=[ALT/'run_native16_lutceil_v2.py',ALT/'run_route16_lutceil.py',ABL/'run_native_static9.py',ABL/'run_route_static9.py',P/'run_energy16_12.py',ALT/'run_energy16_lutceil_12.py',P/'aggregate_hardwareclosure.py']
    stamps=b.pins([Path(__file__),routefile,ROOT/'selective_energy_trial/run_selective_energy.py',b.VIVADO/'data/verilog/src/glbl.v',*scripts])
    progress=P/f'energy_closure_sequence_{args.attempt}.json';assert not progress.exists()
    state=dict(status='running',B=16,steps=[],failures=[],source_sha256=stamps,route_acceptance=str(routefile));success={};attempt=args.attempt
    def run(label,script,argv,gate,dependencies=()):
        b.verify(stamps);state['current_stage']=label;b.write(progress,state)
        if any(not success.get(dep,False)for dep in dependencies):
            record=dict(label=label,status='skipped_failed_prerequisite',dependencies=list(dependencies));success[label]=False
            state['steps'].append(record);state['failures'].append(record);b.write(progress,state);return False
        log=P/f'energy_closure_{label}_{attempt}.log';assert not log.exists();start=time.time()
        with log.open('w',encoding='utf-8')as stream:
            rc=subprocess.run([sys.executable,'-B',str(script),*argv],cwd=P,stdout=stream,stderr=subprocess.STDOUT).returncode
        record=dict(label=label,returncode=rc,seconds=time.time()-start,log_file=str(log),log_sha256=b.sha(log))
        receipt_start=len(RECEIPTS)
        try:
            assert rc==0,('child returncode',rc);gate();b.verify(stamps)
            record['status']='accepted_stage_gate';success[label]=True
        except Exception as exc:
            record['status']='retained_stage_failure';record['reason']=repr(exc);success[label]=False;state['failures'].append(record)
            print(log.read_text(errors='replace')[-2200:],flush=True)
        record['acceptance_gates']=RECEIPTS[receipt_start:]
        state['steps'].append(record);b.write(progress,state)
        print('ENERGY CLOSURE STEP',label,record['status'],'seconds',round(record['seconds'],1),flush=True);return success[label]
    e7native={};e8native={}
    for cohort,stall,capture in [('general',0,0),('general',1,0),('actual_glif',0,1)]:
        label=f'E7_{cohort}_s{stall}';name=f'native_{cohort}_s{stall}_{attempt}';out=ALT/'hardware'/name/'acceptance.json';e7native[label]=out
        run(label,ALT/'run_native16_lutceil_v2.py',['--cohort',cohort,'--stall',str(stall),'--capture',str(capture),'--attempt',name],lambda out=out:accepted(out))
    def routed_ablation(root,engine,script,native,label,dependencies):
        directory=root/'hardware'/f'route12_e{engine}_{attempt}'
        ok=run(label,script,['--native-acceptance',str(native),'--attempt',attempt],lambda:accepted(directory/'hardware.json'),dependencies)
        if not ok and directory.exists()and(directory/'synth/design.dcp').exists()and(directory/'route.log').exists()and 'ERROR: [Synth 20-411]'in(directory/'route.log').read_text(errors='replace')and all(success.get(dep,False)for dep in dependencies):
            retry=attempt+'_checkpoint';old=directory;directory=root/'hardware'/f'route12_e{engine}_{retry}'
            ok=run(label+'_checkpoint',script,['--native-acceptance',str(native),'--attempt',retry,'--resume-synth-from',str(old)],lambda:accepted(directory/'hardware.json'),dependencies)
            success[label]=ok
        return directory,ok
    e7route,e7ok=routed_ablation(ALT,7,ALT/'run_route16_lutceil.py',e7native['E7_general_s0'],'E7_route12',('E7_general_s0','E7_general_s1'))
    for cohort in('pair','scalar'):
        for stall in(0,1):
            label=f'E8_{cohort}_s{stall}';name=f'native_{cohort}_s{stall}_{attempt}';out=ABL/'hardware'/name/'acceptance.json';e8native[label]=out
            run(label,ABL/'run_native_static9.py',['--cohort',cohort,'--stall',str(stall),'--capture','0','--attempt',name],lambda out=out:accepted(out))
    e8route,e8ok=routed_ablation(ABL,8,ABL/'run_route_static9.py',e8native['E8_pair_s0'],'E8_route12',tuple(e8native))
    def energy(workload,engine,root,script,native,directory,dependencies=()):
        tag=f'{attempt}_e{engine}';label=f'{workload.upper()}_energy_e{engine}'
        prog=root/f'energy12_{workload}_{tag}_golden_export_replay_power_progress.json'
        auditfile=root/'hardware'/f'power12_{workload}_e{engine}_{tag}'/'power_audit.json'
        def gate():
            d=accepted(prog);assert not d['failures']and d['engines']==[engine]
            a=accepted(auditfile);assert a['engine']==engine and a['clock_period_ns']==12 and a['fixture_FF']==94 and a['physical_activity_unknown_records']==0
        return run(label,script,['--workload',workload,'--native-acceptance',str(native),'--route-dir-template',template(directory,engine),'--engines',str(engine),'--attempt',tag],gate,dependencies)
    for e in(5,1,2,0,3,4):
        energy('glif',e,P,P/'run_energy16_12.py',P/'hardware/native_actual_glif_s0_a0/acceptance.json',route['selected_routes'][str(e)])
    energy('glif',7,ALT,ALT/'run_energy16_lutceil_12.py',e7native['E7_actual_glif_s0'],e7route,('E7_actual_glif_s0','E7_route12'))
    for e in(5,1,2,6,0,3,4):
        energy('ottt',e,P,P/'run_energy16_12.py',P/'hardware/native_actual128_s0_a0/acceptance.json',route['selected_routes'][str(e)])
    aggregatefile=P/f'hardwareclosure_measured_{attempt}.json'
    run('aggregate',P/'aggregate_hardwareclosure.py',['--label','measured_'+attempt,'--strict-complete'],lambda:accepted(aggregatefile,'pass_complete_fixed16_hardware_closure'))
    state['status']='completed_with_retained_failures'if state['failures']else'pass';state['E8_complete']=e8ok and all(success.get(k,False)for k in e8native)
    state['E8_native_acceptance']={k:str(v)for k,v in e8native.items()};state['E8_hardware_file']=str(e8route/'hardware.json')
    state['artifact_sha256']=b.pins([Path(item['log_file'])for item in state['steps']if 'log_file'in item]);b.write(progress,state)
if __name__=='__main__':main()
