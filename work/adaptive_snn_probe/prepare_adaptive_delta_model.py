"""Saved-model integer trajectories, complete grouping and conservative schedule proxies."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
from pathlib import Path
import json,numpy as np,random
P=Path(__file__).resolve().parent;R=P/'results'
configs=json.loads((R/'final_selected.json').read_text())['models']
profile=[];traces=[];trace_metadata=[];ledger=[]
for cfg in configs:
 for hard in [False,True]:
  d=np.load(R/f"model_seed{cfg['seed']}.npz");x=d['test_x'];y=d['test_y'];w=[d['w0'],d['w1']]
  u=[np.zeros((len(x),a.shape[1]),np.int64)for a in w];cnt=np.zeros((len(x),10),np.int64)
  rng=np.random.default_rng(123);ng=zero=narrow=events=finish=0;lo=hi=0;by_image=np.zeros((len(x),3),np.int64)
  capture=cfg['leak_shift']==3 and not hard
  trace_start=len(traces)
  for t in range(32):
   sp=rng.random(x.shape)<x
   for li,a in enumerate(w):
    old=u[li];lo=min(lo,int(old.min()));hi=max(hi,int(old.max()))
    assert int(old.min())>=-1024 and int(old.max())<=1023,'Saved beta231 membrane exceeds declared wide format'
    n=a.shape[1];blocks=(n+5)//6;pad=blocks*6-n
    groups=np.pad(old,((0,0),(0,pad))).reshape(len(x),blocks,6)
    zg=(groups==0).all(-1);fit=((groups>=-16)&(groups<=15)).all(-1)&~zg
    ng+=len(x)*blocks;zero+=int(zg.sum());narrow+=int(fit.sum())
    pair_events=(sp.sum(-1)+1)//2
    events+=int(pair_events.sum())*blocks;finish+=len(x)*blocks
    by_image[:,0]+=(6-zg.astype(np.int64)*5-fit.astype(np.int64)).sum(-1)
    by_image[:,1]+=(6-zg.astype(np.int64)*5).sum(-1)
    by_image[:,2]+=blocks*(pair_events+1)
    current=sp.astype(np.int64)@a
    leaked=-((-old*231)//256);nxt=leaked+current;fire=nxt>=cfg['thresholds'][li]
    u[li]=np.where(fire,0,nxt)if hard else nxt-fire*cfg['thresholds'][li]
    if capture:
     # First 48 images, every neuron including padded final groups. No range selection.
     for image in range(48):
      ledger.append(dict(seed=cfg['seed'],t=t,layer=li,image=image,start=len(traces),blocks=blocks,
       neurons=n,threshold=cfg['thresholds'][li],current=current[image].tolist(),
       expected_state=u[li][image].tolist(),expected_spikes=fire[image].astype(int).tolist()))
      traces.extend(groups[image].tolist())
    sp=fire
   cnt+=sp
  row=dict(seed=cfg['seed'],saved_leak_shift=cfg['leak_shift'],thresholds=cfg['thresholds'],hard_reset=hard,
   beta=231,changed_dynamics=True,images=len(x),accuracy=float(np.mean(cnt.argmax(1)==y)),
   preleak_min=lo,preleak_max=hi,groups=ng,zero_groups=zero,narrow_nonzero_groups=narrow,
   fixed_issue_slots=3*(ng-zero),adaptive_issue_slots=3*(ng-zero)-narrow,
   fixed_complete_group_cycles=6*(ng-zero)+zero,adaptive_complete_group_cycles=6*(ng-zero)+zero-narrow,
   common_pair_add_proxy_cycles=events,common_threshold_reset_proxy_cycles=finish)
  row['issue_saving']=narrow/(3*(ng-zero));row['complete_group_cycle_saving']=narrow/row['fixed_complete_group_cycles']
  row['total_update_proxy_saving']=narrow/(row['fixed_complete_group_cycles']+events+finish)
  row['per_image_group_cycles_p95_adaptive']=float(np.percentile(by_image[:,0],95))
  row['per_image_group_cycles_p95_fixed']=float(np.percentile(by_image[:,1],95))
  profile.append(row)
  if capture:trace_metadata.append(dict(seed=cfg['seed'],start=trace_start,groups=len(traces)-trace_start,
   sampled_images=48,all_images=len(x),all_images_reference_accuracy=row['accuracy'],
   sampled_reference_accuracy=float(np.mean(cnt[:48].argmax(1)==y[:48])),labels=y[:48].tolist(),
   expected_counts=cnt[:48].tolist(),preleak_min=lo,preleak_max=hi))
wd=R/'adaptive_delta_model_25_1';wd.mkdir(exist_ok=True)
def pack(u):return sum((int(x)&2047)<<(11*i)for i,x in enumerate(u))
(wd/'stim.txt').write_text(str(len(traces))+'\n'+'\n'.join(f'0 25 {pack(u):x}'for u in traces)+'\n')
np.savez_compressed(wd/'expected.npz',groups=np.array(traces,dtype=np.int16))
(R/'adaptive_delta_model_input.json').write_text(json.dumps(dict(metadata=trace_metadata,ledger=ledger),separators=(',',':')))
(R/'adaptive_delta_profile.json').write_text(json.dumps(dict(rows=profile,
 notes=['Beta231 changes saved model dynamics; no retraining','Every neuron is counted; incomplete groups padded with zero',
 'Complete-group cycle formula is for the tested MP1, one-group-at-a-time interface, without intergroup overlap',
 'Total-update proxy adds one cycle per paired active input and one threshold/reset cycle for each six-neuron block; these are not full-neuron RTL timing results']),indent=2))
print(dict(model_rows=len(profile),rtl_trace_groups=len(traces),issue_saving_range=[min(r['issue_saving']for r in profile),max(r['issue_saving']for r in profile)],
 group_cycle_saving_range=[min(r['complete_group_cycle_saving']for r in profile),max(r['complete_group_cycle_saving']for r in profile)],
 total_proxy_saving_range=[min(r['total_update_proxy_saving']for r in profile),max(r['total_update_proxy_saving']for r in profile)]),flush=True)
# Six-neuron stress streams: empty/sparse steps and signed bursts, both reset modes.
rng=random.Random(8912);stress=[];stress_meta=[]
for hard in [False,True]:
 state=[0]*6;begin=len(stress);narrow=zero=pair_add=0
 for t in range(320):
  stress.append(state[:]);zero+=int(all(x==0 for x in state));narrow+=int(all(-16<=x<=15 for x in state)and any(state))
  state=[x-25*x//256 for x in state];n=[0,1,2,4][t%4];pair_add+=n
  for j in range(n):
   phase=t//40%4
   a=[-8 if phase==0 else 7 if phase==1 else rng.randrange(-8,8)for _ in range(6)]
   b=[-8 if phase==0 else 7 if phase==1 else rng.randrange(-8,8)for _ in range(6)]
   state=[x+y+z for x,y,z in zip(state,a,b)]
  state=[(0 if hard else x-35)if x>=35 else x for x in state]
  assert all(-1024<=x<=1023 for x in state)
 stress_meta.append(dict(hard_reset=hard,start=begin,groups=320,narrow_groups=narrow,zero_groups=zero,
  fixed_group_cycles=6*(320-zero)+zero,adaptive_group_cycles=6*(320-zero)+zero-narrow,
  common_add_cycles=pair_add,common_finish_cycles=320))
wd=R/'adaptive_delta_stress_25_1';wd.mkdir(exist_ok=True)
(wd/'stim.txt').write_text(str(len(stress))+'\n'+'\n'.join(f'0 25 {pack(u):x}'for u in stress)+'\n')
np.savez_compressed(wd/'expected.npz',groups=np.array(stress,dtype=np.int16))
(R/'adaptive_delta_stress_input.json').write_text(json.dumps(stress_meta,indent=2))
