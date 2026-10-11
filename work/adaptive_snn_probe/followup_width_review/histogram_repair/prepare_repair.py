"""Prepare a separate exact copy with only ROOT location and snapshot ownership changed."""
from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent
ROOT=P.parents[1]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
source=ROOT/'range_horizon_trial/screen.py'
target=P/'screen.py'
assert not target.exists() and not(P/'repair_plan.json').exists()
text=source.read_text()
changes=[
    ('P=Path(__file__).resolve().parent;ROOT=P.parent;R=ROOT/\'results\'',
     'P=Path(__file__).resolve().parent;ROOT=P.parents[1];R=ROOT/\'results\''),
    ('import sys\nimport numpy as np','import sys\nfrom copy import deepcopy\nimport numpy as np'),
    ("s=dict(stat);s['service_clocks_one_edge_analytic']",
     "s=dict(stat);s['take_histogram']=deepcopy(stat['take_histogram']);s['service_clocks_one_edge_analytic']")]
for old,new in changes:
    assert text.count(old)==1,(old,text.count(old))
    text=text.replace(old,new)
target.write_text(text)
pins=[source,ROOT/'range_horizon_trial/results.json',ROOT/'range_horizon_trial/predeclared_plan.json',
      ROOT/'sum_width_trial/certificates.json',ROOT/'sum_width_trial/plan.json',
      ROOT/'probe.py',ROOT/'base.py',ROOT/'results/final_selected.json',
      ROOT/'natural_u11_trial/native_acceptance.json',
      *(ROOT/f'results/model_seed{s}.npz'for s in range(3)),Path(__file__),target,P/'verify_repair.py']
plan=dict(status='prepared',changes=['Preserve ROOT as original adaptive_snn_probe; use new local output directory',
      'Deep-copy nested take_histogram when taking each horizon snapshot'],
      source_sha256={str(p.resolve()):sha(p)for p in pins},
      required='Rerun all 72 unchanged coefficient/horizon/seed cases; every non-histogram result value must match the original exactly',
      scope='Corrected software snapshot evidence only; original screen/results remain immutable; no native/vendor jobs, retraining, or architecture selection')
(P/'repair_plan.json').write_text(json.dumps(plan,indent=2)+'\n')
print('HISTOGRAM REPAIR PREPARED',flush=True)
