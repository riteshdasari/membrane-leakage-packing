"""Explicit narrow-domain E5/E8 native comparison; root owns tool scheduling."""
from pathlib import Path
import argparse,re,sys,time
sys.dont_write_bytecode=True
import numpy as np
P=Path(__file__).resolve().parent;ROOT=P.parent.parent.parent
sys.path.insert(0,str(ROOT/'selective_energy_trial'))
import run_selective_energy as base
sha,read,write,pins,verify=base.sha,base.read,base.write,base.pins,base.verify
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cohort',choices=['pair','scalar'],required=True);ap.add_argument('--stall',type=int,choices=[0,1],default=0);ap.add_argument('--capture',type=int,choices=[0,1],default=0);ap.add_argument('--attempt',required=True);args=ap.parse_args()
    assert re.fullmatch(r'[a-zA-Z0-9_-]+',args.attempt)
    prep=read(P/'preparation.json');verify(prep['source_sha256']);verify(prep['artifact_sha256'])
    scalar=read(P/'scalar_cohort.json');verify(scalar['source_sha256']);verify(scalar['artifact_sha256'])
    source=P/('narrow_stim.txt'if args.cohort=='pair'else'scalar_stim.txt');output=P/('narrow_expected.npz'if args.cohort=='pair'else'scalar_expected.npz')
    wanted=prep['native_expected_requests_by_index']if args.cohort=='pair'else scalar['expected_requests_by_native_index']
    wd=P/'hardware'/args.attempt;assert not wd.exists();wd.mkdir(parents=True);(wd/'stim.txt').write_bytes(source.read_bytes())
    stamps=prep['source_sha256']|prep['artifact_sha256']|scalar['source_sha256']|scalar['artifact_sha256']|pins([Path(__file__),P/'preparation.json',P/'scalar_cohort.json',wd/'stim.txt'])
    write(wd/'provenance.json',stamps)
    commands=[[base.VIVADO/'bin/xvlog.bat','-sv','-d',f'STALL={args.stall}','-d',f'CAPTURE={args.capture}',P.parent/'leak_core16.sv',P/'leak_core_static9.sv',P/'leak_dsp.sv',P/'tb_static9.sv'],
        [base.VIVADO/'bin/xvlog.bat',base.VIVADO/'data/verilog/src/glbl.v'],
        [base.VIVADO/'bin/xelab.bat','-mt','off','-debug','typical','-L','unisims_ver','tb_sequential_static9','glbl','-s','sim'],
        [base.VIVADO/'bin/xsim.bat','sim','-R']]
    for i,c in enumerate(commands):
        while base.free()<=1.35:time.sleep(5)
        base.job([str(x).replace('\\','/')for x in c],wd,f'tool_{i}',stamps,1.2)
    log=(wd/'tool_3.log').read_text(errors='replace');assert 'LEAK_NATIVE PASS'in log
    a=np.load(output);ends=np.repeat(np.cumsum(a['frame_lengths']),a['frame_lengths']);rows=[]
    for index,e in enumerate((5,8)):
        pos=req=0;lo=10**9;hi=0
        for line in(wd/f'out{index}.txt').read_text().splitlines():
            cycle,count,data,latency=line.split();count=int(count);data=int(data,16);latency=int(latency)
            pair=pos+1<ends[pos]and a['beta'][pos]==a['beta'][pos+1]
            assert count==(2 if pair else 1)
            want=int(a['expected_leak'][pos])&65535
            if pair:want|=(int(a['expected_leak'][pos+1])&65535)<<16
            assert data==want and latency>=2;pos+=count;req+=1;lo=min(lo,latency);hi=max(hi,latency)
        assert pos==len(a['U'])and req==wanted[index]
        match=re.search(rf'LEAK_NATIVE E {index} REQUESTS (\d+) RETIREMENTS (\d+) NEURONS (\d+) CLOCKS (\d+) MIN_LATENCY (\d+) MAX_LATENCY (\d+) FIRST (\d+) LAST (\d+)',log);assert match
        requests,retires,N,clocks,minlat,maxlat,first,last=map(int,match.groups());assert requests==retires==req and N==pos and lo==minlat and hi==maxlat
        if args.stall==0:assert lo==hi==2 and clocks==req+2
        rows.append(dict(engine=e,native_index=index,requests=req,retirements=retires,neurons=N,service_clocks=clocks,min_latency=lo,max_latency=hi,first_accept=first,last_retire=last))
    verify(stamps);record=dict(status='pass',B=16,legal_state_signed_bits=9,cohort=args.cohort,stall=args.stall,capture=args.capture,rows=rows,source_sha256=stamps,artifact_sha256=pins([wd/f'out{i}.txt'for i in range(2)]+([wd/f'trace{i}.txt'for i in range(2)]if args.capture else[])),scope='E8signed9-onlycostablation; E5reference equalityonlegalnarrowinputs, notfull16baseline orwidecorrectness.')
    write(wd/'acceptance.json',record);print('E8 NATIVE PASS',args.cohort,args.stall,rows,flush=True)
if __name__=='__main__':main()
