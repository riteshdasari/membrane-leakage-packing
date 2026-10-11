"""Exact shared-offset arithmetic and range screen; no controller/RTL/performance claim."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
from pathlib import Path
import numpy as np,json,random
P=Path(__file__).resolve().parent;R=P/'results'
def physical(u,d):
 if min(u)>=-16 and max(u)<=15:b=-16
 else:
  assert len({x//32 for x in u})==1
  b=(u[0]//32)*32
 code=[x-b for x in u];assert all(0<=x<32 for x in code)
 a=code[0]+(code[1]<<10)+((code[2]-16)<<20)
 assert -(1<<24)<=a<(1<<24)
 p=(a*d+((16*d)<<20))&((1<<48)-1)
 products=[(p>>(10*i))&1023 for i in range(3)]
 assert products==[d*x for x in code]
 high=d*(b//16);q=high//16;rem=high&15
 # The base is a multiple of16, so the correction carry needs only4-bit addition.
 floor=[q+(v>>8)+((((v>>4)&15)+rem)>>4)for v in products]
 return [x-y for x,y in zip(u,floor)]
cases=0;rng=random.Random(44191)
for d in range(32):
 for x in range(-1024,1024):
  base=(x//32)*32;u=[x,base+rng.randrange(32),base+rng.randrange(32)]
  assert physical(u,d)==[-((-x*(256-d))//256)for x in u];cases+=1
 for x in range(-16,16):
  u=[x,15,-16];assert physical(u,d)==[-((-x*(256-d))//256)for x in u];cases+=1
for j in range(100000):
 d=rng.randrange(32);base=32*rng.randrange(-32,32);u=[base+rng.randrange(32)for _ in range(3)]
 assert physical(u,d)==[-((-x*(256-d))//256)for x in u];cases+=1
def count(g):
 zero=(g==0).all(-1);absfit=((g>=-16)&(g<=15)).all(-1)&~zero
 h=g>>5;hc=(h[...,0:1]==h[...,0:3]).all(-1)&(h[...,3:4]==h[...,3:6]).all(-1)
 a=((g[...,:3]>=-16)&(g[...,:3]<=15)).all(-1)
 b=((g[...,3:]>=-16)&(g[...,3:]<=15)).all(-1)
 c=(h[...,0:1]==h[...,0:3]).all(-1)
 d=(h[...,3:4]==h[...,3:6]).all(-1)
 combined=(a|c)&(b|d)&~zero
 return [int(zero.sum()),int(absfit.sum()),int((hc&~zero).sum()),int(combined.sum())]
rows=[]
for cfg in json.loads((R/'final_selected.json').read_text())['models']:
 for hard in [False,True]:
  data=np.load(R/f"model_seed{cfg['seed']}.npz");x=data['test_x'];w=[data['w0'],data['w1']]
  state=[np.zeros((len(x),a.shape[1]),np.int64)for a in w];rngnp=np.random.default_rng(123)
  total=0;counts=np.zeros(4,np.int64)
  for t in range(32):
   sp=rngnp.random(x.shape)<x
   for li,a in enumerate(w):
    old=state[li];blocks=(a.shape[1]+5)//6;g=np.pad(old,((0,0),(0,blocks*6-a.shape[1]))).reshape(len(x),blocks,6)
    total+=len(x)*blocks;counts+=count(g)
    leaked=old-(25*old//256);nxt=leaked+sp.astype(np.int64)@a;fire=nxt>=cfg['thresholds'][li]
    state[li]=np.where(fire,0,nxt)if hard else nxt-fire*cfg['thresholds'][li];sp=fire
  z,oldfit,coh,newfit=map(int,counts);assert newfit>=oldfit
  rows.append(dict(seed=cfg['seed'],saved_leak_shift=cfg['leak_shift'],hard_reset=hard,groups=total,zero_groups=z,
   original_narrow_nonzero_groups=oldfit,coherent_only_nonzero_groups=coh,combined_narrow_nonzero_groups=newfit,
   original_ideal_issue_saving=oldfit/(3*(total-z)),combined_ideal_issue_saving=newfit/(3*(total-z))))
stress=[];g=np.load(R/'adaptive_delta_stress_25_1/expected.npz')['groups'].astype(np.int64)
for m in json.loads((R/'adaptive_delta_stress_input.json').read_text()):
 z,oldfit,coh,newfit=count(g[m['start']:m['start']+m['groups']]);stress.append(dict(hard_reset=m['hard_reset'],groups=m['groups'],zero_groups=z,
  original_narrow_nonzero_groups=oldfit,coherent_only_nonzero_groups=coh,combined_narrow_nonzero_groups=newfit,
  original_ideal_issue_saving=oldfit/(3*(m['groups']-z)),combined_ideal_issue_saving=newfit/(3*(m['groups']-z))))
result=dict(arithmetic_cases=cases,arithmetic_failures=0,rows=rows,stress=stress,
 formula='Choose b=-16 for an int5 triple, else b=32*(U0//32) when all three upper parts agree. U=b+r, 0<=r<32; pack three delta*r products; exact floor correction uses one shared delta*b/256 quotient and a4-bit carry per lane.',
 limitations=['Arithmetic and opportunity screen only; no RTL, area, timing or overhead for the offset controller',
 'Three full-range fixed residue packing with per-lane high corrections remains a necessary comparison',
 'Correlated synthetic bursts have identical lanes in early phases; the larger stress opportunity is not evidence of natural-model burst acceleration',
 'More eligible groups do not establish a net latency/resource gain'])
(R/'shared_offset_delta_screen.json').write_text(json.dumps(result,indent=2))
print(json.dumps(dict(arithmetic_cases=cases,arithmetic_failures=0,
 original_issue_range=[min(r['original_ideal_issue_saving']for r in rows),max(r['original_ideal_issue_saving']for r in rows)],
 combined_issue_range=[min(r['combined_ideal_issue_saving']for r in rows),max(r['combined_ideal_issue_saving']for r in rows)],stress=stress),indent=2),flush=True)
