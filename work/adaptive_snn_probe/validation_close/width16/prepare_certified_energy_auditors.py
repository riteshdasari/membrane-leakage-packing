"""Add strict balanced-export checks to unchanged cached energy auditors."""
from pathlib import Path
import ast,hashlib,json,sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    receipt=[]
    suffix='''

# Additive export certificate gate. The original cached audit is invoked intact.
_uncertified_annotation = annotation
def annotation(directory):
    _directory=Path(directory).resolve()
    _evidence=read(_directory/'evidence.json')
    _replay=read(Path(_evidence['replay_dir'])/'replay_checks.json')
    _export=Path(_replay['export_artifacts_file']).resolve().parent
    _base=P if (P/'certify_energy_export.py').exists() else P.parent
    _spec=importlib.util.spec_from_file_location('certified_energy_export_reproduction',_base/'certify_energy_export.py')
    _binder=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_binder)
    _certificate=_binder.verify(_export)
    _result=_uncertified_annotation(_directory)
    _result['certified_export_audit']=_certificate
    return _result
'''
    for cached,certified in [(P/'audit_power16_12_cached.py',P/'audit_power16_12_certified.py'),
        (P/'lutceil_e7/audit_power16_lutceil_12_cached.py',P/'lutceil_e7/audit_power16_lutceil_12_certified.py'),
        (P/'ottt_representative/audit_power16_rep3_12_cached.py',P/'ottt_representative/audit_power16_rep3_12_certified.py')]:
        text=cached.read_text();new=text+suffix;ast.parse(new)
        assert new[:-len(suffix)]==text
        if certified.exists():assert certified.read_text()==new
        else:certified.write_text(new,encoding='utf-8')
        receipt.append(dict(cached_file=str(cached),cached_sha256=sha(cached),certified_file=str(certified),certified_sha256=sha(certified),
            cached_checks_unchanged_as_exact_prefix=True,addition='Before original strict annotation audit, independently reproduce EOF-only SDF and exact one-string annotation-path binding certificates.'))
    original=P/'verify_selected_evidence.py';new=P/'verify_selected_evidence_certified.py'
    text=original.read_text();changed=text
    for old,updated in [("ALT/'audit_power16_lutceil_12.py'","ALT/'audit_power16_lutceil_12_certified.py'"),
                        ("P/'audit_power16_12.py'","P/'audit_power16_12_certified.py'")]:
        assert changed.count(old)==1;changed=changed.replace(old,updated)
    assert changed.replace("ALT/'audit_power16_lutceil_12_certified.py'","ALT/'audit_power16_lutceil_12.py'").replace("P/'audit_power16_12_certified.py'","P/'audit_power16_12.py'")==text
    ast.parse(changed)
    if new.exists():assert new.read_text()==changed
    else:new.write_text(changed,encoding='utf-8')
    report=dict(status='pass_additive_certified_energy_auditor_source_checks',changes=receipt,
        selected_verifier=dict(original_file=str(original),original_sha256=sha(original),new_file=str(new),new_sha256=sha(new),
            exact_reverse_two_path_substitutions=True),
        source_sha256={str(Path(__file__).resolve()):sha(__file__),str(P/'cached_energy_auditor_source_equivalence.json'):sha(P/'cached_energy_auditor_source_equivalence.json'),
            str(P/'certify_energy_export.py'):sha(P/'certify_energy_export.py'),str(original):sha(original),**{r['cached_file']:r['cached_sha256'] for r in receipt}},
        artifact_sha256={str(new):sha(new),**{r['certified_file']:r['certified_sha256'] for r in receipt}},vendor_jobs_launched=False)
    destination=P/'certified_energy_auditor_source_checks.json'
    if destination.exists():assert json.loads(destination.read_text())==report
    else:destination.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],manifest=str(destination))))


if __name__=='__main__':main()
