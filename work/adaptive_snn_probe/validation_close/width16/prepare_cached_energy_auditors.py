"""Generate additive auditors; preserve checks and load each NPZ array only once."""
from pathlib import Path
import ast, hashlib, json, sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    receipts=[]
    substitution="actual=np.load(cohort['expected_outputs_file'])"
    replacement="actual={key:value for key,value in np.load(cohort['expected_outputs_file']).items()}"
    for original,new in [(P/'audit_power16_12.py',P/'audit_power16_12_cached.py'),
        (P/'lutceil_e7/audit_power16_lutceil_12.py',P/'lutceil_e7/audit_power16_lutceil_12_cached.py'),
        (P/'ottt_representative/audit_power16_rep3_12.py',P/'ottt_representative/audit_power16_rep3_12_cached.py')]:
        text=original.read_text();assert text.count(substitution)==1
        revised=text.replace(substitution,replacement)
        assert revised.replace(replacement,substitution)==text
        ast.parse(revised)
        if new.exists():assert new.read_text()==revised,'Retain a different existing attempt.'
        else:new.write_text(revised,encoding='utf-8')
        receipts.append(dict(original_file=str(original),original_sha256=sha(original),cached_file=str(new),cached_sha256=sha(new),
            change='Exactly one NPZ handle assignment becomes a dictionary whose arrays are materialized once; all trace, arithmetic, SDF, activity and energy checks unchanged.',
            exact_reverse_substitution_reproduces_original=True,
            arrays_materialized=['U','beta','expected_leak','frame_lengths'],
            original_expression=substitution,replacement_expression=replacement))
    original=P/'verify_selected_evidence.py';new=P/'verify_selected_evidence_cached.py'
    text=original.read_text();revised=text
    for old,updated in [("ALT/'audit_power16_lutceil_12.py'","ALT/'audit_power16_lutceil_12_cached.py'"),
                        ("P/'audit_power16_12.py'","P/'audit_power16_12_cached.py'")]:
        assert revised.count(old)==1;revised=revised.replace(old,updated)
    reverse=revised.replace("ALT/'audit_power16_lutceil_12_cached.py'","ALT/'audit_power16_lutceil_12.py'").replace("P/'audit_power16_12_cached.py'","P/'audit_power16_12.py'")
    assert reverse==text;ast.parse(revised)
    if new.exists():assert new.read_text()==revised
    else:new.write_text(revised,encoding='utf-8')
    receipts.append(dict(original_file=str(original),original_sha256=sha(original),cached_file=str(new),cached_sha256=sha(new),
        change='Exactly two auditor path literals changed to the cached variants; every explicit selection, route, SHA and reproduction check retained.',
        exact_reverse_substitution_reproduces_original=True))
    report=dict(status='pass_additive_cached_auditor_source_equivalence',changes=receipts,vendor_jobs_launched=False,
        source_sha256={str(Path(__file__).resolve()):sha(Path(__file__).resolve()),**{r['original_file']:r['original_sha256'] for r in receipts}},
        artifact_sha256={r['cached_file']:r['cached_sha256'] for r in receipts})
    destination=P/'cached_energy_auditor_source_equivalence.json'
    if destination.exists():assert json.loads(destination.read_text())==report
    else:destination.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],cached_artifacts=len(receipts),manifest=str(destination))))


if __name__=='__main__':main()
