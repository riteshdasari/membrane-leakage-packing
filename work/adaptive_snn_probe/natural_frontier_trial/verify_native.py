"""Independent U13/I8 retirement, protocol, and original-IF feedback checks."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key] = '1'
from pathlib import Path
import argparse
import hashlib
import json
import re
import sys
sys.dont_write_bytecode = True
from prepare_u13_work import load_groups,take_for,sha,signed
P = Path('C:/Users/Ritesh/Documents/Codex/2026-10-08/oka/work/adaptive_snn_probe/residue_frontier_u13_trial')
COLS = ['idx','running','done','rst','in_valid','out_ready','available','U','I','in_ready','take',
        'out_valid','out_count','out_data','narrow_mode','advance','accepted_thiscycle','retired_thiscycle']


def pins(paths):
    return {str(Path(path).resolve()):sha(path) for path in paths}


def audit_trace(path,engine,groups):
    first=last=None
    accepted=retired=neurons=retired_neurons=0
    queue=[]
    group=pos=advance=rows=reset=prelude=0
    for index,line in enumerate(path.open()):
        values=line.split()
        assert len(values)==18
        row={key:int(value,16 if key in ('U','I','out_data') else 10) for key,value in zip(COLS,values)}
        assert row['idx']==index and row['done']==0
        assert 0<=row['U']<(1<<104) and 0<=row['I']<(1<<104) and 0<=row['out_data']<(1<<112)
        rows+=1;reset+=row['rst'];prelude+=not row['running']
        if not row['running']:
            continue
        assert row['rst']==0 and row['in_ready']==row['advance']==(not(row['out_valid'] and not row['out_ready']))
        available=row['available'];assert 0<=available<=8
        prefix=[(signed((row['U']>>(13*k))&8191,13),signed((row['I']>>(13*k))&8191,13)) for k in range(available)]
        n=take_for(engine,prefix,0) if available else 0
        assert row['take']==n and row['narrow_mode']==int(engine==5 and n>5)
        accept=bool(row['in_valid'] and row['in_ready'] and available)
        retire=bool(row['out_valid'] and row['out_ready'])
        assert row['accepted_thiscycle']==accept and row['retired_thiscycle']==retire
        if accept:
            assert group<len(groups) and prefix==groups[group][1][pos:pos+available]
            assert n>=1 and all(-128<=current<=127 for u,current in prefix[:n])
            queue.append((group,pos,prefix[:n],advance));accepted+=1;neurons+=n
            if first is None:first=index
            pos+=n
        if retire:
            assert queue
            gid,start,operands,issued=queue.pop(0)
            assert row['out_count']==len(operands) and advance-issued==1
            for lane in range(8):
                actual=signed((row['out_data']>>(14*lane))&16383,14)
                expected=sum(operands[lane]) if lane<len(operands) else 0
                assert actual==expected,(engine,index,lane,actual,expected)
            retired+=1;retired_neurons+=len(operands);last=index
        if group<len(groups) and pos==len(groups[group][1]) and not queue:
            group+=1;pos=0
        advance+=row['advance']
    assert not queue and group==len(groups) and pos==0
    assert accepted==retired and neurons==retired_neurons
    return dict(trace_file=str(path.resolve()),trace_sha256=sha(path),trace_count=rows,
                first_accept_trace_index=first,last_retire_trace_index=last,
                trace_requests=accepted,trace_neurons=neurons,reset_samples=reset,prelude_samples=prelude)


def check_original_if(ledger,all_sums):
    import numpy as np
    assert len(ledger['ledger'])==len(all_sums)==9216
    models={}
    for meta in ledger['metadata']:
        assert meta['leak_shift'] is None and not meta['hard_reset'] and meta['sampled_images']==48
        assert sha(meta['weights_file'])==meta['weights_sha256']
        saved=np.load(meta['weights_file'])
        weights=[saved['w0'].astype(np.int64),saved['w1'].astype(np.int64)]
        models[meta['seed']]=dict(weights=weights,state=[np.zeros((48,128),np.int64),np.zeros((48,10),np.int64)],
                                counts=np.zeros((48,10),np.int64),hidden_spikes={},meta=meta)
    for record,sums in zip(ledger['ledger'],all_sums):
        seed,layer,image,t=record['seed'],record['layer'],record['image'],record['t']
        model=models[seed]
        assert record['postleak_U']==model['state'][layer][image].tolist(), ('Actual IF state feedback mismatch',seed,t,layer,image)
        incoming=np.array(record['incoming_spikes'],np.int64)
        assert np.all((incoming==0)|(incoming==1))
        if layer==1:
            assert record['incoming_spikes']==model['hidden_spikes'].pop((t,image))
        assert (incoming@model['weights'][layer]).tolist()==record['current']
        expected_plain=(model['state'][layer][image]+incoming@model['weights'][layer]).tolist()
        assert sums==expected_plain
        fired=[int(value>=record['threshold']) for value in sums]
        state=[value-spike*record['threshold'] for value,spike in zip(sums,fired)]
        assert fired==record['expected_spikes'] and state==record['expected_state']
        model['state'][layer][image]=state
        if layer==0:
            model['hidden_spikes'][(t,image)]=fired
        else:
            model['counts'][image]+=fired
    accuracies={}
    for seed,model in models.items():
        assert not model['hidden_spikes']
        meta=model['meta'];assert model['counts'].tolist()==meta['expected_counts']
        predicted=model['counts'].argmax(1).tolist()
        accuracy=sum(value==label for value,label in zip(predicted,meta['labels']))/48
        assert accuracy==meta['sampled_reference_accuracy']
        accuracies[str(seed)]=accuracy
    return dict(saved_states_spikes_counts_classes_match=True,actual_IF_state_feedback_checked=True,
                currents_recomputed_from_actual_hidden_spikes=True,sampled_reference_accuracies=accuracies,
                scope='Actual retired sums drive independent IF state/spike/count feedback for the unchanged first48images of each saved seed; full360 reference restoration is software-only.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--kind',choices=('models','main'),required=True)
    parser.add_argument('--stall',type=int,choices=(0,1),required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();directory=args.directory.resolve();assert not args.output.exists()
    workload=json.loads((directory/'workload.json').read_text())
    groups=load_groups(directory/'stream_stim.txt')
    assert workload['status']=='pass' and workload['kind']==args.kind
    assert workload['neurons']==sum(len(pairs) for _,pairs in groups)
    assert workload['stimulus_sha256']==sha(directory/'stream_stim.txt')
    for path,digest in workload['source_sha256'].items():assert sha(path)==digest
    if args.kind=='main':assert workload['exhaustive_scalar_pairs']==2097152
    else:assert workload['exhaustive_scalar_pairs']==0 and workload['neurons']==635904
    log=(directory/'tool_3.log').read_text()
    assert f'FRONTIER_U13_COMPARE PASS STALL {args.stall}' in log
    candidate=pins([directory/'stream_stim.txt',directory/'workload.json',directory/'tool_3.log'])
    ledger_path=P/'original_if/reference_ledger.json'
    ledger=json.loads(ledger_path.read_text()) if args.kind=='models' else None
    rows=[]
    for engine in range(6):
        match=re.search(r'FRONTIER E '+str(engine)+r' REQUESTS (\d+) RETIREMENTS (\d+) NEURONS (\d+) CLOCKS (\d+) INPUT_STALLS (\d+) OUTPUT_STALLS (\d+) MIN_LATENCY (\d+) MAX_LATENCY (\d+) TRACE_ROWS (\d+) FIRST_ACCEPT_TRACE (-?\d+) LAST_RETIRE_TRACE (-?\d+) GROUP_DRAINS (\d+) RESET_SAMPLES (\d+) PRELUDE_SAMPLES (\d+)',log)
        assert match,(engine,'Missing harness completion')
        req,ret,ns,clocks,input_stalls,output_stalls,latmin,latmax,trace_count,first,last,drains,reset,prelude=map(int,match.groups())
        path=directory/f'frontier_out{engine}.txt';candidate.update(pins([path]))
        group=pos=requests=neurons=0;first_clock=last_clock=None;hist={}
        all_sums=[[] for _ in groups]
        digest=hashlib.sha256()
        for line in path.open():
            parts=line.split();assert len(parts)==7
            gid,start,n=map(int,parts[:3]);bits=int(parts[3],16);accept,retire,advance=map(int,parts[4:])
            assert group<len(groups) and gid==group and start==pos and n==take_for(engine,groups[group][1],pos)
            assert 0<=bits<(1<<112) and advance==1 and retire-accept>=1
            for lane in range(8):
                actual=signed((bits>>(14*lane))&16383,14)
                expected=sum(groups[group][1][pos+lane]) if lane<n else 0
                assert actual==expected,(engine,group,pos,lane,actual,expected)
                if lane<n:
                    digest.update(actual.to_bytes(2,'little',signed=True));all_sums[group].append(actual)
            if first_clock is None:first_clock=accept
            last_clock=retire;requests+=1;neurons+=n;pos+=n
            hist[str(retire-accept)]=hist.get(str(retire-accept),0)+1
            if pos==len(groups[group][1]):group+=1;pos=0
        assert group==len(groups) and pos==0 and neurons==ns==workload['neurons']
        assert requests==req==ret==workload['predicted_issues'][engine]['requests']
        assert clocks==last_clock-first_clock+1 and drains==len(groups)
        assert min(map(int,hist))==latmin and max(map(int,hist))==latmax
        assert reset>=4 and prelude>=15
        if not args.stall:assert input_stalls==output_stalls==0 and latmin==latmax==1
        else:assert input_stalls>0 and output_stalls>0
        row=dict(status='pass',engine=engine,requests=req,neurons=ns,service_clocks=clocks,
                 retirements=ret,input_stalls=input_stalls,output_stalls=output_stalls,group_drains=drains,
                 physical_latency_histogram=hist,numeric_retirement_sha256=digest.hexdigest(),
                 retirement_file=str(path),retirement_sha256=sha(path),reset_samples=reset,prelude_samples=prelude,
                 take_histogram=workload['predicted_issues'][engine]['take_histogram'])
        if ledger:row.update(check_original_if(ledger,all_sums))
        if args.kind=='models' and not args.stall:
            trace_path=directory/f'frontier_trace{engine}.txt';trace=audit_trace(trace_path,engine,groups)
            candidate.update(pins([trace_path]))
            assert trace['trace_count']==trace_count and trace['first_accept_trace_index']==first and trace['last_retire_trace_index']==last
            assert trace['trace_requests']==req and trace['trace_neurons']==ns
            row.update(trace)
        rows.append(row)
    assert len({r['numeric_retirement_sha256'] for r in rows})==1
    sources=pins([Path(__file__),P/'prepare_u13_work.py',P/'tb_frontier_u13_compare.sv',P/'tb_preparation.json',
                 P/'guard_add_frontier_u13.sv',P/'guard_add_frontier_u13_timing.sv',P/'CONTRACT.md'])
    if ledger:sources.update(pins([ledger_path,P/'original_if/profile.json']))
    result=dict(status='pass',kind=args.kind,backpressure=bool(args.stall),rows=rows,trace_columns=COLS,
                source_sha256=sources,candidate_file_sha256=candidate,clock_period_ns=6,
                useful_scalar_updates=workload['neurons'],exhaustive_scalar_pairs=workload['exhaustive_scalar_pairs'],
                supply2_minimum_clocks=workload['supply2_minimum_clocks'],
                scope='Exact U13/I8 integer addition, ordered prefix, zero tails, reset, stalls and1advancingclock; actualIF state/spike/count feedback on originalfirst48images. No full-neuronhardware or board claim.')
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print('U13 VERIFICATION PASS',args.kind,args.stall,[(r['engine'],r['requests'],r['service_clocks']) for r in rows],flush=True)


if __name__=='__main__':
    main()
