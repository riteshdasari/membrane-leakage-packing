from pathlib import Path
import hashlib,json
import numpy as np
P=Path(__file__).resolve().parent
d=json.loads((P/'stage3_results.json').read_text());a=json.loads((P/'stage3_algebra.json').read_text())
assert d['status']=='pass_exact_packed_feedback_and_stream_screen'and a['status']=='pass'
for record in(d,a):
    for path,wanted in record['pins'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==wanted,path
packed=np.load(P/'stage3_logits.npz');reference=np.load(P/'stage2_logits.npz')
assert np.array_equal(packed['logits'],reference['logits'][:64])
assert np.array_equal(packed['predictions'],reference['predictions'][:64])
assert np.array_equal(packed['labels'],reference['labels'][:64])
for key,val in d['total'].items():
    if key=='issues':
        for policy,n in val.items():assert n==sum(r[key][policy]for r in d['rows'])
    else:assert val==sum(r[key]for r in d['rows'])
t=d['total'];assert t['raw_operations']==159383552
assert t['arithmetic_operations']+t['zero_bypassed']==t['raw_operations']
assert t['issues']['adaptive_pre']==t['issues']['fixed_scalar1']-t['adaptive_pairs']
assert t['issues']['fixed_split2']==t['issues']['fixed_scalar1']-t['fixed_split_pairs']
assert t['issues']['adaptive_post']==t['issues']['adaptive_pre']
for row in d['synthetic_bursts']:
    if row['pattern']=='all_wide':
        assert row['issues']['adaptive_pre']==row['width']
        assert row['issues']['fixed_split2']==(row['width']+1)//2
decision=dict(status='pass_and_proceed_to_RTL',source_pin_count=len(d['pins'])+len(a['pins']),
    samples=64,all_logits_identical=True,raw_operations=t['raw_operations'],
    arithmetic_operations=t['arithmetic_operations'],
    narrow9_fraction=t['narrow9_arithmetic_operations']/t['arithmetic_operations'],
    adaptive_issues=t['issues']['adaptive_pre'],fixed_split_issues=t['issues']['fixed_split2'],
    issue_overhead_vs_fixed_split_fraction=t['issues']['adaptive_pre']/t['issues']['fixed_split2']-1,
    decision_reason='Only1.084% extra issues versus the strong one-DSP split control, while the candidate removes two high-part fabric products. A matched routed resource/energy experiment is justified. No win is assumed.',
    unfavorable_wide_bursts_retained=True,full_neuron_latency_measured=False,hardware_energy_measured=False)
(P/'stage3_acceptance.json').write_text(json.dumps(decision,indent=2)+'\n',encoding='utf-8')
print(json.dumps(decision),flush=True)
