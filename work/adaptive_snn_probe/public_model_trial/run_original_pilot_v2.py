"""Official floating GLIF inference and observed operand compatibility screen."""
from pathlib import Path
import hashlib,json,sys,time,types
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
sys.path[:0]=[str(P/'sources'),str(P/'deps')]
import numpy as np
import torch
import networks_for_CIFAR as networks
from layers import LIFSpike_CW
torch.set_num_threads(8);torch.set_num_interop_threads(1)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')
assert not(P/'original_pilot_results_v2.json').exists()
plan=json.loads((P/'original_pilot_plan_v2.json').read_text());units=plan['units']
params={'gate':[.6,.8,.6],'param':[.25,.5,.0625,.5],'t':2,'static_gate':False,
    'static_param':False,'time_wise':False,'soft_mode':True}
model=networks.ResNet_18_stand_CW(params,n_class=10)
checkpoint=torch.load(P/'assets/glif_cifar10_T2.pth.tar',map_location='cpu',weights_only=True)
model.load_state_dict(checkpoint['state_dict'],strict=True);model.eval()
dataset=np.load(P/'original_test64.npz');assert dataset['indices'].tolist()==plan['indices']
pixels=dataset['images'];labels=dataset['labels']
mean=torch.tensor([.4914,.4822,.4465]).view(1,3,1,1)
std=torch.tensor([.247,.243,.261]).view(1,3,1,1)
observers={};state_disagreements=spike_disagreements=0
def signed_width(lo,hi):
    bits=1
    while lo<-(1<<(bits-1))or hi>=(1<<(bits-1)):bits+=1
    return bits
def observe(name,base,current,new,spikes,reset):
    record=observers.setdefault(name,dict(updates=0,spikes=0,base_min=float('inf'),base_max=-float('inf'),
        current_min=float('inf'),current_max=-float('inf'),units={str(s):dict(updates=0,
            U_min=10**30,U_max=-10**30,I_min=10**30,I_max=-10**30,S_min=10**30,S_max=-10**30,
            U_fits_i8=0,I_fits_i8=0,both_fit_i8=0,current_outside_i8=0)for s in units}))
    record['updates']+=base.numel();record['spikes']+=int(spikes.sum())
    record['base_min']=min(record['base_min'],float(base.min()));record['base_max']=max(record['base_max'],float(base.max()))
    record['current_min']=min(record['current_min'],float(current.min()));record['current_max']=max(record['current_max'],float(current.max()))
    b=base.numpy();i=current.numpy()
    for s in units:
        u=np.rint(b*s).astype(np.int64);c=np.rint(i*s).astype(np.int64);total=u+c
        r=record['units'][str(s)];uf=(u>=-128)&(u<=127);cf=(c>=-128)&(c<=127)
        for symbol,array in(('U',u),('I',c),('S',total)):
            r[symbol+'_min']=min(r[symbol+'_min'],int(array.min()));r[symbol+'_max']=max(r[symbol+'_max'],int(array.max()))
        r['updates']+=u.size;r['U_fits_i8']+=int(uf.sum());r['I_fits_i8']+=int(cf.sum())
        r['both_fit_i8']+=int((uf&cf).sum());r['current_outside_i8']+=int((~cf).sum())
def wrap(name,original):
    def instrument(self,u,o,w,tau,Vth,leak,conduct,reVth):
        nonlocal_dummy=None
        global state_disagreements,spike_disagreements
        # Match the original operator grouping, including its final reset subtraction.
        al=self.alpha.view(1,-1,1,1).sigmoid();be=self.beta.view(1,-1,1,1).sigmoid();ga=self.gamma.view(1,-1,1,1).sigmoid()
        current=w*(1-be*(1-conduct[None,:,None,None]))
        base=((1-al*(1-tau[None,:,None,None]))*u*(1-ga*o.clone())-(1-al)*leak[None,:,None,None])
        reset=(1-ga)*reVth[None,:,None,None]*o.clone()
        expected=base+current-reset;expected_spikes=(expected-Vth[None,:,None,None]>0).float()
        new,spikes=original(u,o,w,tau,Vth,leak,conduct,reVth)
        state_disagreements+=int((new!=expected).sum());spike_disagreements+=int((spikes!=expected_spikes).sum())
        observe(name,base,current,new,spikes,reset)
        return new,spikes
    return instrument
for name,module in model.named_modules():
    if isinstance(module,LIFSpike_CW):module.extended_state_update=types.MethodType(wrap(name,module.extended_state_update),module)
started=time.monotonic();logits=[]
with torch.inference_mode():
    for start in range(0,len(labels),4):
        x=torch.from_numpy(pixels[start:start+4].transpose(0,3,1,2).copy()).float()/255
        y=model((x-mean)/std);logits.append(y.numpy().copy())
        print('PILOT',min(start+4,len(labels)),len(labels),'elapsed',round(time.monotonic()-started,1),flush=True)
logits=np.concatenate(logits);pred=logits.argmax(axis=1)
assert state_disagreements==spike_disagreements==0
for r in observers.values():
    for s,x in r['units'].items():
        for key in('U','I','S'):x[key+'_observed_signed_bits']=signed_width(x[key+'_min'],x[key+'_max'])
        x['U8_fraction']=x['U_fits_i8']/x['updates'];x['I8_fraction']=x['I_fits_i8']/x['updates']
        x['both8_fraction']=x['both_fit_i8']/x['updates']
        x['five_full_three_U8_metadata_FF_saving_vs_fixed8_if_contract_legal']=3*max(x['U_observed_signed_bits']-max(8,x['I_observed_signed_bits']),0)
np.savez_compressed(P/'original_pilot_logits_v2.npz',logits=logits,predictions=pred,labels=labels,indices=dataset['indices'])
result=dict(status='pass_official_float_model_operand_observer',model='Official GLIF ResNet18 CIFAR10 T2 CW',
    samples=len(labels),correct=int((pred==labels).sum()),accuracy_percent=100*float((pred==labels).mean()),
    full_test_accuracy=False,elapsed_seconds=time.monotonic()-started,neuron_layers=len(observers),
    neuron_updates=sum(r['updates']for r in observers.values()),spikes=sum(r['spikes']for r in observers.values()),
    observer_float_state_disagreements=state_disagreements,observer_spike_disagreements=spike_disagreements,
    rows=[dict(layer=k,**v)for k,v in observers.items()],
    scope='Float inference with bit-identical observation of its existing U+I component. Unit sweeps are rounded observed-operand screens, not integer inference, safe width certificates, RTL replay, quantization accuracy or FireFly replication.',
    runtime=dict(python=sys.version,torch=torch.__version__,spikingjelly='0.0.0.0.10',device='cpu',threads=8),
    pins={str(p):sha(p)for p in[Path(__file__),P/'original_pilot_plan_v2.json',P/'original_test64.npz',P/'assets/glif_cifar10_T2.pth.tar',
        P/'source_acquisition.json',P/'framework_acquisition.json',P/'full_data_acceptance_v2.json',P/'sources/layers.py',
        P/'sources/blocks.py',P/'sources/networks_for_CIFAR.py',P/'original_pilot_logits_v2.npz']})
save(P/'original_pilot_results_v2.json',result)
print(json.dumps({k:v for k,v in result.items()if k not in('rows','pins','runtime')},indent=2),flush=True)
