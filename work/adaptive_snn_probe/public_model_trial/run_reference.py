"""Unmodified official model control and, when acquired, complete test evaluation."""
from pathlib import Path
import hashlib,json,sys,time
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;sys.path[:0]=[str(P/'sources'),str(P/'deps')]
import numpy as np
import torch
import networks_for_CIFAR as networks
torch.set_num_threads(2);torch.set_num_interop_threads(1)
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
params={'gate':[.6,.8,.6],'param':[.25,.5,.0625,.5],'t':2,'static_gate':False,
    'static_param':False,'time_wise':False,'soft_mode':True}
model=networks.ResNet_18_stand_CW(params,n_class=10)
checkpoint=torch.load(P/'assets/glif_cifar10_T2.pth.tar',map_location='cpu',weights_only=True)
model.load_state_dict(checkpoint['state_dict'],strict=True);model.eval()
pilot=np.load(P/'pilot_test64.npz');mean=torch.tensor([.4914,.4822,.4465]).view(1,3,1,1)
std=torch.tensor([.247,.243,.261]).view(1,3,1,1)
def evaluate(images,batch):
    started=time.monotonic();logits=[]
    with torch.inference_mode():
        for start in range(0,len(images),batch):
            x=torch.from_numpy(images[start:start+batch].transpose(0,3,1,2).copy()).float()/255
            logits.append(model((x-mean)/std).numpy().copy())
            if (start//batch)%10==0:print('REFERENCE',min(start+batch,len(images)),len(images),'seconds',round(time.monotonic()-started,1),flush=True)
    return np.concatenate(logits),time.monotonic()-started
control,seconds=evaluate(pilot['images'],4);original=np.load(P/'pilot_logits.npz')
assert np.array_equal(control,original['logits'])
save(P/'unmodified_control_acceptance.json',dict(status='pass_bit_identical_unmodified_model',samples=64,batch=4,
    logits_equal=True,predictions_equal=True,elapsed_seconds=seconds,model_source_sha256=sha(P/'sources/networks_for_CIFAR.py'),
    observer_logit_sha256=sha(P/'pilot_logits.npz'),runner_sha256=sha(Path(__file__))))
fast,timing=evaluate(pilot['images'],32)
save(P/'batch32_screen.json',dict(status='measured',samples=64,elapsed_seconds=timing,
    class_disagreements=int((fast.argmax(1)!=control.argmax(1)).sum()),max_logit_difference=float(np.abs(fast-control).max()),
    full_test_estimated_seconds=timing*10000/64,
    scope='Batch-size and timing compatibility check, not an accuracy or hardware advantage'))
print('UNMODIFIED CONTROL PASS; BATCH32 SECONDS',round(timing,2),flush=True)
if '--full'not in sys.argv:sys.exit(0)
while not(P/'full_test10000.npz').exists():time.sleep(3)
dataset=np.load(P/'full_test10000.npz');assert len(dataset['labels'])==10000
assert np.array_equal(dataset['images'][:64],pilot['images'])and np.array_equal(dataset['labels'][:64],pilot['labels'])
full,elapsed=evaluate(dataset['images'],32);prediction=full.argmax(1)
np.savez_compressed(P/'full_test_logits.npz',logits=full,predictions=prediction,labels=dataset['labels'],indices=np.arange(10000))
save(P/'full_test_results.json',dict(status='complete_official_float_model_test10000',model='GLIF ResNet18 CIFAR10 T2 CW',
    samples=10000,correct=int((prediction==dataset['labels']).sum()),accuracy_percent=100*float((prediction==dataset['labels']).mean()),
    elapsed_seconds=elapsed,full_test=True,batch=32,neuron_time_steps=2,
    packed_integer_model=False,hardware_replay=False,
    pins={str(p):sha(p)for p in[Path(__file__),P/'assets/glif_cifar10_T2.pth.tar',P/'full_test10000.npz',P/'full_test_logits.npz',
        P/'sources/layers.py',P/'sources/blocks.py',P/'sources/networks_for_CIFAR.py',P/'unmodified_control_acceptance.json',P/'batch32_screen.json']},
    scope='Full held-out accuracy of public floating-point model in the local CPU runtime. No quantized model, packing speedup, FireFly model replication or hardware accuracy claim.'))
print('FULL PUBLIC GLIF TEST COMPLETE',int((prediction==dataset['labels']).sum()),10000,flush=True)
