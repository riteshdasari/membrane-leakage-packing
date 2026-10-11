"""Independently accept completed vendor-native outputs using a cached scalar oracle."""
from pathlib import Path
import argparse,hashlib,json,re,sys,time
sys.dont_write_bytecode=True
import numpy as np
P=Path(__file__).resolve().parent
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as f:
        for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
    return h.hexdigest()
def read(p):return json.loads(Path(p).read_text())
def pins(paths):return{str(Path(p).resolve()):sha(p)for p in paths}
def verify(d):
    for p,s in d.items():assert sha(p)==s,('changed producer/source',p)
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--directory',required=True);ap.add_argument('--cohort',choices=['pair','scalar'],required=True)
    ap.add_argument('--stall',type=int,choices=[0,1],required=True);ap.add_argument('--capture',type=int,choices=[0,1],default=0)
    ap.add_argument('--execution-source-snapshot',required=True);ap.add_argument('--label',required=True);args=ap.parse_args()
    assert re.fullmatch(r'[a-zA-Z0-9_-]+',args.label)
    wd=Path(args.directory).resolve();out=wd/f'acceptance_cached_{args.label}.json';context=wd/f'execution_sources_cached_{args.label}.json'
    assert wd.is_dir()and not out.exists()and not context.exists(),'Retain all original and prior imported artifacts.'
    started=time.monotonic();producer=read(wd/'provenance.json');verify(producer)
    original=P/'run_native_static9.py';assert producer[str(original)]==sha(original)
    prep=read(P/'preparation.json');scalar=read(P/'scalar_cohort.json')
    for d in(prep,scalar):verify(d['source_sha256']);verify(d['artifact_sha256'])
    execution=read(args.execution_source_snapshot);verify(execution['source_sha256'])
    source=P/('narrow_stim.txt'if args.cohort=='pair'else'scalar_stim.txt');expected_file=P/('narrow_expected.npz'if args.cohort=='pair'else'scalar_expected.npz')
    assert sha(wd/'stim.txt')==sha(source)==producer[str(wd/'stim.txt')]
    jobs=[];logs=[]
    for i in range(4):
        file=wd/f'tool_{i}.job.json';j=read(file);log=wd/f'tool_{i}.log'
        assert j['returncode']==0 and Path(j['cwd']).resolve()==wd and j['source_sha256']==producer
        verify(j['source_sha256']);assert j['log_sha256']==sha(log)
        jobs.append(j);logs.extend([file,log])
    c=jobs[0]['argv'];assert Path(c[0]).name=='xvlog.bat'and '-sv'in c and f'STALL={args.stall}'in c and f'CAPTURE={args.capture}'in c
    required=[P.parent/'leak_core16.sv',P/'leak_core_static9.sv',P/'leak_dsp.sv',P/'tb_static9.sv']
    assert [Path(x).resolve()for x in c[-4:]]==required
    c=jobs[1]['argv'];assert Path(c[0]).name=='xvlog.bat'and len(c)==2
    glbl=Path(c[1]).resolve();assert glbl.name=='glbl.v'and execution['source_sha256'][str(glbl)]==sha(glbl)
    c=jobs[2]['argv'];assert Path(c[0]).name=='xelab.bat'and c[1:]==['-mt','off','-debug','typical','-L','unisims_ver','tb_sequential_static9','glbl','-s','sim']
    c=jobs[3]['argv'];assert Path(c[0]).name=='xsim.bat'and c[1:]==['sim','-R']
    text=(wd/'tool_3.log').read_text(errors='replace');assert 'LEAK_NATIVE PASS'in text and not re.search(r'\bFatal:|LEAK_NATIVE.*FAIL',text)
    with np.load(expected_file)as a:
        U=a['U'];beta=a['beta'];saved=a['expected_leak'];lengths=a['frame_lengths']
    assert np.all((-256<=U)&(U<=255))and np.all((0<=beta)&(beta<=256))
    oracle=-np.floor_divide(-(U.astype(np.int64)*beta.astype(np.int64)),256);assert np.array_equal(oracle,saved)
    ends=np.repeat(np.cumsum(lengths),lengths);wanted=prep['native_expected_requests_by_index']if args.cohort=='pair'else scalar['expected_requests_by_native_index'];rows=[]
    for index,e in enumerate((5,8)):
        pos=requests=0;lo=10**9;hi=0;last_cycle=None
        with(wd/f'out{index}.txt').open()as f:
            for line in f:
                cycle,count,value,latency=line.split();cycle=int(cycle);count=int(count);value=int(value,16);latency=int(latency)
                assert pos<len(U);pair=pos+1<ends[pos]and beta[pos]==beta[pos+1]
                assert count==(2 if pair else 1)and latency>=2
                want=int(oracle[pos])&65535
                if pair:want|=(int(oracle[pos+1])&65535)<<16
                assert value==want,(e,pos,value,want)
                if last_cycle is not None:assert cycle>last_cycle
                last_cycle=cycle;pos+=count;requests+=1;lo=min(lo,latency);hi=max(hi,latency)
        assert pos==len(U)and requests==wanted[index]
        m=re.search(rf'LEAK_NATIVE E {index} REQUESTS (\d+) RETIREMENTS (\d+) NEURONS (\d+) CLOCKS (\d+) MIN_LATENCY (\d+) MAX_LATENCY (\d+) FIRST (\d+) LAST (\d+)',text);assert m
        req,ret,N,clocks,minlat,maxlat,first,last=map(int,m.groups());assert req==ret==requests and N==pos and(minlat,maxlat)==(lo,hi)and last==last_cycle
        assert clocks==last-first+1
        if args.stall==0:assert lo==hi==2 and clocks==req+2
        rows.append(dict(engine=e,native_index=index,requests=req,retirements=ret,neurons=N,service_clocks=clocks,min_latency=lo,max_latency=hi,first_accept=first,last_retire=last))
    # Save immutable execution-source context rather than pinning a mutable progress JSON.
    context_record=dict(status='verified_original_execution_sources',original_progress_file=str(Path(args.execution_source_snapshot).resolve()),progress_sha256_at_import=sha(args.execution_source_snapshot),source_sha256=execution['source_sha256'])
    context.write_text(json.dumps(context_record,indent=2)+'\n')
    stamps=producer|execution['source_sha256']|pins([Path(__file__),context,P/'preparation.json',P/'scalar_cohort.json',expected_file,glbl])
    artifacts=[wd/'provenance.json',wd/'stim.txt',*logs,*[wd/f'out{i}.txt'for i in range(2)]]
    if args.capture:artifacts +=[wd/f'trace{i}.txt'for i in range(2)]
    verify(stamps)
    record=dict(status='pass',B=16,legal_state_signed_bits=9,cohort=args.cohort,stall=args.stall,capture=args.capture,rows=rows,source_sha256=stamps,artifact_sha256=pins(artifacts),
                producer_runner_file=str(original),producer_runner_sha256=sha(original),postprocess_auditor_file=str(Path(__file__).resolve()),
                supplemental_execution_context_file=str(context),supplemental_execution_context_role='Original parent sequence source snapshot for preservation and consistency; only provenance.json and tool job records identify the actual native producer sources.',
                scalar_oracle='Independent mathematical ceil(U*beta/256) by signed floor division; saved NPZ values also compared, exact zero mismatches.',
                cached_array_loads=4,host_audit_seconds=time.monotonic()-started,
                scope='Completed original v1 vendor jobs and raw outputs independently audited with cached arrays. New receipt only; original v1/provenance/output artifacts not overwritten. E8signed9-only ablation, not full16 baseline or energy evidence.')
    out.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(dict(status='pass',receipt=str(out),rows=rows,seconds=record['host_audit_seconds'])),flush=True)
if __name__=='__main__':main()
