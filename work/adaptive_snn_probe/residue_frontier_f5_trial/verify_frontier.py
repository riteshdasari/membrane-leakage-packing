"""Independent plain-integer retirement and pin-trace audit, plus saved SNN replay."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
from prepare_frontier_work import load_groups,take_for,sha
COLS=['idx','running','done','rst','in_valid','out_ready','available','U','I','in_ready','take',
      'out_valid','out_count','out_data','narrow_mode','advance','accepted_thiscycle','retired_thiscycle']


def pins(paths):return {str(Path(p).resolve()):sha(p) for p in paths}


def signed(x,w):return x-(1<<w) if x&(1<<(w-1)) else x


def audit_trace(path,e,groups):
    first=last=None;accepted=retired=neurons=retired_neurons=0
    queue=[];grp=pos=advance=0;rows=0;reset=prelude=0
    for idx,line in enumerate(path.open()):
        fields=line.split();assert len(fields)==18
        d={k:int(v,16 if k in ('U','I','out_data') else 10) for k,v in zip(COLS,fields)}
        assert d['idx']==idx and d['done']==0
        rows+=1;reset+=d['rst'];prelude+=not d['running']
        if not d['running']:continue
        assert d['rst']==0 and d['in_ready']==d['advance']==(not(d['out_valid'] and not d['out_ready']))
        av=d['available'];assert 0<=av<=8
        prefix=[(signed((d['U']>>(11*k))&2047,11),signed((d['I']>>(11*k))&2047,11)) for k in range(av)]
        n=take_for(e,prefix,0) if av else 0
        assert d['take']==n and d['narrow_mode']==int(e==5 and n>5)
        accept=bool(d['in_valid'] and d['in_ready'] and av)
        retire=bool(d['out_valid'] and d['out_ready'])
        assert d['accepted_thiscycle']==accept and d['retired_thiscycle']==retire
        if accept:
            assert grp<len(groups)
            assert prefix==groups[grp][1][pos:pos+av]
            assert n>=1 and all(-128<=i<=127 for u,i in prefix[:n])
            queue.append((grp,pos,prefix[:n],advance));accepted+=1;neurons+=n
            if first is None:first=idx
            pos+=n
        if retire:
            assert queue
            gid,start,operands,issued=queue.pop(0)
            assert d['out_count']==len(operands) and advance-issued==4
            for lane in range(8):
                got=signed((d['out_data']>>(12*lane))&4095,12)
                want=sum(operands[lane]) if lane<len(operands) else 0
                assert got==want,(e,idx,lane,got,want)
            retired+=1;retired_neurons+=len(operands);last=idx
        if pos==len(groups[grp][1]) and not queue:grp+=1;pos=0
        advance+=d['advance']
    assert not queue and grp==len(groups) and pos==0
    assert accepted==retired and neurons==retired_neurons
    return dict(trace_file=str(path.resolve()),trace_sha256=sha(path),trace_count=rows,
                first_accept_trace_index=first,last_retire_trace_index=last,
                trace_requests=accepted,trace_neurons=neurons,reset_samples=reset,prelude_samples=prelude)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,required=True);parser.add_argument('--kind',choices=('models','main'),required=True)
    parser.add_argument('--stall',type=int,choices=(0,1),required=True);parser.add_argument('--output',type=Path,required=True)
    a=parser.parse_args();wd=a.directory.resolve();assert not a.output.exists()
    workload=json.loads((wd/'workload.json').read_text());groups=load_groups(wd/'stream_stim.txt')
    assert workload['kind']==a.kind and workload['neurons']==sum(len(v) for _,v in groups)
    assert workload['stimulus_sha256']==sha(wd/'stream_stim.txt')
    for f,h in workload['source_sha256'].items():assert sha(f)==h
    log=(wd/'tool_3.log').read_text();assert f'FRONTIER_COMPARE PASS STALL {a.stall}' in log
    rows=[];candidate=pins([wd/'stream_stim.txt',wd/'workload.json',wd/'tool_3.log'])
    original=P.parent/'residue_frontier_trial'
    parent_pattern=(f'supply2_{a.kind}_{a.stall}_a*/frontier_checks.json'
                    if workload.get('delivery_cap')==2 else f'native_{a.kind}_{a.stall}_a*/frontier_checks.json')
    original_checks,=list((original/'results').glob(parent_pattern))
    parent=json.loads(original_checks.read_text())
    assert parent['status']=='pass' and parent['kind']==a.kind and parent['backpressure']==bool(a.stall)
    parent_pins=pins([original_checks])
    assert sha(wd/'stream_stim.txt')==parent['candidate_file_sha256'][str(original_checks.parent/'stream_stim.txt')]
    ledger_path=P.parent/'results/adaptive_delta_model_input.json'
    ledger=json.loads(ledger_path.read_text()) if a.kind=='models' else None
    for e in range(6):
        match=re.search(r'FRONTIER E '+str(e)+r' REQUESTS (\d+) RETIREMENTS (\d+) NEURONS (\d+) CLOCKS (\d+) INPUT_STALLS (\d+) OUTPUT_STALLS (\d+) MIN_LATENCY (\d+) MAX_LATENCY (\d+) TRACE_ROWS (\d+) FIRST_ACCEPT_TRACE (-?\d+) LAST_RETIRE_TRACE (-?\d+) GROUP_DRAINS (\d+) RESET_SAMPLES (\d+) PRELUDE_SAMPLES (\d+)',log)
        assert match,(e,'Missing TB completion')
        values=list(map(int,match.groups()));req,ret,ns,clocks,ins,outs,latmin,latmax,trcount,first,last,drains,rst,pre=values
        path=wd/f'frontier_out{e}.txt';candidate.update(pins([path]))
        g=pos=requests=neurons=0;first_clk=last_clk=None;hist={};all_sums=[[] for _ in groups]
        digest=hashlib.sha256()
        for line in path.open():
            parts=line.split();assert len(parts)==7
            gid,start,n=map(int,parts[:3]);bits=int(parts[3],16);accept,retire,adv=map(int,parts[4:])
            assert gid==g and start==pos and n==take_for(e,groups[g][1],pos)
            assert 0<=bits<1<<96 and adv==4 and retire-accept>=4
            for lane in range(8):
                got=signed((bits>>(12*lane))&4095,12)
                want=sum(groups[g][1][pos+lane]) if lane<n else 0
                assert got==want,(e,g,pos,lane,got,want)
                if lane<n:digest.update(got.to_bytes(2,'little',signed=True));all_sums[g].append(got)
            if first_clk is None:first_clk=accept
            last_clk=retire;requests+=1;neurons+=n;pos+=n
            hist[str(retire-accept)]=hist.get(str(retire-accept),0)+1
            if pos==len(groups[g][1]):g+=1;pos=0
        assert g==len(groups) and pos==0 and neurons==ns==workload['neurons']
        assert requests==req==ret==workload['predicted_issues'][e]['requests']
        assert clocks==last_clk-first_clk+1 and drains==len(groups)
        assert min(map(int,hist))==latmin and max(map(int,hist))==latmax
        assert rst>=4 and pre>=15
        if not a.stall:assert ins==outs==0 and latmin==latmax==4
        else:assert ins>0 and outs>0
        row=dict(status='pass',engine=e,requests=req,neurons=ns,service_clocks=clocks,
            retirements=ret,input_stalls=ins,output_stalls=outs,group_drains=drains,
            physical_latency_histogram=hist,numeric_retirement_sha256=digest.hexdigest(),
            retirement_file=str(path),retirement_sha256=sha(path),reset_samples=rst,prelude_samples=pre,
            take_histogram=workload['predicted_issues'][e]['take_histogram'])
        if e<5:
            reference,=[item for item in parent['rows'] if item['engine']==e]
            reference_file=Path(reference['retirement_file'])
            assert sha(reference_file)==reference['retirement_sha256']
            assert path.read_bytes()==reference_file.read_bytes(),('Frozen baseline regression',e)
            parent_pins.update(pins([reference_file]))
            row['frozen_original_retirement_bytes_match']=True
        if a.kind=='models':
            counts={m['seed']:[[0]*10 for _ in range(48)] for m in ledger['metadata']}
            for rec,sums in zip(ledger['ledger'],all_sums):
                fired=[int(x>=rec['threshold']) for x in sums]
                state=[x-f*rec['threshold'] for x,f in zip(sums,fired)]
                assert fired==list(map(int,rec['expected_spikes'])) and state==rec['expected_state']
                if rec['layer']==1:
                    for lane,f in enumerate(fired):counts[rec['seed']][rec['image']][lane]+=f
            for meta in ledger['metadata']:
                assert counts[meta['seed']]==meta['expected_counts']
                got=[max(range(10),key=lambda j:r[j]) for r in counts[meta['seed']]]
                assert sum(p==lab for p,lab in zip(got,meta['labels']))/48==meta['sampled_reference_accuracy']
            row['saved_states_spikes_counts_classes_match']=True
        if a.kind=='models' and not a.stall:
            trace=wd/f'frontier_trace{e}.txt';t=audit_trace(trace,e,groups);candidate.update(pins([trace]))
            assert t['trace_count']==trcount and t['first_accept_trace_index']==first and t['last_retire_trace_index']==last
            assert t['trace_requests']==req and t['trace_neurons']==ns
            row.update(t)
        rows.append(row)
    assert len({r['numeric_retirement_sha256'] for r in rows})==1
    sources=pins([Path(__file__),P/'prepare_frontier_work.py',P/'tb_frontier_compare.sv',P/'guard_add_frontier_f5.sv',
                 P/'guard_add_frontier_f5_timing.sv',P/'CONTRACT.md'])
    if ledger:sources.update(pins([ledger_path]))
    sources.update(parent_pins)
    result=dict(status='pass',kind=a.kind,backpressure=bool(a.stall),rows=rows,trace_columns=COLS,
                source_sha256=sources,candidate_file_sha256=candidate,clock_period_ns=6,
                useful_scalar_updates=workload['neurons'],exhaustive_scalar_pairs=workload['exhaustive_scalar_pairs'],
                supply2_minimum_clocks=workload['supply2_minimum_clocks'],
                scope='Plain signed integer sums, ordered groups, tails, reset, stalls, four-advance pipeline and saved integer threshold/reset replay; no trained accuracy or board claim')
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print('FRONTIER VERIFICATION PASS',a.kind,a.stall,[(r['engine'],r['requests'],r['service_clocks']) for r in rows])


if __name__=='__main__':main()
