"""Replay one six-neuron block from the existing seed0 model; no new data/training.
This is an RTL trace check, not a whole-network inference hardware benchmark.
"""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
from pathlib import Path
import json,subprocess,re,ctypes,hashlib
import numpy as np
P=Path(__file__).resolve().parent;R=P/'results'
V=Path('C:/AMDDesignTools/2025.2/Vivado')
class Mem(ctypes.Structure):
 _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong),('total',ctypes.c_ulonglong),('free',ctypes.c_ulonglong),('rest',ctypes.c_ulonglong*5)]
m=Mem();m.length=ctypes.sizeof(m);ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
print('Free GiB',m.free/2**30,flush=True);assert m.free>1.5*2**30
d=np.load(R/'model_seed0.npz');w=d['w0'][:,:6].astype(np.int64);x=d['test_x']
lo=int(np.minimum(w,0).sum(0).min());hi=int(np.maximum(w,0).sum(0).max())
assert lo>=-64 and hi<=56 and w.min()>=-8 and w.max()<=7
rng=np.random.default_rng(123);events=np.stack([rng.random(x.shape)<x for t in range(32)])
def pack(v,b):return sum((int(a)&((1<<b)-1))<<(i*b)for i,a in enumerate(v))
lines=[str(48*32)];expected=[];prefixlo=0;prefixhi=0
for image in range(48):
 u=np.zeros(6,dtype=np.int64)
 for t in range(32):
  u-=u>>3;active=np.flatnonzero(events[t,image]);lines.append(str((len(active)+1)//2));cur=np.zeros(6,dtype=np.int64)
  for j in range(0,len(active),2):
   a=w[active[j]];b=w[active[j+1]] if j+1<len(active)else np.zeros(6,dtype=np.int64)
   lines.append(f'{pack(a,4):x} {pack(b,4):x}');cur+=a+b;u+=a+b
   prefixlo=min(prefixlo,int(cur.min()));prefixhi=max(prefixhi,int(cur.max()))
   assert np.all(u>=-512)and np.all(u<=511)
  fire=u>=17;u-=fire*17;expected.append((pack(u,16),pack(fire,1)))
wd=R/'persistent_model_trace';wd.mkdir(exist_ok=True);(wd/'stim.txt').write_text('\n'.join(lines)+'\n')
tb=(P/'tb_persistent_unit.sv').read_text().replace('.HARD(`HARD),',f'.HARD(`HARD),.TH(17),.LOW({lo}),.HIGH({hi}),')
tb=tb.replace('rawa[0:3],rawb[0:3]','rawa[0:63],rawb[0:63]')
tb=tb.replace('i=$fscanf(rc,"%d",n);', 'if(k>0&&k%32==0)begin @(negedge clk);rst=1;valid=0;repeat(2)@(negedge clk);rst=0;repeat(2)@(negedge clk);end\n    i=$fscanf(rc,"%d",n);')
tb=tb.replace('#2000000;','#10000000;');(wd/'tb_model.sv').write_text(tb)
cmds=[f'"{V}/bin/xvlog.bat" -sv -d "SH=3" -d "LEAK=1" -d "HARD=0" "{P}/persistent_unit.sv" tb_model.sv',
 f'"{V}/bin/xvlog.bat" "{V}/data/verilog/src/glbl.v"',f'"{V}/bin/xelab.bat" -L unisims_ver tb_persistent_unit glbl -s sim',f'"{V}/bin/xsim.bat" sim -R']
for cmd in cmds:
 p=subprocess.run(cmd,shell=True,cwd=wd,capture_output=True,text=True);(wd/'last_tool_output.txt').write_text(p.stdout+p.stderr)
 assert p.returncode==0,p.stdout[-4000:]+p.stderr[-1000:]
rows=[]
for e,b in [(e,16)for e in range(4)]+[(0,12),(1,12)]+[(e,10)for e in range(4)]:
 got=[tuple(int(x,16)for x in s.split())for s in (wd/f'out{e}_{b}.txt').read_text().splitlines()]
 bad=sum(a!=b for a,b in zip(got,expected))+abs(len(got)-len(expected));assert not bad,(e,b,bad)
 count=re.search(rf'ENGINE {e} WIDTH {b} CYCLES (\d+) NARROW (\d+) WIDE (\d+) CHANGES (\d+)',p.stdout);assert count
 row=dict(engine=e,wide_bits=b,mismatches=bad,cycles=int(count[1]),narrow_steps=int(count[2]),wide_steps=int(count[3]),changes=int(count[4]));rows.append(row);print(row,flush=True)
result=dict(seed=0,layer=0,neuron_indices=list(range(6)),images=48,steps_per_image=32,threshold=17,shift=3,hard_reset=False,
 certificate_low=lo,certificate_high=hi,current_prefix_min=prefixlo,current_prefix_max=prefixhi,
 rtl_sha256=hashlib.sha256((P/'persistent_unit.sv').read_bytes()).hexdigest(),rows=rows)
(R/'persistent_model_trace.json').write_text(json.dumps(result,indent=2));print('MODEL TRACE PASS',flush=True)
