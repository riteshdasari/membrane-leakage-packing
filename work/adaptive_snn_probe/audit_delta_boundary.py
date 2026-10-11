"""Re-time routed cores with a declared interface budget; no board claim."""
from pathlib import Path
import subprocess,json,os,ctypes
P=Path(__file__).resolve().parent;R=P/'results';V=Path('C:/AMDDesignTools/2025.2/Vivado/bin/vivado.bat')
class Mem(ctypes.Structure):
 _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong),('total',ctypes.c_ulonglong),('free',ctypes.c_ulonglong),('rest',ctypes.c_ulonglong*5)]
m=Mem();m.length=ctypes.sizeof(m);ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m));print('Free GiB',m.free/2**30,flush=True);assert m.free>2.3*2**30
hardware=[]
for n in ['adaptive_delta_hardware.json','adaptive_delta_compact_hardware.json']:
 if (R/n).exists():hardware.extend(json.loads((R/n).read_text()))
tops=[h['top']for h in hardware];assert tops
temp=R/'delta_boundary_tmp';temp.mkdir(exist_ok=True);env=os.environ.copy();env['TEMP']=str(temp);env['TMP']=str(temp)
cmd=f'"{V}" -mode batch -log results/delta_boundary_vivado.log -journal results/delta_boundary_vivado.jou -source audit_delta_boundary.tcl -tclargs '+ ' '.join(tops)
with (R/'delta_boundary_build.log').open('w')as f:z=subprocess.run(cmd,shell=True,cwd=P,env=env,stdout=f,stderr=subprocess.STDOUT)
assert z.returncode==0,(R/'delta_boundary_build.log').read_text()[-4000:]
rows=[]
for top in tops:
 a=[float(s)for s in (R/f'{top}_route/boundary_slack.txt').read_text().splitlines()]
 assert len(a)==2
 rows.append(dict(top=top,WNS_ns=a[0],WHS_ns=a[1],input_max_delay_ns=1.0,output_max_delay_ns=1.0,
  input_min_delay_ns=.1,output_min_delay_ns=.1,period_estimate_with_boundary_budget_ns=4-a[0]))
(R/'adaptive_delta_boundary.json').write_text(json.dumps(dict(rows=rows,note='Same routed netlists with an assumed 1ns external input/output max delay, 0.1ns min. Includes input membrane range monitor timing. No board measurement or reroute.'),indent=2))
print(json.dumps(rows,indent=2),flush=True)
