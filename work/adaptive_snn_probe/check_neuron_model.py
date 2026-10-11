"""Existing saved-model block replays for the packed neuron arithmetic hypothesis."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
from pathlib import Path
import numpy as np,json,subprocess,re,hashlib,ctypes
P=Path(__file__).resolve().parent;R=P/'results';V=Path('C:/AMDDesignTools/2025.2/Vivado')
class Mem(ctypes.Structure):
 _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong),('total',ctypes.c_ulonglong),('free',ctypes.c_ulonglong),('rest',ctypes.c_ulonglong*5)]
m=Mem();m.length=ctypes.sizeof(m);ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
print('Free GiB',m.free/2**30,flush=True);assert m.free>1.5*2**30
d=np.load(R/'model_seed0.npz');x=d['test_x'];rng=np.random.default_rng(123)
events=np.stack([rng.random(x.shape)<x for t in range(32)])
def pack(v,b):return sum((int(a)&((1<<b)-1))<<(i*b)for i,a in enumerate(v))
rows=[]
for bits,n,shift,threshold in [(8,6,1,9),(10,4,3,17)]:
 w=d['w0'][:,:n].astype(np.int64);expected=[];lines=[str(48*32)]
 assert np.minimum(w,0).sum(0).min()>=-128 and np.maximum(w,0).sum(0).max()<128
 for image in range(48):
  u=np.zeros(n,np.int64)
  for t in range(32):
   u-=u>>shift;active=np.flatnonzero(events[t,image]);lines.append(str((len(active)+1)//2))
   for j in range(0,len(active),2):
    a=w[active[j]];b=w[active[j+1]]if j+1<len(active)else np.zeros(n,np.int64)
    lines.append(f'{pack(a,4):x} {pack(b,4):x}');u+=a+b
    assert u.min()>=-(1<<(bits-1))and u.max()<(1<<(bits-1))
   fire=u>=threshold;u-=fire*threshold;expected.append((pack(u,16),pack(fire,1)))
 wd=R/f'neuron_model{bits}';wd.mkdir(exist_ok=True);(wd/'stim.txt').write_text('\n'.join(lines)+'\n')
 tb=(P/'tb_packed_neuron_alu.sv').read_text().replace('.HARD(`HARD)',f'.HARD(`HARD),.TH({threshold})')
 tb=tb.replace('a[0:3],b[0:3]','a[0:63],b[0:63]').replace('#2000000;','#10000000;')
 tb=tb.replace('i=$fscanf(rc,"%d",n);','if(k>0&&k%32==0)begin @(negedge clk);rst=1;valid=0;repeat(2)@(negedge clk);rst=0;repeat(2)@(negedge clk);end\n   i=$fscanf(rc,"%d",n);')
 (wd/'tb_model.sv').write_text(tb)
 cmds=[f'"{V}/bin/xvlog.bat" -sv -d "SH={shift}" -d "LEAK=1" -d "HARD=0" -d "BITS={bits}" -d "LANES={n}" "{P}/persistent_unit.sv" "{P}/packed_neuron_alu.sv" "{wd}/tb_model.sv"',
  f'"{V}/bin/xvlog.bat" "{V}/data/verilog/src/glbl.v"',f'"{V}/bin/xelab.bat" -L unisims_ver tb_packed_neuron_alu glbl -s sim',f'"{V}/bin/xsim.bat" sim -R']
 for cmd in cmds:
  result=subprocess.run(cmd,shell=True,cwd=wd,capture_output=True,text=True);(wd/'last_tool_output.txt').write_text(result.stdout+result.stderr)
  assert result.returncode==0,result.stdout[-4000:]+result.stderr[-1000:]
 for engine in [0,1,2]:
  got=[tuple(int(x,16)for x in s.split())for s in (wd/f'out{engine}.txt').read_text().splitlines()]
  bad=sum(a!=b for a,b in zip(got,expected))+abs(len(got)-len(expected));assert not bad,(bits,engine,bad)
  c=re.search(rf'ENGINE {engine} CYCLES (\d+)',result.stdout);assert c
  row=dict(seed=0,bits=bits,neurons=n,shift=shift,threshold=threshold,engine=engine,images=48,steps_per_image=32,mismatches=bad,cycles=int(c[1]));rows.append(row);print(row,flush=True)
(R/'neuron_alu_model.json').write_text(json.dumps(dict(rtl_sha256=hashlib.sha256((P/'packed_neuron_alu.sv').read_bytes()).hexdigest(),rows=rows),indent=2));print('NEURON MODEL TRACE PASS',flush=True)
