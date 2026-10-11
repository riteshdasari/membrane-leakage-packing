"""Pre-RTL mechanism screen: persistent packing oracle and exact hard-reset retirement.
No new data, training, downloads, area estimates or FireFly reproduction.
"""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import numpy as np
from pathlib import Path
import json,time,ctypes
P=Path(__file__).resolve().parent;R=P/'results'
BITS=np.array([6,8,12,16]);LANES=48//BITS
def width(lo,hi):
 assert np.all(lo>=-32768)and np.all(hi<=32767)
 return np.where((lo>=-32)&(hi<32),0,np.where((lo>=-128)&(hi<128),1,np.where((lo>=-2048)&(hi<2048),2,3)))
def reset_bounds(lo,hi,th,hard):
 cross=(lo<th)&(hi>=th)
 if hard:return np.minimum(lo,0),np.where(hi<th,hi,np.maximum(0,th-1))
 return np.where(cross,np.minimum(lo,0),np.where(lo>=th,lo-th,lo)),np.where(cross,np.maximum(th-1,hi-th),np.where(hi>=th,hi-th,hi))
def run(setup,hard):
 d=np.load(R/f"model_seed{setup['seed']}.npz")
 ws=[d['w0'].astype(np.int64),d['w1'].astype(np.int64)];x=d['test_x'];y=d['test_y'];B=len(x)
 U=[np.zeros((B,w.shape[1]),np.int64)for w in ws];cnt=np.zeros((B,10),np.int64);rng=np.random.default_rng(123)
 shifts=setup['leak_shift'];data=[]
 for li,w in enumerate(ws):
  I,N=w.shape;L=np.minimum(w,0).sum(0);H=np.maximum(w,0).sum(0)
  # Weight-only finite-horizon proof, including all accumulation prefixes and leak.
  lo=np.zeros(N,np.int64);hi=lo.copy();globlo=lo.copy();globhi=hi.copy()
  for t in range(32):
   if shifts is not None:lo=lo-(lo>>shifts);hi=hi-(hi>>shifts)
   vl=lo+L;vh=hi+H;globlo=np.minimum(globlo,vl);globhi=np.maximum(globhi,vh)
   lo,hi=reset_bounds(vl,vh,setup['thresholds'][li],hard)
   globlo=np.minimum(globlo,lo);globhi=np.maximum(globhi,hi)
  data.append(dict(layer=li,N=N,I=I,cert=width(globlo,globhi),trace_lo=np.zeros(N,np.int64),trace_hi=np.zeros(N,np.int64),
   modes=[],safe_modes=[],end_modes=[],pairs=[],previous=None,changes=0,safe_previous=None,safe_changes=0,group_steps=0,
   retirement={str(k):{name:dict(baseline_lane_events=0,remaining_lane_events=0,baseline_group_pairs=0,remaining_group_pairs=0,checks_group=0,early_neurons=0,neurons=0)
    for name in ['weight_only','active_negative_oracle']}for k in [2,8,16]}, mismatches=0))
 for t in range(32):
  sp=rng.random(x.shape)<x
  for li,w in enumerate(ws):
   dd=data[li];I,N=w.shape;old=U[li].copy();pre=old.copy();th=setup['thresholds'][li]
   if shifts is not None:pre-=pre>>shifts
   pref=np.zeros((B,I+1,N),np.int64);np.cumsum(sp[:,:,None]*w[None,:,:],axis=1,out=pref[:,1:])
   full=pre+sp.astype(np.int64)@w
   assert np.array_equal(full,pre+pref[:,-1])
   fire=full>=th;post=np.where(fire,0,full)if hard else full-fire*th
   low=np.minimum.reduce([old,post,pre+pref.min(1)]);high=np.maximum.reduce([old,post,pre+pref.max(1)])
   mode=width(low,high);assert np.all(mode<=dd['cert'])
   # Causal width: current membrane plus all possible weight prefixes.
   safe=width(np.minimum.reduce([old,pre+np.minimum(w,0).sum(0),np.zeros_like(old)]),
              np.maximum.reduce([old,pre+np.maximum(w,0).sum(0),np.zeros_like(old)]))
   assert np.all(mode<=safe)and np.all(safe<=dd['cert'])
   dd['trace_lo']=np.minimum(dd['trace_lo'],low.min(0));dd['trace_hi']=np.maximum(dd['trace_hi'],high.max(0))
   dd['modes'].append(mode);dd['safe_modes'].append(safe);dd['end_modes'].append(width(post,post));dd['pairs'].append((sp.sum(1)+1)//2)
   gm=np.stack([mode[:,g:g+24].max(1)for g in range(0,N,24)],axis=1)
   if dd['previous']is not None:dd['changes']+=int((gm!=dd['previous']).sum())
   dd['group_steps']+=gm.size;dd['previous']=gm
   sm=np.stack([safe[:,g:g+24].max(1)for g in range(0,N,24)],axis=1)
   if dd['safe_previous']is not None:dd['safe_changes']+=int((sm!=dd['safe_previous']).sum())
   dd['safe_previous']=sm
   if hard:
    events=np.concatenate([np.zeros((B,1),np.int64),np.cumsum(sp,axis=1)],axis=1)
    neg=np.minimum(w,0);suf=np.concatenate([np.cumsum(neg[::-1],axis=0)[::-1],np.zeros((1,N),np.int64)])
    # Upper opportunity diagnostic: needs all future active negative contributions.
    an=np.zeros((B,I+1,N),np.int64);np.cumsum(sp[:,:,None]*neg[None,:,:],axis=1,out=an[:,1:])
    for k in [2,8,16]:
     js=np.array(list(range(0,I,k))+[I])
     for name in ['weight_only','active_negative_oracle']:
      bound=suf[js][None,:,:]if name=='weight_only'else an[:,-1:, :]-an[:,js,:]
      yes=pre[:,None,:]+pref[:,js,:]+bound>=th
      found=yes.any(1);first=yes.argmax(1);stop=np.where(found,js[first],I)
      consumed=np.take_along_axis(events,stop,axis=1)
      # Independently construct retired output: all omitted updates ignored only
      # when a certificate proves hard-reset state and boundary-time spike.
      partial=np.take_along_axis(pref,stop[:,None,:],axis=1)[:,0,:]+pre
      altfire=np.where(found,True,partial>=th);altpost=np.where(altfire,0,partial)
      assert np.array_equal(altfire,fire)and np.array_equal(altpost,post)
      ss=dd['retirement'][str(k)][name]
      ss['baseline_lane_events']+=int(events[:,-1].sum())*N
      ss['remaining_lane_events']+=int(consumed.sum())
      ss['early_neurons']+=int((stop<I).sum());ss['neurons']+=B*N
      # Fixed contiguous six-lane packets: only complete packet retirement
      # shortens service. Free lane refill assumes zero gather/weight cost.
      for g in range(0,N,6):
       groupstop=stop[:,g:g+6].max(1)
       needed=events[np.arange(B),groupstop]
       ss['baseline_group_pairs']+=int(((events[:,-1]+1)//2).sum())
       ss['remaining_group_pairs']+=int(((needed+1)//2).sum())
       # One extra unhidden check per packet at each visited pre-final boundary;
       # zero-spike timesteps bypass this cost, an optimistic assumption.
       ss['checks_group']+=int(((js[:-1][None,:]<=groupstop[:,None])&(events[:,-1,None]>0)).sum())
   U[li]=post;sp=fire
  cnt+=sp
 layers=[]
 for dd in data:
  N=dd['N'];modes=np.stack(dd['modes']);safe=np.stack(dd['safe_modes']);ends=np.stack(dd['end_modes']);pairs=np.stack(dd['pairs'])
  observed=width(dd['trace_lo'],dd['trace_hi']);cert=dd['cert']
  metrics=dict(oracle_group_compute=0,trace_fixed_group_compute=0,cert_fixed_group_compute=0,
   fixed8_current_compute=0,oracle_group_state_bits=0,trace_fixed_group_state_bits=0,cert_fixed_group_state_bits=0,
   certified_group_compute=0,certified_group_state_bits=0,fixed8_current_seeds=0,ideal_wide_merge_work=0)
  for g in range(0,N,24):
   n=min(24,N-g);gm=modes[:,:,g:g+n].max(2);em=ends[:,:,g:g+n].max(2)
   trace=int(observed[g:g+n].max());proof=int(cert[g:g+n].max())
   sm=safe[:,:,g:g+n].max(2)
   metrics['oracle_group_compute']+=int((pairs*((n+LANES[gm]-1)//LANES[gm])).sum())
   metrics['trace_fixed_group_compute']+=int(pairs.sum())*int(np.ceil(n/LANES[trace]))
   metrics['cert_fixed_group_compute']+=int(pairs.sum())*int(np.ceil(n/LANES[proof]))
   metrics['fixed8_current_compute']+=int(pairs.sum())*int(np.ceil(n/6))
   metrics['fixed8_current_seeds']+=int((pairs>0).sum())*int(np.ceil(n/6))
   metrics['ideal_wide_merge_work']+=int((pairs>0).sum())*int(np.ceil(n/3))
   metrics['certified_group_compute']+=int((pairs*((n+LANES[sm]-1)//LANES[sm])).sum())
   metrics['certified_group_state_bits']+=int((BITS[sm]*n+2).sum())
   metrics['oracle_group_state_bits']+=int((n*BITS[em]+2).sum())
   metrics['trace_fixed_group_state_bits']+=int(BITS[trace])*n*32*B
   metrics['cert_fixed_group_state_bits']+=int(BITS[proof])*n*32*B
  metrics.update(oracle_per_neuron_state_bits=int((BITS[ends]+2).sum()),fixed16_state_bits=16*N*32*B,
   format_changes=dd['changes'],certified_format_changes=dd['safe_changes'],group_steps=dd['group_steps'],
   oracle_compute_plus_one_per_change=metrics['oracle_group_compute']+dd['changes'],
   trace_width_hist=np.bincount(observed,minlength=4).tolist(),cert_width_hist=np.bincount(cert,minlength=4).tolist(),
   oracle_width_hist=np.bincount(modes.ravel(),minlength=4).tolist())
  for k in dd['retirement'].values():
   for ss in k.values():
    if ss['baseline_lane_events']:
     ss['free_refill_event_saving']=1-ss['remaining_lane_events']/ss['baseline_lane_events']
     ss['whole_group_pair_saving']=1-ss['remaining_group_pairs']/ss['baseline_group_pairs']
     ss['speed_with_one_check_cycle']=ss['baseline_group_pairs']/(ss['remaining_group_pairs']+ss['checks_group'])
  layers.append(dict(layer=dd['layer'],neurons=N,fanin=dd['I'],persistent=metrics,retirement=dd['retirement']if hard else None))
 return dict(seed=setup['seed'],leak_shift=shifts,hard_reset=hard,images=B,steps=32,accuracy=float((cnt.argmax(1)==y).mean()),layers=layers,exact_retirement_mismatches=0)

def audit():
 rng=np.random.default_rng(654);checks=0;retired=0
 for _ in range(1000):
  w=rng.integers(-8,8,(32,12));sp=rng.integers(0,2,32);pre=rng.integers(-100,100,12);th=35
  pref=np.concatenate([np.zeros((1,12),np.int64),np.cumsum(w*sp[:,None],axis=0)])
  suf=np.concatenate([np.cumsum(np.minimum(w,0)[::-1],axis=0)[::-1],np.zeros((1,12),np.int64)])
  final=pre+pref[-1]
  for j in range(0,33,2):
   done=pre+pref[j]+suf[j]>=th
   assert np.all(final[done]>=th);retired+=int(done.sum());checks+=12
 # Immediate threshold crossing alone is unsafe, and soft reset needs residual.
 assert 12>=10 and 12-5<10
 assert (12+5-10)!=(12-10)
 return dict(random_certificate_lane_checks=checks,certified_lane_checks=retired,failures=0,
  inhibitory_counterexample=dict(partial=12,threshold=10,remaining=-5,final=7),
  soft_reset_counterexample=dict(partial=12,threshold=10,remaining=5,correct_residual=7,discarded_residual=2))
if __name__=='__main__':
 class Mem(ctypes.Structure):
  _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong),('total',ctypes.c_ulonglong),('free',ctypes.c_ulonglong),('rest',ctypes.c_ulonglong*5)]
 m=Mem();m.length=ctypes.sizeof(m);ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
 print('Free RAM GiB',m.free/2**30,flush=True);assert m.free>700*2**20
 result=dict(note=__doc__,widths=BITS.tolist(),audit=audit(),models=[]);start=time.time()
 refs=json.loads((R/'exact_inference.json').read_text())['models']
 for setup in json.loads((R/'final_selected.json').read_text())['models']:
  for hard in [False,True]:
   row=run(setup,hard)
   ref=next(x for x in refs if x['seed']==row['seed']and x['leak_shift']==row['leak_shift']and x['hard_reset']==hard and x['mode']==0)
   assert abs(ref['accuracy']-row['accuracy'])<1e-12
   result['models'].append(row);(R/'simple_membrane_hypotheses.json').write_text(json.dumps(result,indent=2))
   print('PASS',row['seed'],row['leak_shift'],hard,'accuracy',round(row['accuracy'],4),'seconds',round(time.time()-start,1),flush=True)
 print('COMPLETE',flush=True)
