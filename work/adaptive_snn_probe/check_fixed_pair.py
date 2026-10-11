"""Independent Python integer oracle versus four actual UNISIM RTL kernels."""
from pathlib import Path
import subprocess,random,json,ctypes,re
HERE=Path(__file__).resolve().parent
VIV=Path('C:/AMDDesignTools/2025.2/Vivado')
class Mem(ctypes.Structure):
 _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong),('total',ctypes.c_ulonglong),('free',ctypes.c_ulonglong),('rest',ctypes.c_ulonglong*5)]
m=Mem();m.length=ctypes.sizeof(m);ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
print('Free GiB',m.free/2**30,flush=True)
assert m.free>1.5*2**30
def fields(v,b):return sum((int(x)&((1<<b)-1))<<(b*i) for i,x in enumerate(v))
def encode(v,s,native=False):
 n=48//s
 return sum((sum(int(x)<<(s*i) for i,x in enumerate(v[g:g+n]))&((1<<48)-1))<<(48*(g//n)) for g in range(0,24,n)) if not native else fields(v,s)
rows=[]
for sh,leak,hard in [(1,0,0),(1,1,0),(3,1,0),(1,0,1),(1,1,1),(3,1,1)]:
 rng=random.Random(88271);state=[0]*24;expected=[];lines=[];contributions=0;tiles=0
 def command(cmd,lo,aa=None,bb=None,first=0,last=0):
  aa=aa or [0]*24;bb=bb or [0]*24
  words=[]
  for mode,s in enumerate([6,8,12,8]):
   if mode in (2,3):words.extend([fields(aa,4),fields(bb,4),0])
   else:words.extend([encode(aa,s,mode==2),encode(bb,s,mode==2),fields([-x for x in lo],s)])
  # First half saturates the interface; second half adds source bubbles.
  gap=0 if len(expected)<250 else rng.randrange(3)
  lines.append(f'{gap} {cmd} {int(first)} {int(last)} {fields(lo,16):x} '+' '.join(f'{x:x}'for x in words))
 for step in range(240):
  nt=1+step%4
  for t in range(nt):
   k=[0,1,2,3,4,7][(step+t)%6]
   ws=[[(-8 if step%10==0 else 7 if step%10==1 else rng.randrange(-8,8))for _ in range(24)]for _ in range(k)]
   lo=[sum(min(w[i],0)for w in ws)for i in range(24)]
   hi=[sum(max(w[i],0)for w in ws)for i in range(24)]
   assert all(h-l<=63 for l,h in zip(lo,hi))
   command(1,lo)
   if t==0 and leak:state=[x-(x>>sh) for x in state]
   for j in range(0,k,2):
    active=[step%7!=0 and (step%3==0 or rng.random()<.3) for _ in range(2)]
    a=ws[j] if active[0] else [0]*24
    b=ws[j+1] if j+1<k and active[1] else [0]*24
    command(2,lo,a,b)
    state=[u+x+y for u,x,y in zip(state,a,b)];contributions+=48
   last=t==nt-1
   spike=[int(last and u>=35)for u in state]
   state=[(0 if hard else u-35)if f else u for u,f in zip(state,spike)]
   assert all(-32768<=u<=32767 for u in state)
   command(3,lo,first=t==0,last=last)
   expected.append((fields(state,16),fields(spike,1)));tiles+=1
 wd=HERE/'results'/f'fixed_pair_{sh}_{leak}_{hard}';wd.mkdir(exist_ok=True)
 (wd/'stim.txt').write_text(str(len(lines))+'\n'+'\n'.join(lines)+'\n')
 (wd/'expected.txt').write_text('\n'.join(f'{u:x} {s:x}'for u,s in expected)+'\n')
 commands=[f'"{VIV}/bin/xvlog.bat" -sv -d "SH={sh}" -d "LEAK={leak}" -d "HARD={hard}" "{HERE}/fixed_pair.sv" "{HERE}/tb_fixed_pair.sv"',
 f'"{VIV}/bin/xvlog.bat" "{VIV}/data/verilog/src/glbl.v"',
 f'"{VIV}/bin/xelab.bat" -L unisims_ver tb_fixed_pair glbl -s sim',f'"{VIV}/bin/xsim.bat" sim -R']
 for commandline in commands:
  p=subprocess.run(commandline,shell=True,cwd=wd,capture_output=True,text=True)
  (wd/'last_tool_output.txt').write_text(p.stdout+p.stderr)
  if p.returncode:raise RuntimeError(p.stdout[-5000:]+p.stderr[-1000:])
 counts=re.search(r'COUNTS (\d+) (\d+) (\d+)',p.stdout)
 assert counts,p.stdout[-3000:]
 for mode in range(4):
  got=[tuple(int(v,16)for v in l.split())for l in (wd/f'out{mode}.txt').read_text().splitlines()]
  bad=sum(a!=b for a,b in zip(got,expected))+abs(len(got)-len(expected))
  if bad:print('FAIL',mode,[(i,a,b)for i,(a,b)in enumerate(zip(got,expected))if a!=b][:2]);raise AssertionError(bad)
  row=dict(mode=mode,shift=sh,leak=leak,hard=hard,tiles=tiles,timesteps=240,mismatches=bad,cycles=int(counts[1]),accepted=int(counts[2]),stalls=int(counts[3]),contribution_slots=contributions)
  rows.append(row);print(row,flush=True)
 (HERE/'results'/'fixed_pair_checks.json').write_text(json.dumps(rows,indent=2))
print('ALL FOUR KERNELS PASS',flush=True)
