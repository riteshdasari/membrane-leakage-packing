"""Lightweight saved-model range/accuracy screen. Not RTL or a scheduler model."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
from pathlib import Path
import numpy as np,json,ctypes
P=Path(__file__).resolve().parent;R=P/'results'
class Mem(ctypes.Structure):
 _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong),('total',ctypes.c_ulonglong),('free',ctypes.c_ulonglong),('rest',ctypes.c_ulonglong*5)]
m=Mem();m.length=ctypes.sizeof(m);ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m));print('Free GiB',m.free/2**30,flush=True);assert m.free>1.0*2**30
def physical(u,b):
 # Fixed exact low-int8 packing plus integer high correction. Wide correction
 # here is software int64; only the int10 version has the companion RTL.
 B,N=u.shape;pad=N%2;v=np.pad(u,((0,0),(0,pad))).reshape(B,-1,2)
 r=(v+128)%256-128;h=(v-r)//256;q=(r+128).astype(np.uint64)
 k=128*(256-b)+255;p=(q[:,:,0]+(q[:,:,1]<<np.uint64(16)))*np.uint64(b)+np.uint64(k+(k<<16))
 low=np.stack([(p>>np.uint64(o)&np.uint64(255)).astype(np.int64)-128 for o in [8,24]],axis=-1)
 return (low+h*b).reshape(B,-1)[:,:N]
def run(w,th,x,y,b,hard):
 u=[np.zeros((len(x),a.shape[1]),np.int64)for a in w];cnt=np.zeros((len(x),10),np.int64)
 rng=np.random.default_rng(123);groups=fit3=fit5=fit8=zeros=0;low=high=0;bad=0;outside10=0
 for t in range(32):
  sp=rng.random(x.shape)<x
  for li,a in enumerate(w):
   old=u[li];low=min(low,int(old.min()));high=max(high,int(old.max()))
   outside10+=int(np.count_nonzero((old< -512)|(old>511)))
   n=(old.shape[1]//6)*6
   if n:
    g=old[:,:n].reshape(len(x),-1,6);groups+=g.shape[0]*g.shape[1]
    fit3+=int(((g>=-4)&(g<=3)).all(-1).sum());fit5+=int(((g>=-16)&(g<=15)).all(-1).sum());fit8+=int(((g>=-128)&(g<=127)).all(-1).sum());zeros+=int((g==0).all(-1).sum())
   ref=-((-old*b)//256);got=physical(old,b);bad+=int(np.count_nonzero(got!=ref));assert np.array_equal(got,ref)
   nxt=got+sp.astype(np.int64)@a;fire=nxt>=th[li];u[li]=np.where(fire,0,nxt)if hard else nxt-fire*th[li];sp=fire
  cnt+=sp
 return dict(accuracy=float(np.mean(cnt.argmax(1)==y)),integer_leak_mismatches=bad,preleak_min=low,preleak_max=high,
  preleak_values_outside_int10=outside10,groups6=groups,narrow3_groups=fit3,narrow5_groups=fit5,narrow8_groups=fit8,zero_groups=zeros,
  narrow3_nonzero_fraction=(fit3-zeros)/groups,narrow8_fraction=fit8/groups,
  ideal_three_vs_two_leak_issue_saving_excluding_zero=(fit3-zeros)/(3*(groups-zeros))if groups>zeros else 0,
  delta25_three_vs_two_ideal_saving=(fit5-zeros)/(3*(groups-zeros))if b==231 and groups>zeros else None)
rows=[]
for cfg in json.loads((R/'final_selected.json').read_text())['models']:
 d=np.load(R/f"model_seed{cfg['seed']}.npz");ws=[d['w0'],d['w1']]
 original=256 if cfg['leak_shift']is None else 256-(256>>cfg['leak_shift'])
 for hard in [False,True]:
  for coef in sorted(set([original,231])):
   result=run(ws,cfg['thresholds'],d['test_x'],d['test_y'],coef,hard)
   row=dict(seed=cfg['seed'],original_beta=original,beta=coef,changed_dynamics=coef!=original,hard_reset=hard,images=len(d['test_x']),thresholds=cfg['thresholds'],**result);rows.append(row)
(R/'leak_adaptation_screen.json').write_text(json.dumps(dict(note=__doc__,limitations=['Changing beta changes the model; weights were not retrained','Range fractions are numerical opportunities, not measured adaptive latency','Zero groups should be skipped by a strong fixed baseline too','Int64 high correction is not hardware proof outside signed int10'],rows=rows),indent=2))
print(dict(rows=len(rows),mismatches=sum(r['integer_leak_mismatches']for r in rows),delta25_saving_range=[min(r['delta25_three_vs_two_ideal_saving']for r in rows if r['beta']==231),max(r['delta25_three_vs_two_ideal_saving']for r in rows if r['beta']==231)]),flush=True)
