"""Check stronger constant-LUT references using the existing independent oracle."""
from pathlib import Path
import ctypes,hashlib,json,subprocess,os,re
P=Path(__file__).resolve().parent;R=P/'results';V=Path('C:/AMDDesignTools/2025.2/Vivado')
class Mem(ctypes.Structure):
 _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong),('total',ctypes.c_ulonglong),('free',ctypes.c_ulonglong),('rest',ctypes.c_ulonglong*5)]
m=Mem();m.length=ctypes.sizeof(m);ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m));print('Free GiB',m.free/2**30,flush=True);assert m.free>1.0*2**30
wd=R/'distributed_leak';wd.mkdir(exist_ok=True)
(wd/'stim.txt').write_bytes((R/'packed_leak_8_231'/'stim.txt').read_bytes())
tb=(P/'tb_packed_leak.sv').read_text().replace('tb_packed_leak','tb_distributed_leak').replace('[0:2]','[0:1]').replace('[2:0]ov','[1:0]ov').replace('e<3','e<2').replace('j<3','j<2').replace('i<3','i<2').replace('{3{ov[0]}}','{2{ov[0]}}')
tb=tb.replace('packed_leak #(.E(e),.B(`BITS),.BC(`BC))','distributed_leak #(.E(e))')
(wd/'tb_fixed_lut.sv').write_text(tb)
cmds=[f'"{V}/bin/xvlog.bat" -sv -d "BITS=8" "{P}/distributed_leak.sv" "{wd}/tb_fixed_lut.sv"',f'"{V}/bin/xvlog.bat" "{V}/data/verilog/src/glbl.v"',f'"{V}/bin/xelab.bat" -mt off tb_distributed_leak glbl -s sim',f'"{V}/bin/xsim.bat" sim -R']
temp=wd/'tmp';temp.mkdir(exist_ok=True);env=os.environ.copy();env['TEMP']=str(temp);env['TMP']=str(temp)
for i,cmd in enumerate(cmds):
 result=subprocess.run(cmd,shell=True,cwd=wd,env=env,capture_output=True,text=True);(wd/f'tool_{i}.log').write_text(result.stdout+result.stderr)
 assert result.returncode==0,result.stdout[-3000:]+result.stderr[-1000:]
expected=[]
for line in (wd/'stim.txt').read_text().splitlines()[1:]:
 valid,beta,word=line.split();word=int(word,16)
 if int(valid):
  u=[(word>>(8*i)&255)for i in range(2)];u=[x if x<128 else x-256 for x in u]
  expected.append(sum((-((-x*231)//256)&255)<<(8*i)for i,x in enumerate(u)))
rows=[]
for e in [0,1]:
 got=[int(s,16)for s in (wd/f'out{e}.txt').read_text().splitlines()]
 bad=sum(a!=b for a,b in zip(got,expected))+abs(len(got)-len(expected));assert not bad,(e,bad)
 rows.append(dict(engine=e,requests=len(expected),mismatches=bad))
(R/'distributed_leak_checks.json').write_text(json.dumps(dict(rtl_sha256=hashlib.sha256((P/'distributed_leak.sv').read_bytes()).hexdigest(),rows=rows),indent=2));print(rows,flush=True)
