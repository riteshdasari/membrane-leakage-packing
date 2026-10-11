"""Predeclared coefficient/horizon and exact shared-high admission screen.

Software only; saved weights and shift3 thresholds stay fixed. Original beta224,
T32 is the unchanged control. Other dynamics are explicit benchmark variants.
"""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
os.environ['MKL_NUM_THREADS']='1'
from pathlib import Path
import hashlib
import json
import sys
from copy import deepcopy
import numpy as np

sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;ROOT=P.parents[1];R=ROOT/'results'
sys.path.insert(0,str(ROOT));import probe
BETAS=(128,224,231,240,248,252,254,256)
HORIZONS=(32,128,256)
POLICIES=('absolute_U8','shared_high_only','union_U8_shared_high')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
def width(lo,hi):
    b=2
    while lo<-(1<<(b-1))or hi>=(1<<(b-1)):b+=1
    return b
def leak(u,beta):return u-((256-beta)*u//256)
def fresh():return dict(requests=0,groups=0,updates=0,shared_wide_tail_updates=0,
    take_histogram={str(i):0 for i in range(1,9)})
def schedule(stats,u_values,i_values,policy):
    pairs=list(zip(u_values,i_values));pos=0
    while pos<len(pairs):
        av=min(8,len(pairs)-pos);n=min(5,av);h0=pairs[pos][0]//32;hi0=pairs[pos][1]//32
        while n<av:
            u,i=pairs[pos+n];absolute=-128<=u<=127;shared=u//32==h0
            permitted=absolute if policy=='absolute_U8'else shared if policy=='shared_high_only'else absolute or shared
            if not permitted:break
            if policy=='shared_high_only'or(not absolute and shared):
                # Four-bit stored delta; add carry at full reconstructed width.
                delta=i//32-hi0;assert -7<=delta<=7
                field=u%32+i%32
                reconstructed=32*(h0+hi0+delta+(field>>5))+(field&31)
                assert reconstructed==u+i
                if not absolute:stats['shared_wide_tail_updates']+=1
            else:
                base=u//32+i//32;assert -8<=base<=6
                assert 32*(base+((u%32+i%32)>>5))+((u%32+i%32)&31)==u+i
            n+=1
        stats['requests']+=1;stats['take_histogram'][str(n)]+=1;pos+=n
    stats['groups']+=1;stats['updates']+=len(pairs)

def finish(stat):
    s=dict(stat);s['take_histogram']=deepcopy(stat['take_histogram']);s['service_clocks_one_edge_analytic']=s['requests']+s['groups'];return s

def main():
    assert not(P/'results.json').exists()
    cfgs=json.loads((R/'final_selected.json').read_text())['models']
    saved=[next(c for c in cfgs if c['seed']==seed and c['leak_shift']==3)for seed in range(3)]
    inputs=[Path(__file__),ROOT/'probe.py',ROOT/'base.py',R/'final_selected.json',
        ROOT/'natural_u11_trial/native_acceptance.json',*(R/f'model_seed{s}.npz'for s in range(3))]
    source={str(p):sha(p)for p in inputs}
    write(P/'predeclared_plan.json',dict(status='prepared',betas=list(BETAS),horizons=list(HORIZONS),
        policies=list(POLICIES),threshold_source='Saved shift3 per-seed thresholds; no retuning',
        equation='U_leak=U-floor((256-beta)*U/256)=ceil(beta*U/256); S=U_leak+I; fire=(S>=theta); U_next=S-fire*theta',
        scope='Other than beta224/T32, these are changed numerical benchmark variants, not unchanged original trained-model accuracy; one saved converted architecture, no retraining/download.',source_sha256=source))
    global16=hashlib.sha256();results=[]
    for cfg in saved:
        seed=cfg['seed'];data=np.load(R/f'model_seed{seed}.npz')
        ws=[data['w0'].astype(np.int64),data['w1'].astype(np.int64)];x=data['test_x'];labels=data['test_y'];theta=cfg['thresholds']
        mins=[np.minimum(w,0).sum(0)for w in ws];maxs=[np.maximum(w,0).sum(0)for w in ws]
        assert all(int(v.min())>=-128 and int(h.max())<=127 for v,h in zip(mins,maxs))
        for beta in BETAS:
            state=[np.zeros((360,w.shape[1]),np.int64)for w in ws];counts=np.zeros((360,10),np.int64)
            lo=[np.zeros(w.shape[1],np.int64)for w in ws];hi=[v.copy()for v in lo]
            certlo=0;certhi=0;observedlo=0;observedhi=0
            lower=[];upper=[];c=256-beta
            if c:
                for li in range(2):
                    l=-((-mins[li]*256+c-1)//c)
                    h=np.maximum(theta[li]-1,(np.maximum(maxs[li]-theta[li],0)*256+c-1)//c)
                    assert np.all(leak(l,beta)+mins[li]>=l)
                    assert np.all(np.maximum(theta[li]-1,leak(h,beta)+maxs[li]-theta[li])<=h)
                    lower.append(l);upper.append(h)
            rng=np.random.default_rng(123);stats={p:fresh()for p in POLICIES};fixed=fresh()
            digests={T:hashlib.sha256()for T in HORIZONS}
            for t in range(max(HORIZONS)):
                spikes=rng.random(x.shape)<x
                for li,w in enumerate(ws):
                    pre=leak(state[li],beta)
                    assert np.array_equal(pre,-((-beta*state[li])//256))
                    clo=leak(lo[li],beta);chi=leak(hi[li],beta)
                    certlo=min(certlo,int(clo.min()));certhi=max(certhi,int(chi.max()))
                    assert np.all(pre>=clo)and np.all(pre<=chi)
                    current=spikes.astype(np.int64)@w
                    assert np.all(current>=mins[li])and np.all(current<=maxs[li])
                    sums=pre+current;r=pre%32+current%32
                    reconstructed=32*(pre//32+current//32+r//32)+r%32
                    assert np.array_equal(reconstructed,sums)
                    observedlo=min(observedlo,int(pre.min()));observedhi=max(observedhi,int(pre.max()))
                    spikes=sums>=theta[li];state[li]=sums-theta[li]*spikes
                    slo=clo+mins[li];shi=chi+maxs[li];lo[li]=slo
                    hi[li]=np.where(shi>=theta[li],np.maximum(theta[li]-1,shi-theta[li]),shi)
                    if c:lo[li]=np.maximum(lo[li],lower[li]);hi[li]=np.minimum(hi[li],upper[li])
                    assert np.all(state[li]>=lo[li])and np.all(state[li]<=hi[li])
                    encoded=sums[:48].astype('<i4').tobytes()
                    for T in HORIZONS:
                        if t<T:digests[T].update(encoded)
                    if beta==224 and t<32:
                        assert int(sums.min())>=-32768 and int(sums.max())<=32767
                        global16.update(sums[:48].astype('<i2').tobytes())
                    us=pre[:48].tolist();ii=current[:48].tolist()
                    for row_u,row_i in zip(us,ii):
                        for policy in POLICIES:schedule(stats[policy],row_u,row_i,policy)
                        fixed['requests']+=(len(row_u)+7)//8;fixed['groups']+=1;fixed['updates']+=len(row_u)
                counts+=spikes
                T=t+1
                if T in HORIZONS:
                    b=width(certlo,certhi);observed_b=width(observedlo,observedhi)
                    assert b>=observed_b
                    accuracy=float(np.mean(counts.argmax(1)==labels))
                    if beta==224 and T==32:assert accuracy==cfg['reference_accuracy']
                    native_lanes=4 if b+1<=12 else 2 if b+1<=24 else 0
                    bits=dict(fixed8_DSP_metadata_FF=5+8*(b-4),
                        absolute_adaptive_DSP_metadata_FF=5+5*(b-4)+12,
                        union_adaptive_DSP_metadata_FF=5+5*(b-4)+12+3,
                        native_hybrid_FF=5+(8-native_lanes)*(b+1),native_DSP_lanes=native_lanes,
                        scope='Analytic explicit fabric storage only; no LUT, slice, mapped timing or energy estimate. Static U8 specialization is stronger when the bound fits U8.')
                    record=dict(seed=seed,beta=beta,timesteps=T,thresholds=theta,all360_variant_accuracy=accuracy,
                        first48_variant_accuracy=float(np.mean(counts[:48].argmax(1)==labels[:48])),
                        certified_postleak_U_range=[certlo,certhi],required_signed_U_bits=b,
                        observed_all360_postleak_U_range=[observedlo,observedhi],observed_signed_U_bits=observed_b,
                        policy_stats={p:finish(s)for p,s in stats.items()},fixed8=finish(fixed),
                        sampled_scalar_sum_i32_sha256=digests[T].hexdigest(),analytic_storage=bits,
                        unchanged_original_control=(beta==224 and T==32),indefinite_certificate_available=bool(c))
                    results.append(record)
                    print('RANGE HORIZON',seed,beta,T,'CERT_BITS',b,'ACCURACY',round(accuracy,6),
                        'CLOCKS',[record['policy_stats'][p]['service_clocks_one_edge_analytic']for p in POLICIES],
                        'FIXED8',record['fixed8']['service_clocks_one_edge_analytic'],flush=True)
    original=json.loads((ROOT/'natural_u11_trial/native_acceptance.json').read_text())
    control=next(c for c in original['cohorts']if c['kind']=='shift3'and not c['backpressure'])
    assert global16.hexdigest()==control['rows'][0]['numeric_retirement_sha256']
    for T in HORIZONS:
        for beta in BETAS:
            cohort=[r for r in results if r['beta']==beta and r['timesteps']==T]
            assert len(cohort)==3
            assert sum(r['fixed8']['updates']for r in cohort)==3*48*T*138
    for name,h in source.items():assert sha(name)==h
    write(P/'results.json',dict(status='pass_software_screen',rows=results,source_sha256=source,
        predeclared_plan_sha256=sha(P/'predeclared_plan.json'),original_shift3_T32_numeric_i16_sha256=global16.hexdigest(),
        shared_high_contract='Tail accepted if U//32 matches lane0 U//32. Store I//32-I0//32 in signed4 and reconstruct at full high width from lane0 precomputed base, tail delta, DSP field carry, and low residue. Union also accepts original U8 tails and needs per-tail mode bits.',
        range_proof='Weight-derived signed8 current intervals; finite interval recurrence with exact integer leakage and one subtractive reset; intersect with separately checked indefinite bounds when beta<256. Observed test maxima never determine legal widths.',
        scope='No new RTL/hardware/energy, no independently trained architectures, no original-model accuracy claim for changed coefficients or horizons. All selected variants and adverse counts are retained.'))
    print('RANGE/HORIZON AND SHARED-HIGH SOFTWARE SCREEN CLOSED',len(results),flush=True)

if __name__=='__main__':main()
