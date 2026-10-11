import argparse,datetime,hashlib,json,sys,time
from pathlib import Path
import numpy as np
import torch
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P/'ottt_source'))
from models import spiking_vgg
from modules import neuron,surrogate
from ottt_integer import IntegerLIF
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def dump(path,obj):path.write_text(json.dumps(obj,indent=2))
def model(node):
    return spiking_vgg.online_spiking_vgg11_ws(single_step_neuron=node,
        tau=2.,surrogate_function=surrogate.Sigmoid(),track_rate=True,c_in=3,
        num_classes=10,neuron_dropout=0.,grad_with_rate=True,fc_hw=1,v_reset=None)
def inference(net,x):
    out=None
    for t in range(6):
        value=net(x,init=t==0,save_spike=True)
        out=value.clone() if out is None else out+value
    return out
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--samples',type=int,default=64)
    ap.add_argument('--batch',type=int,default=4);ap.add_argument('--threads',type=int,default=2)
    args=ap.parse_args();torch.set_num_threads(args.threads);torch.set_num_interop_threads(1)
    torch.manual_seed(2022);np.random.seed(2022)
    outdir=P/f'cifar10_T6_n{args.samples}_a1';outdir.mkdir(exist_ok=False)
    data_path=P.parents[1]/'public_model_trial'/'full_test10000.npz'
    ckpt_path=P/'cifar10_ottta.pth'
    plan={'samples':args.samples,'batch':args.batch,'threads':args.threads,
        'source_commit':json.loads((P/'ottt_commit.json').read_text())['sha'],
        'checkpoint_sha256':sha(ckpt_path),'data_sha256':sha(data_path),
        'contract_sha256':sha(P/'ottt_contract.md'),'runner_sha256':sha(__file__),
        'integer_sha256':sha(P/'ottt_integer.py')}
    dump(outdir/'plan.json',plan)
    ckpt=torch.load(ckpt_path,map_location='cpu',weights_only=True)
    fp=model(neuron.OnlineLIFNode).eval()
    integer=model(IntegerLIF).eval();packed=model(IntegerLIF).eval()
    for net in (fp,integer,packed):net.load_state_dict(ckpt['net'],strict=True)
    for node in packed.modules():
        if isinstance(node,IntegerLIF):node.packed=True
    arrays=np.load(data_path)
    images=arrays['images'][:args.samples];labels=arrays['labels'][:args.samples]
    assert images.dtype==np.uint8
    mean=torch.tensor([.4914,.4822,.4465])[None,:,None,None]
    std=torch.tensor([.2023,.1994,.2010])[None,:,None,None]
    all_logits=[[],[],[]];counts={};state_mismatch=spike_mismatch=0
    ranges={};started=time.time()
    with torch.inference_mode():
        for base in range(0,args.samples,args.batch):
            x=torch.from_numpy(images[base:base+args.batch].copy()).permute(0,3,1,2).float()/255
            x=(x-mean)/std
            outs=[inference(net,x) for net in (fp,integer,packed)]
            for i,out in enumerate(outs):all_logits[i].append(out.numpy())
            print({'logit_max_diff':float((outs[1]-outs[2]).abs().max())},flush=True)
            inode=[(n,m) for n,m in integer.named_modules() if isinstance(m,IntegerLIF)]
            pnode=[(n,m) for n,m in packed.named_modules() if isinstance(m,IntegerLIF)]
            for (name,ia),(pname,pa) in zip(inode,pnode):
                assert name==pname
                for it,pt in zip(ia.steps,pa.steps):
                    state_mismatch+=int(torch.count_nonzero(it['state_digest']!=pt['state_digest']))
                    spike_mismatch+=int(torch.count_nonzero(it['spike_digest']!=pt['spike_digest']))
                    r=ranges.setdefault(name,{k:it[k] for k in it if not k.endswith('digest')})
                    for k in r:r[k]=(min if k.endswith('min') else max)(r[k],it[k])
                for key,val in pa.stats.items():counts[key]=counts.get(key,0)+val
                pa.stats={}
                ia.steps=[];pa.steps=[]
            dump(outdir/'progress.json',{'processed':base+len(x),'elapsed_s':time.time()-started})
            print(json.dumps({'processed':base+len(x),'elapsed_s':round(time.time()-started,3)}),flush=True)
    values=[np.concatenate(z) for z in all_logits]
    predictions=[v.argmax(1) for v in values]
    np.savez_compressed(outdir/'logits.npz',float=values[0],integer=values[1],packed=values[2],labels=labels)
    result={**plan,'elapsed_s':time.time()-started,'checkpoint_saved_max_accuracy':ckpt.get('max_test_acc'),
        'correct':dict(zip(('float','integer','packed'),[int((p==labels).sum()) for p in predictions])),
        'integer_vs_float_changed_classes':int((predictions[0]!=predictions[1]).sum()),
        'packed_vs_integer_changed_classes':int((predictions[1]!=predictions[2]).sum()),
        'packed_vs_integer_logits_equal':bool(np.array_equal(values[1],values[2])),
        'state_mismatches':state_mismatch,'spike_mismatches':spike_mismatch,
        'range_by_layer':ranges,'operation_counts':counts,
        'leak':{'beta_q8':128,'tau':2,'exact_shift_control':'ceil(U/2), zero DSP'},
        'hardware_domain_coverage':1-counts['signed12_exceptions']/max(1,counts['nonzero']),
        'scope':'Software full feedback; FP32 synapses/readout; no FPGA performance or energy claim'}
    dump(outdir/'results.json',result);print(json.dumps(result,indent=2))
if __name__=='__main__':main()
