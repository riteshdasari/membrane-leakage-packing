"""Untrained synthetic large-fan-in traces: range/burst stress, not task accuracy."""
import os,sys,json
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1';sys.dont_write_bytecode=True
import numpy as np
import probe as p
from promote_probe import seeded

def traces(fanin,mean,burst,shift):
 rng=np.random.default_rng(91);B,N=12,96
 w=np.clip(np.round(rng.normal(mean,1.6,(fanin,N))),-8,7).astype(np.int64)
 u=np.zeros((B,N),np.int64);rec=[];rates=[.05]*8 if not burst else [.01,.01,.6,.8,.01,.01,.6,.8]
 for rate in rates:
  sp=rng.random((B,fanin))<rate;pre=u-(u>>shift)
  new=pre+sp.astype(np.int64)@w;fired=new>=64;u=new-64*fired
  rec.append((0,pre,sp,new,fired))
 return [w],rec,rates

out={'note':__doc__,'models':[]}
for fan in (256,2304):
 for mean in (0.,.4):
  for burst in (False,True):
   ws,rec,rates=traces(fan,mean,burst,3);p.THRESHOLDS=[64]
   row={'fanin':fan,'weight_mean':mean,'rates':rates,'policies':[], 'promotion':[]}
   for slot in (6,8,10):
    for policy in ('margin','fixed'):
     row['policies'].append(p.characterize(rec,ws,slot,'serial',policy))
    row['promotion'].append(seeded(rec,ws,[64],slot))
   out['models'].append(row);(p.OUT/'stress.json').write_text(json.dumps(out,indent=2))
   print('STRESS',fan,mean,burst,[(r['slot'],r['policy'],round(r['dsp_work_ratio'],3),round(r['barrier_latency_ratio'],3)) for r in row['policies']],flush=True)
