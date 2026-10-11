"""Arithmetic-only audit of a potential three-lane narrow leakage format."""
from pathlib import Path
import json,itertools
R=Path(__file__).resolve().parent/'results';cases=0
for delta in range(32):
 beta=256-delta;k=512-16*delta
 for u0,u1,u2 in itertools.product(range(-16,16),repeat=3):
  a=(u0+16)+((u1+16)<<10)+(u2<<20)
  assert -(1<<24)<=a<(1<<24)
  p=(a*delta+k+(k<<10))&((1<<48)-1)
  d0=((p>>8)&3)-2;d1=((p>>18)&3)-2;d2=(p>>28)&3
  if d2>=2:d2-=4
  got=[u0-d0,u1-d1,u2-d2]
  ref=[-((-beta*u)//256)for u in [u0,u1,u2]]
  assert got==ref,(delta,u0,u1,u2,got,ref)
  cases+=1
(R/'delta_packing_algebra.json').write_text(json.dumps(dict(cases=cases,failures=0,delta_range=[0,31],membrane_range=[-16,15],lanes=3,note='Arithmetic proof/check only; no RTL, controller or routed hardware for this format.'),indent=2));print('DELTA PACKING PASS',cases,flush=True)
