"""Feasibility tests for moving leak/reset into packed DSP arithmetic."""
from pathlib import Path
import ctypes,subprocess,json,re,random,hashlib
P=Path(__file__).resolve().parent;R=P/'results';V=Path('C:/AMDDesignTools/2025.2/Vivado')
class Mem(ctypes.Structure):
 _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong),('total',ctypes.c_ulonglong),('free',ctypes.c_ulonglong),('rest',ctypes.c_ulonglong*5)]
m=Mem();m.length=ctypes.sizeof(m);ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
print('Free GiB',m.free/2**30,flush=True);assert m.free>1.5*2**30
def pack(v,b):return sum((x&((1<<b)-1))<<(i*b)for i,x in enumerate(v))
audit=0;rng=random.Random(2201)
for bits,n,shift in [(8,6,1),(8,6,3),(10,4,3),(12,4,3),(16,3,1),(16,3,3)]:
 mask=(1<<bits)-1;bias=1<<(bits-1);kw=pack([bias>>shift]*n,bits)
 for _ in range(10000):
  q=[rng.randrange(mask+1)for i in range(n)];u=[x-bias for x in q]
  v=(pack(q,bits)-pack([x>>shift for x in q],bits)+kw)&((1<<48)-1)
  expected=[x-(x>>shift)+bias for x in u]
  assert v==pack(expected,bits),(bits,q,v,expected);audit+=1
  for hard in [0,1]:
   delta=[(x if hard else 35)if x>=35 else 0 for x in u]
   v=(pack(q,bits)-pack(delta,bits))&((1<<48)-1)
   expect=[(0 if hard else x-35)if x>=35 else x for x in u]
   assert v==pack([x+bias for x in expect],bits);audit+=1
(R/'neuron_alu_algebra.json').write_text(json.dumps(dict(cases=audit,failures=0),indent=2))
rows=[]
for bits,n,shift,leak in [(8,6,1,1),(10,4,3,1),(12,4,3,1),(16,3,1,0)]:
 for hard in [0,1]:
  rng=random.Random(8912);state=[0]*n;lines=['320'];expected=[]
  for t in range(320):
   if leak:state=[x-(x>>shift)for x in state]
   pairs=[0,1,2,4][t%4];lines.append(str(pairs))
   for j in range(pairs):
    phase=t//40%4
    a=[-8 if phase==0 else 7 if phase==1 else rng.randrange(-8,8)for i in range(n)]
    b=[-8 if phase==0 else 7 if phase==1 else rng.randrange(-8,8)for i in range(n)]
    lines.append(f'{pack(a,4):x} {pack(b,4):x}')
    state=[s+x+y for s,x,y in zip(state,a,b)]
    assert all(-(1<<(bits-1))<=x<(1<<(bits-1))for x in state)
   fire=[int(x>=35)for x in state];state=[(0 if hard else x-35)if f else x for x,f in zip(state,fire)]
   expected.append((pack(state,16),pack(fire,1)))
  wd=R/f'neuron_alu_{bits}_{shift}_{leak}_{hard}';wd.mkdir(exist_ok=True);(wd/'stim.txt').write_text('\n'.join(lines)+'\n')
  cmds=[f'"{V}/bin/xvlog.bat" -sv -d "SH={shift}" -d "LEAK={leak}" -d "HARD={hard}" -d "BITS={bits}" -d "LANES={n}" "{P}/persistent_unit.sv" "{P}/packed_neuron_alu.sv" "{P}/tb_packed_neuron_alu.sv"',
   f'"{V}/bin/xvlog.bat" "{V}/data/verilog/src/glbl.v"',f'"{V}/bin/xelab.bat" -L unisims_ver tb_packed_neuron_alu glbl -s sim',f'"{V}/bin/xsim.bat" sim -R']
  for cmd in cmds:
   result=subprocess.run(cmd,shell=True,cwd=wd,capture_output=True,text=True);(wd/'last_tool_output.txt').write_text(result.stdout+result.stderr)
   assert result.returncode==0,result.stdout[-4000:]+result.stderr[-1000:]
  for engine in [0,1,2]:
   got=[tuple(int(x,16)for x in s.split())for s in (wd/f'out{engine}.txt').read_text().splitlines()]
   bad=sum(a!=b for a,b in zip(got,expected))+abs(len(got)-len(expected));assert not bad,(engine,bits,shift,leak,hard,[(i,a,b)for i,(a,b)in enumerate(zip(got,expected))if a!=b][:2])
   count=re.search(rf'ENGINE {engine} CYCLES (\d+)',result.stdout);assert count
   row=dict(engine=engine,bits=bits,neurons=n,shift=shift,leak=leak,hard_reset=hard,steps=320,mismatches=bad,cycles=int(count[1]))
   rows.append(row);print(row,flush=True)
   (R/'neuron_alu_checks.json').write_text(json.dumps(dict(rtl_sha256=hashlib.sha256((P/'packed_neuron_alu.sv').read_bytes()).hexdigest(),algebra_cases=audit,rows=rows),indent=2))
print('NEURON ALU CHECKS PASS',flush=True)
