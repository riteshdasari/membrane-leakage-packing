"""Aggregate explicit partial receipts; preserve frozen child and selected audits.

This script launches no vendor, inference, native, route, or energy producers.
--run-selected-audit invokes only the existing read-only selected verifier.
"""
from pathlib import Path
import argparse, ast, hashlib, importlib.util, json, os, re, subprocess, sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
GATE=P/'energy_partition_aggregate_source_checks.json'
EXPECTED={
    'run_energy_profiled_sequence.py':'61449f4b5642901e7129265d91e41fea0a75b654cfe219ff75a68d38a346aa23',
    'run_energy_profiled_partition.py':'68397ee3c99f2cb4832bd12ae0d7b416432734cf43a8f0932872bf47e421b9fa',
    'verify_selected_evidence_certified.py':'ad8053174af02caa11d805f7d577c5bc5578bc8c8439b241c725a4a1efe3e484',
}
def sha(f):return hashlib.sha256(Path(f).read_bytes()).hexdigest()
def read(f):return json.loads(Path(f).read_text(encoding='utf-8'))
def pins(files):return {str(Path(f).resolve()):sha(f) for f in files}
def verify_pins(values):
    for file,pin in values.items():assert sha(file)==pin,('changed explicit evidence',file)
def atomic_bytes(file,data):
    file=Path(file).resolve();assert not file.exists(),('Retain earlier evidence',str(file))
    tmp=file.with_name(file.name+f'.owned_tmp_{os.getpid()}')
    with tmp.open('xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
    try:
        # Windows rename is atomic and fails if destination already exists.
        assert os.name=='nt','Non-overwriting Windows atomic rename required.'
        os.rename(tmp,file)
    finally:
        if tmp.exists():tmp.unlink()
def atomic_json(file,obj):atomic_bytes(file,(json.dumps(obj,indent=2)+'\n').encode('utf-8'))
def load(file,name):
    spec=importlib.util.spec_from_file_location(name,file);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def function_text(file,name):
    content=Path(file).read_text(encoding='utf-8');tree=ast.parse(content)
    node=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name==name)
    return ast.get_source_segment(content,node)
def prepare_gate():
    for name,pin in EXPECTED.items():assert sha(P/name)==pin,('Frozen dependency changed',name)
    assert function_text(P/'run_energy_profiled_sequence.py','accepted_child')==function_text(P/'run_energy_profiled_partition.py','accepted_child')
    files=[Path(__file__),*(P/name for name in EXPECTED),P/'profiled_partition_source_checks.json',P/'profiled_sequence_source_checks.json',P/'cached_energy_auditor_source_equivalence.json',P/'certified_energy_auditor_source_checks.json']
    record=dict(status='pass_frozen_partition_aggregate_source_binding',source_sha256=pins(files),
        accepted_child_function_sha256=hashlib.sha256(function_text(P/'run_energy_profiled_sequence.py','accepted_child').encode()).hexdigest(),
        child_acceptance_invoked_from_frozen_sequence=True,selected_auditor_invoked_unmodified=True,
        acceptance_checks_relaxed=False,vendor_or_model_jobs_launched=False,
        duplicate_policy='Only identical explicit child/power paths and hashes may be deduplicated; differing receipts reject selection.')
    if GATE.exists():assert read(GATE)==record,'Retain existing different source binding.'
    else:atomic_json(GATE,record)
    print(json.dumps(dict(status=record['status'],receipt=str(GATE),vendor_jobs_launched=False)))

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--prepare-source-checks',action='store_true')
    ap.add_argument('--route-acceptance');ap.add_argument('--e7-hardware')
    ap.add_argument('--state',action='append',default=[])
    ap.add_argument('--child-progress',action='append',default=[])
    ap.add_argument('--scheduler-interruption-receipt')
    ap.add_argument('--label');ap.add_argument('--run-selected-audit',action='store_true')
    args=ap.parse_args()
    if args.prepare_source_checks:
        assert not args.run_selected_audit and not args.state and not args.child_progress
        prepare_gate();return
    assert args.route_acceptance and args.e7_hardware and args.label and args.state
    assert re.fullmatch(r'[a-zA-Z0-9_-]+',args.label)
    gate=read(GATE);assert gate['status']=='pass_frozen_partition_aggregate_source_binding'
    verify_pins(gate['source_sha256'])
    m=load(P/'run_energy_profiled_sequence.py','frozen_partition_aggregate_sequence')
    routefile=Path(args.route_acceptance).resolve();route=m.checked(routefile)
    assert route['B']==16 and route['period_ns']==12 and set(route['selected_routes'])==set(map(str,range(7)))
    selected={int(e):Path(d).resolve() for e,d in route['selected_routes'].items()}
    e7file=Path(args.e7_hardware).resolve();selected[7]=e7file.parent
    for e,directory in selected.items():
        hw=m.checked(directory/'hardware.json')
        assert (hw['B'],hw['engine'],hw['clock_period_ns'],hw['part'],hw['latency_advancing_edges'])==(16,e,12,'xc7a100tcsg324-1',2)
        assert (hw['slice_accounting']['launch_FF'],hw['slice_accounting']['capture_FF'],hw['slice_accounting']['fixture_FF'])==(55,39,94)
        assert min(hw[k] for k in ('WNS_ns','WHS_ns','boundary_WNS_ns','boundary_WHS_ns'))>=0
    expected={('glif',e) for e in (0,1,2,3,4,5,7)}|{('ottt',e) for e in (0,1,2,3,4,5,6)}
    entries={};failures=[];inputfiles=[];contexts=[];receipts=[];input_hashes={}
    interruption=None
    if args.scheduler_interruption_receipt:
        interruptionfile=Path(args.scheduler_interruption_receipt).resolve();interruption=read(interruptionfile)
        assert isinstance(interruption,list) and interruption
        assert all(x['Name']=='python.exe' and 'run_energy_profiled_sequence.py' in x['CommandLine'] and '--attempt profiled_all_a0' in x['CommandLine'] for x in interruption)
        input_hashes[str(interruptionfile)]=sha(interruptionfile)
    def add_child(path,origin,claimed=None):
        path=Path(path).resolve();child=m.checked(path);key=(child['workload'],child['engines'][0])
        assert key in expected,('Unexpected explicit child',key)
        gates=m.accepted_child(path,selected,*key)
        powergate=next(x for x in gates if Path(x['path']).name=='power_audit.json')
        childgate=next(x for x in gates if Path(x['path'])==path)
        if claimed is not None:
            assert {(str(Path(x['path']).resolve()),x['sha256']) for x in claimed}=={(x['path'],x['sha256']) for x in gates},'State claimed gates differ from reproduced child gates.'
        value=dict(path=powergate['path'],sha256=powergate['sha256'],child_progress_file=childgate['path'],child_progress_sha256=childgate['sha256'])
        if key in entries:assert entries[key]==value,('Conflicting duplicate explicit receipt',key)
        else:entries[key]=value
        receipts.append(dict(workload=key[0],engine=key[1],origin=origin,acceptance_gates=gates))
    for file in args.state:
        file=Path(file).resolve();raw=file.read_bytes();state=json.loads(raw)
        assert file not in inputfiles,'Duplicate state input.'
        inputfiles.append(file);input_hashes[str(file)]=hashlib.sha256(raw).hexdigest()
        m.b.verify(state.get('source_sha256',{}));m.b.verify(state.get('artifact_sha256',{}))
        assert (state['B'],state['clock_ns'],state['fixture_FF'])==(16,12,94)
        assert Path(state['route_acceptance']).resolve()==routefile and Path(state['e7_hardware_file']).resolve()==e7file
        assert state['status'] in ('running','running_selected_partition','pass_selected_partition','completed_partition_with_retained_failures_or_missing_controls','pass_complete_explicit_certified_fixed16_energy','completed_with_retained_failures_or_missing_controls')
        if state['status']=='running':assert interruption is not None,'Running historical sequence requires explicit deliberate scheduler-interruption context.'
        if 'partition' in state:
            assert state['status'] in ('pass_selected_partition','completed_partition_with_retained_failures_or_missing_controls'),'Partition must have finished its complete included plan.'
            expected_plan=([('glif',e) for e in (0,3,4,2)] if state['partition']=='glif_remaining' else [('ottt',e) for e in (5,1,6,0,3,4,2)])
            assert state['partition'] in ('glif_remaining','ottt_stress')
            assert [(x['workload'],x['engine']) for x in state['plan']]==expected_plan
            assert len(state['steps'])==len(expected_plan)
        contexts.append(dict(path=str(file),sha256=input_hashes[str(file)],status=state['status'],current_stage=state.get('current_stage'),partition=state.get('partition'),
            aggregate_context='deliberately_interrupted_scheduler_snapshot_not_completed_sequence' if state['status']=='running' else 'terminal_selected_partition',
            original_sequence_completion_claim=False if state['status']=='running' else None))
        failures.extend(state.get('failures',[]))
        for step in state['steps']:
            if 'log_file' in step:assert sha(step['log_file'])==step['log_sha256']
            if step.get('status')!='accepted_stage_gate':
                assert step.get('status')=='retained_stage_failure',('Unexpected nonaccepted step',step)
                if step not in failures:failures.append(step)
                continue
            claimed=step['acceptance_gates']
            for r in claimed:assert sha(r['path'])==r['sha256']
            children=[Path(r['path']).resolve() for r in claimed if Path(r['path']).name.endswith('_progress.json')]
            assert len(children)==1,'Exactly one passing child progress per accepted state step.'
            add_child(children[0],str(file),claimed)
    for file in args.child_progress:
        file=Path(file).resolve();input_hashes[str(file)]=sha(file);add_child(file,'explicit_child_argument')
    missing=[f'{w}/e{e}' for w,e in sorted(expected-set(entries))]
    primary_expected=expected-{('glif',2),('ottt',2)}
    missing_primary=[f'{w}/e{e}' for w,e in sorted(primary_expected-set(entries))]
    verify_pins(input_hashes);verify_pins(gate['source_sha256'])
    print(json.dumps(dict(status='explicit_aggregate_read_only_validation_pass',accepted_controls=len(entries),missing_all14=missing,missing_primary=missing_primary,retained_failures=len(failures),vendor_jobs_launched=False)))
    if not args.run_selected_audit:return
    manifest=P/f'energy_partition_aggregate_{args.label}.json'
    mapfile=P/f'energy_partition_aggregate_power_map_{args.label}.json'
    log=P/f'energy_partition_aggregate_selected_audit_{args.label}.log'
    auditfile=P/f'selected_evidence_{args.label}.json'
    assert not any(f.exists() for f in [manifest,mapfile,log,auditfile,auditfile.with_suffix('.md')]),'Retain earlier aggregate outputs.'
    snapshots=[]
    for i,file in enumerate(inputfiles):
        snapshot=P/f'energy_partition_aggregate_{args.label}_state{i}_snapshot.json'
        data=file.read_bytes();assert hashlib.sha256(data).hexdigest()==input_hashes[str(file)]
        atomic_bytes(snapshot,data);snapshots.append(snapshot)
    powerpaths={'glif':{},'ottt':{}}
    for (w,e),value in entries.items():powerpaths[w][str(e)]={'path':value['path'],'sha256':value['sha256']}
    atomic_json(mapfile,dict(power_paths=powerpaths,retained_failures=failures,explicit_child_receipts=receipts,
        input_contexts=contexts,scheduler_interruption_receipt=str(interruptionfile) if interruption is not None else None,
        missing_all14=missing,source_sha256=pins([GATE,*snapshots,routefile,e7file,*(Path(v['child_progress_file']) for v in entries.values()),*([interruptionfile] if interruption is not None else [])]),
        scope='Explicit union of original partial sequence and terminal partitions; no latest/best selection.'))
    argv=[sys.executable,'-B',str(P/'verify_selected_evidence_certified.py'),'--route-acceptance',str(routefile),'--e7-hardware',str(e7file),'--power-map',str(mapfile),'--label',args.label,'--strict-primary']
    with log.open('x',encoding='utf-8') as stream:
        rc=subprocess.run(argv,cwd=P,stdout=stream,stderr=subprocess.STDOUT).returncode
    status='incomplete_or_retained_control_failure';audit=None
    if auditfile.exists():
        audit=read(auditfile);m.b.verify(audit.get('source_sha256',{}));m.b.verify(audit.get('artifact_sha256',{}))
        if rc==0 and not missing and not failures and audit['status']=='pass_selected_primary_hardware_energy_comparisons' and audit['all_attempted_control_status']=='pass':status='pass_complete_explicit_certified_fixed16_energy'
    verify_pins(input_hashes);verify_pins(gate['source_sha256'])
    artifacts=[mapfile,log,*snapshots]+([auditfile,auditfile.with_suffix('.md')] if auditfile.exists() else [])
    atomic_json(manifest,dict(status=status,all14_verifier_invoked=True,selected_audit_returncode=rc,selected_audit_file=str(auditfile),
        missing_all14=missing,retained_failures=failures,accepted_control_count=len(entries),complete_all14_energy_claim=status.startswith('pass_complete_'),
        source_sha256=pins([Path(__file__),GATE,routefile,e7file,*snapshots,*([interruptionfile] if interruption is not None else [])]),artifact_sha256=pins(artifacts),vendor_or_model_jobs_launched=False))
    print(json.dumps(dict(status=status,manifest=str(manifest),selected_audit=str(auditfile))))
    if status!='pass_complete_explicit_certified_fixed16_energy':raise SystemExit(2)

if __name__=='__main__':main()
