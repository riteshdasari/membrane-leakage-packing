"""Arithmetic-only stronger fixed baseline: int5 residues plus exact high corrections."""
from pathlib import Path
import json,random
P=Path(__file__).resolve().parent;R=P/'results'
def physical(u,d):
 r=[(x+16)%32-16 for x in u];h=[(x-y)//32 for x,y in zip(u,r)]
 a=(r[0]+16)+((r[1]+16)<<10)+(r[2]<<20);k=512-16*d
 assert -(1<<24)<=a<(1<<24)
 p=(a*d+k+(k<<10))&((1<<48)-1)
 product=[(p&1023)-512,((p>>10)&1023)-512,(p>>20)&1023]
 if product[2]>=512:product[2]-=1024
 assert product==[d*x for x in r]
 return [x-((32*d*y+z)//256)for x,y,z in zip(u,h,product)]
cases=0;rng=random.Random(37912)
for d in range(32):
 for x in range(-1024,1024):
  u=[x,((x+1024)*73%2048)-1024,((x+1024)*971%2048)-1024]
  assert physical(u,d)==[-((-x*(256-d))//256)for x in u];cases+=1
for _ in range(100000):
 d=rng.randrange(32);u=[rng.randrange(-1024,1024)for _ in range(3)]
 assert physical(u,d)==[-((-x*(256-d))//256)for x in u];cases+=1
(R/'fixed_three_delta_algebra.json').write_text(json.dumps(dict(cases=cases,failures=0,wide_bits=11,delta_range=[0,31],lanes=3,
 formula='U=32*h+r, r=int5; ceil((256-d)*U/256)=U-floor((32*d*h+d*r)/256)',
 note='Three full-range operations are algebraically possible in a fixed DSP format; larger high correction cost is not simulated/routed here. Two lanes per DSP is not an absolute packing-capacity bound.'),indent=2))
print('FIXED THREE ARITHMETIC PASS',cases,flush=True)
