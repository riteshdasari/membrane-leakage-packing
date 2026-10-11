"""Final registered-guard scheduling stress; synthetic, untrained traces."""
import os,sys,json
os.environ['OPENBLAS_NUM_THREADS']='1';sys.dont_write_bytecode=True
import numpy as np
import probe as p
out={'note':__doc__,'models':[]}
for mean in (0.,.4):
 rng=np.random.default_rng(91);B,N,F=12,96,2304
 w=np.clip(np.round(rng.normal(mean,1.6,(F,N))),-8,7).astype(np.int64)
 u=np.zeros((B,N),np.int64);rec=[]
 rates=[.01,.01,.6,.8,.01,.01,.6,.8]
 currents=[]
 for rate in rates:
  sp=rng.random((B,F))<rate;pre=u-(u>>3)
  cur=sp.astype(np.int64)@w;new=pre+cur;fire=new>=64;u=new-64*fire
  currents.append(cur);rec.append((0,pre,sp,new,fire))
 p.THRESHOLDS=[64]
 row={'fanin':F,'weight_mean':mean,'rates':rates,
      'current_min':int(min(c.min() for c in currents)),
      'current_max':int(max(c.max() for c in currents)),
      'policies':[p.characterize(rec,[w],8,'serial',pol) for pol in ('margin','pipe_margin','fixed')]}
 assert row['current_min']>=-2048 and row['current_max']<2048
 out['models'].append(row)
 print(mean,[(r['policy'],round(r['dsp_work_ratio'],4),round(r['selective_barrier_latency_ratio'],4),r['flushes']) for r in row['policies']],flush=True)
(p.OUT/'stress_selected.json').write_text(json.dumps(out,indent=2))
