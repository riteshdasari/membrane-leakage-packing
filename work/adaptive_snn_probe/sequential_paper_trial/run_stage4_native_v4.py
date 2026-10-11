"""Serial RAM-gated native arithmetic/protocol cohorts for six controls."""
from pathlib import Path
import hashlib,json,re,sys,time
sys.dont_write_bytecode=True
import numpy as np
P=Path(__file__).resolve().parent;ROOT=P.parent
sys.path.insert(0,str(ROOT/'selective_energy_trial'))
import run_selective_energy as base
sha,read,write,pins,verify=base.sha,base.read,base.write,base.pins,base.verify
def frames(kind):
    actual=[];lines=iter((P/'stage3_actual_frames.txt').read_text().splitlines());nf=int(next(lines))
    for _ in range(nf):
        n=int(next(lines));actual.append([tuple(map(int,next(lines).split()))for _ in range(n)])
    if kind=='actual':return actual
    groups=[]
    # Every narrow first-lane value and coefficient, with a different second lane.
    for b in range(257):
        for u in range(-256,256):groups.append([(u,b),(((u+256)*73%512)-256,b)])
    boundary=(-2048,-2047,-1024,-257,-256,-4,-3,-2,-1,0,1,127,128,255,256,257,1023,1024,2046,2047)
    for b in range(257):
        for u in boundary:groups.append([(u,b),(-u-1,b)])
    rng=np.random.default_rng(23917)
    for _ in range(1000):groups.append([(int(rng.integers(-2048,2048)),int(rng.integers(257)))for j in range(4)])
    return groups+actual
def predicted_take(e,items,pos):
    left=len(items)-pos
    if left==1:return 1
    u,b=items[pos];v,c=items[pos+1]
    if e in(2,3):return 2
    if e==4:return 1
    if e==1:return 2 if b==c else 1
    return 2 if b==c and -256<=u<=255 and -256<=v<=255 and(e==5 or b>=64)else 1
def tool(command,wd,label,stamps,gate=1.2):
    while base.free()<=gate+.15:time.sleep(5)
    return base.job([str(x).replace('\\','/')for x in command],wd,label,stamps,gate)
def check(wd,groups,stall):
    values=[p for g in groups for p in g];ends=[];end=0
    for g in groups:end+=len(g);ends.extend([end]*len(g))
    rows=[];log=(wd/'tool_3.log').read_text(errors='replace')
    assert 'LEAK_NATIVE PASS'in log
    for e in range(6):
        pos=0;request=0;gidx=0;local=0;minimum=10**9;maximum=0
        with(wd/f'out{e}.txt').open()as stream:
            for line in stream:
                cycle,count,data,lat=line.split();count=int(count);data=int(data,16);lat=int(lat)
                while local==len(groups[gidx]):gidx+=1;local=0
                wanttake=predicted_take(e,groups[gidx],local)
                assert count==wanttake,(e,pos,count,wanttake)
                want=0
                for lane in range(count):
                    u,b=values[pos+lane];want|=((-((-u*b)//256))&4095)<<(12*lane)
                assert data==want,(e,pos,data,want)
                pos+=count;local+=count;request+=1;minimum=min(minimum,lat);maximum=max(maximum,lat)
        assert pos==len(values)
        pat=rf'LEAK_NATIVE E {e} REQUESTS (\d+) RETIREMENTS (\d+) NEURONS (\d+) CLOCKS (\d+) MIN_LATENCY (\d+) MAX_LATENCY (\d+) FIRST (\d+) LAST (\d+)'
        m=re.search(pat,log);assert m
        req,ret,n,clocks,lo,hi,first,last=map(int,m.groups())
        assert req==ret==request and n==pos and lo==minimum and hi==maximum
        if not stall:assert lo==hi==2 and clocks==request+2
        rows.append(dict(engine=e,requests=req,retirements=ret,neurons=n,service_clocks=clocks,
            min_latency=lo,max_latency=hi,first_accept=first,last_retire=last,output_sha256=sha(wd/f'out{e}.txt')))
    return rows
def main():
    prepared=read(P/'stage4_source_preparation.json');verify(prepared['source_sha256'])
    stamps=prepared['source_sha256']|pins([P/'tb_native_v3.sv',Path(__file__),P/'stage3_actual_frames.txt',P/'stage3_acceptance.json'])
    complete=[]
    for kind,stall,capture in(('main',0,0),('main',1,0),('actual',0,1)):
        wd=P/'hardware'/f'native_{kind}_s{stall}_a3';assert not wd.exists();wd.mkdir(parents=True)
        groups=frames(kind);flat=[p for g in groups for p in g];end=0
        with(wd/'stim.txt').open('w',encoding='utf-8',newline='\n')as stream:
            stream.write(str(len(flat))+'\n')
            for group in groups:
                end+=len(group)
                for u,b in group:stream.write(f'{u} {b} {end}\n')
        this=stamps|pins([wd/'stim.txt']);write(wd/'provenance.json',this)
        commands=[[base.VIVADO/'bin/xvlog.bat','-sv','-d',f'STALL={stall}','-d',f'CAPTURE={capture}',P/'leak_core.sv',P/'leak_dsp.sv',P/'tb_native_v3.sv'],
            [base.VIVADO/'bin/xvlog.bat',base.VIVADO/'data/verilog/src/glbl.v'],
            [base.VIVADO/'bin/xelab.bat','-mt','off','-debug','typical','-L','unisims_ver','tb_sequential_leak','glbl','-s','sim'],
            [base.VIVADO/'bin/xsim.bat','sim','-R']]
        for i,c in enumerate(commands):tool(c,wd,f'tool_{i}',this)
        rows=check(wd,groups,stall);verify(this)
        record=dict(status='pass',kind=kind,stall=stall,rows=rows,source_sha256=this,
            artifact_sha256=pins([wd/f'out{e}.txt'for e in range(6)]+([wd/f'trace{e}.txt'for e in range(6)]if capture else[])),
            sampled_true_model_operations=len(flat)if kind=='actual'else None)
        write(wd/'acceptance.json',record);complete.append(str(wd/'acceptance.json'))
        print('STAGE4 NATIVE PASS',kind,stall,rows,flush=True)
    write(P/'stage4_native_acceptance_v4.json',dict(status='pass',cohorts=complete,source_sha256=stamps,artifact_sha256=pins(map(Path,complete))))
if __name__=='__main__':main()
