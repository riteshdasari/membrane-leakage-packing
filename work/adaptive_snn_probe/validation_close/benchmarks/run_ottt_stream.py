"""FP32-original plus packed integer full-feedback, no third redundant network."""
from run_ottt_v3 import P,model,sha,dump,inference
from ottt_integer_v3 import StreamIntegerLIF
from modules import neuron
import argparse,datetime,json,time
import numpy as np
import torch
import ctypes
from ctypes import wintypes
class MemoryStatus(ctypes.Structure):
    _fields_=[('length',wintypes.DWORD),('load',wintypes.DWORD),('total',ctypes.c_ulonglong),('available',ctypes.c_ulonglong),('total_page',ctypes.c_ulonglong),('avail_page',ctypes.c_ulonglong),('total_virtual',ctypes.c_ulonglong),('avail_virtual',ctypes.c_ulonglong),('extended',ctypes.c_ulonglong)]
def free_memory():
    m=MemoryStatus();m.length=ctypes.sizeof(m);ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m));return m.available/(1024**3)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--samples',type=int,default=16);ap.add_argument('--batch',type=int,default=8)
    ap.add_argument('--threads',type=int,default=4);ap.add_argument('--name',default='profile16_a0');args=ap.parse_args()
    torch.set_num_threads(args.threads);torch.set_num_interop_threads(1);torch.manual_seed(2022)
    outdir=P/args.name;outdir.mkdir(exist_ok=False)
    data_path=P.parents[1]/'public_model_trial'/'full_test10000.npz';checkpoint=P/'cifar10_ottta.pth'
    plan={'samples':args.samples,'batch':args.batch,'threads':args.threads,
        'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_commit':json.loads((P/'ottt_commit.json').read_text())['sha'],
        'checkpoint_sha256':sha(checkpoint),'data_sha256':sha(data_path),
        'runner_sha256':sha(__file__),'adapter_sha256':sha(P/'ottt_integer_v3.py'),
        'packing_sha256':sha(P/'ottt_integer_v2.py'),'contract_sha256':sha(P/'ottt_contract.md'),
        'separate_feedback64_sha256':sha(P/'cifar10_T6_n64_a2'/'results.json'),
        'validation':'Every packed leakage checked against independent scalar ceil before actualpackedfeedback; separate64threeexecution allstates/spikes/logits check retained'}
    dump(outdir/'plan.json',plan)
    state=torch.load(checkpoint,map_location='cpu',weights_only=True)
    fp=model(neuron.OnlineLIFNode).eval();integer=model(StreamIntegerLIF).eval()
    for net in (fp,integer):net.load_state_dict(state['net'],strict=True)
    nodes=[(name,nd) for name,nd in integer.named_modules() if isinstance(nd,StreamIntegerLIF)]
    for name,nd in nodes:nd.layer_name=name
    arrays=np.load(data_path);images=arrays['images'][:args.samples];labels=arrays['labels'][:args.samples]
    mean=torch.tensor([.4914,.4822,.4465])[None,:,None,None];std=torch.tensor([.2023,.1994,.2010])[None,:,None,None]
    logits=[[],[]];started=time.time();minfree=free_memory()
    with torch.inference_mode():
        for first in range(0,args.samples,args.batch):
            x=torch.from_numpy(images[first:first+args.batch].copy()).permute(0,3,1,2).float()/255;x=(x-mean)/std
            for name,nd in nodes:nd.capture=first<64;nd.batch_index=first
            values=[inference(fp,x),inference(integer,x)]
            for i,v in enumerate(values):logits[i].append(v.numpy())
            minfree=min(minfree,free_memory())
            progress={'processed':first+len(x),'elapsed_s':time.time()-started,'minimum_observed_free_GiB':minfree,
                'estimated_total_s':(time.time()-started)*args.samples/(first+len(x))}
            dump(outdir/'progress.json',progress)
            if first%128==0 or first+len(x)==args.samples:print(json.dumps(progress),flush=True)
    values=[np.concatenate(z) for z in logits];pred=[v.argmax(1) for v in values]
    np.savez_compressed(outdir/'logits.npz',float=values[0],integer=values[1],labels=labels)
    total={};frames=[]
    for _,nd in nodes:
        for k,v in nd.stats.items():total[k]=total.get(k,0)+v
        frames.extend(nd.sample_frames)
    # Restore original batch -> timestep -> layer order, retaining neuron order.
    layer_order={name:i for i,(name,_) in enumerate(nodes)}
    frames.sort(key=lambda f:(f['batch_first_image'],f['timestep'],layer_order[f['layer']]))
    dump(outdir/'actual_operand_frames.json',frames)
    text=[str(len(frames))]
    for f in frames:
        text.append(str(len(f['u'])));text.extend(f'{v} 128' for v in f['u'])
    (outdir/'actual_operand_frames.txt').write_text('\n'.join(text)+'\n')
    result={**plan,'elapsed_s':time.time()-started,'minimum_observed_free_GiB':minfree,
        'correct':{'float':int((pred[0]==labels).sum()),'integer_packed':int((pred[1]==labels).sum())},
        'changed_integer_vs_float_predictions':int((pred[0]!=pred[1]).sum()),
        'checkpoint_saved_max_accuracy_metadata':state.get('max_test_acc'),
        'operation_counts':total,'range_by_layer':{name:nd.ranges for name,nd in nodes},
        'sample_operand_count':sum(len(f['u']) for f in frames),
        'sample_u_min':min(min(f['u']) for f in frames),'sample_u_max':max(max(f['u']) for f in frames),
        'sample_sha256':sha(outdir/'actual_operand_frames.txt'),
        'exact_shift_control':'tau2 => ceil(U/2), zero DSP; no measured DSP advantage over shift',
        'domain_note':'B12 unsupportedexceptions exactsoftwarefallback retained; B16 requestcounts use same signed9pairing, no newRTLclaim'}
    dump(outdir/'results.json',result);print(json.dumps(result,indent=2),flush=True)
if __name__=='__main__':main()
