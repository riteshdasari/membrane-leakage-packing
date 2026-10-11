"""Independent plain signed sum, protocol and original LIF feedback verification."""
from pathlib import Path
import argparse,hashlib,json,re,sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;ROOT=P.parent
sys.path.insert(0,str(ROOT/'trained_reference_native_trial'))
from prepare_restored_work import sha,pins,verify,signed
from verify_restored_native import network_replay
from workload import load_groups,take_for,MAP
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,required=True)
    ap.add_argument('--kind',choices=('main','shift1','shift3'),required=True)
    ap.add_argument('--stall',type=int,choices=(0,1),required=True);a=ap.parse_args()
    wd=a.directory.resolve();out=wd/'native_checks.json';assert not out.exists()
    work=json.loads((wd/'workload.json').read_text());verify(work['source_sha256']);verify(json.loads((wd/'provenance.json').read_text()))
    assert work['status']=='pass' and work['kind']==a.kind and sha(wd/'stream_stim.txt')==work['stimulus_sha256']
    groups=load_groups(wd/'stream_stim.txt');assert len(groups)==work['groups']
    ledger=None;oldnumeric=None
    if a.kind!='main':
        shift=int(a.kind[-1]);ledger=json.loads((wd/'reference_ledger.json').read_text())
        assert sha(wd/'reference_ledger.json')==work['ledger_sha256']
        assert len(groups)==len(ledger['ledger'])==9216
        assert all(gap==0 and pairs==list(zip(rec['postleak_U'],rec['current']))for(gap,pairs),rec in zip(groups,ledger['ledger']))
        prior=ROOT/'trained_reference_native_trial/results'/f'native_shift{shift}_stall{a.stall}_a1/native_checks.json'
        old=json.loads(prior.read_text());assert old['status']=='pass';oldnumeric=old['rows'][0]['numeric_retirement_sha256']
    else:
        assert work['exhaustive_scalar_pairs']==238592
        for offset,(_,pairs)in enumerate(groups[:932]):assert pairs==[(offset-686,i)for i in range(-128,128)]
    log=(wd/'tool_3.log').read_text();assert f'CERTIFIED_U11 PASS STALL {a.stall}'in log
    assert not re.search(r'Fatal:|Error:|Timing violation',log,re.I)
    artifacts=pins([wd/'stream_stim.txt',wd/'workload.json',wd/'tool_3.log']);rows=[]
    if ledger is not None:artifacts.update(pins([wd/'reference_ledger.json',prior]))
    pattern=(r'FRONTIER E {e} REQUESTS (\d+) RETIREMENTS (\d+) NEURONS (\d+) CLOCKS (\d+) '
        r'INPUT_STALLS (\d+) OUTPUT_STALLS (\d+) MIN_LATENCY (\d+) MAX_LATENCY (\d+) '
        r'TRACE_ROWS (\d+) FIRST_ACCEPT_TRACE (-?\d+) LAST_RETIRE_TRACE (-?\d+) GROUP_DRAINS (\d+) RESET_SAMPLES (\d+) PRELUDE_SAMPLES (\d+)')
    for e in range(5):
        m=re.search(pattern.format(e=e),log);assert m
        req,ret,ns,clocks,ins,outs,minlat,maxlat,trcount,first,last,drains,rst,pre=map(int,m.groups())
        path=wd/f'frontier_out{e}.txt';artifacts.update(pins([path]));gid=pos=neurons=requests=0
        all_sums=[[]for _ in groups];digest=hashlib.sha256();hist={};startclock=endclock=None
        for line in path.open():
            group,start,n,bits,accepted,retired,advance=line.split()
            group,start,n,accepted,retired,advance=map(int,(group,start,n,accepted,retired,advance));bits=int(bits,16)
            assert gid==group and pos==start and n==take_for(e,groups[gid][1],pos)
            assert 0<=bits<1<<96 and advance==1 and retired-accepted>=1
            for lane in range(8):
                got=signed((bits>>(12*lane))&4095,12);want=sum(groups[gid][1][pos+lane])if lane<n else 0
                assert got==want,(e,gid,pos,lane,got,want)
                if lane<n:
                    if e in(0,4)and lane>=5:assert -128<=groups[gid][1][pos+lane][0]<=127
                    all_sums[gid].append(got);digest.update(got.to_bytes(2,'little',signed=True))
            requests+=1;neurons+=n;pos+=n
            if startclock is None:startclock=accepted
            endclock=retired;hist[str(retired-accepted)]=hist.get(str(retired-accepted),0)+1
            if pos==len(groups[gid][1]):gid+=1;pos=0
        assert gid==len(groups)and pos==0 and neurons==ns==work['neurons'] and requests==req==ret==work['predictions'][e]['requests']
        assert clocks==endclock-startclock+1 and drains==len(groups)and rst>=4 and pre>=15
        assert first>=0 and last<trcount and min(map(int,hist))==minlat and max(map(int,hist))==maxlat
        if a.stall:assert ins>0 and outs>0
        else:
            assert ins==outs==0 and minlat==maxlat==1
            if ledger is not None:assert clocks==req+9216
        row=dict(status='pass',engine=e,label=MAP[e],requests=req,retirements=ret,neurons=ns,service_clocks=clocks,
            take_histogram=work['predictions'][e]['take_histogram'],physical_latency_histogram=hist,
            numeric_retirement_sha256=digest.hexdigest(),retirement_file=str(path),retirement_sha256=sha(path),
            input_stalls=ins,output_stalls=outs,group_drains=drains,reset_samples=rst,prelude_samples=pre)
        if ledger is not None:
            assert digest.hexdigest()==oldnumeric
            row['actual_retired_feedback']=network_replay(all_sums,ledger,shift)
            row['original_LIF_numeric_retirements_match']=True
        rows.append(row)
    assert len({r['numeric_retirement_sha256']for r in rows})==1
    assert (wd/'frontier_out0.txt').read_bytes()==(wd/'frontier_out4.txt').read_bytes()
    assert (wd/'frontier_out1.txt').read_bytes()==(wd/'frontier_out2.txt').read_bytes()==(wd/'frontier_out3.txt').read_bytes()
    value=dict(status='pass',kind=a.kind,backpressure=bool(a.stall),rows=rows,
        latency_advancing_edges=1,operand_domain='Certified U [-686,245], signed8 I; exact signextended sum11',
        exhaustive_scalar_pairs=work['exhaustive_scalar_pairs'],source_sha256=pins([Path(__file__),P/'workload.py']),
        candidate_file_sha256=artifacts,scope='Native arithmetic/protocol and actual unchanged LIFfeedback only; no routed SDF or new power/accuracygain')
    out.write_text(json.dumps(value,indent=2)+'\n');print('NATURAL U11 VERIFIED',a.kind,a.stall,flush=True)
if __name__=='__main__':main()
