"""Prepare additive, explicitly partial energy runners; never launch a job."""
from pathlib import Path
import hashlib, json, ast

P=Path(__file__).resolve().parent
original=P/'run_energy_profiled_sequence.py'
target=P/'run_energy_profiled_partition.py'
receipt=P/'profiled_partition_source_checks.json'
raw=original.read_text(encoding='utf-8')
sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
changes=[]

old="    ap.add_argument('--attempt',required=True)\n"
new=old+"    ap.add_argument('--partition',required=True,choices=('glif_remaining','ottt_stress'))\n"
changes.append(('explicit_partition_CLI',old,new))

start=raw.index("    plan=[('glif',e)")
end=raw.index("    powerpaths={'glif':{},'ottt':{}}",start)
old=raw[start:end]
new=old.replace("    plan=[('glif',e) for e in (5,1,7,0,3,4,2)]+[('ottt',e) for e in (5,1,6,0,3,4,2)]\n", "    plans={'glif_remaining':[('glif',e) for e in (0,3,4,2)],\n           'ottt_stress':[('ottt',e) for e in (5,1,6,0,3,4,2)]}\n    plan=plans[args.partition]\n    equivalencefile=P/'profiled_partition_source_checks.json'\n    equivalence=checked(equivalencefile,'pass_additive_profiled_partition_source_checks')\n    assert equivalence['exact_reverse_three_named_blocks'] and equivalence['child_or_audit_checks_changed'] is False\n")
new=new.replace("    stamps=b.pins([Path(__file__),P/'run_energy_profiled_child.py',", "    stamps=b.pins([Path(__file__),equivalencefile,P/'run_energy_profiled_sequence.py',\n        P/'profiled_sequence_source_checks.json',P/'run_energy_profiled_child.py',")
new=new.replace("progress=P/f'energy_recovery_sequence_{args.attempt}.json'", "progress=P/f'energy_recovery_partition_{args.partition}_{args.attempt}.json'")
new=new.replace("print('ENERGY-ONLY RECOVERY READ-ONLY VALIDATION PASS'", "print('ENERGY-ONLY PARTITION READ-ONLY VALIDATION PASS'")
new=new.replace("dict(plan=plan,reused=", "dict(partition=args.partition,plan=plan,all14_verifier_planned=False,reused=")
new=new.replace("state=dict(status='running',B=16,", "state=dict(status='running_selected_partition',partition=args.partition,all14_verifier_invoked=False,B=16,")
new=new.replace("scope='Bounded representative GLIF plus retained OTTT wide-value stress capture; representative OTTT is a separate cohort.'", "scope='Explicit energy partition only; no complete-control or representative-OTTT closure claim.'")
changes.append(('explicit_plan_source_pins_partial_running_state',old,new))

start=raw.index("    mapfile=P/f'energy_recovery_power_map_")
end=raw.index("\n\n\nif __name__",start)
old=raw[start:end]
new="""    mapfile=P/f'energy_recovery_partition_power_map_{args.partition}_{args.attempt}.json'
    snapshot=P/f'energy_recovery_partition_{args.partition}_{args.attempt}_preaudit.json'
    assert not mapfile.exists() and not snapshot.exists(),'Retain previous partition evidence.'
    b.verify(stamps)
    expected={(w,str(e)) for w,e in plan}
    accepted={(w,e) for w,engines in powerpaths.items() for e in engines}
    all_included_pass=accepted==expected and len(state['steps'])==len(plan) and not state['failures']
    state['status']='pass_selected_partition' if all_included_pass else 'completed_partition_with_retained_failures_or_missing_controls'
    state['selected_audit_invoked']=False
    state['all14_verifier_invoked']=False
    state['all_included_controls_status']='pass' if all_included_pass else 'fail_or_missing'
    state['accepted_control_count']=len(accepted)
    state['included_control_count']=len(plan)
    state['complete_all14_energy_claim']=False
    b.write(progress,state)
    snapshot.write_bytes(progress.read_bytes())
    b.write(mapfile,dict(status=state['status'],partition=args.partition,power_paths=powerpaths,
        included_controls=state['plan'],retained_failures=state['failures'],
        explicit_child_receipts=[s['acceptance_gates'] for s in state['steps'] if s['status']=='accepted_stage_gate'],
        all14_verifier_invoked=False,complete_all14_energy_claim=False,source_sha256=b.pins([snapshot])))
    state['power_map_file']=str(mapfile);state['power_map_sha256']=b.sha(mapfile)
    state['artifact_sha256']=b.pins([Path(s['log_file']) for s in state['steps'] if 'log_file' in s]+[mapfile,snapshot])
    b.verify(stamps);b.write(progress,state)
    print('ENERGY PARTITION COMPLETE',args.partition,state['status'],flush=True)
    if state['status']!='pass_selected_partition':raise SystemExit(2)
"""
changes.append(('partial_aggregation_without_final_all14_verifier',old,new))

out=raw
for name,old,new in changes:
    assert old!=new and out.count(old)==1,name
    out=out.replace(old,new,1)
reversed_text=out
for name,old,new in reversed(changes):
    assert reversed_text.count(new)==1,name
    reversed_text=reversed_text.replace(new,old,1)
assert reversed_text==raw,'Only the three named blocks may change.'
ast.parse(out)
assert out[out.index('def accepted_child('):out.index('\n\ndef main():')]==raw[raw.index('def accepted_child('):raw.index('\n\ndef main():')]
assert out[out.index('    for workload,e in plan:'):out.index('    mapfile=')]==raw[raw.index('    for workload,e in plan:'):raw.index('    mapfile=')]
assert 'verify_selected_evidence_certified.py' not in out[out.index('    mapfile='):], 'No final strict audit in a partition.'
if target.exists():assert target.read_text(encoding='utf-8')==out,'Retain different prepared version.'
else:target.write_text(out,encoding='utf-8',newline='\n')
record=dict(status='pass_additive_profiled_partition_source_checks',
    exact_reverse_three_named_blocks=True,named_changes=[dict(name=n,original_block_sha256=hashlib.sha256(o.encode()).hexdigest(),new_block_sha256=hashlib.sha256(v.encode()).hexdigest()) for n,o,v in changes],
    child_or_audit_checks_changed=False,child_launch_loop_exactly_unchanged=True,
    vendor_thresholds_changed=False,vendor_or_model_jobs_launched=False,final_all14_verifier_removed_from_partition_only=True,
    partitions=dict(glif_remaining=[0,3,4,2],ottt_stress=[5,1,6,0,3,4,2]),
    source_sha256={str(f.resolve()):sha(f) for f in [Path(__file__),original,P/'profiled_sequence_source_checks.json',P/'run_energy_profiled_child.py']},
    artifact_sha256={str(target.resolve()):sha(target)})
encoded=json.dumps(record,indent=2)+'\n'
if receipt.exists():assert receipt.read_text(encoding='utf-8')==encoded,'Retain different prepared receipt.'
else:receipt.write_text(encoded,encoding='utf-8')
print(json.dumps(dict(status=record['status'],target=str(target),sha256=sha(target),vendor_jobs_launched=False)))
