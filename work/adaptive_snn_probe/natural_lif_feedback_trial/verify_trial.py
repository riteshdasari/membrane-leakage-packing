"""Independent numeric/protocol and actual original LIF state-feedback audit."""
from pathlib import Path
import argparse,hashlib,json,re,sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;ROOT=P.parent;OLD=ROOT/'trained_reference_native_trial'
sys.path.insert(0,str(OLD))
from prepare_restored_work import sha,pins,verify,signed
from verify_restored_native import network_replay
from run_trial import take_for,MAP


def groups13(path):
    with Path(path).open() as stream:
        groups=[];total=int(stream.readline())
        for _ in range(total):
            count,gap=map(int,stream.readline().split());pairs=[]
            for _ in range(count):
                u,i=(signed(int(x,16),13) for x in stream.readline().split())
                assert -1024<=u<=1023 and -128<=i<=127;pairs.append((u,i))
            groups.append((gap,pairs))
        assert not stream.read().strip()
    return groups


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,required=True)
    ap.add_argument('--shift',type=int,choices=(1,3),required=True);ap.add_argument('--stall',type=int,choices=(0,1),required=True)
    a=ap.parse_args();wd=a.directory.resolve();out=wd/'native_checks.json';assert not out.exists()
    workload=json.loads((wd/'workload.json').read_text());verify(workload['source_sha256']);verify(json.loads((wd/'provenance.json').read_text()))
    assert sha(wd/'stream_stim.txt')==workload['stimulus_sha256'] and sha(wd/'reference_ledger.json')==workload['ledger_sha256']
    groups=groups13(wd/'stream_stim.txt');ledger=json.loads((wd/'reference_ledger.json').read_text())
    assert len(groups)==len(ledger['ledger'])==9216
    assert all(pairs==list(zip(rec['postleak_U'],rec['current'])) for (_,pairs),rec in zip(groups,ledger['ledger']))
    log=(wd/'tool_3.log').read_text();assert f'NATURAL_LIF_COMPARE PASS STALL {a.stall}' in log
    assert not re.search(r'Fatal:|Error:|Timing violation',log,re.I)
    oldcheck=json.loads((OLD/'results'/f'native_shift{a.shift}_stall{a.stall}_a1/native_checks.json').read_text())
    expected_numeric=oldcheck['rows'][0]['numeric_retirement_sha256'];assert oldcheck['status']=='pass'
    rows=[];artifacts=pins([wd/'stream_stim.txt',wd/'reference_ledger.json',wd/'workload.json',wd/'tool_3.log'])
    pattern=(r'FRONTIER E {e} REQUESTS (\d+) RETIREMENTS (\d+) NEURONS (\d+) CLOCKS (\d+) '
        r'INPUT_STALLS (\d+) OUTPUT_STALLS (\d+) MIN_LATENCY (\d+) MAX_LATENCY (\d+) '
        r'TRACE_ROWS (\d+) FIRST_ACCEPT_TRACE (-?\d+) LAST_RETIRE_TRACE (-?\d+) GROUP_DRAINS (\d+) RESET_SAMPLES (\d+) PRELUDE_SAMPLES (\d+)')
    for e in range(4):
        m=re.search(pattern.format(e=e),log);assert m
        req,ret,ns,clocks,ins,outs,minlat,maxlat,trcount,first,last,drains,rst,pre=map(int,m.groups())
        path=wd/f'frontier_out{e}.txt';artifacts.update(pins([path]));gid=pos=neurons=requests=0
        all_sums=[[] for _ in groups];digest=hashlib.sha256();hist={};startclock=endclock=None
        for line in path.open():
            group,start,n,bits,accepted,retired,advance=line.split()
            group,start,n,accepted,retired,advance=map(int,(group,start,n,accepted,retired,advance));bits=int(bits,16)
            assert gid==group and pos==start and n==take_for(e,groups[gid][1],pos)
            assert 0<=bits<(1<<112) and advance==1 and retired-accepted>=1
            for lane in range(8):
                got=signed((bits>>(14*lane))&16383,14);want=sum(groups[gid][1][pos+lane]) if lane<n else 0
                assert got==want,(e,gid,pos,lane,got,want)
                if lane<n:all_sums[gid].append(got);digest.update(got.to_bytes(2,'little',signed=True))
            requests+=1;neurons+=n;pos+=n
            if startclock is None:startclock=accepted
            endclock=retired;hist[str(retired-accepted)]=hist.get(str(retired-accepted),0)+1
            if pos==len(groups[gid][1]):gid+=1;pos=0
        assert gid==len(groups) and pos==0 and neurons==ns==635904 and requests==req==ret==workload['predictions'][e]['requests']
        assert clocks==endclock-startclock+1 and drains==9216 and rst>=4 and pre>=15
        assert min(map(int,hist))==minlat and max(map(int,hist))==maxlat
        if a.stall:assert ins>0 and outs>0
        else:assert ins==outs==0 and minlat==maxlat==1 and clocks==req+9216
        assert digest.hexdigest()==expected_numeric,'Numeric results differ from immutable original LIF hardware replay'
        rows.append(dict(status='pass',engine=e,implementation=MAP[e],requests=req,neurons=ns,service_clocks=clocks,
            take_histogram=workload['predictions'][e]['take_histogram'],physical_latency_histogram=hist,
            numeric_retirement_sha256=digest.hexdigest(),retirement_file=str(path),retirement_sha256=sha(path),
            actual_retired_feedback=network_replay(all_sums,ledger,a.shift),
            original_LIF_numeric_retirements_match=True,input_stalls=ins,output_stalls=outs))
    assert (wd/'frontier_out0.txt').read_bytes()==(wd/'frontier_out3.txt').read_bytes()
    assert (wd/'frontier_out1.txt').read_bytes()==(wd/'frontier_out2.txt').read_bytes()
    summary=json.loads((ROOT/'trained_reference_admission_study/restored_reference_summary.json').read_text())
    certificates=[]
    for profile in summary['profiles']:
        if profile['leak_shift']!=a.shift:continue
        layers=[]
        for rec in profile['weight_current_certificate']:
            lower=(2**a.shift-1)*min(rec['current_lower']);upper=(2**a.shift-1)*max(rec['current_upper'])
            assert -1024<=lower<=upper<=1023
            if a.shift==1:assert -128<=lower<=upper<=127
            layers.append(dict(layer=rec['layer'],all_binary_history_postleak_range=[lower,upper]))
        certificates.append(dict(seed=profile['seed'],layers=layers,static_postleak_U8=a.shift==1,
            observed_all360_U_range=profile['full360_postleak_U_range']))
    value=dict(status='pass',shift=a.shift,backpressure=bool(a.stall),rows=rows,precision_certificates=certificates,
        source_sha256=pins([Path(__file__),OLD/'verify_restored_native.py',OLD/'prepare_restored_work.py',
            OLD/'results'/f'native_shift{a.shift}_stall{a.stall}_a1/native_checks.json',ROOT/'trained_reference_admission_study/restored_reference_summary.json']),
        candidate_file_sha256=artifacts,latency_advancing_edges=1,
        scope='All three original LIF conversions, original coefficients and full360 RNG, first48 hardwarefeedback; only native exactness/service, no AdEx,routedtiming,power or trainedSNNaccuracygain')
    out.write_text(json.dumps(value,indent=2)+'\n');print('NATURAL LIF VERIFIED',a.shift,a.stall,flush=True)


if __name__=='__main__':main()
