"""Full 360-image inference with physical packed48 arithmetic, both exact engines.
All three saved models, IF/LIF, soft and hard reset. These are numerical engine
tests, not FPGA-host inference or measurements of SRAM system latency.
"""
import os,sys,json
os.environ['OPENBLAS_NUM_THREADS']='1';sys.dont_write_bytecode=True
import numpy as np
import probe as p
MASK=np.uint64((1<<48)-1);OFF=np.arange(6,dtype=np.uint64)*8
BIAS=np.sum(np.uint64(128)<<OFF,dtype=np.uint64)
def unpack(P):return ((P[:,:,None]>>OFF)&np.uint64(255)).astype(np.int64)-128
def packed(pre,sp,w,mode):
 B,N=pre.shape;G=(N+5)//6;pad=G*6-N
 wp=np.pad(w,((0,0),(0,pad))).reshape(w.shape[0],G,6)
 init=np.pad(pre,((0,0),(0,pad))).reshape(B,G,6)
 if mode==0:wide=init.copy();P=np.full((B,G),BIAS,np.uint64);active=np.ones((B,G),bool)
 else:
  active=((init>=-112)&(init<=111)).all(-1);wide=np.where(active[:,:,None],0,init)
  P=np.sum(((init+128).astype(np.uint64)&255)<<OFF,axis=-1,dtype=np.uint64)
  P=np.where(active,P,BIAS)
 flushes=0
 for j in range(w.shape[0]):
  # Signed weight word in a single physical ONE48 add, not independent lanes.
  word=np.sum(wp[j]*(np.int64(1)<<OFF.astype(np.int64)),axis=-1,dtype=np.int64).astype(np.uint64)
  use=sp[:,j,None]&active
  P=(P+np.where(use,word[None,:],np.uint64(0)))&MASK
  if mode==1:wide+=np.where((sp[:,j,None]&~active)[:,:,None],wp[j][None,:,:],0)
  fields=unpack(P);hit=active&((fields< -112)|(fields>111)).any(-1)
  if hit.any():
   wide+=np.where(hit[:,:,None],fields,0);P=np.where(hit,BIAS,P);flushes+=int(hit.sum())
   if mode==1:active&=~hit
  assert np.all((wide+unpack(P))>=-32768) and np.all((wide+unpack(P))<32768)
 return (wide+unpack(P)).reshape(B,-1)[:,:N],flushes

def run(ws,th,x,shift,hard,mode=None):
 rng=np.random.default_rng(123);u=[np.zeros((len(x),w.shape[1]),np.int64)for w in ws]
 cnt=np.zeros((len(x),10),np.int64);records=[];flushes=0
 for t in range(32):
  sp=rng.random(x.shape)<x
  for li,w in enumerate(ws):
   pre=u[li].copy()
   if shift is not None:pre-=pre>>shift
   if mode is None:new=pre+sp.astype(np.int64)@w
   else:new,f=packed(pre,sp,w,mode);flushes+=f
   fire=new>=th[li];u[li]=np.where(fire,0,new)if hard else new-th[li]*fire
   assert np.all(u[li]>=-32768)and np.all(u[li]<32768)
   records.append((u[li].copy(),fire.copy()));sp=fire
  cnt+=sp
 return cnt.argmax(1),records,flushes

if __name__=='__main__':
 setups=json.loads((p.OUT/'final_selected.json').read_text())['models'];out={'note':__doc__,'models':[]}
 for setup in setups:
  d=np.load(p.OUT/f"model_seed{setup['seed']}.npz");ws=[d['w0'],d['w1']];x,y=d['test_x'],d['test_y']
  for hard in (False,True):
   ref,rr,_=run(ws,setup['thresholds'],x,setup['leak_shift'],hard)
   for mode in (0,1):
    got,gr,fl=run(ws,setup['thresholds'],x,setup['leak_shift'],hard,mode)
    row={'seed':setup['seed'],'leak_shift':setup['leak_shift'],'hard_reset':hard,'mode':mode,'images':len(x),
         'accuracy':float(np.mean(got==y)),'reference_accuracy':float(np.mean(ref==y)),
         'prediction_disagreements':int(np.count_nonzero(got!=ref)),
         'state_disagreements':sum(int(np.count_nonzero(a[0]!=b[0]))for a,b in zip(rr,gr)),
         'spike_disagreements':sum(int(np.count_nonzero(a[1]!=b[1]))for a,b in zip(rr,gr)),
         'checkpoint_or_promotion_groups':fl}
    assert row['prediction_disagreements']==row['state_disagreements']==row['spike_disagreements']==0
    out['models'].append(row);(p.OUT/'exact_inference.json').write_text(json.dumps(out,indent=2));print(row,flush=True)
