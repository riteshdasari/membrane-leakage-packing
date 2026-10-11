"""Independent oracle, ordered-window policy and exact streaming RTL checks."""
from pathlib import Path
import os,json,hashlib,random,re,subprocess,sys,ctypes
P=Path(__file__).resolve().parent;R=P/'results';V=Path('C:/AMDDesignTools/2025.2/Vivado')
def free():
 class M(ctypes.Structure):
  _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong),('total',ctypes.c_ulonglong),('free',ctypes.c_ulonglong),('rest',ctypes.c_ulonglong*5)]
 m=M();m.length=ctypes.sizeof(m);ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m));return m.free/2**30
def hashes(variant='offset'):
 stem='stream_fold_leak'
 return {n:hashlib.sha256((P/n).read_bytes()).hexdigest()for n in [stem+'.sv','tb_'+stem+'.sv']}
def policy(u,d,e,variant='offset'):
 n=min(3,len(u));x=u[:n]
 absolute=n==3 and all(-16<=v<=15 for v in x)
 coherent=n==3 and len({v//32 for v in x})==1
 eligible=(absolute or coherent)if variant=='offset'else(n==3 and len({(v+16)//32 for v in x})==1)
 fit6=n==3 and all(-32<=v<=31 for v in x)
 fit7=n==3 and all(-64<=v<=63 for v in x)
 narrow=(e==0 and (fit6 or (d<=25 and fit7)))or(e==6 and fit6)
 bypass=d==0 or not any(x)
 take=3 if n==3 and(e in [3,4,5]or narrow or bypass or x[2]==0)else min(2,n)
 return take,int(narrow),bypass
def write_stim(wd,frames):
 with(wd/'stream_stim.txt').open('w')as f:
  f.write(str(len(frames))+'\n')
  for u,d,gap in frames:
   f.write(f'{len(u)} {d} {gap}\n');f.writelines(f'{x&2047:03x}\n'for x in u)
def simulate(tag,frames,dc,stall,variant='offset'):
 wd=R/tag;wd.mkdir(exist_ok=True);write_stim(wd,frames)
 stem='stream_fold_leak'
 stamp=hashes(variant);print(tag,'free GiB',round(free(),2),'frames',len(frames),flush=True);assert free()>1.2
 debug=' -d DEBUG'if '--debug'in sys.argv else''
 commands=[f'"{V}/bin/xvlog.bat" -sv -d "DC={dc}" -d "STALL={stall}"{debug} "{P}/{stem}.sv" "{P}/tb_{stem}.sv"',
  f'"{V}/bin/xvlog.bat" "{V}/data/verilog/src/glbl.v"',
  f'"{V}/bin/xelab.bat" -mt off -L unisims_ver tb_{stem} glbl -s sim',f'"{V}/bin/xsim.bat" sim -R']
 temp=wd/'tmp';temp.mkdir(exist_ok=True);env=os.environ.copy();env['TEMP']=str(temp);env['TMP']=str(temp)
 for i,c in enumerate(commands):
  z=subprocess.run(c,shell=True,cwd=wd,env=env,capture_output=True,text=True);(wd/f'tool_{i}.log').write_text(z.stdout+z.stderr)
  assert z.returncode==0,z.stdout[-4000:]+z.stderr[-1000:]
 assert 'STREAM OFFSET PASS'in z.stdout,z.stdout[-4000:]
 assert hashes(variant)==stamp,'Source changed during simulation'
 rows=[]
 for e in [0,1,2,3,4,5,6]:
  outputs=(wd/f'stream_out{e}.txt').read_text().splitlines();positions=[0]*len(frames);bad=0;expected_req=0;expected_issues=0
  for fid,(u,d,gap)in enumerate(frames):
   pos=0;d=dc if dc>=0 else d
   while pos<len(u):
    n,_,by=policy(u[pos:],d,e,variant);pos+=n;expected_req+=1;expected_issues+=not by
  assert len(outputs)==expected_req,(e,len(outputs),expected_req)
  for line in outputs:
   fid,pos,n,d,packed,ac,rc,mode=line.split();fid,pos,n,d,ac,rc,mode=map(int,[fid,pos,n,d,ac,rc,mode]);packed=int(packed,16)
   u,fd,gap=frames[fid];fd=dc if dc>=0 else fd
   nn,mm,by=policy(u[pos:],fd,e,variant);assert (n,mode,d,pos)==(nn,mm,fd,positions[fid]),(e,line,u[pos:pos+3])
   got=[(packed>>(11*i))&2047 for i in range(3)];expected=[(-((-x*(256-d))//256))&2047 for x in u[pos:pos+n]]+[0]*(3-n)
   if got!=expected:
    bad+=1
    if bad<=3:print('MISMATCH',e,line,u[pos:pos+n],got,expected,flush=True)
   positions[fid]+=n
   if not stall:assert rc-ac==3,(e,ac,rc)
  assert not bad,(tag,e,bad);assert positions==[len(f[0])for f in frames]
  m=re.search(rf'STREAM E {e} REQUESTS (\d+) NEURONS (\d+) ISSUES (\d+) NARROW (\d+) BYPASS (\d+) CLOCKS (\d+)',z.stdout);assert m
  row=dict(engine=e,requests=int(m[1]),neurons=int(m[2]),arithmetic_issues=int(m[3]),narrow_requests=int(m[4]),bypass_requests=int(m[5]),clocks=int(m[6]),mismatches=bad)
  assert row['requests']==expected_req and row['arithmetic_issues']==expected_issues
  if not stall and not any(f[2]for f in frames):assert row['clocks']==row['requests']+3
  rows.append(row);print(row,flush=True)
 result=dict(source_hashes=stamp,constant_delta=dc,backpressure=bool(stall),frames=len(frames),rows=rows)
 (R/(tag+'_checks.json')).write_text(json.dumps(result,indent=2));return result
if __name__=='__main__':
 small='--small'in sys.argv;rg=random.Random(73159);frames=[]
 for d in ([25,0,31]if small else range(32)):
  for x in ([-1024,-1000,-513,-17,-16,-1,0,1,15,16,31,32,511,1000,1023]if small else range(-1024,1024)):
   b=(x//32)*32
   frames.extend([([x,b+31,b],d,0),([x,((x+1024)*97%2048)-1024,-x-1],d,0)])
 if not small:
  # All signed-int5 triples for the constant target, including the -1/0 bin crossing.
  for a in range(-16,16):
   for b in range(-16,16):
    for c in range(-16,16):frames.append(([a,b,c],25,0))
 for j in range(100 if small else 3000):
  d=rg.randrange(32);length=rg.randrange(1,35)
  if j%7==0:u=[0]*length
  elif j%3==0:
   b=rg.randrange(-32,32)*32;u=[b+rg.randrange(32)for _ in range(length)]
  else:u=[rg.randrange(-1024,1024)for _ in range(length)]
  frames.append((u,d,rg.randrange(3)if j%9==0 else 0))
 for dc,stall in [(25,0),(-1,1)]:simulate(f'stream_fold_{"smoke"if small else"main"}_{dc}_{stall}',frames,dc,stall)
