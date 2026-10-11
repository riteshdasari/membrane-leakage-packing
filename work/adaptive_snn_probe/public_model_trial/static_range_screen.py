"""Real-arithmetic workload envelopes; not a bit-true integer certificate."""
from pathlib import Path
import json,time,hashlib
import numpy as np
P=Path(__file__).resolve().parent
while not(P/'checkpoint_arrays.npz').exists():time.sleep(3)
w=np.load(P/'checkpoint_arrays.npz');pilot=json.loads((P/'pilot_results.json').read_text())
def a(key):return w[key].astype(np.float64)
def sigmoid(v):return 1/(1+np.exp(-v))
def conv(prefix,lo,hi,padding):
    weight=a(prefix+'.weight');assert weight.ndim==4
    if padding:lo=np.minimum(lo,0);hi=np.maximum(hi,0)
    positive=np.maximum(weight,0).sum((2,3));negative=np.minimum(weight,0).sum((2,3))
    return positive@lo+negative@hi,positive@hi+negative@lo
def bn(prefix,lo,hi,alpha):
    gain=alpha*float(a(prefix+'.Vth'))*a(prefix+'.weight')/np.sqrt(a(prefix+'.running_var')+1e-5)
    offset=a(prefix+'.bias')-gain*a(prefix+'.running_mean')
    return np.minimum(gain*lo,gain*hi)+offset,np.maximum(gain*lo,gain*hi)+offset
def convbn(prefix,lo,hi,alpha=1,padding=True):
    lo,hi=conv(prefix+'.0',lo,hi,padding);return bn(prefix+'.1',lo,hi,alpha)
def bits(lo,hi):
    n=1
    while lo<-(1<<(n-1))or hi>=(1<<(n-1)):n+=1
    return n
rows=[]
def lif(name,current_lo,current_hi):
    al=sigmoid(a(name+'.alpha'));be=sigmoid(a(name+'.beta'));ga=sigmoid(a(name+'.gamma'))
    decay=1-al*(1-sigmoid(a(name+'.tau')));leak=(1-al)*sigmoid(a(name+'.leak'))
    threshold=sigmoid(a(name+'.Vth'));reset=(1-ga)*sigmoid(a(name+'.reVth'))
    conduct=sigmoid(a(name+'.conduct'));u_lo=np.zeros_like(decay);u_hi=np.zeros_like(decay)
    steps=[]
    for t in range(2):
        factor=1-be*(1-conduct[t]);i_lo=current_lo*factor;i_hi=current_hi*factor
        if t==0:
            base_lo=base_hi=-leak;new_lo=base_lo+i_lo;new_hi=base_hi+i_hi
        else:
            base_lo=np.full_like(decay,np.inf);base_hi=np.full_like(decay,-np.inf)
            new_lo=np.full_like(decay,np.inf);new_hi=np.full_like(decay,-np.inf)
            for spike in(0,1):
                lo=u_lo if spike==0 else np.maximum(u_lo,threshold)
                hi=np.minimum(u_hi,threshold)if spike==0 else u_hi
                valid=lo<=hi;coefficient=decay*(1-ga*spike)
                b_lo=coefficient*lo-leak;b_hi=coefficient*hi-leak
                base_lo=np.where(valid,np.minimum(base_lo,b_lo),base_lo);base_hi=np.where(valid,np.maximum(base_hi,b_hi),base_hi)
                new_lo=np.where(valid,np.minimum(new_lo,b_lo+i_lo-reset*spike),new_lo)
                new_hi=np.where(valid,np.maximum(new_hi,b_hi+i_hi-reset*spike),new_hi)
        assert np.isfinite(new_lo).all()and np.isfinite(new_hi).all()
        steps.append(dict(timestep=t,base_min=float(base_lo.min()),base_max=float(base_hi.max()),
            current_min=float(i_lo.min()),current_max=float(i_hi.max()),state_min=float(new_lo.min()),state_max=float(new_hi.max())))
        u_lo,u_hi=new_lo,new_hi
    base_min=min(x['base_min']for x in steps);base_max=max(x['base_max']for x in steps)
    i_min=min(x['current_min']for x in steps);i_max=max(x['current_max']for x in steps)
    obs=next(x for x in pilot['rows']if x['layer']==name)
    for key,lo,hi in(('base',base_min,base_max),('current',i_min,i_max)):
        tolerance=1e-5*max(1,abs(lo),abs(hi));assert obs[key+'_min']>=lo-tolerance and obs[key+'_max']<=hi+tolerance
    screens=[]
    for scale in(16,64,256,1024):
        # Outward integer cover of the real envelope is a screen, not a newly defined quantized model.
        blo,bhi=int(np.floor(base_min*scale)),int(np.ceil(base_max*scale))
        ilo,ihi=int(np.floor(i_min*scale)),int(np.ceil(i_max*scale))
        screens.append(dict(scale=scale,U_screen_bits=bits(blo,bhi),I_screen_bits=bits(ilo,ihi),
            U_screen_min=blo,U_screen_max=bhi,I_screen_min=ilo,I_screen_max=ihi,
            existing_I8_contract_covered_by_real_envelope=ilo>=-128 and ihi<=127))
    rows.append(dict(layer=name,steps=steps,unit_screens=screens,pilot_inside_real_envelopes=True,
        decay_coefficient_min=float(decay.min()),decay_coefficient_max=float(decay.max())))
    return np.zeros_like(decay),np.ones_like(decay)
image_lo=(np.zeros(3)-np.array([.4914,.4822,.4465]))/np.array([.247,.243,.261])
image_hi=(np.ones(3)-np.array([.4914,.4822,.4465]))/np.array([.247,.243,.261])
cl,ch=convbn('conv1.0',image_lo,image_hi);lo,hi=lif('conv1.1',cl,ch)
for k in range(8):
    p=f'features.{k}'
    cl,ch=convbn(p+'.body.0',lo,hi);inner_lo,inner_hi=lif(p+'.body.1',cl,ch)
    branch_lo,branch_hi=convbn(p+'.body.2',inner_lo,inner_hi,alpha=1/np.sqrt(2))
    if a(p+'.downsample.0.weight').ndim==4:
        skip_lo,skip_hi=convbn(p+'.downsample.0',lo,hi,alpha=1/np.sqrt(2),padding=False)
    else:skip_lo,skip_hi=bn(p+'.downsample.0',lo,hi,1/np.sqrt(2))
    lo,hi=lif(p+'.lif',branch_lo+skip_lo,branch_hi+skip_hi)
result=dict(status='pass_real_arithmetic_envelope_screen',layers=len(rows),rows=rows,
    pilot_operand_envelope_violations=0,
    scope='Real-valued affine/convolution envelopes for all allowed input pixels and binary intermediate spikes, plus correlated previous-spike GLIF bounds atT2. Separate states and currents covered. Not a certified IEEE32 bound, integer neuron equation, RTL width certificate or accuracy-preserving quantization. No additional numerical model is executed.',
    pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in[Path(__file__),P/'checkpoint_arrays.npz',P/'pilot_results.json']})
(P/'static_range_screen.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print('PUBLIC MODEL REAL-RANGE SCREEN PASS',len(rows),'layers',flush=True)
print([(s,sum(not next(x for x in r['unit_screens']if x['scale']==s)['existing_I8_contract_covered_by_real_envelope']for r in rows))for s in(16,64,256,1024)],flush=True)
