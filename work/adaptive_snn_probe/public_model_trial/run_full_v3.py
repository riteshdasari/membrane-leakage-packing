"""Complete all10000 test samples using the fastest pilot-exact CPU setting."""
from pathlib import Path
import hashlib,json,sys,time,ctypes
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;sys.path[:0]=[str(P/'sources'),str(P/'deps')]
import numpy as np
import torch
import networks_for_CIFAR as networks
torch.set_num_threads(8);torch.set_num_interop_threads(1)
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
class Mem(ctypes.Structure):
    _fields_=[('length',ctypes.c_uint32),('load',ctypes.c_uint32)]+[(n,ctypes.c_uint64)for n in('totalPhys','availPhys','totalPage','availPage','totalVirt','availVirt','availExt')]
def free_gib():
    m=Mem();m.length=ctypes.sizeof(m);assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m));return m.availPhys/(1024**3)
timing=json.loads((P/'thread_timing_v2.json').read_text())
row=next(x for x in timing['rows']if x['threads']==8 and x['batch']==4)
assert row['class_disagreements']==0 and row['max_logit_difference']==0
plan=dict(samples=10000,indices='0..9999 in original order',threads=8,batch=4,free_RAM_floor_GiB=1.2,
    reference='Unmodified pinned original GLIF code/checkpoint, CPU FP32. No quantization or hardware replay.',
    selection='Fastest measured pilot setting with bit-identical logits',full_dataset_integrity_required=True)
assert not(P/'full_test_plan_v3.json').exists();save(P/'full_test_plan_v3.json',plan)
params={'gate':[.6,.8,.6],'param':[.25,.5,.0625,.5],'t':2,'static_gate':False,'static_param':False,'time_wise':False,'soft_mode':True}
model=networks.ResNet_18_stand_CW(params,n_class=10)
state=torch.load(P/'assets/glif_cifar10_T2.pth.tar',map_location='cpu',weights_only=True)['state_dict']
model.load_state_dict(state,strict=True);model.eval()
np.savez_compressed(P/'checkpoint_arrays_v3.npz',**{k:v.numpy()for k,v in state.items()});del state
while not(P/'full_data_acceptance_v2.json').exists()or not(P/'original_pilot_results_v2.json').exists():time.sleep(3)
data=np.load(P/'full_test10000.npz');assert data['indices'].tolist()==list(range(10000))
pixels=data['images'];labels=data['labels'];original=np.load(P/'original_pilot_logits_v2.npz')['logits']
mean=torch.tensor([.4914,.4822,.4465]).view(1,3,1,1);std=torch.tensor([.247,.243,.261]).view(1,3,1,1)
started=time.monotonic();logits=[];memory=[];prefix_results=[]
with torch.inference_mode():
    for start in range(0,10000,4):
        if start%256==0:
            while free_gib()<1.2:
                print('WAIT AVAILABLE RAM',round(free_gib(),2),'GiB',flush=True);time.sleep(5)
        x=torch.from_numpy(pixels[start:start+4].transpose(0,3,1,2).copy()).float()/255
        y=model((x-mean)/std).numpy().copy();logits.append(y)
        if start<64:assert np.array_equal(y,original[start:start+4])
        if (start+4)%256==0 or start+4==10000:
            completed=start+4;correct=sum(int((v.argmax(1)==labels[i*4:i*4+len(v)]).sum())for i,v in enumerate(logits))
            point=dict(completed=completed,correct=correct,elapsed_seconds=time.monotonic()-started,free_RAM_GiB=free_gib())
            memory.append(point['free_RAM_GiB']);prefix_results.append(point)
            save(P/'full_test_progress_v3.json',dict(status='running',**point,full_test=False))
            print('FULL TEST',completed,10000,'correct',correct,'seconds',round(point['elapsed_seconds'],1),flush=True)
full=np.concatenate(logits);prediction=full.argmax(1)
np.savez_compressed(P/'full_test_logits_v3.npz',logits=full,predictions=prediction,labels=labels,indices=np.arange(10000))
result=dict(status='complete_official_float_model_test10000',model='GLIF ResNet18 CIFAR10 T2 CW',samples=10000,
    correct=int((prediction==labels).sum()),accuracy_percent=100*float((prediction==labels).mean()),
    elapsed_seconds=time.monotonic()-started,full_test=True,batch=4,threads=8,neuron_time_steps=2,
    packed_integer_model=False,hardware_replay=False,minimum_sampled_free_RAM_GiB=min(memory),
    first64_logits_bit_identical_to_observed_pilot=True,progress_points=prefix_results,
    pins={str(p):sha(p)for p in[Path(__file__),P/'full_test_plan_v3.json',P/'assets/glif_cifar10_T2.pth.tar',P/'full_test10000.npz',
        P/'full_test_logits_v3.npz',P/'checkpoint_arrays_v3.npz',P/'sources/layers.py',P/'sources/blocks.py',P/'sources/networks_for_CIFAR.py',
        P/'full_data_acceptance_v2.json',P/'original_pilot_results_v2.json',P/'thread_timing_v2.json',P/'preview_pilot_rejection.json']},
    scope='Full public floating-point model accuracy in local CPU runtime; original reference reproduction gate. No integer SNN, exact packing hardware accuracy, speedup or FireFly replication claim.')
save(P/'full_test_results_v3.json',result);save(P/'full_test_progress_v3.json',dict(status='complete',completed=10000,correct=result['correct'],full_test=True))
print('COMPLETE PUBLIC GLIF TEST',result['accuracy_percent'],'percent',flush=True)
