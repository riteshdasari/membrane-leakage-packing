"""Independent arithmetic screening, then no-padding real-trace schedule audit."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
from pathlib import Path
import numpy as np,json,hashlib
P=Path(__file__).resolve().parent;R=P/'results'
u=np.stack(np.meshgrid(*([np.arange(-16,16,dtype=np.int64)]*3),indexing='ij'),-1).reshape(-1,3)
direct_cases=0
for d in range(32):
 a=(u[:,0]+16)+((u[:,1]+16)<<10)+(u[:,2]<<20)
 k=512-16*d;p=a*d+k+(k<<10)
 got=[]
 for l in range(3):
  q=(p>>(10*l))&1023
  f=(q>>8)-(2 if l<2 else 0)
  if l==2:f=np.where(f>=2,f-4,f)
  got.append(u[:,l]-f)
 got=np.stack(got,1);expected=u-(d*u//256)
 assert np.array_equal(got,expected),(d,'direct product decoding')
 assert got.min()>=-16 and got.max()<=15
 direct_cases+=len(u)
# Verify split common-upper reconstruction on every possible eleven-bit H/r pair,
# including wrap at int11 positive/negative limits. Bit pattern must equal H+r.
h=np.arange(-1024,1024,dtype=np.int64)[:,None];r=np.arange(32,dtype=np.int64)[None,:]
lo=(h&31)+r;hi=((h&2047)>>5)+(lo>>5)
got=((hi&63)<<5)|(lo&31);assert np.array_equal(got,(h+r)&2047)
ledger=json.loads((R/'adaptive_delta_model_input.json').read_text())
old=np.load(R/'adaptive_delta_model_25_1/expected.npz')['groups']
frames=[old[rec['start']:rec['start']+rec['blocks']].reshape(-1)[:rec['neurons']].tolist()for rec in ledger['ledger']]
from check_stream_compact import policy
rows=[]
for e in [0,1,3,5,6]:
 req=narrow=bypass=0
 for values in frames:
  pos=0
  while pos<len(values):
   n,m,b=policy(values[pos:],25,e);pos+=n;req+=1;narrow+=m;bypass+=b
 rows.append(dict(engine=e,requests=req,narrow=narrow,bypass=bypass,continuous_clock_proxy=req+3))
out=dict(direct_exhaustive_triples=direct_cases,direct_scalar_comparisons=3*direct_cases,shared_upper_pairs=got.size,
 frames=len(frames),neurons=sum(map(len,frames)),rows=rows,
 notes=['Direct arithmetic covers all signed-int5 triples and all shared delta0..31; no new coefficient/model assumptions',
 'Shared upper reconstruction tested as eleven-bit modular bit patterns; actual leakage output remains representable',
 'Schedules are analytical before RTL replay; source window/memory handling still excluded'])
(R/'stream_compact_arithmetic_screen.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2),flush=True)
