"""Full-word integer audit of two-input signed radix encoding and certified fields.
This does not validate DSP primitive configuration, timing, or a scheduler.
"""
from pathlib import Path
import random,json
r=random.Random(20261008);mask=(1<<48)-1
def enc(v,b):return sum(x<<(b*i)for i,x in enumerate(v))&mask
def digits(p,b,n):return [(p>>(b*i))&((1<<b)-1)for i in range(n)]
counts={};bounds_cases=0
for b in (6,8,12,16):
 n=48//b;done=0;memdone=0
 while done<2000:
  k=r.choice((4,8,16,32));w=[[r.randrange(-8,8)for _ in range(n)]for _ in range(k)]
  sp=[r.random()<.3 for _ in range(k)];active=sum(sp)
  low=[sum(sorted(min(w[j][i],0)for j in range(k))[:active])for i in range(n)]
  high=[sum(sorted((max(w[j][i],0)for j in range(k)),reverse=True)[:active])for i in range(n)]
  if max(h-l for l,h in zip(low,high))>=1<<b:continue
  offset=[-l for l in low];P=enc(offset,b);cur=[0]*n
  for j in range(0,k,2):
   words=[enc(w[z],b)if sp[z] else 0 for z in range(j,min(j+2,k))]
   P=(P+sum(words))&mask
   for z in range(j,min(j+2,k)):
    if sp[z]:cur=[v+d for v,d in zip(cur,w[z])]
   assert all(l<=v<=h for l,v,h in zip(low,cur,high))
   assert digits(P,b,n)==[v+o for v,o in zip(cur,offset)]
   assert [v+l for v,l in zip(digits(P,b,n),low)]==cur
  # Same known-count bounds, this time representing actual U in signed fields.
  half=1<<(b-1)
  U=[r.randint(-half-l,half-1-h)for l,h in zip(low,high)]
  P=enc([u+half for u in U],b);ref=U[:]
  for j in range(0,k,2):
   P=(P+sum(enc(w[z],b)if sp[z] else 0 for z in range(j,min(j+2,k))))&mask
   for z in range(j,min(j+2,k)):
    if sp[z]:ref=[v+d for v,d in zip(ref,w[z])]
   assert [v-half for v in digits(P,b,n)]==ref
  assert all((h-l)<=(1<<b)-1 for l,h in zip(low,high))
  done+=1;memdone+=1;bounds_cases+=n
 counts[str(b)]={'current_tiles':done,'membrane_tiles':memdone,'lanes':n}
assert enc([-1,2],8)==511 and ((255)|(2<<8))==767
out={'note':__doc__,'counts':counts,'mismatches':0,'lane_interval_cases':bounds_cases,
 'signed_word_counterexample':{'weights':[-1,2],'correct_linear_encoding':511,'naive_concatenation':767}}
(Path(__file__).resolve().parent/'results/certified_arithmetic_audit.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
