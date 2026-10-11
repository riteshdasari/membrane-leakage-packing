"""Energy-only serial closure using explicit accepted routes and fresh attempts.

No native simulation, inference, synthesis, optimization or routing occurs here.
Existing energy may be reused only by an explicit passing child progress receipt,
followed by independent reproduction of its complete certified power audit.
"""
from pathlib import Path
import argparse, importlib.util, re, subprocess, sys, time
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;ALT=P/'lutceil_e7';ROOT=P.parent.parent
sys.path.insert(0,str(ROOT/'selective_energy_trial'))
import run_selective_energy as b


def checked(path,status='pass'):
    path=Path(path).resolve();d=b.read(path)
    assert d['status']==status,(str(path),d['status'])
    b.verify(d.get('source_sha256',{}));b.verify(d.get('artifact_sha256',{}))
    return d


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def route_template(directory,e):
    directory=Path(directory).resolve()
    name=re.sub(rf'e{e}(?=_)','e{engine}',directory.name)
    assert '{engine}' in name
    return str(directory.parent/name)


def accepted_child(path,selected,workload,e):
    path=Path(path).resolve();progress=checked(path)
    assert (progress['B'],progress['workload'],progress['clock_ns'],progress['engines'])==(16,workload,12,[e])
    assert progress['stages']==[[stage,e] for stage in ('golden','export','replay','power')] and not progress['failures']
    auditfile=Path(progress['accepted_power_audit_file']).resolve()
    assert progress['accepted_power_audit_sha256']==b.sha(auditfile)
    audit=checked(auditfile)
    assert audit['engine']==e and audit['clock_period_ns']==12 and audit['fixture_FF']==94 and audit['physical_activity_unknown_records']==0
    route=selected[e]/'hardware.json'
    assert Path(audit['routed_hardware_file']).resolve()==route and audit['routed_hardware_sha256']==b.sha(route)
    auditorfile=(ALT/'audit_power16_lutceil_12_certified.py' if e==7 else P/'audit_power16_12_certified.py')
    assert audit['auditor_sha256']==b.sha(auditorfile)
    actual=load(auditorfile,'recovery_sequence_independent_auditor_'+str(e)).annotation(auditfile.parent)
    assert actual==audit,'Explicit child power audit does not reproduce independently.'
    return [dict(path=str(path),sha256=b.sha(path),status='pass'),dict(path=str(auditfile),sha256=b.sha(auditfile),status='pass')]


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--route-acceptance',required=True)
    ap.add_argument('--e7-hardware',required=True)
    ap.add_argument('--e7-native-acceptance',required=True)
    ap.add_argument('--attempt',required=True)
    ap.add_argument('--reuse-child-progress',action='append',default=[])
    ap.add_argument('--reuse-e5-golden-dir')
    ap.add_argument('--reuse-e5-export-dir')
    ap.add_argument('--run',action='store_true')
    args=ap.parse_args();assert re.fullmatch(r'[a-zA-Z0-9_-]+',args.attempt)
    routefile=Path(args.route_acceptance).resolve();route=checked(routefile)
    assert route['B']==16 and route['period_ns']==12 and set(route['selected_routes'])==set(map(str,range(7)))
    selected={int(e):Path(d).resolve() for e,d in route['selected_routes'].items()}
    selected[7]=Path(args.e7_hardware).resolve().parent
    for e,directory in selected.items():
        hw=checked(directory/'hardware.json')
        assert (hw['B'],hw['engine'],hw['clock_period_ns'],hw['part'],hw['latency_advancing_edges'])==(16,e,12,'xc7a100tcsg324-1',2)
        assert (hw['slice_accounting']['launch_FF'],hw['slice_accounting']['capture_FF'],hw['slice_accounting']['fixture_FF'])==(55,39,94)
        assert min(hw[k] for k in ('WNS_ns','WHS_ns','boundary_WNS_ns','boundary_WHS_ns'))>=0
    mainnative={'glif':P/'hardware/native_actual_glif_s0_a0/acceptance.json','ottt':P/'hardware/native_actual128_s0_a0/acceptance.json'}
    e7native=Path(args.e7_native_acceptance).resolve()
    for f in [*mainnative.values(),e7native]:
        native=checked(f);assert native['B']==16 and native['stall']==0 and native['capture']==1
    plan=[('glif',e) for e in (5,1,7,0,3,4,2)]+[('ottt',e) for e in (5,1,6,0,3,4,2)]
    reused={};reusedgates={}
    for file in args.reuse_child_progress:
        file=Path(file).resolve();d=checked(file);key=(d['workload'],d['engines'][0])
        assert key in plan and key not in reused
        reusedgates[key]=accepted_child(file,selected,*key);reused[key]=file
    stamps=b.pins([Path(__file__),P/'run_energy_profiled_child.py',P/'certify_energy_export.py',
        P/'cached_energy_auditor_source_equivalence.json',P/'certified_energy_auditor_source_checks.json',
        P/'verify_selected_evidence_certified.py',routefile,Path(args.e7_hardware),*mainnative.values(),e7native,
        *reused.values(),ROOT/'selective_energy_trial/run_selective_energy.py',b.VIVADO/'data/verilog/src/glbl.v'])
    progress=P/f'energy_recovery_sequence_{args.attempt}.json'
    assert not progress.exists(),'Retain prior sequences.'
    if not args.run:
        b.verify(stamps)
        print('ENERGY-ONLY RECOVERY READ-ONLY VALIDATION PASS',dict(plan=plan,reused=[list(k) for k in reused],
              future_progress=str(progress),vendor_jobs_launched=False,native_or_route_jobs_planned=False),flush=True)
        return
    state=dict(status='running',B=16,steps=[],failures=[],source_sha256=stamps,route_acceptance=str(routefile),
        e7_hardware_file=str(Path(args.e7_hardware).resolve()),clock_ns=12,fixture_FF=94,
        plan=[dict(workload=w,engine=e) for w,e in plan],scope='Bounded representative GLIF plus retained OTTT wide-value stress capture; representative OTTT is a separate cohort.')
    powerpaths={'glif':{},'ottt':{}}
    for workload,e in plan:
        label=f'{workload.upper()}_energy_e{e}';state['current_stage']=label;b.write(progress,state);b.verify(stamps)
        if (workload,e) in reused:
            receipts=reusedgates[workload,e]
            record=dict(label=label,status='accepted_stage_gate',reused_child_progress=str(reused[workload,e]),vendor_jobs_rerun=False,acceptance_gates=receipts)
        else:
            tag=f'{args.attempt}_e{e}'
            native=e7native if e==7 else mainnative[workload]
            root=ALT if e==7 else P
            childprog=root/f'energy_recovery_{workload}_e{e}_{tag}_progress.json'
            argv=[sys.executable,'-B',str(P/'run_energy_profiled_child.py'),'--workload',workload,'--engine',str(e),
                  '--native-acceptance',str(native),'--route-dir-template',route_template(selected[e],e),'--attempt',tag,'--run']
            if workload=='glif' and e==5:
                if args.reuse_e5_golden_dir:argv+=['--reuse-golden-dir',str(Path(args.reuse_e5_golden_dir).resolve())]
                if args.reuse_e5_export_dir:argv+=['--reuse-export-dir',str(Path(args.reuse_e5_export_dir).resolve())]
            log=P/f'energy_recovery_{label}_{args.attempt}.log';assert not log.exists()
            start=time.time()
            with log.open('w',encoding='utf-8') as stream:
                rc=subprocess.run(argv,cwd=P,stdout=stream,stderr=subprocess.STDOUT).returncode
            record=dict(label=label,returncode=rc,seconds=time.time()-start,log_file=str(log),log_sha256=b.sha(log),acceptance_gates=[])
            try:
                assert rc==0,('child returncode',rc)
                record['acceptance_gates']=accepted_child(childprog,selected,workload,e)
                record['status']='accepted_stage_gate'
            except Exception as exc:
                record.update(status='retained_stage_failure',reason=repr(exc),accepted_energy=False)
                state['failures'].append(record)
                print(log.read_text(errors='replace')[-2500:],flush=True)
        state['steps'].append(record)
        if record['status']=='accepted_stage_gate':
            powerfile=next(x for x in record['acceptance_gates'] if Path(x['path']).name=='power_audit.json')
            powerpaths[workload][str(e)]={'path':powerfile['path'],'sha256':powerfile['sha256']}
        b.verify(stamps);b.write(progress,state)
        print('ENERGY RECOVERY SEQUENCE',label,record['status'],flush=True)
    mapfile=P/f'energy_recovery_power_map_{args.attempt}.json'
    snapshot=P/f'energy_recovery_sequence_{args.attempt}_preaudit.json'
    assert not snapshot.exists();snapshot.write_bytes(progress.read_bytes())
    b.write(mapfile,dict(power_paths=powerpaths,retained_failures=state['failures'],source_sha256=b.pins([snapshot])))
    label='recovery_'+args.attempt
    log=P/f'energy_recovery_selected_audit_{args.attempt}.log'
    with log.open('w',encoding='utf-8') as stream:
        rc=subprocess.run([sys.executable,'-B',str(P/'verify_selected_evidence_certified.py'),
            '--route-acceptance',str(routefile),'--e7-hardware',str(Path(args.e7_hardware).resolve()),
            '--power-map',str(mapfile),'--label',label,'--strict-primary'],cwd=P,stdout=stream,stderr=subprocess.STDOUT).returncode
    auditfile=P/f'selected_evidence_{label}.json'
    state['selected_audit_file']=str(auditfile);state['selected_audit_returncode']=rc
    if auditfile.exists():state['selected_audit_sha256']=b.sha(auditfile)
    state['power_map_file']=str(mapfile);state['power_map_sha256']=b.sha(mapfile)
    state['artifact_sha256']=b.pins([Path(s['log_file']) for s in state['steps'] if 'log_file' in s]+[log])
    if rc==0 and len(powerpaths['glif'])==len(powerpaths['ottt'])==7 and not state['failures']:
        audit=checked(auditfile,'pass_selected_primary_hardware_energy_comparisons')
        assert audit['all_attempted_control_status']=='pass'
        state['status']='pass_complete_explicit_certified_fixed16_energy'
    else:state['status']='completed_with_retained_failures_or_missing_controls'
    b.write(progress,state)
    if state['status']!='pass_complete_explicit_certified_fixed16_energy':raise SystemExit(2)


if __name__=='__main__':main()
