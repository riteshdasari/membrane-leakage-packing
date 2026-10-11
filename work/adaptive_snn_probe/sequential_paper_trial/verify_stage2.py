"""Independent artifact and full-test accounting gate for the integer reference."""
from pathlib import Path
import hashlib,json
import numpy as np
P=Path(__file__).resolve().parent;PUBLIC=P.parent/'public_model_trial'
result=json.loads((P/'stage2_results.json').read_text(encoding='utf-8'))
assert result['status']=='complete_integer_neuron_public_test'
assert result['samples']==10000 and not result['packing_executed'] and not result['hardware_replay']
for path,wanted in result['pins'].items():
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==wanted,path
plan=json.loads((P/'stage2_plan.json').read_text(encoding='utf-8'))
assert plan['unit']==256 and plan['coefficient_fractional_bits']==8 and plan['neuron_state_and_current_signed_bits']==24
integer=np.load(P/'stage2_logits.npz');floating=np.load(PUBLIC/'full_test_logits_v3.npz')
assert integer['indices'].tolist()==list(range(10000))
assert np.array_equal(integer['labels'],floating['labels'])
pred=integer['logits'].argmax(1);f=floating['logits'].argmax(1);labels=integer['labels']
assert np.array_equal(pred,integer['predictions'])
correct=int((pred==labels).sum());fc=int((f==labels).sum());different=int((pred!=f).sum())
assert (correct,fc,different)==(result['correct'],result['float_correct'],result['class_disagreements'])
assert result['accuracy_percent']==correct/100 and result['float_accuracy_percent']==fc/100
assert result['observed_neuron_updates']==sum(r['updates']for r in result['rows'].values())
assert len(result['rows'])==17
assert result['observed_neuron_updates']==159383552*10000//64
assert all(r['independent_state_mismatches']==r['independent_spike_mismatches']==0 for r in result['rows'].values())
assert all(-2**23<=r[k]<2**23 for r in result['rows'].values()for k in('U_min','U_max','I_min','I_max','next_min','next_max'))
answer=dict(status='pass',samples=10000,correct=correct,float_correct=fc,class_disagreements=different,
    neuron_updates=result['observed_neuron_updates'],checked_pin_count=len(result['pins']),
    observed_old_state_range=[min(r['U_min']for r in result['rows'].values()),max(r['U_max']for r in result['rows'].values())],
    observed_next_state_range=[min(r['next_min']for r in result['rows'].values()),max(r['next_max']for r in result['rows'].values())],
    scope='Artifact integrity, full-test classification accounting, observed bounds and first-batch independent numerical checks. Not full-model integer-synapse or hardware verification.')
(P/'stage2_acceptance.json').write_text(json.dumps(answer,indent=2)+'\n',encoding='utf-8')
print(json.dumps(answer),flush=True)
