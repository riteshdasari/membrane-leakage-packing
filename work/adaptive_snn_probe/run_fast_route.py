"""Serial local OOC builds; no downloads, package installs or board access."""
from pathlib import Path
import ctypes,subprocess,json,re,time,os,sys,hashlib
HERE=Path(__file__).resolve().parent
VIV=Path('C:/AMDDesignTools/2025.2/Vivado/bin/vivado.bat')
class Mem(ctypes.Structure):
 _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong),('total',ctypes.c_ulonglong),('free',ctypes.c_ulonglong),('rest',ctypes.c_ulonglong*5)]
summary=HERE/'results'/'fast_unit_hardware.json'
rows=json.loads(summary.read_text()) if summary.exists() else []
rtl_hash=hashlib.sha256((HERE/'persistent_unit_fast.sv').read_bytes()).hexdigest()
for top in sys.argv[1:]:
 m=Mem();m.length=ctypes.sizeof(m);ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
 print(top,'free GiB',round(m.free/2**30,2),flush=True)
 assert m.free>1.5*2**30,'Insufficient RAM for next routed build'
 assert hashlib.sha256((HERE/'persistent_unit_fast.sv').read_bytes()).hexdigest()==rtl_hash,'RTL changed while building'
 start=time.time();log=HERE/'results'/f'{top}_build.log'
 tmp=HERE/'results'/'persist_tmp';tmp.mkdir(exist_ok=True)
 env=os.environ.copy();env['TEMP']=str(tmp);env['TMP']=str(tmp)
 cmd=f'"{VIV}" -mode batch -log results/{top}_vivado.log -journal results/{top}_vivado.jou -source route_fast_unit.tcl -tclargs {top}'
 with log.open('w')as out:p=subprocess.run(cmd,shell=True,cwd=HERE,env=env,stdout=out,stderr=subprocess.STDOUT)
 assert p.returncode==0,log.read_text()[-3000:]
 dest=HERE/'results'/f'{top}_route';util=(dest/'util.rpt').read_text();timing=(dest/'timing.rpt').read_text()
 def get(label):
  found=re.search(r'\|\s*'+re.escape(label)+r'\s*\|\s*(\d+)',util);assert found,label
  return int(found[1])
 row=dict(top=top,LUT=get('Slice LUTs'),FF=get('Slice Registers'),DSP=get('DSPs'),
  WNS_ns=float((dest/'slack.txt').read_text()),seconds=round(time.time()-start,1),target_ns=4,
  rtl_sha256=rtl_hash)
 match=re.search(r'WNS\(ns\).*?\n\s*-+.*?\n\s*([-\d.]+)\s+([-\d.]+)\s+(\d+)\s+(\d+)\s+([-\d.]+)',timing,re.S)
 if match:row['WHS_ns']=float(match[5])
 row['critical_period_estimate_ns']=4-row['WNS_ns']
 rows=[r for r in rows if r['top']!=top];rows.append(row);print(row,flush=True)
 summary.write_text(json.dumps(rows,indent=2))
