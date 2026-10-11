"""Same declared integer reference in NumPy, with original Torch synapses."""
import types
import numpy as np
import torch
from integer_glif import PUBLIC,UNIT,BITS,LIMIT,PARAMS,load_model,parameters,normalized,LIFSpike_CW

def install(model,observer=None,audit_first_batch=False):
    rows={}
    for name,module in model.named_modules():
        if not isinstance(module,LIFSpike_CW):continue
        p={k:v.numpy().copy()for k,v in parameters(module).items()}
        assert all(np.all((p[k]>=0)&(p[k]<=256))for k in ('k0','k1'))
        rows[name]=dict(updates=0,U_min=0,U_max=0,I_min=0,I_max=0,next_min=0,next_max=0,
            spikes=0,independent_state_mismatches=0,independent_spike_mismatches=0,
            coefficient0=p['k0'].ravel().tolist(),coefficient1=p['k1'].ravel().tolist())
        calls=[0]
        def forward(self,x,name=name,p=p,calls=calls):
            source=x.numpy();u=np.zeros(source.shape[1:],dtype=np.int64)
            previous=np.zeros_like(u);out=np.zeros(source.shape,dtype=np.float32);row=rows[name]
            for step in range(self.T):
                coefficient=np.where(previous!=0,p['k1'],p['k0'])
                current=np.rint((source[step]*p['gain'][step][None,:,None,None])*np.float32(UNIT)).astype(np.int64)
                leak=(coefficient*u+255)>>8
                new=leak+current-p['bias']-p['reset']*previous
                spikes=(new>p['threshold']).astype(np.int64)
                extrema=(int(u.min()),int(u.max()),int(current.min()),int(current.max()),int(new.min()),int(new.max()))
                assert min(extrema)>=-LIMIT and max(extrema)<LIMIT,(name,extrema)
                for key,value in zip(('U_min','U_max','I_min','I_max','next_min','next_max'),extrema):
                    row[key]=min(row[key],value)if key.endswith('min')else max(row[key],value)
                row['updates']+=u.size;row['spikes']+=int(spikes.sum())
                if audit_first_batch and calls[0]==0:
                    # Independent Torch int64 division and FP32 current computation.
                    tu=torch.from_numpy(u);tc=torch.from_numpy(coefficient)
                    ti=torch.round(x[step]*torch.from_numpy(p['gain'][step])[None,:,None,None]*UNIT).long()
                    wanted=-torch.div(-(tu*tc),256,rounding_mode='floor')+ti-torch.from_numpy(p['bias'])-torch.from_numpy(p['reset'])*torch.from_numpy(previous)
                    row['independent_state_mismatches']+=int(np.count_nonzero(wanted.numpy()!=new))
                    row['independent_spike_mismatches']+=int(np.count_nonzero((wanted>torch.from_numpy(p['threshold'])).numpy()!=(spikes!=0)))
                if observer is not None:
                    observer(name,step,*(torch.from_numpy(a)for a in(u,coefficient,current,leak,new,spikes,previous)),
                        {k:torch.from_numpy(v)for k,v in p.items()})
                u,previous=new,spikes;out[step]=spikes.astype(np.float32)
            calls[0]+=1
            return torch.from_numpy(out)
        module.forward=types.MethodType(forward,module)
    return rows
