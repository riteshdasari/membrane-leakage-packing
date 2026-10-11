"""Packed unsigned residual algebra, including every delta and high correction."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
from pathlib import Path
import numpy as np,json
P=Path(__file__).resolve().parent;R=P/'results'
r0,r1=np.meshgrid(np.arange(256,dtype=np.int64),np.arange(256,dtype=np.int64),indexing='ij')
u=np.arange(-1024,1024,dtype=np.int64)
for d in range(32):
 p=(r0+(r1<<16))*d
 assert np.array_equal((p>>8)&31,d*r0//256)
 assert np.array_equal((p>>24)&31,d*r1//256)
 h=u//256;r=u%256;pre=u-d*h;got=pre-d*r//256
 assert np.array_equal(got,u-d*u//256)
 assert pre.min()>=-1024 and pre.max()<=1023
out=dict(packed_residual_pairs=32*r0.size,full_int11_scalar_corrections=32*len(u),mismatches=0,
 notes=['All delta0..31 and every pair of unsigned8 residuals; product fields cannot carry into each other',
 'All int11 scalar high corrections; exact ceil((256-delta)*U/256) and representable metadata',
 'Applied to adaptive and matched fixed pair/hybrid; not a one-sided optimization'])
(R/'stream_unsigned_arithmetic_screen.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2),flush=True)
