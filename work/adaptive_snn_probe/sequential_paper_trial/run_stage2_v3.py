"""Predeclared full public test of one integer-neuron model, without retuning."""
from pathlib import Path
import ctypes, hashlib, json, sys, time
sys.dont_write_bytecode = True
import numpy as np
import torch
from integer_glif_numpy_v3 import PUBLIC, UNIT, BITS, load_model, install, normalized
P = Path(__file__).resolve().parent
torch.set_num_threads(8)
torch.set_num_interop_threads(1)
def save(name,obj): (P/name).write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
class Mem(ctypes.Structure):
    _fields_=[('length',ctypes.c_uint32),('load',ctypes.c_uint32)]+[(n,ctypes.c_uint64)for n in('totalPhys','availPhys','totalPage','availPage','totalVirt','availVirt','availExt')]
def free():
    m=Mem();m.length=ctypes.sizeof(m)
    assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return m.availPhys/1024**3
assert not (P/'stage2_v3_plan.json').exists(), 'Use a new version rather than overwrite an experiment.'
plan = dict(unit=UNIT, coefficient_fractional_bits=8, neuron_state_and_current_signed_bits=BITS,
    samples=10000, indices='original order 0..9999', time_steps=2, batch=4, threads=8,
    coefficient_rounding='nearest-even; learned effective kappa quantized separately for previous spike 0/1',
    leakage_rounding='ceil(beta*U/256), all signs', current_rounding='nearest-even of FP32 effective current times256',
    equation='U_next=ceil(beta(previous_spike)*U/256)+I-bias-reset*previous_spike; spike=(U_next>threshold)',
    reset='previous-spike subtractive term from pinned GLIF; no extra immediate reset',
    bias_reset_threshold_rounding='nearest-even of pinned FP32 quantities times256',
    saturation='none; fail if any U/current/next state leaves signed24 contract',
    selection='One fixed unit chosen before any integer inference. No test-set retuning or retraining.',
    scope='Integer neuron states and arithmetic inside original floating convolution/BN/readout network. Not a fully quantized accelerator or vanilla-LIF conversion.',
    accuracy_gate='Report all observed accuracy changes; exact packing later must reproduce this integer reference, not claim floating-model exactness.',
    source_commit='60638b28ff8b688b51867e7dd44f1e065d4892b0')
save('stage2_v3_plan.json',plan)
started=time.monotonic()
# Broad signed scalar check against independent division, including extrema.
u=np.arange(-4096,4096,dtype=np.int64)
for beta in range(257):
    a=(beta*u+255)>>8
    b=-np.floor_divide(-(beta*u),256)
    assert np.array_equal(a,b)
data=np.load(PUBLIC/'full_test10000.npz')
assert data['indices'].tolist()==list(range(10000))
float_reference=np.load(PUBLIC/'full_test_logits_v3.npz')
assert np.array_equal(data['labels'],float_reference['labels'])
model=load_model()
rows=install(model,audit_first_batch=True)
logits=[];minimum_free=float('inf');progress=[]
with torch.inference_mode():
    for start in range(0,10000,4):
        if start%256==0:
            assert free()>=1.2, 'RAM floor reached; retain partial result and resume in a new runner.'
        y=model(normalized(data['images'][start:start+4])).numpy().copy()
        logits.append(y)
        if start==60:
            prefix=np.concatenate(logits);labels=data['labels'][:64]
            assert np.array_equal(prefix,np.load(P/'stage2_int64_pilot_logits.npz')['logits'])
            save('stage2_v3_pilot.json',dict(status='pass_integer_contract',samples=64,
                correct=int((prefix.argmax(1)==labels).sum()),
                float_correct=int((float_reference['predictions'][:64]==labels).sum()),
                class_disagreements=int((prefix.argmax(1)!=float_reference['predictions'][:64]).sum()),
                independent_state_mismatches=sum(r['independent_state_mismatches']for r in rows.values()),
                independent_spike_mismatches=sum(r['independent_spike_mismatches']for r in rows.values()),
                scalar_cases=257*8192,rows=rows,elapsed_seconds=time.monotonic()-started))
            assert all(r['independent_state_mismatches']==r['independent_spike_mismatches']==0 for r in rows.values())
        if (start+4)%256==0 or start+4==10000:
            n=start+4;prediction=np.concatenate(logits).argmax(1)
            minimum_free=min(minimum_free,free())
            point=dict(completed=n,correct=int((prediction==data['labels'][:n]).sum()),
                class_disagreements=int((prediction!=float_reference['predictions'][:n]).sum()),
                elapsed_seconds=time.monotonic()-started,free_RAM_GiB=free())
            progress.append(point);save('stage2_v3_progress.json',dict(status='running',**point))
            print('INTEGER TEST',n,'/10000',point['correct'],'correct',round(point['elapsed_seconds'],1),'seconds',flush=True)
full=np.concatenate(logits);prediction=full.argmax(1);labels=data['labels']
np.savez_compressed(P/'stage2_v3_logits.npz',logits=full,predictions=prediction,labels=labels,indices=data['indices'])
result=dict(status='complete_integer_neuron_public_test',samples=10000,
    correct=int((prediction==labels).sum()),accuracy_percent=100*float((prediction==labels).mean()),
    float_correct=int((float_reference['predictions']==labels).sum()),
    float_accuracy_percent=100*float((float_reference['predictions']==labels).mean()),
    class_disagreements=int((prediction!=float_reference['predictions']).sum()),
    integer_correct_float_wrong=int(((prediction==labels)&(float_reference['predictions']!=labels)).sum()),
    float_correct_integer_wrong=int(((prediction!=labels)&(float_reference['predictions']==labels)).sum()),
    scalar_cases=257*8192,observed_neuron_updates=sum(r['updates']for r in rows.values()),
    independent_first_batch_state_mismatches=sum(r['independent_state_mismatches']for r in rows.values()),
    independent_first_batch_spike_mismatches=sum(r['independent_spike_mismatches']for r in rows.values()),
    minimum_sampled_free_RAM_GiB=minimum_free,elapsed_seconds=time.monotonic()-started,rows=rows,progress=progress,
    scope=plan['scope'],all_state_ranges_checked=True,packing_executed=False,hardware_replay=False,
    pins={str(p):sha(p)for p in[Path(__file__),P/'integer_glif_numpy_v3.py',P/'stage2_v3_plan.json',P/'stage2_v3_logits.npz',
        PUBLIC/'full_test10000.npz',PUBLIC/'assets/glif_cifar10_T2.pth.tar',PUBLIC/'full_test_results_v3.json',
        PUBLIC/'full_test_logits_v3.npz',PUBLIC/'sources/layers.py',PUBLIC/'sources/networks_for_CIFAR.py']})
result['accuracy_difference_percentage_points']=result['accuracy_percent']-result['float_accuracy_percent']
save('stage2_v3_results.json',result);save('stage2_v3_progress.json',dict(status='complete',completed=10000,correct=result['correct']))
print('STAGE2 COMPLETE',result['accuracy_percent'],'percent; float',result['float_accuracy_percent'],flush=True)
