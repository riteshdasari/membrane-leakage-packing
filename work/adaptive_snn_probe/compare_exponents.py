"""Matched integer-reference comparison of saved block-exponent numerical design.
Six signed8 mantissas share one exponent. No exponent RTL or hardware cost claim.
Uses original exponent update/threshold rounding, but integer-reference leakage,
identical input RNG, and spike-count-only classification for a matched baseline.
"""
import os,sys,json
os.environ['OPENBLAS_NUM_THREADS']='1';sys.dont_write_bytecode=True
import numpy as np
import probe as p
from base import Lanes
rows=json.loads((p.OUT/'final_selected.json').read_text())['models']
out={'note':__doc__,'models':[]}
for seed in (0,):
 d=np.load(p.OUT/f'model_seed{seed}.npz');ws=[d['w0'],d['w1']];x,y=d['test_x'],d['test_y']
 for row in [r for r in rows if r['seed']==seed]:
  sh=row['leak_shift'];th=row['thresholds'];pred,ref=p.reference(ws,th,x,sh)
  rr={'seed':seed,'leak_shift':sh,'thresholds':th,'reference_accuracy':float(np.mean(pred==y)),'policies':[]}
  for policy in ('dps_mono','dps_bi'):
   for rounding in ('trunc','rha'):
    rng=np.random.default_rng(123);ln=[Lanes(policy,8,rounding,len(x),w.shape[1],v,G=6) for w,v in zip(ws,th)]
    count=np.zeros((len(x),10),np.int64);badsp=badstate=0;maxerr=0.
    for t in range(32):
     sp=rng.random(x.shape)<x
     for li,(w,l) in enumerate(zip(ws,ln)):
      # Match reference floor leakage at exponent zero for both rounding modes.
      # At nonzero exponent, mantissa-domain leakage is itself approximate.
      if sh is not None:l.u=l.u-np.floor(l.u/(2**sh))
      for j in range(w.shape[0]):l.add(w[j],sp[:,j])
      sp=l.fire();l.maybe_shift_left()
      _,pre,refsp,new,rf=ref[t*2+li]
      exact=new-th[li]*rf;actual=l.membrane_real()
      badsp+=int(np.count_nonzero(sp!=rf));badstate+=int(np.count_nonzero(actual!=exact))
      maxerr=max(maxerr,float(abs(actual-exact).max()))
     count+=sp
    got=count.argmax(1)
    r={'policy':policy,'rounding':rounding,'accuracy':float(np.mean(got==y)),
       'prediction_disagreements':int(np.count_nonzero(got!=pred)),
       'spike_disagreements':badsp,'state_disagreements':badstate,'max_state_difference':maxerr,
       'upshift_events':sum(l.events for l in ln),'final_max_exponent':max(int(l.e.max()) for l in ln)}
    rr['policies'].append(r);print(sh,r,flush=True)
   
  out['models'].append(rr);(p.OUT/'exponent_matched.json').write_text(json.dumps(out,indent=2))
