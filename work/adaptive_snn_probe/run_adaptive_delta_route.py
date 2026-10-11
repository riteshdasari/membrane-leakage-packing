"""Serial, RAM-gated builds; retained logs and one checkpoint retry on tool failure."""
from pathlib import Path
import ctypes,subprocess,json,re,time,os,sys,hashlib
P=Path(__file__).resolve().parent;R=P/'results';V=Path('C:/AMDDesignTools/2025.2/Vivado/bin/vivado.bat')
class Mem(ctypes.Structure):
 _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong),('total',ctypes.c_ulonglong),('free',ctypes.c_ulonglong),('rest',ctypes.c_ulonglong*5)]
summary=R/'adaptive_delta_hardware.json';rows=json.loads(summary.read_text())if summary.exists()else[]
source=P/'adaptive_delta_leak.sv';rtl_hash=hashlib.sha256(source.read_bytes()).hexdigest()
for top in sys.argv[1:]:
 m=Mem();m.length=ctypes.sizeof(m);ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
 print(top,'free GiB',round(m.free/2**30,2),flush=True);assert m.free>2.3*2**30,'Insufficient RAM; no build started'
 assert hashlib.sha256(source.read_bytes()).hexdigest()==rtl_hash,'RTL changed during queue'
 start=time.time();tmp=R/'adaptive_delta_tmp';tmp.mkdir(exist_ok=True);env=os.environ.copy();env['TEMP']=str(tmp);env['TMP']=str(tmp)
 retried=False
 for attempt in range(2):
  note='resume_'if attempt else'';log=R/f'{top}_{note}build.log'
  script='route_neuron_alu_resume.tcl'if attempt else'route_adaptive_delta_leak.tcl'
  cmd=f'"{V}" -mode batch -log results/{top}_{note}vivado.log -journal results/{top}_{note}vivado.jou -source {script} -tclargs {top}'
  with log.open('w')as out:z=subprocess.run(cmd,shell=True,cwd=P,env=env,stdout=out,stderr=subprocess.STDOUT)
  if z.returncode==0:break
  fail=log.read_text()
  if attempt==0 and 'ERROR: [Synth 20-411]'in fail and (R/f'{top}_synth/design.dcp').exists():
   print('Retry unchanged synthesis checkpoint after known Vivado failure',flush=True);retried=True;continue
  raise RuntimeError(fail[-3500:])
 dest=R/f'{top}_route';util=(dest/'util.rpt').read_text();timing=(dest/'timing.rpt').read_text()
 def get(label):
  found=re.search(r'\|\s*'+re.escape(label)+r'\s*\|\s*([\d.]+)',util);assert found,label;return float(found[1])
 row=dict(top=top,LUT=int(get('Slice LUTs')),FF=int(get('Slice Registers')),DSP=int(get('DSPs')),RAMB18=int(get('RAMB18')),RAMB36=int(get('RAMB36/FIFO*')),
  WNS_ns=float((dest/'slack.txt').read_text()),seconds=round(time.time()-start,1),target_ns=4,rtl_sha256=rtl_hash,retried_checkpoint=retried)
 match=re.search(r'WNS\(ns\).*?\n\s*-+.*?\n\s*([-\d.]+)\s+([-\d.]+)\s+(\d+)\s+(\d+)\s+([-\d.]+)',timing,re.S)
 if match:row['WHS_ns']=float(match[5])
 row['internal_period_estimate_ns']=4-row['WNS_ns']
 rows=[r for r in rows if r['top']!=top];rows.append(row);summary.write_text(json.dumps(rows,indent=2));print(row,flush=True)
