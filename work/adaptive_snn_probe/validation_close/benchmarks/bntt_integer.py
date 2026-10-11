"""Source-preserving CPU original and exact declared BNTT integer feedback.

This module is prepared without performing model inference. The original source
is transformed only to remove explicit parameterless .cuda() placement calls.
"""
import ast, hashlib, sys, types
from pathlib import Path
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P/'ottt_source'))
import numpy as np
import torch
from ottt_integer_v2 import exact_post

class RemoveCudaPlacement(ast.NodeTransformer):
    def visit_Call(self,node):
        node=self.generic_visit(node)
        if isinstance(node.func,ast.Attribute) and node.func.attr=='cuda':
            assert not node.args and not node.keywords
            return ast.copy_location(node.func.value,node)
        return node

def original_cpu_module():
    path=P/'bntt_visual_source'/'model.py'
    source=path.read_text()
    tree=RemoveCudaPlacement().visit(ast.parse(source))
    ast.fix_missing_locations(tree)
    module=types.ModuleType('bntt_original_cpu')
    exec(compile(tree,str(path),mode='exec'),module.__dict__)
    return module

class IntegerBNTT:
    """Wrap original loaded model layers, replacing only hidden neuron updates."""
    def __init__(self,model,packed=False,retain_steps=False):
        self.model=model;self.packed=packed;self.retain_steps=retain_steps
        self.stats={};self.ranges={};self.steps=[];self.expected_steps=None
        self.state_mismatches=0;self.spike_mismatches=0;self.compare_index=0

    def update(self,old,current,name,step):
        spike=old>256
        if self.packed:
            leak,counts=exact_post(old,beta=253)
            for k,v in counts.items():self.stats[k]=self.stats.get(k,0)+v
        else:leak=-torch.div(-old*253,256,rounding_mode='floor')
        rounded=torch.round(current*256).to(torch.int64)
        stored=leak+rounded-spike.to(torch.int64)*256
        assert bool(torch.all((stored>=-(1<<23))&(stored<(1<<23))))
        r=self.ranges.setdefault(name,{})
        vals={'old_min':int(old.min()),'old_max':int(old.max()),
            'current_min':int(rounded.min()),'current_max':int(rounded.max()),
            'state_min':int(stored.min()),'state_max':int(stored.max())}
        for k,v in vals.items():r[k]=v if k not in r else (min if k.endswith('min') else max)(r[k],v)
        for key,tensor in [('old_signed16_exceptions',old),('stored_signed16_exceptions',stored)]:
            self.stats[key]=self.stats.get(key,0)+int(torch.count_nonzero((tensor<-(1<<15))|(tensor>=(1<<15))))
        if self.retain_steps:self.steps.append((name,step,stored.clone(),spike.clone()))
        if self.expected_steps is not None:
            ename,et,estate,espike=self.expected_steps[self.compare_index]
            assert name==ename and step==et
            self.state_mismatches+=int(torch.count_nonzero(stored!=estate))
            self.spike_mismatches+=int(torch.count_nonzero(spike!=espike))
            # Drop the previous reference trace after the direct comparison.
            self.expected_steps[self.compare_index]=None
            self.compare_index+=1
        return stored,spike.to(current.dtype).contiguous()

    def __call__(self,inp):
        m=self.model;b,_,h,w=inp.shape
        assert h==w==64 and m.num_steps==30 and m.leak_mem==.99
        self.steps=[];self.compare_index=0
        shapes=[(64,h,w),(128,h//2,w//2),(256,h//4,w//4),(256,h//4,w//4),
            (512,h//8,w//8),(512,h//8,w//8),(512,h//16,w//16),(512,h//16,w//16)]
        mem=[torch.zeros((b,*shape),dtype=torch.int64) for shape in shapes]
        fc_mem=torch.zeros((b,4096),dtype=torch.int64);readout=torch.zeros((b,200),dtype=inp.dtype)
        # Pool maps match the original source's conv1,2,4,6 transitions.
        pools={0:m.pool1,1:m.pool2,3:m.pool3,5:m.pool4}
        for t in range(30):
            rnd=torch.rand_like(inp)
            out=torch.mul(torch.le(rnd*2.0,torch.abs(inp)).float(),torch.sign(inp))
            for i in range(8):
                conv=getattr(m,f'conv{i+1}');bn=getattr(m,f'bn{i+1}_list')[t]
                assert conv.threshold==1.0
                current=bn(conv(out))
                mem[i],out=self.update(mem[i],current,f'conv{i+1}',t)
                if i in pools:out=pools[i](out).clone()
            out=m.avg_pool(out).clone().reshape(b,-1)
            assert m.fc1.threshold==1.0
            fc_mem,out=self.update(fc_mem,m.bnfc_list[t](m.fc1(out)),'fc1',t)
            readout=1*readout+m.fc2(out.clone())
        if self.expected_steps is not None:assert self.compare_index==len(self.expected_steps)
        return readout/30

def cpu_port_manifest():
    source=(P/'bntt_visual_source'/'model.py').read_bytes()
    tree=RemoveCudaPlacement().visit(ast.parse(source.decode()))
    ast.fix_missing_locations(tree)
    return {'source_sha256':hashlib.sha256(source).hexdigest(),
        'transformed_ast_sha256':hashlib.sha256(ast.dump(tree,include_attributes=False).encode()).hexdigest(),
        'transformation':'Only remove explicit parameterless .cuda() calls; no semantic or equation edits',
        'prepared_only':True}
