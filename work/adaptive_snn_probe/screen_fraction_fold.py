"""Fold exact fractional high correction into DSP C; screen before RTL."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
from pathlib import Path
import numpy as np,json
from check_stream_offset import free
P=Path(__file__).resolve().parent;R=P/'results'
print('fraction fold free GiB',round(free(),2),flush=True);assert free()>1.2
def verify(lo,hi,deltas):
 values=np.arange(lo,hi,dtype=np.int64)
 u=np.stack(np.meshgrid(*([values]*3),indexing='ij'),-1).reshape(-1,3)
 h=u//32;r=u%32;a=r[:,0]+(r[:,1]<<10)+((r[:,2]-16)<<20)
 cases=0;maxfield=0
 for d in deltas:
  q=d*h//8;frac=(d*h)%8;field=d*r+32*frac
  assert field.min()>=0 and field.max()<1024,(lo,hi,d,int(field.max()))
  c=(frac[:,0]<<5)+(frac[:,1]<<15)+((16*d+(frac[:,2]<<5))<<20)
  p=a*d+c
  extracted=np.stack([(p>>(10*l))&1023 for l in range(3)],1)
  assert np.array_equal(extracted,field)
  pre=u-q;got=pre-(extracted>>8);expected=u-d*u//256
  assert np.array_equal(got,expected),(lo,hi,d)
  assert pre.min()>=lo and pre.max()<hi and got.min()>=lo and got.max()<hi
  cases+=len(u);maxfield=max(maxfield,int(field.max()))
 return dict(range=[lo,hi-1],deltas=list(deltas),exhaustive_triples=cases,scalar_comparisons=3*cases,max_product_field=maxfield)
# int6 has only h=-1/0. Its coefficient-dependent fractional bias always fits10bits.
six=verify(-32,32,range(32))
# At delta25 every h has fractional residue0..7 and31*25+224=999<1024.
seven=verify(-64,64,[25])
# All full-range scalar lanes for all allowed fixed3 folded coefficients0..25.
u=np.arange(-1024,1024,dtype=np.int64);h=u//32;r=u%32
for d in range(26):
 f=d*r+32*((d*h)%8);assert f.max()<1024
 assert np.array_equal(u-d*h//8-f//256,u-d*u//256)
# Counterexample beyond the declared coefficient condition.
counter=dict(U=63,delta=31,field=31*(63%32)+32*((31*(63//32))%8))
assert counter['field']>1023
ledger=json.loads((R/'adaptive_delta_model_input.json').read_text());old=np.load(R/'adaptive_delta_model_25_1/expected.npz')['groups']
frames=[old[z['start']:z['start']+z['blocks']].reshape(-1)[:z['neurons']].tolist()for z in ledger['ledger']]
rows=[]
for bits in [5,6,7]:
 req=nar=by=0
 for u in frames:
  pos=0
  while pos<len(u):
   x=u[pos:pos+3];n=len(x);fit=n==3 and all(-(1<<(bits-1))<=v<(1<<(bits-1))for v in x)
   bypass=not any(x);take=3 if n==3 and(fit or bypass or x[2]==0)else min(2,n)
   req+=1;nar+=fit;by+=bypass;pos+=take
 rows.append(dict(bits=bits,requests=req,continuous_clock_proxy=req+3,narrow=nar,bypass=by))
out=dict(signed6=six,signed7_delta25=seven,fixed3_scalar_checks=26*2048,
 fullrange_fixed3_condition='delta<=25',counterexample_outside_condition=counter,model_rows=rows,
 notes=['Numerical screening only; controller, RTL mapping and timing not measured for this candidate',
 'delta25 is the existing beta231 reference, not a newly chosen model',
 'Each lane splits U=32*h+r; DSP C absorbs32*((delta*h)mod8), metadata stores U-floor(delta*h/8)',
 'DSP output extraction then requires only subtracting its unsigned two-bit quotient; no separate fractional carry decoder',
 'Any RTL trial must optimize the fixed full-range3 lane by the same algebra when delta<=25; controller savings cannot be inferred from comparison to the older unoptimized triple'])
(R/'fraction_fold_screen.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2),flush=True)
