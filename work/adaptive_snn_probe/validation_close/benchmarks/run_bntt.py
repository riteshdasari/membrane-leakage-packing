"""Prepared bounded benchmark; run only after coordinating RAM with root."""
import argparse, ctypes, datetime, hashlib, io, json, time, zipfile
from pathlib import Path
import numpy as np
import torch
from PIL import Image
from torchvision.transforms import functional as TF
from bntt_integer import IntegerBNTT,original_cpu_module,cpu_port_manifest

P=Path(__file__).resolve().parent

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def dump(path,obj):path.write_text(json.dumps(obj,indent=2)+'\n')

def scalar_metadata(value):
    if isinstance(value,torch.Tensor):return value.item() if value.numel()==1 else {'tensor_shape':list(value.shape)}
    if isinstance(value,np.generic):return value.item()
    if isinstance(value,(int,float,str,bool)) or value is None:return value
    return str(type(value))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--samples',type=int,default=64)
    ap.add_argument('--threads',type=int,default=4);ap.add_argument('--name',default='tiny_T30_n64_a0')
    args=ap.parse_args();assert 1<=args.samples<=64 and 1<=args.threads<=4
    torch.set_num_threads(args.threads);torch.set_num_interop_threads(1)
    outdir=P/args.name;outdir.mkdir(exist_ok=False)
    acquisition=json.loads((P/'bntt_acquisition.json').read_text())
    for filename,expected_hash in acquisition['source_files_sha256'].items():
        assert sha(P/'bntt_visual_source'/filename)==expected_hash,filename
    checkpoint=P/'bntt_pretrained_tiny_t30.pth.tar';dataset=P/'tiny-imagenet-200.zip'
    cpusource=cpu_port_manifest()
    for asset in acquisition['assets']:
        assert sha(P/asset['filename'])==asset['sha256']
    selected=np.sort(np.random.default_rng(20211001).choice(10000,64,replace=False))[:args.samples]
    declared=json.loads((P/'bntt_predeclared_subset.json').read_text())
    assert selected.tolist()==[s['canonical_index'] for s in declared['samples'][:args.samples]]
    plan={'samples':args.samples,'threads':args.threads,'batch':1,'timesteps':30,
        'source_commit':acquisition['source_commit'],'source_cpu_port':cpusource,
        'checkpoint_sha256':sha(checkpoint),'dataset_sha256':sha(dataset),
        'contract_sha256':sha(P/'bntt_contract.md'),'runner_sha256':sha(__file__),
        'adapter_sha256':sha(P/'bntt_integer.py'),'packing_sha256':sha(P/'ottt_integer_v2.py'),
        'predeclared_subset_sha256':sha(P/'bntt_predeclared_subset.json'),
        'subset_selection':'Sorted firstN of predeclared64 canonical validation indices from NumPy default_rng20211001 without replacement',
        'selected_indices':selected.tolist(),'poisson_per_image_seed':'2021+canonical validation index; reset identically for every original/plaininteger/packed execution',
        'declared_conversion':'unit1/256; beta253; ceil253U/256; RNE BN effective currents; spike oldU>256; nextU=leak+current−256spike',
        'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    dump(outdir/'plan.json',plan)
    original=original_cpu_module()
    # Legacy author file has a NumPy scalar accuracy metadata field. Permit only
    # those audited NumPy scalar/dtype constructors, retaining weights_only.
    allow=[(np._core.multiarray.scalar,'numpy.core.multiarray.scalar'),
        np.dtype,type(np.dtype('float64')),type(np.dtype('float32'))]
    with torch.serialization.safe_globals(allow):
        state=torch.load(checkpoint,map_location='cpu',weights_only=True)
    assert isinstance(state,dict) and 'state_dict' in state
    weights=state['state_dict']
    if all(k.startswith('module.') for k in weights):weights={k[7:]:v for k,v in weights.items()}
    nets=[original.SNN_VGG11(num_timestep=30,leak_mem=.99).eval() for _ in range(3)]
    for net in nets:net.load_state_dict(weights,strict=True)
    for key,tensor in nets[0].state_dict().items():
        assert all(torch.equal(tensor,net.state_dict()[key]) for net in nets[1:])
    checkpoint_metadata={k:scalar_metadata(v) for k,v in state.items() if k not in ('state_dict','optimizer')}
    del state,weights
    plain=IntegerBNTT(nets[1],packed=False,retain_steps=True)
    packed=IntegerBNTT(nets[2],packed=True,retain_steps=False)
    arrays=[[],[],[]];labels=[];sample_metadata=[];started=time.time()
    mean=torch.tensor([.485,.456,.406])[:,None,None];std=torch.tensor([.229,.224,.225])[:,None,None]
    with zipfile.ZipFile(dataset) as z,torch.inference_mode():
        classes=sorted(z.read('tiny-imagenet-200/wnids.txt').decode().splitlines())
        class_to_idx={name:i for i,name in enumerate(classes)}
        rows={r[0]:r[1] for r in (line.split('\t') for line in z.read('tiny-imagenet-200/val/val_annotations.txt').decode().splitlines())}
        for number,index in enumerate(selected):
            # Canonical image suffix defines sample identity, independent of archive listing order.
            filename=f'val_{int(index)}.JPEG';label=class_to_idx[rows[filename]]
            jpeg=z.read('tiny-imagenet-200/val/images/'+filename)
            with Image.open(io.BytesIO(jpeg)) as image:
                x=TF.to_tensor(image.convert('RGB'));assert tuple(x.shape)==(3,64,64)
            x=((x-mean)/std)[None].contiguous()
            seed=2021+int(index)
            torch.manual_seed(seed);fp=nets[0](x)
            torch.manual_seed(seed);integer=plain(x)
            packed.expected_steps=plain.steps
            torch.manual_seed(seed);e5=packed(x)
            assert packed.state_mismatches==packed.spike_mismatches==0
            assert torch.equal(integer,e5)
            packed.expected_steps=None;plain.steps=[]
            for target,v in zip(arrays,(fp,integer,e5)):target.append(v.numpy())
            labels.append(label);sample_metadata.append({'canonical_index':int(index),'image':filename,'class_id':rows[filename],
                'label':label,'jpeg_sha256':hashlib.sha256(jpeg).hexdigest(),'poisson_seed':seed})
            elapsed=time.time()-started
            progress={'processed':number+1,'elapsed_s':elapsed,'estimated_total_s':elapsed*args.samples/(number+1)}
            dump(outdir/'progress.json',progress)
            print(json.dumps(progress),flush=True)
    values=[np.concatenate(v) for v in arrays];labels=np.asarray(labels)
    predictions=[v.argmax(1) for v in values]
    np.savez_compressed(outdir/'logits.npz',float=values[0],integer=values[1],packed=values[2],labels=labels,indices=selected)
    dump(outdir/'selected_images.json',sample_metadata)
    supported=packed.stats['old_signed16_exceptions']==packed.stats['stored_signed16_exceptions']==0
    result={**plan,'elapsed_s':time.time()-started,
        'correct':dict(zip(('float','integer','packed'),[int((p==labels).sum()) for p in predictions])),
        'integer_vs_float_changed_predictions':int((predictions[0]!=predictions[1]).sum()),
        'packed_vs_integer_changed_predictions':int((predictions[1]!=predictions[2]).sum()),
        'packed_vs_integer_logits_bit_equal':bool(np.array_equal(values[1],values[2])),
        'state_mismatches':packed.state_mismatches,'spike_mismatches':packed.spike_mismatches,
        'operation_counts':packed.stats,'range_by_layer':packed.ranges,
        'fixed16_hardware_domain_supported':supported,
        'constant_specific_zero_DSP_control':'ceil(253U/256)=U−floor(3U/256); form3U with shift/add and use arithmetic shift8 then subtract at sufficient width',
        'checkpoint_accuracy_metadata':checkpoint_metadata,
        'scope':'Bounded actual public checkpoint evaluation; FP32 synapses/BN/readout; coefficient conversion253/256 is approximate versus .99 FP32; exact packing versus plain declared integer; no board energy/performance claim; outside signed16 explicitly unsupported'}
    dump(outdir/'results.json',result);print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':main()
