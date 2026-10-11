"""Optimistic zero-pair-skipping baseline, not implemented RTL or measured timing."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
from pathlib import Path
import json,numpy as np
P=Path(__file__).resolve().parent;R=P/'results'
def metrics(g):
    zero=(g==0).all(-1)
    narrow=((g>=-16)&(g<=15)).all(-1)&~zero
    n2=(g.reshape(*g.shape[:-1],3,2)!=0).any(-1).sum(-1)
    n3=(g.reshape(*g.shape[:-1],2,3)!=0).any(-1).sum(-1)
    best=np.where(narrow,np.minimum(n2,n3),n2)
    values=[zero.size,int(zero.sum()),int(narrow.sum()),
            int(np.where(zero,1,6).sum()),int(np.where(zero,1,6-narrow).sum()),
            int(n2.sum()),int(np.where(zero,1,n2+3).sum()),
            int(best.sum()),int(np.where(zero,1,best+3).sum())]
    return np.array(values,np.int64)
def row(values,**meta):
    keys=['groups','zero_groups','narrow_groups','tested_fixed_cycles','tested_adaptive_cycles',
          'zero_pair_fixed_issues','zero_pair_fixed_cycles','zero_skip_adaptive_issues','zero_skip_adaptive_cycles']
    out=dict(meta,**dict(zip(keys,map(int,values))))
    out['tested_adaptive_saving_vs_optimistic_zero_pair_fixed']=1-out['tested_adaptive_cycles']/out['zero_pair_fixed_cycles']
    out['optimistic_zero_skip_adaptive_saving']=1-out['zero_skip_adaptive_cycles']/out['zero_pair_fixed_cycles']
    return out
sample=row(metrics(np.load(R/'adaptive_delta_model_25_1/expected.npz')['groups'].astype(np.int64)),scope='RTL-replayed inputs')
rows=[]
for cfg in json.loads((R/'final_selected.json').read_text())['models']:
    data=np.load(R/f"model_seed{cfg['seed']}.npz");x=data['test_x'];w=[data['w0'],data['w1']]
    for hard in [False,True]:
        state=[np.zeros((len(x),a.shape[1]),np.int64)for a in w]
        rng=np.random.default_rng(123);counts=np.zeros(9,np.int64)
        for t in range(32):
            sp=rng.random(x.shape)<x
            for li,a in enumerate(w):
                old=state[li];blocks=(a.shape[1]+5)//6
                g=np.pad(old,((0,0),(0,blocks*6-a.shape[1]))).reshape(len(x),blocks,6)
                counts+=metrics(g)
                nxt=old-(25*old//256)+sp.astype(np.int64)@a;fire=nxt>=cfg['thresholds'][li]
                state[li]=np.where(fire,0,nxt)if hard else nxt-fire*cfg['thresholds'][li];sp=fire
        rows.append(row(counts,seed=cfg['seed'],saved_leak_shift=cfg['leak_shift'],hard_reset=hard))
profiles=json.loads((R/'adaptive_delta_profile.json').read_text())['rows']
for a,b in zip(rows,profiles):
    assert a['tested_fixed_cycles']==b['fixed_complete_group_cycles']
    assert a['tested_adaptive_cycles']==b['adaptive_complete_group_cycles']
result=dict(sample=sample,rows=rows,notes=[
 'Arithmetic schedule audit only: zero-pair skipping and metadata/output bypass logic have not been built or routed',
 'Uses the existing MP1 service formula: one clock for a zero group, otherwise active issues plus three pipeline/service clocks',
 'Models have128 hidden and10 output neurons; six-lane groups contain padded zeros, including complete zero pairs',
 'The tested adaptive RTL does not skip individual zero pairs; both tested fixed and adaptive cores skip only all-zero groups',
 'The optimistic adaptive schedule additionally skips zero triples and selects the cheaper eligible two/three format; it is not tested RTL'])
(R/'adaptive_delta_zero_pair_audit.json').write_text(json.dumps(result,indent=2))
print(json.dumps(dict(sample=sample,profile_current_saving_range=[min(r['tested_adaptive_saving_vs_optimistic_zero_pair_fixed']for r in rows),max(r['tested_adaptive_saving_vs_optimistic_zero_pair_fixed']for r in rows)],profile_optimistic_saving_range=[min(r['optimistic_zero_skip_adaptive_saving']for r in rows),max(r['optimistic_zero_skip_adaptive_saving']for r in rows)]),indent=2),flush=True)
