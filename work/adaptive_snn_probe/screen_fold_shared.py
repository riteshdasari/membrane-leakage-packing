from pathlib import Path
import json
P=Path(__file__).resolve().parent;R=P/'results'
cases=0
for d in range(32):
 qp=d//8;qn=-((d+7)//8);qnn=-((d+3)//4)
 fn=(-d)%8;fnn=(-2*d)%8
 for h in [-2,-1,0,1]:
  q={-2:qnn,-1:qn,0:0,1:qp}[h];f={-2:fnn,-1:fn,0:0,1:d%8}[h]
  assert q==d*h//8 and f==d*h%8,(d,h,q,f)
  assert -8<=q<=3 and 0<=f<=7
  cases+=1
out=dict(coefficient_high_cases=cases,mismatches=0,policy_unchanged=True,
 notes=['Every delta0..31 and h=-2,-1,0,1; q_twoneg=-ceil(delta/4), q_neg=-ceil(delta/8)',
 'All rounding tables are computed once per shared coefficient and selected by each membrane high part'])
(R/'fold_shared_screen.json').write_text(json.dumps(out,indent=2));print(out,flush=True)
