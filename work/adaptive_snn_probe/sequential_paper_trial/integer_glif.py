"""Explicit integer-neuron reference; original floating synaptic network retained."""
from pathlib import Path
import sys, types
sys.dont_write_bytecode = True
PUBLIC = Path(__file__).resolve().parent.parent / 'public_model_trial'
sys.path[:0] = [str(PUBLIC/'sources'), str(PUBLIC/'deps')]
import numpy as np
import torch
from layers import LIFSpike_CW
import networks_for_CIFAR as networks

UNIT = 256
BITS = 24
LIMIT = 1 << (BITS-1)
PARAMS = dict(gate=[.6,.8,.6], param=[.25,.5,.0625,.5], t=2,
              static_gate=False, static_param=False, time_wise=False, soft_mode=True)

def load_model():
    model = networks.ResNet_18_stand_CW(PARAMS, n_class=10)
    checkpoint = torch.load(PUBLIC/'assets/glif_cifar10_T2.pth.tar',
                            map_location='cpu', weights_only=True)
    model.load_state_dict(checkpoint['state_dict'], strict=True)
    return model.eval()

def parameters(module):
    # FP32 learned parameters are quantized once, using nearest-even rounding.
    al, be, ga = module.alpha.sigmoid(), module.beta.sigmoid(), module.gamma.sigmoid()
    a0 = 1-al*(1-module.tau.sigmoid())
    a1 = a0*(1-ga)
    shaped = lambda x: x.view(1, -1, 1, 1)
    q = lambda x: torch.round(x).to(torch.int64)
    return dict(k0=shaped(q(256*a0)), k1=shaped(q(256*a1)),
                bias=shaped(q(UNIT*(1-al)*module.leak.sigmoid())),
                reset=shaped(q(UNIT*(1-ga)*module.reVth.sigmoid())),
                threshold=shaped(q(UNIT*module.Vth.sigmoid())),
                gain=1-be[None,:]*(1-module.conduct.sigmoid()))

def install(model, observer=None, audit_first_batch=False):
    rows = {}
    for name, module in model.named_modules():
        if not isinstance(module, LIFSpike_CW):
            continue
        p = parameters(module)
        assert (p['k0']>=0).all() and (p['k0']<=256).all()
        assert (p['k1']>=0).all() and (p['k1']<=256).all()
        rows[name] = dict(updates=0, U_min=0, U_max=0, I_min=0, I_max=0,
                          next_min=0, next_max=0, spikes=0,
                          independent_state_mismatches=0,
                          independent_spike_mismatches=0,
                          coefficient0=p['k0'].flatten().tolist(),
                          coefficient1=p['k1'].flatten().tolist())
        calls = [0]
        def forward(self, x, name=name, p=p, calls=calls):
            u = torch.zeros(x.shape[1:], dtype=torch.int64, device=x.device)
            previous = torch.zeros_like(u)
            out = torch.zeros_like(x)
            row = rows[name]
            for step in range(self.T):
                coefficient = torch.where(previous.bool(), p['k1'], p['k0'])
                effective_current = x[step]*p['gain'][step][None,:,None,None]
                current = torch.round(effective_current*UNIT).to(torch.int64)
                # Arithmetic right shift rounds down, giving ceil(beta*U/256).
                leak = (coefficient*u+255) >> 8
                new = leak+current-p['bias']-p['reset']*previous
                spikes = (new>p['threshold']).to(torch.int64)
                extrema = tuple(int(t.item()) for t in
                    (u.min(), u.max(), current.min(), current.max(), new.min(), new.max()))
                assert min(extrema)>=-LIMIT and max(extrema)<LIMIT, (name, extrema)
                for key, value in zip(('U_min','U_max','I_min','I_max','next_min','next_max'), extrema):
                    row[key] = min(row[key],value) if key.endswith('min') else max(row[key],value)
                row['updates'] += u.numel()
                row['spikes'] += int(spikes.sum())
                if audit_first_batch and calls[0]==0:
                    a,b,c = u.numpy(),coefficient.numpy(),current.numpy()
                    # Independent signed division form, not an arithmetic shift.
                    expected = -np.floor_divide(-(a*b),256)+c-p['bias'].numpy()-p['reset'].numpy()*previous.numpy()
                    expected_spikes = expected>p['threshold'].numpy()
                    row['independent_state_mismatches'] += int(np.count_nonzero(expected!=new.numpy()))
                    row['independent_spike_mismatches'] += int(np.count_nonzero(expected_spikes!=spikes.numpy()))
                if observer is not None:
                    observer(name,step,u,coefficient,current,leak,new,spikes,previous,p)
                u,previous = new,spikes
                out[step] = spikes.float()
            calls[0] += 1
            return out
        module.forward = types.MethodType(forward,module)
    return rows

def normalized(images):
    x = torch.from_numpy(images.transpose(0,3,1,2).copy()).float()/255
    mean = torch.tensor([.4914,.4822,.4465]).view(1,3,1,1)
    std = torch.tensor([.247,.243,.261]).view(1,3,1,1)
    return (x-mean)/std
