"""Ideal lower-bound cost of membrane-seeded narrow packing with whole-group promotion.
The wide fallback is assumed to process ceil(n/4) passes per event; packing mode routing
and reload costs are NOT synthesized and would increase these estimates.
"""
import os,sys,json
os.environ['OPENBLAS_NUM_THREADS']='1'; os.environ['OMP_NUM_THREADS']='1'
sys.dont_write_bytecode=True
import numpy as np
import probe as p
from pathlib import Path

def seeded(records,ws,thresholds,slot):
 n=48//slot; actual=max(int(abs(w).max()) for w in ws);margin=1<<actual.bit_length(); bias=1<<(slot-1)
 low=-bias+margin; high=bias-margin-1
 st=dict(slot=slot,lanes=n,initial_groups=0,initial_narrow=0,promoted=0,
         events=0,narrow_events=0,ideal_cycles=0,baseline_cycles=0,mismatches=0)
 for li,pre,sp,new,fired in records:
  pre,sp,new=pre[:48],sp[:48],new[:48]; B,N=pre.shape; G=(N+n-1)//n
  pad=G*n-N; wp=np.pad(ws[li],((0,0),(0,pad))).reshape(ws[li].shape[0],G,n)
  initial=np.pad(pre,((0,0),(0,pad))).reshape(B,G,n)
  narrow=((initial>=low)&(initial<=high)).all(-1)
  chunk=np.where(narrow[...,None],initial,0); wide=np.where(narrow[...,None],0,initial)
  st['initial_groups']+=B*G; st['initial_narrow']+=int(narrow.sum())
  cyc=0; numevents=0
  for j in range(wp.shape[0]):
   active=sp[:,j,None]; delta=active[...,None]*wp[j][None]
   st['events']+=int(active.sum())*G; st['narrow_events']+=int((active&narrow).sum())
   cyc+=int((active*narrow).sum())+int((active&~narrow).sum())*((n+3)//4)
   chunk+=np.where(narrow[...,None],delta,0); wide+=np.where(narrow[...,None],0,delta)
   hit=narrow&((chunk<low)|(chunk>high)).any(-1)
   if hit.any():
    assert np.all(chunk>=-bias) and np.all(chunk<bias)
    wide+=np.where(hit[...,None],chunk,0); chunk=np.where(hit[...,None],0,chunk)
    narrow=narrow&~hit; st['promoted']+=int(hit.sum());cyc+=int(hit.sum())*(n+1)
   numevents+=int(active.sum())
  st['mismatches']+=int(np.count_nonzero((wide+chunk).reshape(B,-1)[:,:N]!=new))
  st['ideal_cycles']+=cyc+B*G*(n+1)
  bg=(N+3)//4; st['baseline_cycles']+=numevents*bg+B*bg*5
 st['initial_fit']=st['initial_narrow']/st['initial_groups']
 st['narrow_event_fraction']=st['narrow_events']/st['events']
 st['ideal_dsp_work_ratio']=st['ideal_cycles']/st['baseline_cycles']
 return st

if __name__=='__main__':
 out={'note':__doc__,'models':[]}
 for seed in (0,1,2):
  xc,yc,xt,yt,w1,w2=p.model(seed); scales=[abs(w).max()/7 for w in (w1,w2)]
  ws=[np.round(w/s).astype(np.int64) for w,s in zip((w1,w2),scales)]
  for sh in (1,3,None):
   th=p.tune(ws,xc,yc,w1,w2,scales,sh); pred,rec=p.reference(ws,th,xt,sh)
   row={'seed':seed,'leak_shift':sh,'policies':[seeded(rec,ws,th,s) for s in (6,7,8,9,10)]}
   # A common exact downshift must also represent every possible incoming weight exactly.
   row['all_weights_even_fraction']=float(np.mean(np.all(ws[0]%2==0,axis=0)))
   out['models'].append(row)
   (p.OUT/'promotion.json').write_text(json.dumps(out,indent=2))
   print('PROMOTION',seed,sh,[(r['slot'],round(r['initial_fit'],3),round(r['narrow_event_fraction'],3),round(r['ideal_dsp_work_ratio'],3)) for r in row['policies']],flush=True)
