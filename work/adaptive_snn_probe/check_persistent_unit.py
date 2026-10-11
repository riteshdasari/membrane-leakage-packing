from pathlib import Path
import json,subprocess,random,ctypes,re
P=Path(__file__).resolve().parent;R=P/'results';V=Path('C:/AMDDesignTools/2025.2/Vivado')
class Mem(ctypes.Structure):
 _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong),('total',ctypes.c_ulonglong),('free',ctypes.c_ulonglong),('rest',ctypes.c_ulonglong*5)]
m=Mem();m.length=ctypes.sizeof(m);ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
print('Free GiB',m.free/2**30,flush=True);assert m.free>1.5*2**30
def pack(v,b):return sum((x&((1<<b)-1))<<(b*i)for i,x in enumerate(v))
rows=[]
for sh,leak,hard in [(1,1,0),(3,1,0),(1,0,0),(1,1,1),(3,1,1),(1,0,1)]:
 rng=random.Random(8912);state=[0]*6;expected=[];lines=['320'];maxprefix=0
 for t in range(320):
  if leak:state=[x-(x>>sh)for x in state]
  n=[0,1,2,4][t%4];lines.append(str(n));current=[0]*6
  for j in range(n):
   phase=t//40%4
   a=[-8 if phase==0 else 7 if phase==1 else rng.randrange(-8,8)for _ in range(6)]
   b=[-8 if phase==0 else 7 if phase==1 else rng.randrange(-8,8)for _ in range(6)]
   lines.append(f'{pack(a,4):x} {pack(b,4):x}');current=[u+x+y for u,x,y in zip(current,a,b)]
   assert all(-64<=x<=56 for x in current)
   maxprefix=max(maxprefix,max(abs(x)for x in current));state=[u+x+y for u,x,y in zip(state,a,b)]
  fire=[int(x>=35)for x in state];state=[(0 if hard else x-35)if f else x for x,f in zip(state,fire)]
  assert all(-32768<=x<=32767 for x in state)
  expected.append((pack(state,16),pack(fire,1)))
 wd=R/f'persist_unit_{sh}_{leak}_{hard}';wd.mkdir(exist_ok=True)
 (wd/'stim.txt').write_text('\n'.join(lines)+'\n')
 cmds=[f'"{V}/bin/xvlog.bat" -sv -d "SH={sh}" -d "LEAK={leak}" -d "HARD={hard}" "{P}/persistent_unit.sv" "{P}/tb_persistent_unit.sv"',
 f'"{V}/bin/xvlog.bat" "{V}/data/verilog/src/glbl.v"',f'"{V}/bin/xelab.bat" -L unisims_ver tb_persistent_unit glbl -s sim',f'"{V}/bin/xsim.bat" sim -R']
 for cmd in cmds:
  p=subprocess.run(cmd,shell=True,cwd=wd,capture_output=True,text=True);(wd/'last_tool_output.txt').write_text(p.stdout+p.stderr)
  assert p.returncode==0,p.stdout[-4000:]+p.stderr[-1000:]
 for e,w in [(e,16)for e in range(5)]+[(0,12),(1,12)]+[(e,10)for e in range(4)]:
  if e==4 and(not leak or sh!=1):continue
  if w<16 and not leak:continue
  if w<16:assert all(-(1<<(w-1))<=((x>>(16*i))&65535)-(65536 if ((x>>(16*i))&32768)else 0)<(1<<(w-1)) for x,_ in expected for i in range(6))
  got=[tuple(int(x,16)for x in s.split())for s in (wd/f'out{e}_{w}.txt').read_text().splitlines()]
  bad=sum(a!=b for a,b in zip(got,expected))+abs(len(got)-len(expected))
  if bad:raise AssertionError((e,sh,leak,hard,[(i,a,b)for i,(a,b)in enumerate(zip(got,expected))if a!=b][:2],len(got)))
  count=re.search(rf'ENGINE {e} WIDTH {w} CYCLES (\d+) NARROW (\d+) WIDE (\d+) CHANGES (\d+)',p.stdout);assert count
  row=dict(engine=e,wide_bits=w,shift=sh,leak=leak,hard_reset=hard,steps=320,mismatches=bad,cycles=int(count[1]),narrow_steps=int(count[2]),wide_steps=int(count[3]),changes=int(count[4]),max_abs_current_prefix=maxprefix)
  rows.append(row);print(row,flush=True)
  (R/'persistent_unit_checks.json').write_text(json.dumps(rows,indent=2))
print('ALL PERSISTENT UNIT CHECKS PASS',flush=True)
