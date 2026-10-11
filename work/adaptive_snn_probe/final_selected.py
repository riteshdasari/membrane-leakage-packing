"""Refresh final scheduling models for the final registered-warning implementation."""
import os,sys,json
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1';sys.dont_write_bytecode=True
import numpy as np
import probe as p
from promote_probe import seeded
out={'note':'Three trained digits models. Scheduling statistics use first 48 test examples; reference classification uses all 360. Costs are optimistic core schedules, not full accelerator measurements. Registered guard modeled conservatively with immediate warning at two-event headroom.', 'models':[]}
for seed in (0,1,2):
 xc,yc,xt,yt,w1,w2=p.model(seed);scales=[abs(w).max()/7 for w in (w1,w2)]
 ws=[np.round(w/s).astype(np.int64) for w,s in zip((w1,w2),scales)]
 np.savez_compressed(p.OUT/f'model_seed{seed}.npz',w0=ws[0],w1=ws[1],test_x=xt,test_y=yt)
 for sh in (1,3,None):
  th=p.tune(ws,xc,yc,w1,w2,scales,sh);pred,rec=p.reference(ws,th,xt,sh);p.THRESHOLDS=th
  row={'seed':seed,'leak_shift':sh,'thresholds':th,'reference_accuracy':float(np.mean(pred==yt)),
       'policies':[p.characterize(rec,ws,8,'serial',policy) for policy in ('margin','pipe_margin','fixed')],
       'promotion':seeded(rec,ws,th,8)}
  out['models'].append(row);(p.OUT/'final_selected.json').write_text(json.dumps(out,indent=2))
  print('SELECTED',seed,sh,[(r['policy'],round(r['dsp_work_ratio'],3),round(r['selective_barrier_latency_ratio'],3))for r in row['policies']],flush=True)
