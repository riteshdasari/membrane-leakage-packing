"""Trace/cost screen, not RTL timing or a measured FireFly implementation.
Profiles all saved test images; no training or downloads. NumPy only.
"""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
from pathlib import Path
import json,time,ctypes
import numpy as np
HERE=Path(__file__).resolve().parent
OUT=HERE/'results'
BITS=np.array([6,8,12,16]); LANES=48//BITS
KS=[4,8,16,32,0]

def widths(lo,hi):
    assert np.all(lo>=-32768) and np.all(hi<=32767), 'Certificate exceeds supported wide range'
    return np.where((lo>=-32)&(hi<=31),0,np.where((lo>=-128)&(hi<=127),1,np.where((lo>=-2048)&(hi<=2047),2,3)))

def empty():
    return dict(compute=0.,seeds=0.,checks_parallel=0.,checks_serial=0.,switches=0.,
      work_by_width=[0.,0.,0.,0.],oracle_compute=0.,clairvoyant_group_compute=0.,
      static_current_compute=0.,static_current_seeds=0.,static_current_merges=0.,
      biased_current_compute=0.,biased_current_seeds=0.,biased_current_oracle_compute=0.,
      counted_current_compute=0.,counted_current_seeds=0.,counted_switches=0.,counted_work_by_width=[0.,0.,0.,0.],
      native12_compute=0.,native12_seeds=0.,native12_merges=0.,
      partial_tiles=0.,tile_neuron_visits=0.)

def run(setup,hard):
    d=np.load(OUT/f"model_seed{setup['seed']}.npz")
    ws=[d['w0'].astype(np.int64),d['w1'].astype(np.int64)]
    x,y=d['test_x'],d['test_y'];batch=len(x)
    U=[np.zeros((batch,w.shape[1]),np.int64) for w in ws]
    counts=np.zeros((batch,10),np.int64);rng=np.random.default_rng(123)
    layer_stats={str(li):{str(k):{kind:empty() for kind in ['dense','active_spikes']} for k in KS}for li in range(2)}
    previous={};cache={};prefix_mismatch=0
    for li,w in enumerate(ws):
      I,N=w.shape
      for kval in KS:
        k=kval or I
        for a in range(0,I,k):
          b=min(a+k,I);part=w[a:b]
          L=np.minimum(part,0).sum(0);H=np.maximum(part,0).sum(0)
          span=H-L
          biased=np.where(span<=63,0,np.where(span<=255,1,np.where(span<=4095,2,3)))
          cl=np.vstack([np.zeros((1,N),np.int64),np.cumsum(np.sort(np.minimum(part,0),axis=0),axis=0)])
          ch=np.vstack([np.zeros((1,N),np.int64),np.cumsum(np.sort(np.maximum(part,0),axis=0)[::-1],axis=0)])
          cache[li,kval,a]=(b,L,H,widths(L,H),biased,cl,ch)
    for t in range(32):
      sp=rng.random(x.shape)<x
      for li,w in enumerate(ws):
        I,N=w.shape;pre=U[li].copy()
        if setup['leak_shift'] is not None:pre-=pre>>setup['leak_shift']
        pref=np.zeros((batch,I+1,N),np.int64)
        np.cumsum(sp[:,:,None]*w[None,:,:],axis=1,out=pref[:,1:,:])
        direct=pre+sp.astype(np.int64)@w
        assert np.array_equal(pre+pref[:,-1],direct)
        for kval in KS:
          k=kval or I
          for a in range(0,I,k):
            b,L,H,current_bits,biased_bits,cl,ch=cache[li,kval,a]
            start=pre+pref[:,a]
            lo=start+L;hi=start+H;mode=widths(lo,hi)
            assert np.all(biased_bits[None,:]<=mode), 'Static translated-current width must dominate certified U width'
            trace_lo=pre+pref[:,a:b+1].min(1);trace_hi=pre+pref[:,a:b+1].max(1)
            assert np.all(trace_lo>=lo) and np.all(trace_hi<=hi)
            hindsight=widths(trace_lo,trace_hi)
            events=sp[:,a:b].sum(1)
            count_lo=cl[events];count_hi=ch[events];span=count_hi-count_lo
            counted_bits=np.where(span<=63,0,np.where(span<=255,1,np.where(span<=4095,2,3)))
            assert np.all(pref[:,a:b+1].min(1)-pref[:,a]>=count_lo)
            assert np.all(pref[:,a:b+1].max(1)-pref[:,a]<=count_hi)
            assert np.all(counted_bits<=biased_bits[None,:])
            for kind in ['dense','active_spikes']:
              s=layer_stats[str(li)][str(kval)][kind]
              jobs=np.full(batch,b-a) if kind=='dense' else events
              pairs=(jobs+1)//2;active=jobs>0
              s['partial_tiles']+=int(active.sum())
              s['tile_neuron_visits']+=int(active.sum())*N
              # Fractional lane pooling is an optimistic bound: free grouping,
              # no packet padding, seeding, metadata, checker, or migration.
              s['oracle_compute']+=float((pairs[:,None]/LANES[mode]).sum())
              s['biased_current_oracle_compute']+=float((pairs[:,None]/LANES[biased_bits]).sum())
              # A static current chunk still needs a wide-state merge.
              # Optimistic merge: three independent signed16 additions/DSP-cycle.
              s['static_current_merges']+=int(active.sum())*int(np.ceil(N/3))
              s['native12_merges']+=int(active.sum())*int(np.ceil(N/3))
              for g in range(0,N,24):
                n=min(24,N-g)
                gm=mode[:,g:g+n].max(1);hm=hindsight[:,g:g+n].max(1)
                rm=counted_bits[:,g:g+n].max(1)
                cm=int(current_bits[g:g+n].max())
                bm=int(biased_bits[g:g+n].max())
                assert cm<=2, 'Native12 current benchmark not valid'
                passes=(n+LANES[gm]-1)//LANES[gm]
                hp=(n+LANES[hm]-1)//LANES[hm]
                cp=int(np.ceil(n/LANES[cm]));np12=int(np.ceil(n/4))
                bp=int(np.ceil(n/LANES[bm]))
                rp=(n+LANES[rm]-1)//LANES[rm]
                s['compute']+=int((passes*pairs).sum())
                s['seeds']+=int((passes*active).sum())
                s['clairvoyant_group_compute']+=int((hp*pairs).sum())
                s['checks_parallel']+=int(active.sum())
                s['checks_serial']+=int(active.sum())*n
                for m in range(4):s['work_by_width'][m]+=int(jobs[gm==m].sum())*n
                s['static_current_compute']+=int(pairs.sum())*cp
                s['static_current_seeds']+=int(active.sum())*cp
                s['biased_current_compute']+=int(pairs.sum())*bp
                s['biased_current_seeds']+=int(active.sum())*bp
                s['counted_current_compute']+=int((rp*pairs).sum())
                s['counted_current_seeds']+=int((rp*active).sum())
                for m in range(4):s['counted_work_by_width'][m]+=int(jobs[rm==m].sum())*n
                rkey=('counted',kval,kind,li,g)
                rprev=previous.setdefault(rkey,np.full(batch,-1,np.int8))
                s['counted_switches']+=int(((rprev>=0)&(rprev!=rm)&active).sum())
                rprev[active]=rm[active]
                s['native12_compute']+=int(pairs.sum())*np12
                s['native12_seeds']+=int(active.sum())*np12
                # Previous format per output block, across tiles and timesteps.
                # Empty sparse tiles leave the cached format unchanged.
                key=(kval,kind,li,g)
                prev=previous.setdefault(key,np.full(batch,-1,np.int8))
                s['switches']+=int(((prev>=0)&(prev!=gm)&active).sum())
                prev[active]=gm[active]
        fire=direct>=setup['thresholds'][li]
        U[li]=np.where(fire,0,direct) if hard else direct-fire*setup['thresholds'][li]
        assert np.all(U[li]>=-32768) and np.all(U[li]<=32767)
        sp=fire
      counts+=sp
    stats={str(k):{kind:empty() for kind in ['dense','active_spikes']} for k in KS}
    for kval in KS:
      for kind in ['dense','active_spikes']:
        for field in stats[str(kval)][kind]:
          vals=[layer_stats[str(li)][str(kval)][kind][field] for li in range(2)]
          stats[str(kval)][kind][field]=np.sum(vals,axis=0).tolist()
    result=dict(seed=setup['seed'],leak_shift=setup['leak_shift'],hard_reset=hard,
      images=batch,timesteps=32,accuracy=float((counts.argmax(1)==y).mean()),tiles=stats,per_layer=layer_stats)
    for scope in [stats,*layer_stats.values()]:
     for kind in ['dense','active_spikes']:
      for kval in KS:
        s=scope[str(kval)][kind]
        s['q']=(np.array(s['work_by_width'])/sum(s['work_by_width'])).tolist()
        s['candidate_free_control']=s['compute']+s['seeds']
        s['candidate_parallel_check']=s['candidate_free_control']+s['checks_parallel']
        s['candidate_serial_check']=s['candidate_free_control']+s['checks_serial']
        s['candidate_parallel_check_repack2']=s['candidate_parallel_check']+2*s['switches']
        s['static_current_total']=s['static_current_compute']+s['static_current_seeds']+s['static_current_merges']
        s['static_current_overlap_merge']=s['static_current_compute']+s['static_current_seeds']
        s['biased_current_overlap_merge']=s['biased_current_compute']+s['biased_current_seeds']
        s['biased_current_one_merge']=s['biased_current_overlap_merge']+s['static_current_merges']
        s['biased_current_two_merges']=s['biased_current_overlap_merge']+2*s['static_current_merges']
        s['counted_current_overlap_merge']=s['counted_current_compute']+s['counted_current_seeds']+s['checks_parallel']+2*s['counted_switches']
        s['counted_current_one_merge']=s['counted_current_overlap_merge']+s['static_current_merges']
        s['counted_current_two_merges']=s['counted_current_overlap_merge']+2*s['static_current_merges']
        s['counted_q']=(np.array(s['counted_work_by_width'])/sum(s['counted_work_by_width'])).tolist()
        assert s['biased_current_compute']<=s['compute']
        s['native12_total']=s['native12_compute']+s['native12_seeds']+s['native12_merges']
    return result

if __name__=='__main__':
    class Mem(ctypes.Structure):
      _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(s,ctypes.c_ulonglong)for s in ['total','avail','pf','apf','v','av','ae']]
    m=Mem();m.length=ctypes.sizeof(m);ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    print('Free RAM GiB',round(m.avail/2**30,2),flush=True)
    assert m.avail>700*2**20
    setups=json.loads((OUT/'final_selected.json').read_text())['models']
    refs=json.loads((OUT/'exact_inference.json').read_text())['models']
    output=dict(note=__doc__,bits=BITS.tolist(),lanes=LANES.tolist(),group_neurons=24,
      assumptions=['Same precision and same input activity for candidate and references.',
      'Cost unit is serialized pooled DSP service cycles, not wall-clock FPGA inference.',
      'One seed cycle per packed output word, including fixed current initialization.',
      'Static current merge uses ideal three-lane signed16 addition, ceil(N/3) cycles per active tile.',
      'Biased current stores I-L in an unsigned field. Compare fully overlapped, one-pass and two-pass wide merge scenarios; implementations unverified.',
      'Counted-current bounds use the known tile spike count r: sum up to r most negative/positive weights. Prefix tables assume a lookup; footprint and bandwidth excluded.',
      'Checker and repacking costs are hypothetical unhidden cycles; no area/clock/bandwidth model.',
      'Common leak/threshold operations omitted; exact neuron equation retained in reference traces.',
      'Oracle is a fractional-lane lower bound with zero overhead; not a realizable scheduler.',
      'Tile key zero means full fan-in independently for each layer.'],models=[])
    start=time.monotonic()
    for setup in setups:
      for hard in [False,True]:
        row=run(setup,hard)
        ref=next(r for r in refs if r['seed']==setup['seed'] and r['leak_shift']==setup['leak_shift'] and r['hard_reset']==hard and r['mode']==0)
        assert abs(row['accuracy']-ref['accuracy'])<1e-12
        output['models'].append(row)
        (OUT/'certified_packing_profile.json').write_text(json.dumps(output,indent=2))
        a=[row['tiles'][str(k)]['active_spikes'] for k in KS]
        bestbase=min(s['static_current_total']for s in a)
        bestcand=min(s['candidate_parallel_check_repack2']for s in a)
        print('DONE',setup['seed'],setup['leak_shift'],hard,'best static/candidate',round(bestbase/bestcand,4),'elapsed',round(time.monotonic()-start,1),flush=True)
