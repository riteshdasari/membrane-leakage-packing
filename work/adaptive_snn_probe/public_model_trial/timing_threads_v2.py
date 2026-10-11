"""Measure faster safe CPU inference settings; same model and test64."""
from pathlib import Path
import json,sys,time
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;sys.path[:0]=[str(P/'sources'),str(P/'deps')]
import numpy as np
import torch
import networks_for_CIFAR as networks
torch.set_num_interop_threads(1)
params={'gate':[.6,.8,.6],'param':[.25,.5,.0625,.5],'t':2,'static_gate':False,'static_param':False,'time_wise':False,'soft_mode':True}
model=networks.ResNet_18_stand_CW(params,n_class=10)
model.load_state_dict(torch.load(P/'assets/glif_cifar10_T2.pth.tar',map_location='cpu',weights_only=True)['state_dict'],strict=True);model.eval()
data=np.load(P/'pilot_test64.npz');original=np.load(P/'pilot_logits.npz')['logits']
x=torch.from_numpy(data['images'].transpose(0,3,1,2).copy()).float()/255
x=(x-torch.tensor([.4914,.4822,.4465]).view(1,3,1,1))/torch.tensor([.247,.243,.261]).view(1,3,1,1)
rows=[]
with torch.inference_mode():
    for threads,batch in((4,4),(8,4),(8,16)):
        torch.set_num_threads(threads);started=time.monotonic()
        y=torch.cat([model(x[s:s+batch])for s in range(0,64,batch)]).numpy();elapsed=time.monotonic()-started
        rows.append(dict(threads=threads,batch=batch,samples=64,elapsed_seconds=elapsed,
            class_disagreements=int((y.argmax(1)!=original.argmax(1)).sum()),max_logit_difference=float(np.abs(y-original).max())))
        print('CPU TIMING',rows[-1],flush=True)
(P/'thread_timing_v2.json').write_text(json.dumps(dict(status='measured_unmodified_model',rows=rows),indent=2)+'\n')
