"""Serial local builds with RAM gate and stable source. Explicit --resume only."""
from pathlib import Path
import ctypes,subprocess,json,re,time,os,sys,hashlib
P=Path(__file__).resolve().parent;R=P/'results';V=Path('C:/AMDDesignTools/2025.2/Vivado/bin/vivado.bat')
class Mem(ctypes.Structure):
 _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong),('total',ctypes.c_ulonglong),('free',ctypes.c_ulonglong),('rest',ctypes.c_ulonglong*5)]
summary=R/'distributed_leak_hardware.json';rows=json.loads(summary.read_text())if summary.exists()else[]
rtl_hash=hashlib.sha256((P/'distributed_leak.sv').read_bytes()).hexdigest();resume='--resume'in sys.argv[1:]
for top in [a for a in sys.argv[1:]if a!='--resume']:
 m=Mem();m.length=ctypes.sizeof(m);ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
 print(top,'free GiB',round(m.free/2**30,2),flush=True)
 assert m.free>2.3*2**30,'Insufficient RAM for routed build (needs >2.3 GiB free); no build started'
 assert hashlib.sha256((P/'distributed_leak.sv').read_bytes()).hexdigest()==rtl_hash,'RTL changed during queue'
 note='resume_'if resume else'';log=R/f'{top}_{note}build.log';start=time.time()
 tmp=R/'leak_tmp';tmp.mkdir(exist_ok=True);env=os.environ.copy();env['TEMP']=str(tmp);env['TMP']=str(tmp)
 script='route_neuron_alu_resume.tcl'if resume else'route_distributed_leak.tcl'
 cmd=f'"{V}" -mode batch -log results/{top}_{note}vivado.log -journal results/{top}_{note}vivado.jou -source {script} -tclargs {top}'
 with log.open('w')as out:result=subprocess.run(cmd,shell=True,cwd=P,env=env,stdout=out,stderr=subprocess.STDOUT)
 assert result.returncode==0,log.read_text()[-2500:]
 dest=R/f'{top}_route';util=(dest/'util.rpt').read_text();timing=(dest/'timing.rpt').read_text()
 def get(label):
  found=re.search(r'\|\s*'+re.escape(label)+r'\s*\|\s*(\d+)',util);assert found,label;return int(found[1])
 row=dict(top=top,LUT=get('Slice LUTs'),FF=get('Slice Registers'),DSP=get('DSPs'),WNS_ns=float((dest/'slack.txt').read_text()),seconds=round(time.time()-start,1),target_ns=4,rtl_sha256=rtl_hash)
 match=re.search(r'WNS\(ns\).*?\n\s*-+.*?\n\s*([-\d.]+)\s+([-\d.]+)\s+(\d+)\s+(\d+)\s+([-\d.]+)',timing,re.S)
 if match:row['WHS_ns']=float(match[5])
 row['internal_period_estimate_ns']=4-row['WNS_ns']
 if resume:row['build_note']='Reopened unchanged synthesis checkpoint after tool failure; failure retained.'
 rows=[r for r in rows if r['top']!=top];rows.append(row);summary.write_text(json.dumps(rows,indent=2));print(row,flush=True)
