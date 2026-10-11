"""Exact integer SNN traces and guarded dynamic-checkpoint design-space probe.
No models/packages downloaded. DSP-cycle estimates are explicitly scheduling models.
"""
import os, sys, json, gzip, time
os.environ['OMP_NUM_THREADS']='1'
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['MKL_NUM_THREADS']='1'
sys.dont_write_bytecode=True
import numpy as np
import base
from pathlib import Path
HERE=Path(__file__).resolve().parent
OUT=HERE/'results'; OUT.mkdir(exist_ok=True)

def model(seed):
    r=np.random.default_rng(seed); base.rng=np.random.default_rng(seed)
    d=np.loadtxt(gzip.open(HERE/'digits.csv.gz'),delimiter=',')
    p=r.permutation(len(d)); x=d[p,:64]/16; y=d[p,64].astype(int)
    w1,w2=base.train_mlp(x[:1077],y[:1077],epochs=200)
    return x[1077:1437],y[1077:1437],x[1437:],y[1437:],w1,w2

def reference(ws,vth,x,shift,T=32):
    rng=np.random.default_rng(123); u=[np.zeros((len(x),w.shape[1]),np.int64) for w in ws]
    count=np.zeros_like(u[-1]); records=[]
    for t in range(T):
        sp=rng.random(x.shape)<x
        for li,w in enumerate(ws):
            pre=u[li].copy()
            if shift is not None: pre-=pre>>shift
            cur=sp.astype(np.int64)@w
            new=pre+cur; fired=new>=vth[li]; u[li]=new-vth[li]*fired
            records.append((li,pre,sp.copy(),new.copy(),fired.copy()))
            sp=fired
        count+=sp
    return count.argmax(1),records

def tune(ws,xf,yf,w1,w2,scales,shift):
    a=np.maximum(xf@w1,0); b=a@w2; best=None
    for f in (.25,.5,.75,1.):
        v=[max(1,int(round(f*np.percentile(a,99)/scales[0]))),
           max(1,int(round(f*np.percentile(b,99)/scales[1])))]
        pred,_=reference(ws,v,xf[:120],shift)
        acc=float(np.mean(pred==yf[:120]))
        if best is None or acc>best[0]:best=(acc,v)
    return best[1]

def characterize(records,ws,slot,drain_cost,policy='midpoint'):
    """One guard bit; early warning at signed (slot-1)-bit boundary.
    The slot itself is signed slot-bit arithmetic with bias 2**(slot-1).
    Entire groups are drained and initialized after a warning, before the next add.
    """
    n=48//slot; actual_max=max(int(np.abs(w).max()) for w in ws)
    margin=1<<actual_max.bit_length()  # includes the most negative value of the weight format
    if policy=='pipe_margin':margin*=2
    lo=-(1<<(slot-2)) if policy=='midpoint' else -(1<<(slot-1))+margin
    hi=(1<<(slot-2))-1 if policy=='midpoint' else (1<<(slot-1))-margin-1
    fixedK=min(((1<<(slot-1))-1)//actual_max,(1<<(slot-1))//actual_max)
    static_safe=[]
    for w in ws:
        lower=np.minimum(w,0).sum(0); upper=np.maximum(w,0).sum(0)
        static_safe.extend(((lower>=-(1<<(slot-1)))&(upper<(1<<(slot-1)))).tolist())
    stats=dict(slot=slot,lanes=n,policy=policy,drain_cost=drain_cost,events=0,flushes=0,
               offline_worstcase_safe_neuron_fraction=float(np.mean(static_safe)),
               group_opportunities=0,seed_groups_fit=0,group_sum_cycles=0,
               baseline_sum_cycles=0,barrier_cycles=0,baseline_barrier_cycles=0,
               selective_barrier_cycles=0,
               max_post_warning=0,exact_mismatches=0,spike_mismatches=0)
    for li,pre,sp,new,fired in records:
        pre,sp,new,fired=pre[:48],sp[:48],new[:48],fired[:48]
        w=ws[li]; B,N=pre.shape; G=(N+n-1)//n; pad=G*n-N
        wp=np.pad(w,((0,0),(0,pad))).reshape(w.shape[0],G,n)
        pp=np.pad(pre,((0,0),(0,pad))).reshape(B,G,n)
        stats['group_opportunities']+=B*G
        stats['seed_groups_fit']+=int(((pp>=lo)&(pp<=hi)).all(-1).sum())
        chunk=np.zeros((B,G,n),np.int64); wide=np.zeros_like(chunk)
        # Independent groups are optimistic; barrier drains ALL groups on any warning.
        barrier_chunk=np.zeros_like(chunk)
        active_events=sp.sum(1); flashes=np.zeros((B,G),np.int64); barrier_flashes=np.zeros(B,np.int64)
        event_counter=np.zeros(B,np.int64)
        selective_barriers=np.zeros(B,np.int64)
        for j in range(w.shape[0]):
            delta=sp[:,j,None,None]*wp[j][None]
            chunk+=delta; barrier_chunk+=delta
            hit=((chunk<lo)|(chunk>hi)).any(-1)
            event_counter+=sp[:,j]
            if policy=='fixed':hit=np.broadcast_to((event_counter>=fixedK)[:,None],(B,G))
            selective_barriers+=hit.any(-1)
            if hit.any():
                stats['max_post_warning']=max(stats['max_post_warning'],int(np.abs(chunk[hit]).max()))
                # A warning still has an additional guard bit of safe numeric headroom.
                assert np.all(chunk>=-(1<<(slot-1))) and np.all(chunk<(1<<(slot-1)))
                wide+=np.where(hit[...,None],chunk,0)
                chunk=np.where(hit[...,None],0,chunk); flashes+=hit
            bh=((barrier_chunk<lo)|(barrier_chunk>hi)).any((1,2))
            if policy=='fixed':bh=event_counter>=fixedK
            barrier_flashes+=bh; barrier_chunk=np.where(bh[:,None,None],0,barrier_chunk)
            if policy=='fixed':event_counter=np.where(bh,0,event_counter)
        out=(wide+chunk).reshape(B,-1)[:,:N]+pre
        stats['exact_mismatches']+=int(np.count_nonzero(out!=new))
        # The carried reference membrane is exact because each current is recovered exactly.
        # Check firing before reset separately.
        stats['spike_mismatches']+=int(np.count_nonzero((out>=THRESHOLDS[li])!=fired))
        flush=int(flashes.sum()); stats['flushes']+=flush
        stats['events']+=int(active_events.sum())*G
        # Every variant must read all neurons at end of timestep; n reads + initialize.
        final=n+1; baseG=(N+3)//4
        dc=(n+1 if drain_cost=='serial' else 2*n+1 if drain_cost=='rmw' else 2)
        stats['group_sum_cycles']+=int(active_events.sum())*G+flush*dc+B*G*final
        stats['baseline_sum_cycles']+=int(active_events.sum())*baseG+B*baseG*5
        stats['barrier_cycles']+=int(active_events.sum())+int(barrier_flashes.sum())*dc+B*final
        stats['selective_barrier_cycles']+=int(active_events.sum())+int(selective_barriers.sum())*dc+B*final
        stats['baseline_barrier_cycles']+=int(active_events.sum())+B*5
    stats['seed_fit_fraction']=stats['seed_groups_fit']/stats['group_opportunities']
    stats['flush_per_group_event']=stats['flushes']/max(1,stats['events'])
    stats['dsp_work_ratio']=stats['group_sum_cycles']/stats['baseline_sum_cycles']
    stats['barrier_latency_ratio']=stats['barrier_cycles']/stats['baseline_barrier_cycles']
    stats['selective_barrier_latency_ratio']=stats['selective_barrier_cycles']/stats['baseline_barrier_cycles']
    return stats

def bit_packing_check():
    """Exercise physical 48-bit sums, both signs, all widths, and dynamic drain boundaries."""
    rng=np.random.default_rng(77); cases=0; flushes=0
    for slot in (6,7,8,9,10,12):
        n=48//slot; bias=1<<(slot-1); lm=(1<<slot)-1; mask=(1<<48)-1
        low=-bias+8; high=bias-9; P=sum(bias<<(i*slot) for i in range(n)); exact=np.zeros(n,np.int64); wide=exact.copy()
        for j in range(10000):
            w=rng.integers(-8,8,n) if j%3 else np.full(n,7 if j%2 else -8)
            P=(P+sum(int(v)<<(i*slot) for i,v in enumerate(w)))&mask
            f=np.array([((P>>(i*slot))&lm)-bias for i in range(n)])
            exact+=w
            assert np.array_equal(wide+f,exact),(slot,j)
            if np.any((f < low)|(f>high)):
                wide+=f; P=sum(bias<<(i*slot) for i in range(n)); flushes+=1
            cases+=1
    # Counterexamples to general saturation and discarded-bit recovery claims.
    assert np.clip(np.clip(0+40,-32,31)-40,-32,31)==-9
    assert (3>>1)*2!=3
    return dict(physical_packed_add_checks=cases,flushes=flushes,
                saturation_counterexample={'sequence':[40,-40],'exact':0,'sat_signed6':-9},
                discard_counterexample={'value':3,'right_shift':1,'restored':2})

if __name__=='__main__':
    result={'validation':bit_packing_check(),'models':[],'note':'cycle ratios are models; final reads and clears included; no SRAM/migration cost hidden as measured hardware'}
    for seed in (0,1,2):
        xc,yc,xt,yt,w1,w2=model(seed)
        for wb in (4,):
            mx=(1<<(wb-1))-1; scales=[np.abs(w).max()/mx for w in (w1,w2)]
            ws=[np.round(w/s).astype(np.int64) for w,s in zip((w1,w2),scales)]
            for shift in (1,3,None):
                THRESHOLDS=tune(ws,xc,yc,w1,w2,scales,shift)
                pred,records=reference(ws,THRESHOLDS,xt,shift)
                row=dict(seed=seed,weight_bits=wb,leak_shift=shift,thresholds=THRESHOLDS,
                         test_accuracy=float(np.mean(pred==yt)),policies=[],
                         weight_bounds=[dict(min_sum=int(np.minimum(w,0).sum(0).min()),max_sum=int(np.maximum(w,0).sum(0).max())) for w in ws])
                for slot in ((6,7,8,9,10,12) if wb==4 else (10,12,16)):
                    for policy in ('midpoint','margin','fixed'):
                        row['policies'].append(characterize(records,ws,slot,'serial',policy))
                result['models'].append(row)
                (OUT/'numerical.json').write_text(json.dumps(result,indent=2))
                print('DONE',seed,wb,shift,'acc',round(row['test_accuracy'],4),
                      [(r['slot'],round(r['dsp_work_ratio'],3),round(r['barrier_latency_ratio'],3),round(r['seed_fit_fraction'],3))
                       for r in row['policies'] if r['policy']=='margin'],flush=True)
    print('ALL COMPLETE',flush=True)
