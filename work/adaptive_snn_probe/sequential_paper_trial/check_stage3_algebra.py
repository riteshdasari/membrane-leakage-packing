"""Exhaustive exact pair algebra, including sign/carry corners."""
from pathlib import Path
import hashlib,json,time
import numpy as np
P=Path(__file__).resolve().parent
assert json.loads((P/'stage2_acceptance.json').read_text())['status']=='pass'
assert not(P/'stage3_algebra.json').exists()
started=time.monotonic()
def oracle(u,beta):return -np.floor_divide(-(u*beta),256)
def predicted_negative(u,beta):
    return (u<=-4)|((u==-3)&(beta>=86))|((u==-2)&(beta>=128))|((u==-1)&(beta==256))
u0=np.arange(-256,256,dtype=np.int64)[:,None]
u1=np.arange(-256,256,dtype=np.int64)[None,:]
cases=0;postcases=0
for beta in range(257):
    A=(u0+256)+(u1<<16)
    assert A.min()>=-(1<<24)and A.max()<(1<<24)
    # Generic modulo-two post-correction control, applicable to all coefficients.
    C=255-256*beta+(255<<16);p=A*beta+C
    ref=((beta&1)&(u1&1))^1
    n=((p>>16)&1)^ref
    lower=((p>>8)&255)-256*n
    upper=((p>>24)&511);upper=np.where(upper>=256,upper-512,upper)
    upper+=n&(((p>>16)&255)==255)
    assert np.array_equal(lower,np.broadcast_to(oracle(u0,beta),lower.shape)),('post_low',beta)
    assert np.array_equal(upper,np.broadcast_to(oracle(u1,beta),upper.shape)),('post_high',beta)
    postcases+=512*512
    if beta>=64:
        n=predicted_negative(u0,beta).astype(np.int64)
        assert np.array_equal(n,(beta*u0+255<0).astype(np.int64))
        C=255-256*beta+((255+n)<<16)
        # Hardware-friendly form: negated beta in low byte, constants above.
        wired=((254+n)<<16)+(((-beta)&255)<<8)+255
        assert np.array_equal(C,wired)
        p=A*beta+C
        low=((p>>8)&255)-256*n
        high=(p>>24)&511;high=np.where(high>=256,high-512,high)
        assert np.array_equal(low,np.broadcast_to(oracle(u0,beta),low.shape)),('pre_low',beta)
        assert np.array_equal(high,np.broadcast_to(oracle(u1,beta),high.shape)),('pre_high',beta)
        cases+=512*512
full=np.arange(-2048,2048,dtype=np.int64);widecases=0;splitcases=0
for beta in range(257):
    assert np.array_equal((full*beta+255)>>8,oracle(full,beta))
    h=full>>8;r=full&255
    assert np.array_equal(h*beta+((r*beta+255)>>8),oracle(full,beta))
    widecases+=len(full);splitcases+=len(full)
answer=dict(status='pass',precompensated_pairs=cases,postcorrected_pairs=postcases,
    signed12_scalar_cases=widecases,signed12_split_cases=splitcases,
    elapsed_seconds=time.monotonic()-started,failures=0,
    pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in[Path(__file__),P/'stage3_plan.json',P/'stage2_acceptance.json']})
(P/'stage3_algebra.json').write_text(json.dumps(answer,indent=2)+'\n',encoding='utf-8')
print(json.dumps(answer),flush=True)
