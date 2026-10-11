"""Packed-leak feedback and original-order issue screen of the accepted model."""
from pathlib import Path
import hashlib,json,time
import numpy as np
import torch
from integer_glif import PUBLIC,load_model,normalized
from packed_executor import packed,oracle,POLICIES,starts_for
P=Path(__file__).resolve().parent
assert json.loads((P/'stage2_acceptance.json').read_text())['status']=='pass'
assert json.loads((P/'stage3_algebra.json').read_text())['status']=='pass'
assert not(P/'integer_glif_packed.py').exists()
source=(P/'integer_glif.py').read_text(encoding='utf-8')
source=source.replace('def install(model, observer=None, audit_first_batch=False):','def install(model, observer=None, audit_first_batch=False, leak_executor=None):')
line='leak = (coefficient*u+255) >> 8'
assert source.count(line)==1
source=source.replace(line,line+'\n                if leak_executor is not None:\n                    leak = leak_executor(name,step,u,coefficient,leak)')
(P/'integer_glif_packed.py').write_text(source,encoding='utf-8')
from integer_glif_packed import install
torch.set_num_threads(8);torch.set_num_interop_threads(1)
rows={};frames=[];started=time.monotonic()
# Verify the vectorized greedy matching against an independent sequential loop.
rng=np.random.default_rng(91364)
for length in range(1,100):
    for repeat in range(50):
        e=rng.integers(0,2,length-1).astype(bool);want=[];pos=0
        while pos<length:
            if pos<length-1 and e[pos]:want.append(pos);pos+=2
            else:pos+=1
        assert starts_for(e).tolist()==want
def execute(name,step,u,coefficient,reference):
    v=u.numpy().reshape(-1);b=coefficient.numpy().reshape(-1)
    result,counts=packed(v,b)
    assert np.array_equal(result,reference.numpy().reshape(-1))
    key=name+':'+str(step)
    row=rows.setdefault(key,dict(layer=name,time_step=step,frames=0,raw_operations=0,zero_bypassed=0,
        arithmetic_operations=0,narrow9_arithmetic_operations=0,same_coefficient_edges=0,
        adaptive_pairs=0,post_pairs=0,fixed_split_pairs=0,issues={p:0 for p in POLICIES}))
    row['frames']+=1
    for k,value in counts.items():
        if k=='issues':
            for p,n in value.items():row['issues'][p]+=n
        else:row[k]+=value
    # A bounded true-operand sample for later native RTL and timing replays.
    nz=np.flatnonzero((v!=0)&(b!=0));selected=nz[:64]
    if len(selected):frames.append((v[selected].copy(),b[selected].copy(),key))
    return torch.from_numpy(result.reshape(u.shape))
data=np.load(PUBLIC/'original_test64.npz');reference=np.load(P/'stage2_logits.npz')
model=load_model();states=install(model,audit_first_batch=True,leak_executor=execute);logits=[]
with torch.inference_mode():
    for start in range(0,64,4):
        logits.append(model(normalized(data['images'][start:start+4])).numpy().copy())
        print('PACKED FEEDBACK',start+4,'/64',round(time.monotonic()-started,1),'seconds',flush=True)
full=np.concatenate(logits);assert np.array_equal(full,reference['logits'][:64])
assert all(r['independent_state_mismatches']==r['independent_spike_mismatches']==0 for r in states.values())
total=dict(raw_operations=0,zero_bypassed=0,arithmetic_operations=0,narrow9_arithmetic_operations=0,
    adaptive_pairs=0,post_pairs=0,fixed_split_pairs=0,issues={p:0 for p in POLICIES})
for r in rows.values():
    for k in total:
        if k=='issues':
            for p,n in r[k].items():total[k][p]+=n
        else:total[k]+=r[k]
assert total['raw_operations']==159383552
comparisons=[]
for p in POLICIES:
    issue=total['issues'][p]
    comparisons.append(dict(policy=p,arithmetic_issues=issue,
        useful_operations_per_arithmetic_issue=total['arithmetic_operations']/issue,
        adaptive_issue_saving_fraction=1-total['issues']['adaptive_pre']/issue))
stream=P/'stage3_actual_frames.txt'
stream.write_text(str(len(frames))+'\n'+'\n'.join(str(len(u))+'\n'+'\n'.join(f'{int(a)} {int(c)}'for a,c in zip(u,b))for u,b,key in frames)+'\n',encoding='utf-8')
# Unfavorable wide bursts are part of the same predeclared operation test.
bursts=[]
for width in(1,4,16,64,256):
    for pattern in('all_narrow','all_wide','narrow_wide_narrow'):
        if pattern=='all_narrow':v=np.full(width,100,dtype=np.int64)
        elif pattern=='all_wide':v=np.full(width,1000,dtype=np.int64)
        else:v=np.concatenate((np.full(width,100),np.full(width,1000),np.full(width,100))).astype(np.int64)
        out,c=packed(v,np.full(len(v),153,dtype=np.int64));bursts.append(dict(width=width,pattern=pattern,**c))
gate=dict(status='proceed_to_measured_RTL_frontier_trial',reason='Exact pair/full arithmetic passed; area is unmeasured. The precompensated design removes both high-part fabric products used by fixed_split2. Its observed issue overhead and all other controls are retained. This warrants a route, not a win claim.',
    adaptive_vs_fixed_split_issue_overhead_fraction=total['issues']['adaptive_pre']/total['issues']['fixed_split2']-1,
    no_measured_resource_or_energy_advantage_yet=True)
np.savez_compressed(P/'stage3_logits.npz',logits=full,labels=data['labels'],predictions=full.argmax(1))
answer=dict(status='pass_exact_packed_feedback_and_stream_screen',samples=64,
    correct=int((full.argmax(1)==data['labels']).sum()),all_logits_bit_identical_to_integer_reference=True,
    state_spike_arithmetic_mismatches=0,total=total,comparisons=comparisons,rows=list(rows.values()),
    synthetic_bursts=bursts,gate=gate,elapsed_seconds=time.monotonic()-started,
    scope='Software exact packing and analytic multiplier issue counts with common zero filtering. No RTL latency, filter bandwidth/cost, total neuron-update latency or hardware energy claim.',
    pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in[Path(__file__),P/'packed_executor.py',P/'integer_glif_packed.py',P/'stage3_plan.json',P/'stage3_algebra.json',P/'stage2_acceptance.json',P/'stage3_logits.npz',stream]})
(P/'stage3_results.json').write_text(json.dumps(answer,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(status=answer['status'],total=total,comparisons=comparisons,gate=gate)),flush=True)
