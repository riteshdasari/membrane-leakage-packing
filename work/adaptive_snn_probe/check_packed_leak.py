"""Independent integer and UNISIM RTL check; no models/packages/downloads."""
from pathlib import Path
import ctypes,hashlib,json,random,re,subprocess,os
P=Path(__file__).resolve().parent;R=P/'results';V=Path('C:/AMDDesignTools/2025.2/Vivado')
class Mem(ctypes.Structure):
 _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong),('total',ctypes.c_ulonglong),('free',ctypes.c_ulonglong),('rest',ctypes.c_ulonglong*5)]
def free():
 m=Mem();m.length=ctypes.sizeof(m);ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m));return m.free/2**30
def pack(v,b):return sum((x&((1<<b)-1))<<(i*b)for i,x in enumerate(v))
def leak(u,beta):return -((-beta*u)//256)
count=0
for beta in range(257):
 k=128*(256-beta)+255
 for u in range(-128,128):
  raw=beta*(u+128)+k
  assert 0<=raw<=65535
  assert (raw>>8)-128==leak(u,beta);count+=1
rng=random.Random(86031)
for _ in range(100000):
 beta=rng.randrange(257);u=[rng.randrange(-128,128)for i in range(2)]
 q=[x+128 for x in u];k=128*(256-beta)+255
 p=(q[0]+(q[1]<<16))*beta+k+(k<<16)
 assert p==(q[0]*beta+k)+((q[1]*beta+k)<<16)
 assert [(p>>off&255)-128 for off in [8,24]]==[leak(x,beta)for x in u];count+=1
(R/'packed_leak_algebra.json').write_text(json.dumps(dict(cases=count,failures=0),indent=2))
rows=[];source_hash=hashlib.sha256((P/'packed_leak.sv').read_bytes()).hexdigest()
for bits,bc in [(8,231),(8,-1),(10,231),(10,-1)]:
 # This small two-lane simulation has no Vivado synthesis/place/route process.
 # Its gate is lower than the separate >2.3 GiB routed-build gate.
 print('Free GiB',round(free(),2),flush=True);assert free()>1.0,'Insufficient RAM for small RTL simulation'
 samples=[]
 if bits==8 and bc>=0:
  samples=[(1,231,[a,b])for a in range(-128,128)for b in range(-128,128)]
 elif bits==8:
  samples=[(1,beta,[u,((u+128)*73%256)-128])for beta in range(257)for u in range(-128,128)]
 for _ in range(6000):
  beta=rng.randrange(257);lo=-(1<<(bits-1));hi=1<<(bits-1)
  samples.append((int(rng.random()>.13),beta,[rng.randrange(lo,hi),rng.randrange(lo,hi)]))
 samples += [(1,beta,[u0,u1])for beta in [0,1,128,224,231,255,256]for u0 in [-(1<<(bits-1)),-1,0,(1<<(bits-1))-1]for u1 in [-(1<<(bits-1)),-1,0,(1<<(bits-1))-1]]
 expected=[pack([leak(x,bc if bc>=0 else beta)for x in u],bits)for valid,beta,u in samples if valid]
 wd=R/f'packed_leak_{bits}_{bc}';wd.mkdir(exist_ok=True)
 (wd/'stim.txt').write_text(str(len(samples))+'\n'+'\n'.join(f'{valid} {beta} {pack(u,bits):x}'for valid,beta,u in samples)+'\n')
 cmds=[f'"{V}/bin/xvlog.bat" -sv -d "BITS={bits}" -d "BC={bc}" "{P}/packed_leak.sv" "{P}/tb_packed_leak.sv"',
  f'"{V}/bin/xvlog.bat" "{V}/data/verilog/src/glbl.v"',f'"{V}/bin/xelab.bat" -mt off -L unisims_ver tb_packed_leak glbl -s sim',f'"{V}/bin/xsim.bat" sim -R']
 temp=wd/'tmp';temp.mkdir(exist_ok=True);env=os.environ.copy();env['TEMP']=str(temp);env['TMP']=str(temp)
 for i,cmd in enumerate(cmds):
  result=subprocess.run(cmd,shell=True,cwd=wd,env=env,capture_output=True,text=True)
  (wd/f'tool_{i}.log').write_text(result.stdout+result.stderr)
  assert result.returncode==0,result.stdout[-4000:]+result.stderr[-1000:]
 cycles=re.search(r'LEAK CYCLES (\d+) ACCEPTED (\d+) OUTPUTS (\d+)',result.stdout);assert cycles,result.stdout[-4000:]
 for engine in [0,1,2]:
  got=[int(s,16)for s in (wd/f'out{engine}.txt').read_text().splitlines()]
  mismatch=sum(a!=b for a,b in zip(got,expected))+abs(len(got)-len(expected))
  assert mismatch==0,(bits,bc,engine,mismatch,[(i,a,b)for i,(a,b)in enumerate(zip(got,expected))if a!=b][:5])
  row=dict(bits=bits,constant_beta=bc,engine=engine,requests=len(expected),mismatches=mismatch,driver_cycles=int(cycles[1]),accepted=int(cycles[2]),outputs=int(cycles[3]));rows.append(row);print(row,flush=True)
 (R/'packed_leak_checks.json').write_text(json.dumps(dict(rtl_sha256=source_hash,rows=rows),indent=2))
print('PACKED LEAK CHECKS PASS',flush=True)
