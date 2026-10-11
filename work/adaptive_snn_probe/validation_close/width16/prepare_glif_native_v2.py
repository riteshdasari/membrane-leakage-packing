"""Add a fixed16 GLIF representative cohort without altering active native files."""
from pathlib import Path
import hashlib,json,ast
import numpy as np
P=Path(__file__).resolve().parent;A=P.parent/'activity/random_stratified_v2'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not(P/'domain_acceptance_glif_v2.json').exists()
accept=json.loads((A/'acceptance.json').read_text());gate=json.loads((A/'representativeness_acceptance.json').read_text());r=json.loads((A/'results.json').read_text())
assert accept['status']==gate['status']==r['status']=='pass'
for group in('source_sha256','artifact_sha256'):
    for name,want in r[group].items():assert sha(Path(name))==want
data=np.load(A/'activity_operands.npz')
assert np.all((-32768<=data['U'])&(data['U']<=32767))
stim=P/'actual_glif_stim.txt';stim.write_bytes((A/'representative_stim.txt').read_bytes())
out=P/'actual_glif_expected.npz';np.savez_compressed(out,U=data['U'],beta=data['beta'],expected_leak=data['expected_leak'],frame_lengths=data['window_lengths'])
domain=json.loads((P/'domain_acceptance.json').read_text())
domain['cohorts']['actual_glif']=dict(stimulus_file=str(stim),expected_outputs_file=str(out),operations=r['sample_operations'],groups=r['sample_windows'],
    expected_requests_by_engine=r['sample_issues_by_engine'],expected_unstalled_min_max_latency=2,
    artifact_sha256={str(p):sha(p)for p in[stim,out]})
domain['source_sha256']|={str(p):sha(p)for p in[Path(__file__),P/'domain_acceptance.json',A/'acceptance.json',A/'representativeness_acceptance.json',A/'results.json',A/'activity_operands.npz',A/'representative_stim.txt']}
domain['new_cohort_scope']='Same fixed16 full membrane hardware domain and original unit256; representative64image GLIF arithmetic capture passed predeclared distributions; oldsigned12 hardware retained separately.'
(P/'domain_acceptance_glif_v2.json').write_text(json.dumps(domain,indent=2)+'\n')
runner=(P/'run_native16.py').read_text().replace("['general','shift128','actual128']","['general','shift128','actual128','actual_glif']")
runner=runner.replace("P/'domain_acceptance.json'","P/'domain_acceptance_glif_v2.json'").replace("shift=0 if args.cohort=='general' else 1","shift=0 if args.cohort in('general','actual_glif') else 1")
ast.parse(runner);(P/'run_native16_v2.py').write_text(runner,encoding='utf-8')
record=dict(status='prepared',original_active_runner_unchanged_sha256=sha(P/'run_native16.py'),
            source_sha256={str(p):sha(p)for p in[Path(__file__),P/'domain_acceptance.json',A/'acceptance.json',A/'representativeness_acceptance.json']},
            artifact_sha256={str(p):sha(p)for p in[P/'domain_acceptance_glif_v2.json',P/'run_native16_v2.py',stim,out]},
            GLIF_expected_counts=r['sample_issues_by_engine'],GLIF_operations=r['sample_operations'])
(P/'glif_native_v2_preparation.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2),flush=True)
