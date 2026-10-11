"""Prepare a new recovery attempt; never overwrite executed sources/results."""
from pathlib import Path
import hashlib
import json
P=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(P.parent/'natural_u11_trial/run_trial.py')=='390c6cb743299d9bb7b695582e644d5c5754996f52542396524851218312a160'
target=P/'audit_power_v2.py';assert not target.exists()
original=P/'audit_power.py';text=original.read_text()
assert text.count('fixture_FF=338')==1 and text.count('common 338-FF OOC fixture')==1
target.write_text(text.replace('fixture_FF=338','fixture_FF=290').replace('common 338-FF OOC fixture','common 290-FF OOC fixture'))
record=dict(status='prepared',original_auditor_sha256=sha(original),new_auditor_sha256=sha(target),
    corrected_fields=['Returned fixture_FF metadata','Returned scope description'],
    gates_changed=False,
    source_restoration=dict(path=str(P.parent/'natural_u11_trial/run_trial.py'),
        expected_and_restored_sha256=sha(P.parent/'natural_u11_trial/run_trial.py'),
        explanation='A stale subagent added resume-log naming to an already executed runner. Strict hash gate rejected E0 audit. Root reversed the exact patch and independently matched the original recorded SHA256. No tool inputs/checkpoints/netlists/simulation artifacts were changed by the patch.'),
    retained_failed_attempt=str(P/'repair_completion.json'))
(P/'repair_v2_preparation.json').write_text(json.dumps(record,indent=2)+'\n')
print('ENERGY RECOVERY V2 PREPARED; original source hash restored')
