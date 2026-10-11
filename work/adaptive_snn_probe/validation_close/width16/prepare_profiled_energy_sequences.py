"""Additive launch adapter substitutions; preserve every sequence acceptance gate."""
from pathlib import Path
import ast,hashlib,json,sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;REP=P/'ottt_representative'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    changes=[]
    for source,target,old,new,number in [
        (P/'run_energy_recovery_sequence.py',P/'run_energy_profiled_sequence.py',"P/'run_energy_recovery_child.py'","P/'run_energy_profiled_child.py'",2),
        (REP/'prepare_and_run_certified.py',REP/'prepare_and_run_profiled.py',"W/'run_energy_recovery_representative_child.py'","W/'run_energy_profiled_child.py'",2)]:
        text=source.read_text();assert text.count(old)==number
        updated=text.replace(old,new)
        if target.parent==REP:
            marker="['--workload',WORKLOAD,'--native-acceptance'"
            substitute="['--representative','--workload',WORKLOAD,'--native-acceptance'"
            assert updated.count(marker)==1;updated=updated.replace(marker,substitute)
            assert updated.replace(substitute,marker).replace(new,old)==text
        else:assert updated.replace(new,old)==text
        ast.parse(updated)
        if target.exists():assert target.read_text()==updated
        else:target.write_text(updated,encoding='utf-8')
        changes.append(dict(original_file=str(source),original_sha256=sha(source),profiled_file=str(target),profiled_sha256=sha(target),
            exact_reverse_launch_adapter_substitutions=True,acceptance_checks_changed=False))
    report=dict(status='pass_additive_profiled_sequence_source_checks',changes=changes,
        source_sha256={str(Path(__file__).resolve()):sha(__file__),str(P/'run_energy_profiled_child.py'):sha(P/'run_energy_profiled_child.py'),
            str(P/'completed_stage_memory_audit_a0.json'):sha(P/'completed_stage_memory_audit_a0.json'),**{r['original_file']:r['original_sha256'] for r in changes}},
        artifact_sha256={r['profiled_file']:r['profiled_sha256'] for r in changes},vendor_jobs_launched=False)
    dest=P/'profiled_sequence_source_checks.json'
    if dest.exists():assert json.loads(dest.read_text())==report
    else:dest.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],manifest=str(dest))))


if __name__=='__main__':main()
