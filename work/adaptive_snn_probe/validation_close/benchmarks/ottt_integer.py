"""Exact E5 executor and declared integer conversion of official vanilla LIF."""
import numpy as np
import torch
from modules.neuron import OnlineLIFNode

def pair_starts(edges):
    if not len(edges): return np.empty(0, np.int64)
    ix=np.arange(len(edges),dtype=np.int64)
    false=np.maximum.accumulate(np.where(~edges,ix,-1))
    return np.flatnonzero(edges & (((ix-false-1)&1)==0))

def exact_post(u,beta=128):
    """Actual packed decoded values form the result, including scalar exceptions."""
    a=u.reshape(-1).numpy().astype(np.int64,copy=False)
    ref=-np.floor_divide(-a*beta,256)
    result=np.zeros_like(a)
    nz=np.flatnonzero(a!=0); v=a[nz]
    legal=(v>=-2048)&(v<=2047)
    narrow=(v>=-256)&(v<=255)
    pairs=pair_starts(narrow[:-1]&narrow[1:])
    done=np.zeros(len(v),bool); vals=np.empty_like(v)
    if len(pairs):
        first,second=v[pairs],v[pairs+1]
        p=((first+256)+(second<<16))*beta+255-256*beta+(255<<16)
        neg=((p>>16)&1)^((beta&1)&(second&1))^1
        low=((p>>8)&255)-256*neg
        high=(p>>24)&511; high=np.where(high>=256,high-512,high)
        high+=neg&(((p>>16)&255)==255)
        vals[pairs]=low; vals[pairs+1]=high
        done[pairs]=True;done[pairs+1]=True
    singles=np.flatnonzero(~done)
    vals[singles]=(v[singles]*beta+255)>>8
    result[nz]=vals
    mismatch=int(np.count_nonzero(result!=ref))
    assert mismatch==0
    return torch.from_numpy(result.reshape(u.shape)), {
        'raw':len(a),'zero':len(a)-len(v),'nonzero':len(v),
        'signed12_exceptions':int((~legal).sum()),'narrow':int(narrow.sum()),
        'pairs':len(pairs),'issues_adaptive':len(v)-len(pairs),
        'issues_fixed_split':(len(v)+1)//2,'issues_scalar':len(v),
        'issues_LUT2':(len(v)+1)//2,'packed_mismatches':mismatch}

class IntegerLIF(OnlineLIFNode):
    def __init__(self,*args,packed=False,**kwargs):
        super().__init__(*args,**kwargs)
        assert self.tau==2 and not self.decay_input and self.v_reset is None
        self.packed=packed; self.integer_u=None; self.steps=[]; self.stats={}
    def forward(self,x,**kwargs):
        if kwargs.get('init',False):
            self.integer_u=torch.zeros_like(x,dtype=torch.int64)
            self.steps=[]
        old=self.integer_u
        if self.packed:
            leak,counts=exact_post(old)
            for key,val in counts.items(): self.stats[key]=self.stats.get(key,0)+val
        else: leak=-torch.div(-old*128,256,rounding_mode='floor')
        current=torch.round(x*256).to(torch.int64)
        charged=leak+current
        spike=charged>=256
        self.integer_u=charged-spike.to(torch.int64)*256
        assert bool(torch.all((self.integer_u>=-(1<<23))&(self.integer_u<(1<<23))))
        self.v=self.integer_u.to(torch.float32)/256
        self.spike=spike.to(x.dtype)
        self.steps.append({'old_min':int(old.min()),'old_max':int(old.max()),
            'current_min':int(current.min()),'current_max':int(current.max()),
            'state_min':int(self.integer_u.min()),'state_max':int(self.integer_u.max()),
            'state_digest':self.integer_u.clone(),'spike_digest':spike.clone()})
        return self.spike
