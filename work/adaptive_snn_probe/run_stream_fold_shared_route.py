"""Serial RAM-gated routing of the functional-checked streaming variants."""
from pathlib import Path
import ctypes,subprocess,json,re,time,os,sys,hashlib
P=Path(__file__).resolve().parent;R=P/'results';V=Path('C:/AMDDesignTools/2025.2/Vivado/bin/vivado.bat')
class Mem(ctypes.Structure):
 _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong),('total',ctypes.c_ulonglong),('free',ctypes.c_ulonglong),('rest',ctypes.c_ulonglong*5)]
source=P/'stream_fold_shared_leak.sv';stamp=hashlib.sha256(source.read_bytes()).hexdigest()
assert json.loads((R/'stream_fold_shared_main_25_0_checks.json').read_text())['source_hashes'][source.name]==stamp
summary=R/'stream_fold_shared_hardware.json';rows=json.loads(summary.read_text())if summary.exists()else[]
for top in sys.argv[1:]:
 m=Mem();m.length=ctypes.sizeof(m);ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
 print(top,'free GiB',round(m.free/2**30,2),flush=True);assert m.free>2.3*2**30
 assert hashlib.sha256(source.read_bytes()).hexdigest()==stamp,'Source changed during build queue'
 if any(r['top']==top and r['rtl_sha256']==stamp for r in rows):print('Already complete',top,flush=True);continue
 tmp=R/'stream_offset_tmp';tmp.mkdir(exist_ok=True);env=os.environ.copy();env['TEMP']=str(tmp);env['TMP']=str(tmp)
 start=time.time();retried=False
 for attempt in range(2):
  suffix='_resume'if attempt else'';log=R/f'{top}{suffix}_build.log'
  cmd=f'"{V}" -mode batch -log results/{top}{suffix}_vivado.log -journal results/{top}{suffix}_vivado.jou -source route_stream_fold_shared.tcl -tclargs {top}'+(' resume'if attempt else'')
  with log.open('w')as f:z=subprocess.run(cmd,shell=True,cwd=P,env=env,stdout=f,stderr=subprocess.STDOUT)
  if z.returncode==0:break
  failure=log.read_text()
  if attempt==0 and 'ERROR: [Synth 20-411]'in failure and (R/f'{top}_synth/design.dcp').exists():retried=True;continue
  raise RuntimeError(failure[-4000:])
 dest=R/f'{top}_route';util=(dest/'util.rpt').read_text()
 def get(label):
  a=re.search(r'\|\s*'+re.escape(label)+r'\s*\|\s*([\d.]+)',util);assert a,label;return int(float(a[1]))
 internal=list(map(float,(dest/'slack.txt').read_text().splitlines()));boundary=list(map(float,(dest/'boundary_slack.txt').read_text().splitlines()))
 row=dict(top=top,LUT=get('Slice LUTs'),FF=get('Slice Registers'),DSP=get('DSPs'),RAMB18=get('RAMB18'),RAMB36=get('RAMB36/FIFO*'),
  WNS_ns=internal[0],WHS_ns=internal[1],internal_period_estimate_ns=4-internal[0],
  boundary_WNS_ns=boundary[0],boundary_WHS_ns=boundary[1],boundary_period_estimate_ns=4-boundary[0],
  target_ns=4,seconds=round(time.time()-start,1),rtl_sha256=stamp,retried_checkpoint=retried)
 rows=[r for r in rows if r['top']!=top];rows.append(row);summary.write_text(json.dumps(rows,indent=2));print(row,flush=True)
