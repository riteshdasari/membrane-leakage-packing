"""Matched 24-neuron UNISIM tests, independent ready/valid streams per engine."""
import sys,subprocess,json,random,os,ctypes
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;VIV=Path('C:/AMDDesignTools/2025.2/Vivado')
class Mem(ctypes.Structure):
 _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong),('total',ctypes.c_ulonglong),('free',ctypes.c_ulonglong),('rest',ctypes.c_ulonglong*5)]
m=Mem();m.length=ctypes.sizeof(m);ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
print('Free RAM GB',round(m.free/2**30,2),flush=True)
assert m.free>2*2**30,'Need at least 2 GB free RAM for Vivado simulation'
results=[]
configs=[(1,1,0),(3,1,0),(1,0,0),(1,1,1),(3,1,1),(1,0,1)]
if os.environ.get('QUICK'):configs=configs[:1]
for sh,leak,hard in configs:
 for bounded in (False,True):
  wd=HERE/'results'/f'exact_tile_sh{sh}_l{leak}_h{hard}_b{int(bounded)}';wd.mkdir(exist_ok=True)
  rng=random.Random(20261008);S=[0]*24;stim=['120'];expect=[];prefixmax=0
  for t in range(120):
   if leak:S=[s-(s>>sh) for s in S]
   e=0 if t%12==0 else rng.randint(3,12) if bounded else rng.randint(10,100)
   stim.append(str(e));cur=[0]*24
   for j in range(e):
    W=[7 if t%6==0 else -8 if t%6==1 else (7 if j<e//2 else -8) if t%6==2 else rng.randint(-8,7) for _ in range(24)]
    stim.append(' '.join(map(str,W)));cur=[a+b for a,b in zip(cur,W)]
    prefixmax=max(prefixmax,max(abs(a) for a in cur));S=[a+b for a,b in zip(S,W)]
    assert max(abs(a) for a in S)<32768
   assert min(cur)>=-2048 and max(cur)<2048
   spike=[int(s>=35) for s in S];S=[(0 if hard else s-35) if f else s for s,f in zip(S,spike)]
   expect.append(S+spike)
  (wd/'stim.txt').write_text('\n'.join(stim)+'\n')
  defs=f'-d "SH={sh}" -d "LEAK={leak}" -d "HARD={hard}"'
  if os.environ.get('TRACE'):defs+=' -d "TRACE"'
  sources=['packed_exact_acc.sv','old_acc_engines.sv','exact_checkpoint.sv','exact_promote.sv','exact_tile.sv','tb_exact_tile.sv']
  commands=[f'"{VIV}/bin/xvlog.bat" -sv {defs} '+' '.join(f'"{HERE/s}"' for s in sources),
   f'"{VIV}/bin/xvlog.bat" "{VIV}/data/verilog/src/glbl.v"',
   f'"{VIV}/bin/xelab.bat" -L unisims_ver tb_exact_tile glbl -s sim',f'"{VIV}/bin/xsim.bat" sim -R']
  for cmd in commands:
   r=subprocess.run(cmd,shell=True,cwd=wd,capture_output=True,text=True)
   if os.environ.get('TRACE') and 'xsim.bat' in cmd:(wd/'trace.txt').write_text(r.stdout)
   if r.returncode:print(r.stdout[-3500:],r.stderr[-1000:]);sys.exit(1)
  for mode in (0,1,2,3,4) if bounded else (0,1,2,4):
   got=[[int(x) for x in l.split()[1:]]for l in (wd/f'out{mode}.txt').read_text().splitlines()]
   bad=sum(a!=b for a,b in zip(expect,got))+abs(len(expect)-len(got))
   row={'mode':mode,'shift':sh,'leak':leak,'hard_reset':hard,'bounded_current':bounded,'timesteps':len(got),
        'mismatch_rows':bad,'max_abs_current_prefix':prefixmax,
        'cycles':[int(x) for x in (wd/f'cycles{mode}.txt').read_text().split()]}
   results.append(row);print(row,flush=True)
   (HERE/'results'/'exact_tile_checks.json').write_text(json.dumps(results,indent=2))
   if bad:
    print('First failures',[(i,a[:24],b[:24])for i,(a,b)in enumerate(zip(expect,got))if a!=b][:2]);sys.exit(1)
print('ALL MATCHED TILE CHECKS PASS',flush=True)
