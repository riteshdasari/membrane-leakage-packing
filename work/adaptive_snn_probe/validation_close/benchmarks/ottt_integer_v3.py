"""Streaming integer feedback with checked E5 results and bounded trace capture."""
from ottt_integer_v2 import exact_post
from modules.neuron import OnlineLIFNode
import numpy as np
import torch

class StreamIntegerLIF(OnlineLIFNode):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        assert self.tau==2 and not self.decay_input and self.v_reset is None
        self.integer_u=None;self.stats={};self.ranges={};self.sample_frames=[]
        self.capture=False;self.layer_name=None;self.batch_index=None;self.step_index=0
    def forward(self,x,**kwargs):
        if kwargs.get('init',False):
            self.integer_u=torch.zeros_like(x,dtype=torch.int64);self.step_index=0
        old=self.integer_u
        leak,counts=exact_post(old)
        flat=old.reshape(-1).numpy()
        counts['signed16_exceptions']=int(np.count_nonzero((flat<-(1<<15))|(flat>=(1<<15))))
        counts['B16_adaptive_issues']=counts['issues_adaptive']
        for key,val in counts.items():self.stats[key]=self.stats.get(key,0)+val
        current=torch.round(x*256).to(torch.int64)
        charged=leak+current;spike=charged>=256
        self.integer_u=charged-spike.to(torch.int64)*256
        assert bool(torch.all((self.integer_u>=-(1<<23))&(self.integer_u<(1<<23))))
        values={'old_min':int(old.min()),'old_max':int(old.max()),
            'current_min':int(current.min()),'current_max':int(current.max()),
            'state_min':int(self.integer_u.min()),'state_max':int(self.integer_u.max())}
        for k,v in values.items():
            self.ranges[k]=v if k not in self.ranges else (min if k.endswith('min') else max)(self.ranges[k],v)
        if self.capture:
            nonzero=np.flatnonzero(flat!=0)
            wide=np.flatnonzero((flat<-2048)|(flat>2047))[:32]
            selected=np.unique(np.concatenate((nonzero[:64],wide)))
            if len(selected):self.sample_frames.append({'layer':self.layer_name,
                'batch_first_image':self.batch_index,'timestep':self.step_index,
                'shape':list(old.shape),'flat_neuron_indices':selected.tolist(),
                'u':flat[selected].tolist(),'beta':128,
                'selection':'ordered first64nonzero plus first32signed12exceptions; stress coverage, not unbiasedenergy'})
        self.step_index+=1
        self.v=self.integer_u.to(torch.float32)/256
        self.spike=spike.to(x.dtype).contiguous()
        return self.spike
