"""Audit actual ordered sums and feedback SNN states against original dynamics."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
os.environ['MKL_NUM_THREADS']='1'
from pathlib import Path
import argparse
import hashlib
import json
import re
import sys
sys.dont_write_bytecode=True
import numpy as np
from prepare_restored_work import load_groups,take_for,sha,pins,verify,signed
P=Path(__file__).resolve().parent
RESULTS=P.parent/'results'

def network_replay(all_sums,ledger,shift):
    cursor=0;result=[]
    for meta in ledger['metadata']:
        seed=meta['seed'];assert meta['leak_shift']==shift and not meta['hard_reset']
        data=np.load(RESULTS/f'model_seed{seed}.npz');x=data['test_x'];labels=data['test_y'][:48]
        weights=[data['w0'].astype(np.int64),data['w1'].astype(np.int64)]
        assert x.shape==(360,64) and np.array_equal(labels,np.array(meta['labels']))
        state=[np.zeros((48,w.shape[1]),np.int64)for w in weights]
        counts=np.zeros((48,10),np.int64);rng=np.random.default_rng(123)
        for t in range(32):
            spikes=(rng.random(x.shape)<x)[:48]
            for layer,w in enumerate(weights):
                postleak=state[layer]-(state[layer]>>shift)
                current=spikes.astype(np.int64)@w
                actual=np.empty_like(state[layer])
                for image in range(48):
                    rec=ledger['ledger'][cursor]
                    assert (rec['seed'],rec['t'],rec['layer'],rec['image'])==(seed,t,layer,image)
                    assert rec['leak_shift']==shift and not rec['hard_reset']
                    assert np.array_equal(postleak[image],rec['postleak_U'])
                    assert np.array_equal(current[image],rec['current'])
                    assert len(all_sums[cursor])==w.shape[1]
                    actual[image]=all_sums[cursor];cursor+=1
                assert np.array_equal(actual,postleak+current)
                spikes=actual>=meta['thresholds'][layer]
                state[layer]=actual-spikes*meta['thresholds'][layer]
                for image in range(48):
                    rec=ledger['ledger'][cursor-48+image]
                    assert np.array_equal(spikes[image],rec['expected_spikes'])
                    assert np.array_equal(state[layer][image],rec['expected_state'])
            counts+=spikes
        assert np.array_equal(counts,np.array(meta['expected_counts']))
        predictions=counts.argmax(1);accuracy=float(np.mean(predictions==labels))
        assert accuracy==meta['sampled_reference_accuracy']
        result.append(dict(seed=seed,sampled_images=48,sampled_accuracy=accuracy,
            all360_saved_software_reference_accuracy=meta['all_images_reference_accuracy'],
            original_leak_shift=shift,hard_reset=False,state_spike_count_class_disagreements=0))
    assert cursor==len(ledger['ledger'])==len(all_sums)
    return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,required=True)
    ap.add_argument('--shift',type=int,choices=(1,3),required=True)
    ap.add_argument('--stall',type=int,choices=(0,1),required=True)
    ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    assert not a.output.exists();wd=a.directory.resolve()
    workload=json.loads((wd/'workload.json').read_text());groups=load_groups(wd/'stream_stim.txt')
    ledger=json.loads((wd/'reference_ledger.json').read_text())
    assert workload['status']=='pass' and workload['shift']==a.shift
    assert len(groups)==len(ledger['ledger'])==workload['groups']==9216
    assert sha(wd/'stream_stim.txt')==workload['stimulus_sha256']
    assert sha(wd/'reference_ledger.json')==workload['ledger_sha256']
    verify(workload['source_sha256']);verify(json.loads((wd/'provenance.json').read_text()))
    log=(wd/'tool_3.log').read_text()
    assert f'RESTORED_REFERENCE_COMPARE PASS STALL {a.stall} ENGINES {workload["engines"]}' in log
    assert not re.search(r'Fatal:|Error:|Timing violation',log,re.I)
    artifacts=pins([wd/'stream_stim.txt',wd/'reference_ledger.json',wd/'workload.json',wd/'tool_3.log'])
    rows=[]
    pattern=(r'FRONTIER E {e} REQUESTS (\d+) RETIREMENTS (\d+) NEURONS (\d+) CLOCKS (\d+) '
             r'INPUT_STALLS (\d+) OUTPUT_STALLS (\d+) MIN_LATENCY (\d+) MAX_LATENCY (\d+) '
             r'TRACE_ROWS (\d+) FIRST_ACCEPT_TRACE (-?\d+) LAST_RETIRE_TRACE (-?\d+) GROUP_DRAINS (\d+) '
             r'RESET_SAMPLES (\d+) PRELUDE_SAMPLES (\d+)')
    for e in range(workload['engines']):
        match=re.search(pattern.format(e=e),log);assert match,('Missing completion',e)
        req,ret,neurons,clocks,ins,outs,minlat,maxlat,trcount,first,last,drains,rst,pre=map(int,match.groups())
        path=wd/f'frontier_out{e}.txt';artifacts.update(pins([path]))
        group=pos=total=issued=0;all_sums=[[]for _ in groups];hist={};digest=hashlib.sha256()
        first_clock=last_clock=None
        with path.open() as stream:
            for line in stream:
                parts=line.split();assert len(parts)==7
                gid,start,n=map(int,parts[:3]);bits=int(parts[3],16)
                accepted,retired,adv=map(int,parts[4:])
                assert gid==group and start==pos and n==take_for(e,groups[group][1],pos)
                assert 1<=n<=8 and 0<=bits<1<<96 and adv==4 and retired-accepted>=4
                for lane in range(8):
                    got=signed((bits>>(12*lane))&4095,12)
                    want=sum(groups[group][1][pos+lane])if lane<n else 0
                    assert got==want,(e,gid,start,lane,got,want)
                    if lane<n:
                        u,i=groups[group][1][pos+lane]
                        if e==12:assert -128<=u<=127
                        all_sums[group].append(got);digest.update(got.to_bytes(2,'little',signed=True))
                issued+=1;total+=n;pos+=n
                if first_clock is None:first_clock=accepted
                last_clock=retired;hist[str(retired-accepted)]=hist.get(str(retired-accepted),0)+1
                if pos==len(groups[group][1]):group+=1;pos=0
        assert group==len(groups) and pos==0 and total==neurons==workload['neurons']==635904
        assert issued==req==ret==workload['predicted_issues'][e]['requests']
        assert clocks==last_clock-first_clock+1 and drains==len(groups)
        assert min(map(int,hist))==minlat and max(map(int,hist))==maxlat
        assert rst>=4 and pre>=15 and first>=0 and last<trcount
        if a.stall:assert ins>0 and outs>0
        else:assert ins==outs==0 and minlat==maxlat==4 and clocks==req+4*len(groups)
        family='original'if e<6 else ('f5'if e<12 else 'staticU8')
        core=e if e<6 else (e-6 if e<12 else None)
        row=dict(status='pass',engine=e,family=family,core_engine=core,requests=req,retirements=ret,
            neurons=neurons,service_clocks=clocks,input_stalls=ins,output_stalls=outs,
            physical_latency_histogram=hist,take_histogram=workload['predicted_issues'][e]['take_histogram'],
            retirement_file=str(path),retirement_sha256=sha(path),numeric_retirement_sha256=digest.hexdigest(),
            reset_samples=rst,prelude_samples=pre,group_drains=drains,
            original_reference_network_replay=network_replay(all_sums,ledger,a.shift))
        if 6<=e<=10:
            parent_path=wd/f'frontier_out{e-6}.txt'
            assert path.read_bytes()==parent_path.read_bytes(),('Sibling altered fixed baseline',e)
            row['original_baseline_retirement_bytes_match']=True
        if e==12:
            # Both fixed eight-lane policies accept the same operands on identical clocks.
            assert path.read_bytes()==(wd/'frontier_out2.txt').read_bytes()
            row['fixed8_precomputed_retirement_bytes_match']=True
        rows.append(row)
    assert len({r['numeric_retirement_sha256']for r in rows})==1
    sources=pins([Path(__file__),P/'prepare_restored_work.py',P/'tb_restored_reference_compare.sv',
        P/'CONTRACT.md',P/'range_certificate.json',*(RESULTS/f'model_seed{s}.npz'for s in range(3))])
    value=dict(status='pass',shift=a.shift,backpressure=bool(a.stall),rows=rows,
        source_sha256=sources,candidate_file_sha256=artifacts,clock_period_ns=6,
        sampled_images_per_seed=48,ordered_groups=9216,useful_scalar_updates=635904,
        scope='Actual unchanged original/F5 RTL retirement, plain integer sums, ordered groups and sampled feedback SNN states/spikes/counts/classes against original saved dynamics. Global input-domain certificates and full360 software accuracy are separate; no new route/power/board claim.')
    a.output.write_text(json.dumps(value,indent=2)+'\n')
    print('RESTORED NATIVE VERIFICATION PASS',a.shift,a.stall,[(r['engine'],r['requests'],r['service_clocks'])for r in rows],flush=True)

if __name__=='__main__':main()
