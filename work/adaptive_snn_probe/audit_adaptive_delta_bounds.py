"""Inductive integer range certificates for saved weights at beta231."""
from pathlib import Path
import numpy as np,json
P=Path(__file__).resolve().parent;R=P/'results';rows=[]
def leak(u):return -((-231*u)//256)
for cfg in json.loads((R/'final_selected.json').read_text())['models']:
 d=np.load(R/f"model_seed{cfg['seed']}.npz")
 for li,n in enumerate(['w0','w1']):
  w=d[n].astype(np.int64);negative=-np.minimum(w,0).sum(0);positive=np.maximum(w,0).sum(0);th=cfg['thresholds'][li]
  lower=-((256*negative+24)//25)
  upper=np.maximum(th-1,(256*np.maximum(positive-th,0)+24)//25)
  # For U in [lower,upper], monotonic leak preserves endpoint ordering.
  # Every allowed binary current/prefix is [-negative,positive].
  before_min=leak(lower)-negative;before_max=leak(upper)+positive
  assert np.all(before_min>=lower)
  assert np.all(np.maximum(th-1,before_max-th)<=upper)
  assert np.all(lower<=0)and np.all(upper>=0)
  assert np.all(before_min>=-1024)and np.all(before_max<=1023)
  rows.append(dict(seed=cfg['seed'],saved_leak_shift=cfg['leak_shift'],layer=li,threshold=th,
   min_lower=int(lower.min()),max_upper=int(upper.max()),min_prefix=int(before_min.min()),max_prefix=int(before_max.max()),
   max_negative_current=int(negative.max()),max_positive_current=int(positive.max()),all_state_and_prefix_values_in_int11=True))
lo,hi=-646,216
assert leak(lo)-64==lo and leak(hi)+56-35==hi
stress=dict(post_state_bound=[lo,hi],current_prefix_bound=[-64,56],prethreshold_upper=leak(hi)+56,
 threshold=35,beta=231,all_prefix_values_in_int11=True)
(R/'adaptive_delta_model_bounds.json').write_text(json.dumps(dict(rows=rows,stress=stress,failures=0,
 note='Inductive bounds for beta231, arbitrary allowed binary patterns, paired current prefixes, and one hard or subtractive reset per timestep. Not a universal bound for other coefficients.'),indent=2))
print('BOUND CERTIFICATES PASS',len(rows),flush=True)
