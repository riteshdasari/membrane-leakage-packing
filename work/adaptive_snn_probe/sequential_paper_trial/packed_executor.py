"""Ordered software model of one-DSP pair/full leakage; no reordering."""
import numpy as np
POLICIES=('adaptive_pre','fixed_scalar1','fixed_scalar2','fixed_LUT2','fixed_split2','adaptive_post')
def oracle(u,b):return -np.floor_divide(-(u*b),256)
def starts_for(edges):
    if len(edges)==0:return np.empty(0,dtype=np.int64)
    idx=np.arange(len(edges),dtype=np.int64)
    previous_false=np.maximum.accumulate(np.where(~edges,idx,-1))
    return np.flatnonzero(edges&(((idx-previous_false-1)&1)==0))
def nflag(u,b):return (u<=-4)|((u==-3)&(b>=86))|((u==-2)&(b>=128))|((u==-1)&(b==256))
def packed(u,b):
    assert u.dtype==b.dtype==np.int64
    assert np.all((u>=-2048)&(u<=2047))and np.all((b>=0)&(b<=256))
    zero=(u==0)|(b==0);nz=np.flatnonzero(~zero);v=u[nz];c=b[nz]
    n=len(v);same=c[:-1]==c[1:];narrow=(v>=-256)&(v<=255)
    adapt=same&narrow[:-1]&narrow[1:]&(c[:-1]>=64)
    post=same&narrow[:-1]&narrow[1:]
    pairs=starts_for(adapt);postpairs=starts_for(post);splitpairs=starts_for(same)
    # Reconstruct accepted pair results from the packed DSP integer, not scalar leakage.
    output=np.zeros_like(u);completed=np.zeros(n,dtype=bool);local=np.empty_like(v)
    if len(pairs):
        a,d,beta=v[pairs],v[pairs+1],c[pairs]
        neg=nflag(a,beta).astype(np.int64)
        A=(a+256)+(d<<16);C=255-256*beta+((255+neg)<<16);P=A*beta+C
        low=((P>>8)&255)-256*neg
        high=(P>>24)&511;high=np.where(high>=256,high-512,high)
        local[pairs]=low;local[pairs+1]=high
        completed[pairs]=True;completed[pairs+1]=True
    singleton=np.flatnonzero(~completed)
    # Full-format DSP has a signed25 multiplicand and an exact add255 rounding term.
    if len(singleton):local[singleton]=(v[singleton]*c[singleton]+255)>>8
    assert np.array_equal(local,oracle(v,c))
    output[nz]=local
    # Strong low-residue/high-product fixed control, all scalar results checked.
    split=(v>>8)*c+(((v&255)*c+255)>>8)
    assert np.array_equal(split,local)
    if len(postpairs):
        a,d,beta=v[postpairs],v[postpairs+1],c[postpairs]
        P=((a+256)+(d<<16))*beta+255-256*beta+(255<<16)
        neg=((P>>16)&1)^((beta&1)&(d&1))^1
        low=((P>>8)&255)-256*neg
        high=(P>>24)&511;high=np.where(high>=256,high-512,high)
        high+=neg&(((P>>16)&255)==255)
        assert np.array_equal(low,local[postpairs])and np.array_equal(high,local[postpairs+1])
    counts=dict(raw_operations=len(u),zero_bypassed=int(zero.sum()),arithmetic_operations=n,
        narrow9_arithmetic_operations=int(narrow.sum()),same_coefficient_edges=int(same.sum()),
        adaptive_pairs=len(pairs),post_pairs=len(postpairs),fixed_split_pairs=len(splitpairs),
        issues=dict(adaptive_pre=n-len(pairs),adaptive_post=n-len(postpairs),fixed_scalar1=n,
            fixed_scalar2=(n+1)//2,fixed_LUT2=(n+1)//2,fixed_split2=n-len(splitpairs)))
    return output,counts
