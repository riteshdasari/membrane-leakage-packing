"""Independent scalar oracle, packing audit and ready/valid group RTL trial."""
from pathlib import Path
import ctypes,hashlib,json,random,re,subprocess,os,sys
P=Path(__file__).resolve().parent;R=P/'results';V=Path('C:/AMDDesignTools/2025.2/Vivado')
def free():
 class Mem(ctypes.Structure):
  _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong),('total',ctypes.c_ulonglong),('free',ctypes.c_ulonglong),('rest',ctypes.c_ulonglong*5)]
 m=Mem();m.length=ctypes.sizeof(m);ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m));return m.free/2**30
def pack(u):return sum((int(x)&2047)<<(11*i)for i,x in enumerate(u))
def leak(u,d):return -((-int(u)*(256-d))//256)
def wide_pair(u,d):
 r=[(x+128)%256-128 for x in u];h=[(x-y)//256 for x,y in zip(u,r)]
 k=32768-128*d;a=(r[0]+128)+((r[1]+128)<<16);p=a*d+k+(k<<16)
 floor=[((p>>(8+16*i))&255)-128 for i in range(2)]
 return [x-d*y-z for x,y,z in zip(u,h,floor)]
def narrow_triple(u,d):
 a=(u[0]+16)+((u[1]+16)<<10)+(u[2]<<20);k=512-16*d
 p=(a*d+k+(k<<10))&((1<<48)-1)
 f=[((p>>8)&3)-2,((p>>18)&3)-2,((p>>28)&3)]
 if f[2]>=2:f[2]-=4
 return [x-y for x,y in zip(u,f)]
if '--audit' in sys.argv:
 n=0
 for d in range(32):
  for x in range(-1024,1024):
   u=[x,((x+1024)*971%2048)-1024]
   assert wide_pair(u,d)==[leak(x,d)for x in u];n+=1
 (R/'adaptive_delta_compact_algebra.json').write_text(json.dumps(dict(wide_cases=n,wide_bits=11,failures=0),indent=2))
 print('WIDE DELTA AUDIT PASS',n,flush=True)
if '--sim' not in sys.argv:sys.exit(0)
small='--small'in sys.argv;dataset='smoke'if small else'main'
source_hashes={n:hashlib.sha256((P/n).read_bytes()).hexdigest()for n in ['adaptive_delta_compact.sv','tb_adaptive_delta_compact.sv']}
rows=[];rng=random.Random(791209)
for dc,mp in [(25,1),(-1,1),(25,0),(-1,0)]:
 print('Free GiB',round(free(),2),flush=True);assert free()>1.0,'Insufficient RAM for simulation'
 samples=[]
 # Every value/coefficient on the wider path; companion lanes vary deterministically.
 for d in (range(32)if dc<0 and not small else [25]):
  for x in (range(-1024,1024)if not small else [-1024,-513,-512,-129,-128,-17,-16,-1,0,1,15,16,127,128,511,512,1023]):
   u=[x,((x+1024)*73%2048)-1024,17,-17,1023,-1024]
   samples.append((0,d,u))
 # Exercise every narrow triple for delta25; every narrow value for all coefficients.
 if not small:
  for a in range(-16,16):
   for b in range(-16,16):
    for c in range(-16,16):samples.append((0,25,[a,b,c,c,a,b]))
  for d in range(32):
   for x in range(-16,16):samples.append((0,d,[x,15,-16,-1,0,1]))
 # Boundaries, all-zero, delta0 identity and back-to-back mode/coefficient changes.
 for j in range(80 if small else 5000):
  d=rng.randrange(32)
  if j%11==0:u=[0]*6
  elif j%3==0:u=[rng.randrange(-16,16)for _ in range(6)]
  else:u=[rng.randrange(-1024,1024)for _ in range(6)]
  samples.append((rng.randrange(4)if j%7==0 else 0,d,u))
 wd=R/f'adaptive_delta_compact_{dataset}_{dc}_{mp}';wd.mkdir(exist_ok=True)
 (wd/'stim.txt').write_text(str(len(samples))+'\n'+'\n'.join(f'{g} {d} {pack(u):x}'for g,d,u in samples)+'\n')
 exp=[pack([leak(x,dc if dc>=0 else d)for x in u])for _,d,u in samples]
 cmd=[f'"{V}/bin/xvlog.bat" -sv -d "DC={dc}" -d "MP={mp}" "{P}/adaptive_delta_compact.sv" "{P}/tb_adaptive_delta_compact.sv"',
  f'"{V}/bin/xvlog.bat" "{V}/data/verilog/src/glbl.v"',
  f'"{V}/bin/xelab.bat" -mt off -L unisims_ver tb_adaptive_delta_compact glbl -s sim',f'"{V}/bin/xsim.bat" sim -R']
 temp=wd/'tmp';temp.mkdir(exist_ok=True);env=os.environ.copy();env['TEMP']=str(temp);env['TMP']=str(temp)
 for i,c in enumerate(cmd):
  z=subprocess.run(c,shell=True,cwd=wd,env=env,capture_output=True,text=True);(wd/f'tool_{i}.log').write_text(z.stdout+z.stderr)
  assert z.returncode==0,z.stdout[-4000:]+z.stderr[-1000:]
 assert 'ADAPTIVE DELTA PASS'in z.stdout,z.stdout[-4000:]
 for e in [0,1,2,3]+([5]if dc>=0 else[]):
  outputs=[s.split()for s in (wd/f'out{e}.txt').read_text().splitlines()];got=[int(s[0],16)for s in outputs]
  assert len(got)==len(exp),(dc,mp,e,len(got),len(exp))
  bad=sum(a!=b for a,b in zip(got,exp));assert not bad,(dc,mp,e,bad,[(i,a,b,samples[i])for i,(a,b)in enumerate(zip(got,exp))if a!=b][:5])
  cycles=re.search(rf'DELTA E {e} CYCLES (\d+) ACCEPTED (\d+) OUTPUTS (\d+) ISSUES (\d+) NARROW (\d+) BYPASS (\d+)',z.stdout);assert cycles
  hist={}
  for s in outputs:
   latency=int(s[2])-int(s[1]);hist[latency]=hist.get(latency,0)+1
  row=dict(constant_delta=dc,multiplier_pipeline=mp,engine=e,groups=len(got),neuron_operations=6*len(got),mismatches=bad,
   driver_cycles=int(cycles[1]),issue_slots=int(cycles[4]),narrow_groups=int(cycles[5]),bypass_groups=int(cycles[6]),accept_to_output_cycles=hist)
  rows.append(row);print(row,flush=True)
  # Validate issue counts with a separately written schedule expression.
  nissues=0
  for _,d,u in samples:
   if (dc if dc>=0 else d)==0 or all(x==0 for x in u):continue
   nissues+=1 if e==3 else (2 if e==0 and min(u)>=-16 and max(u)<=15 else 3)
  assert nissues==row['issue_slots']
  for i,s in enumerate(outputs):
   _,d,u=samples[i];bypass=(dc if dc>=0 else d)==0 or all(x==0 for x in u)
   slots=1 if e==3 else (2 if e==0 and min(u)>=-16 and max(u)<=15 else 3)
   assert int(s[2])-int(s[1])==(0 if bypass else slots+mp+1)
 (R/f'adaptive_delta_compact_{dataset}_checks.json').write_text(json.dumps(dict(source_hashes=source_hashes,rows=rows),indent=2))
print('ADAPTIVE DELTA ORACLE PASS',flush=True)
