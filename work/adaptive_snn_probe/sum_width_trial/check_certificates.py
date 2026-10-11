"""Model-certified sum and high-part widths; do not infer widths from samples.

This independently recomputes the finite interval recurrence in the completed
72-row screen, retains all selected dynamics, and distinguishes a generic full
signed-word primitive from model-specific interval contracts. No new RTL result.
"""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
from pathlib import Path
import hashlib
import json
import sys
import numpy as np

sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent; ROOT=P.parent; R=ROOT/'results'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def width(lo,hi):
    b=1
    while lo<-(1<<(b-1)) or hi>=(1<<(b-1)):b+=1
    return b
def leak(u,b):return -((-b*u)//256)
def reset_bounds(lo,hi,theta):
    # Exact hull of one subtractive reset, including its discontinuity.
    lower=np.where(hi<theta,lo,np.where(lo>=theta,lo-theta,np.minimum(lo,0)))
    upper=np.where(hi<theta,hi,np.where(lo>=theta,hi-theta,np.maximum(theta-1,hi-theta)))
    return lower,upper
def storage(u,s,base):
    lanes=4 if max(u,s)<=12 else 2 if max(u,s)<=24 else 0
    return dict(native_DSP_lanes=lanes,
        fixed8_DSP_FF=5+8*base,
        adaptive_absolute_DSP_FF=5+5*base+12,
        adaptive_union_DSP_FF=5+5*base+12+3,
        native_hybrid_FF=5+(8-lanes)*s,
        full_LUT8_FF=5+8*s,
        adaptive_minus_native_FF=5*base+12-(8-lanes)*s)

def main():
    assert not(P/'certificates.json').exists()
    screen_path=ROOT/'range_horizon_trial/results.json'
    screen=json.loads(screen_path.read_text())
    cfg_path=R/'final_selected.json'
    cfgs=json.loads(cfg_path.read_text())['models']
    inputs=[Path(__file__),screen_path,ROOT/'range_horizon_trial/screen.py',cfg_path,
            *(R/f'model_seed{s}.npz'for s in range(3))]
    pins={str(p):sha(p)for p in inputs}
    write(P/'plan.json',dict(status='prepared',source_sha256=pins,
        contracts=['generic full signed U-word and signed8 I',
                   'uniform certified postleak U interval and any signed8 I',
                   'certified per-neuron U and weight-derived I intervals'],
        rule='Native FOUR12 is legal when both operands and their sum fit signed12. Required membrane width alone does not decide the SIMD mode.',
        scope='Endpoint certificate and analytic explicit register storage only; no area/timing/energy or trained-model-generalization claim.'))
    rows=[]
    for seed in range(3):
        cfg=next(c for c in cfgs if c['seed']==seed and c['leak_shift']==3)
        data=np.load(R/f'model_seed{seed}.npz')
        ws=[data['w0'].astype(np.int64),data['w1'].astype(np.int64)]
        imin=[np.minimum(w,0).sum(0)for w in ws]
        imax=[np.maximum(w,0).sum(0)for w in ws]
        assert all(np.all(l>=-128)and np.all(h<=127)for l,h in zip(imin,imax))
        theta=cfg['thresholds']
        assert all(v>0 for v in theta)
        for beta in (128,224,231,240,248,252,254,256):
            lo=[np.zeros(w.shape[1],np.int64)for w in ws]
            hi=[v.copy()for v in lo]
            c=256-beta
            invariant=[]
            if c:
                for li in range(2):
                    lower=-((-imin[li]*256+c-1)//c)
                    upper=np.maximum(theta[li]-1,(np.maximum(imax[li]-theta[li],0)*256+c-1)//c)
                    rl,rh=reset_bounds(leak(lower,beta)+imin[li],leak(upper,beta)+imax[li],theta[li])
                    assert np.all(rl>=lower)and np.all(rh<=upper)
                    assert np.all(lower<=0)and np.all(upper>=0)
                    invariant.append((lower,upper))
            ulo=uhi=slo=shi=blo=bhi=0
            for t in range(1,257):
                for li in range(2):
                    pl,ph=leak(lo[li],beta),leak(hi[li],beta)
                    sl,sh=pl+imin[li],ph+imax[li]
                    bl,bh=pl//32+imin[li]//32,ph//32+imax[li]//32
                    ulo=min(ulo,int(pl.min()));uhi=max(uhi,int(ph.max()))
                    slo=min(slo,int(sl.min()));shi=max(shi,int(sh.max()))
                    blo=min(blo,int(bl.min()));bhi=max(bhi,int(bh.max()))
                    lo[li],hi[li]=reset_bounds(sl,sh,theta[li])
                    if c:
                        lo[li]=np.maximum(lo[li],invariant[li][0])
                        hi[li]=np.minimum(hi[li],invariant[li][1])
                    assert np.all(lo[li]<=hi[li])
                if t not in (32,128,256):continue
                saved=next(r for r in screen['rows']if (r['seed'],r['beta'],r['timesteps'])==(seed,beta,t))
                assert [ulo,uhi]==saved['certified_postleak_U_range']
                u=width(ulo,uhi)
                relaxed_s=(ulo-128,uhi+127)
                relaxed_base=(ulo//32-4,uhi//32+3)
                generic_range=(-(1<<(u-1)),(1<<(u-1))-1)
                generic_s=(generic_range[0]-128,generic_range[1]+127)
                generic_base=(generic_range[0]//32-4,generic_range[1]//32+3)
                contracts={}
                for name,s_range,base_range in (
                    ('generic_full_word',generic_s,generic_base),
                    ('uniform_U_any_I8',relaxed_s,relaxed_base),
                    ('per_neuron_model',(slo,shi),(blo,bhi))):
                    s_bits=width(*s_range);base_bits=width(*base_range)
                    contracts[name]=dict(sum_range=list(s_range),sum_bits=s_bits,
                        precomputed_high_base_range=list(base_range),high_base_bits=base_bits,
                        storage=storage(u,s_bits,base_bits))
                    # All high-plus-carry reconstructions fit the declared sum
                    # interval; carry is added at full width, never to narrow metadata.
                    assert -(1<<(base_bits-1))<=base_range[0]<=base_range[1]<(1<<(base_bits-1))
                    assert -(1<<(s_bits-1))<=s_range[0]<=s_range[1]<(1<<(s_bits-1))
                assert contracts['per_neuron_model']['sum_bits']<=contracts['uniform_U_any_I8']['sum_bits']<=contracts['generic_full_word']['sum_bits']
                rows.append(dict(seed=seed,beta=beta,timesteps=t,certified_U_range=[ulo,uhi],U_bits=u,
                    contracts=contracts,unchanged_original_control=saved['unchanged_original_control'],
                    previous_analytic_storage=saved['analytic_storage']))
                print('SUM CERT',seed,beta,t,'U',u,'S',[v['sum_bits']for v in contracts.values()],
                      'BASE',[v['high_base_bits']for v in contracts.values()],flush=True)
    assert len(rows)==72
    for name,h in pins.items():assert sha(name)==h
    write(P/'certificates.json',dict(status='pass_interval_certificate',rows=rows,source_sha256=pins,
        plan_sha256=sha(P/'plan.json'),
        proof='All initial states zero; leak is monotone ceil(beta U/256); independent per-neuron currents are bounded by sums of positive/negative weights; exact reset hull is propagated and intersected with independently checked invariants.',
        caution='Specialized widths change the caller contract. Prior exhaustive full-word U11 tests do not authorize narrowing under that original generic contract. Hardware savings remain analytic and need a new bounded-domain RTL trial.',
        conclusion='Use certified sum width and high-base width fairly in both adaptive and strongest fixed controls before selecting a precision-cliff hardware experiment.'))
if __name__=='__main__':main()
