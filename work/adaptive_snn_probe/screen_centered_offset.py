"""Single centered-bin monitor, shared exact high correction; arithmetic screen."""
from pathlib import Path
import json,random,numpy as np
from check_stream_offset import policy
P=Path(__file__).resolve().parent;R=P/'results'
def physical(u,d):
 h=[(v+16)//32 for v in u];assert h[0]==h[1]==h[2]
 r=[v-32*h[0]for v in u];assert all(-16<=v<=15 for v in r)
 k=512-16*d;a=(r[0]+16)+((r[1]+16)<<10)+(r[2]<<20)
 p=(a*d+k+(k<<10))&((1<<48)-1);hp=d*h[0]
 high=32*h[0]-hp//8;frac=hp%8;answer=[]
 for l in range(3):
  field=(p>>(10*l))&1023
  floor=(field>>8)-(2 if l<2 else(4 if field>=512 else 0))
  carry=(((field>>5)&7)+frac)>>3
  answer.append(high+r[l]-floor-carry)
 return answer
rg=random.Random(9118);cases=0
for d in range(32):
 for x in range(-1024,1024):
  h=(x+16)//32
  legal=[v for v in range(max(-1024,32*h-16),min(1023,32*h+15)+1)]
  u=[x,rg.choice(legal),rg.choice(legal)]
  assert physical(u,d)==[-((-v*(256-d))//256)for v in u];cases+=1
for j in range(100000):
 d=rg.randrange(32);h=rg.randrange(-31,32);u=[32*h+rg.randrange(-16,16)for _ in range(3)]
 assert physical(u,d)==[-((-v*(256-d))//256)for v in u];cases+=1
def requests(u,centered):
 pos=total=0
 while pos<len(u):
  if centered:
   window=u[pos:pos+3];n=len(window)
   eligible=n==3 and len({(v+16)//32 for v in window})==1
   take=3 if n==3 and(eligible or not any(window)or window[2]==0)else min(2,n)
  else:take=policy(u[pos:],25,0)[0]
  pos+=take;total+=1
 return total
original=np.load(R/'adaptive_delta_model_25_1/expected.npz')['groups']
ledger=json.loads((R/'adaptive_delta_model_input.json').read_text())['ledger']
old=new=0
for rec in ledger:
 u=original[rec['start']:rec['start']+rec['blocks']].reshape(-1)[:rec['neurons']].tolist()
 old+=requests(u,False);new+=requests(u,True)
stress=np.load(R/'adaptive_delta_stress_25_1/expected.npz')['groups']
st=dict(original_requests=sum(requests(u.tolist(),False)for u in stress),centered_requests=sum(requests(u.tolist(),True)for u in stress))
out=dict(arithmetic_cases=cases,arithmetic_failures=0,model_original_requests=old,model_centered_requests=new,stress=st,
 note='Arithmetic and schedule screen only. A single centered-bin equality replaces absolute-int5 OR uncentered-bin equality; eligibility sets differ.')
(R/'stream_centered_screen.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2),flush=True)
