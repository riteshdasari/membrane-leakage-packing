"""Check the exact full-range baseline before assigning savings to adaptation."""
from pathlib import Path
import ctypes,hashlib,json,random,re,subprocess,os
P=Path(__file__).resolve().parent;R=P/'results';V=Path('C:/AMDDesignTools/2025.2/Vivado')
class Mem(ctypes.Structure):
 _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong),('total',ctypes.c_ulonglong),('free',ctypes.c_ulonglong),('rest',ctypes.c_ulonglong*5)]
def free():
 m=Mem();m.length=ctypes.sizeof(m);ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m));return m.free/2**30
def pack(v):return sum((x&1023)<<(10*i)for i,x in enumerate(v))
def leak(u,b):return -((-u*b)//256)
cases=0
for b in range(257):
 for u in range(-512,512):
  r=((u+128)%256)-128;h=(u-r)//256
  assert -2<=h<=2 and u==256*h+r
  assert b*h+leak(r,b)==leak(u,b);cases+=1
(R/'split_leak_algebra.json').write_text(json.dumps(dict(cases=cases,failures=0),indent=2))
rows=[];rng=random.Random(67099)
hashes={n:hashlib.sha256((P/n).read_bytes()).hexdigest()for n in ['split_leak.sv','packed_leak.sv']}
for bc in [231,-1]:
 print('Free GiB',round(free(),2),flush=True);assert free()>1.0,'Insufficient RAM for small RTL simulation'
 samples=[(1,b if bc<0 else bc,[u,((u+512)*73%1024)-512])for b in (range(257)if bc<0 else[bc])for u in range(-512,512)]
 samples += [(int(rng.random()>.13),rng.randrange(257),[rng.randrange(-512,512)for i in range(2)])for _ in range(8000)]
 exp=[pack([leak(x,bc if bc>=0 else b)for x in u])for v,b,u in samples if v]
 wd=R/f'split_leak_{bc}';wd.mkdir(exist_ok=True)
 (wd/'stim.txt').write_text(str(len(samples))+'\n'+'\n'.join(f'{v} {b} {pack(u):x}'for v,b,u in samples)+'\n')
 cmds=[f'"{V}/bin/xvlog.bat" -sv -d "BC={bc}" "{P}/packed_leak.sv" "{P}/split_leak.sv" "{P}/tb_split_leak.sv"',f'"{V}/bin/xvlog.bat" "{V}/data/verilog/src/glbl.v"',f'"{V}/bin/xelab.bat" -mt off -L unisims_ver tb_split_leak glbl -s sim',f'"{V}/bin/xsim.bat" sim -R']
 temp=wd/'tmp';temp.mkdir(exist_ok=True);env=os.environ.copy();env['TEMP']=str(temp);env['TMP']=str(temp)
 for i,cmd in enumerate(cmds):
  result=subprocess.run(cmd,shell=True,cwd=wd,env=env,capture_output=True,text=True);(wd/f'tool_{i}.log').write_text(result.stdout+result.stderr)
  assert result.returncode==0,result.stdout[-3000:]+result.stderr[-1000:]
 cycle=re.search(r'SPLIT CYCLES (\d+) ACCEPTED (\d+) OUTPUTS (\d+)',result.stdout);assert cycle,result.stdout[-3000:]
 for e in [0,1]:
  got=[int(s,16)for s in (wd/f'out{e}.txt').read_text().splitlines()]
  bad=sum(a!=b for a,b in zip(got,exp))+abs(len(got)-len(exp));assert not bad,(bc,e,bad,[(i,a,b)for i,(a,b)in enumerate(zip(got,exp))if a!=b][:4])
  row=dict(constant_beta=bc,engine=e,requests=len(exp),mismatches=bad,driver_cycles=int(cycle[1]),accepted=int(cycle[2]),outputs=int(cycle[3]));rows.append(row);print(row,flush=True)
 (R/'split_leak_checks.json').write_text(json.dumps(dict(source_hashes=hashes,rows=rows),indent=2))
print('SPLIT LEAK PASS',flush=True)
