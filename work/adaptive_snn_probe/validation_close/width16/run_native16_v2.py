"""Explicitly invoked serial native16 run; preparation alone never launches tools."""
from pathlib import Path
import argparse,hashlib,json,re,sys,time
sys.dont_write_bytecode=True
import numpy as np
P=Path(__file__).resolve().parent;ROOT=P.parent.parent
sys.path.insert(0,str(ROOT/'selective_energy_trial'))
import run_selective_energy as base
sha,read,write,pins,verify=base.sha,base.read,base.write,base.pins,base.verify
def job(command,wd,label,stamps):
    while base.free()<=1.35:time.sleep(5)
    return base.job([str(x).replace('\\','/')for x in command],wd,label,stamps,1.2)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cohort',choices=['general','shift128','actual128','actual_glif'],required=True)
    ap.add_argument('--stall',type=int,choices=[0,1],default=0);ap.add_argument('--capture',type=int,choices=[0,1],default=1)
    ap.add_argument('--attempt',required=True);args=ap.parse_args()
    assert re.fullmatch(r'[a-zA-Z0-9_-]+',args.attempt)
    prep=read(P/'preparation_v2.json');verify(prep['source_sha256']);verify(prep['artifact_sha256'])
    domain=read(P/'domain_acceptance_glif_v2.json');assert domain['arithmetic_mismatches']==0
    verify(domain['source_sha256']);co=domain['cohorts'][args.cohort];verify(co['artifact_sha256'])
    wd=P/'hardware'/args.attempt;assert not wd.exists();wd.mkdir(parents=True)
    (wd/'stim.txt').write_bytes(Path(co['stimulus_file']).read_bytes())
    stamps=prep['source_sha256']|prep['artifact_sha256']|domain['source_sha256']|co['artifact_sha256']|pins([Path(__file__),wd/'stim.txt',P/'domain_acceptance_glif_v2.json'])
    write(wd/'provenance.json',stamps)
    shift=0 if args.cohort in('general','actual_glif') else 1
    commands=[[base.VIVADO/'bin/xvlog.bat','-sv','-d',f'STALL={args.stall}','-d',f'CAPTURE={args.capture}','-d',f'SHIFT_COHORT={shift}',P/'leak_core16.sv',P/'leak_dsp.sv',P/'tb_native16.sv'],
        [base.VIVADO/'bin/xvlog.bat',base.VIVADO/'data/verilog/src/glbl.v'],
        [base.VIVADO/'bin/xelab.bat','-mt','off','-debug','typical','-L','unisims_ver','tb_sequential_leak16','glbl','-s','sim'],
        [base.VIVADO/'bin/xsim.bat','sim','-R']]
    for i,command in enumerate(commands):job(command,wd,f'tool_{i}',stamps)
    log=(wd/'tool_3.log').read_text(errors='replace');assert 'LEAK_NATIVE PASS'in log
    expected=np.load(co['expected_outputs_file']);u=expected['U'];beta=expected['beta'];wanted=expected['expected_leak'];lengths=expected['frame_lengths'];ends=np.repeat(np.cumsum(lengths),lengths)
    rows=[]
    for e,want_requests in enumerate(co['expected_requests_by_engine']):
        pos=req=0;minlat=10**9;maxlat=0
        for line in(wd/f'out{e}.txt').read_text().splitlines():
            cycle,sz,out,lat=line.split();sz=int(sz);out=int(out,16);lat=int(lat)
            canpair=pos+1<ends[pos]
            if e==4:canpair=False
            elif e==1:canpair=canpair and beta[pos]==beta[pos+1]
            elif e in(0,5):canpair=canpair and beta[pos]==beta[pos+1]and -256<=u[pos]<=255 and -256<=u[pos+1]<=255 and(e==5 or beta[pos]>=64)
            assert sz==(2 if canpair else 1)
            want=int(wanted[pos])&65535
            if sz==2:want|=(int(wanted[pos+1])&65535)<<16
            assert out==want,(e,pos,out,want)
            assert lat>=2;minlat=min(minlat,lat);maxlat=max(maxlat,lat);pos+=sz;req+=1
        assert pos==co['operations']and req==want_requests
        pattern=rf'LEAK_NATIVE E {e} REQUESTS (\d+) RETIREMENTS (\d+) NEURONS (\d+) CLOCKS (\d+) MIN_LATENCY (\d+) MAX_LATENCY (\d+) FIRST (\d+) LAST (\d+)'
        match=re.search(pattern,log);assert match
        requests,retires,n,clocks,lo,hi,first,last=map(int,match.groups())
        assert requests==retires==req and n==pos and lo==minlat and hi==maxlat
        if args.stall==0:assert lo==hi==2 and clocks==req+2
        trace=wd/f'trace{e}.txt'
        rows.append(dict(engine=e,requests=req,retirements=retires,neurons=n,service_clocks=clocks,
            min_latency=lo,max_latency=hi,first_accept=first,last_retire=last,
            trace_rows=sum(1 for _ in trace.open()) if args.capture else None,output_sha256=sha(wd/f'out{e}.txt')))
    verify(stamps)
    acceptance=dict(status='pass',B=16,cohort=args.cohort,stall=args.stall,capture=args.capture,rows=rows,
        source_sha256=stamps,artifact_sha256=pins([wd/f'out{e}.txt'for e in range(len(rows))]+([wd/f'trace{e}.txt'for e in range(len(rows))]if args.capture else[])),
        scope='Native primitive exact outputs, order, admission, natural2edge latency and held-output protocol. Not model FPGA inference or timing/power validation.')
    write(wd/'acceptance.json',acceptance);print(json.dumps(dict(status='pass',B=16,cohort=args.cohort,rows=rows)),flush=True)
if __name__=='__main__':main()
