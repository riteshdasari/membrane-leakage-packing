"""Separate scalar baseline screen; no main RTL/test mutations.

--simulate runs exact scalar RTL exhaustion; --synth screens resources only.
Synthesis timing is estimated, without placement/route, and cannot establish
three-lane timing, control sharing, occupied slices, or an adaptive-core win.
All variants have the same raw -> quotient/original -> subtraction -> output
pipeline. Digit differs from full only at constant25. Programmable delta keeps
the same generic expression in those two controls; split is the new candidate.
"""
from pathlib import Path
import argparse,ctypes,hashlib,json,os,re,subprocess,time

P=Path(__file__).resolve().parent;R=P/'results';V=Path('C:/AMDDesignTools/2025.2/Vivado')
SOURCES=['quotient_screen.sv','tb_quotient_screen.sv','screen_pipeline_quotients.py','screen_pipeline_quotients.tcl']
def stamps():return {n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in SOURCES}
def free():
 class M(ctypes.Structure):
  _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong),('total',ctypes.c_ulonglong),('free',ctypes.c_ulonglong),('rest',ctypes.c_ulonglong*5)]
 m=M();m.length=ctypes.sizeof(m);assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m));return m.free/2**30
def env(wd):
 tmp=wd/'tmp';tmp.mkdir(exist_ok=True);e=os.environ.copy();e['TEMP']=str(tmp);e['TMP']=str(tmp);return e
def simulate(dc,stall,pin):
 wd=R/f'quotient_screen_{dc}_{stall}';wd.mkdir(parents=True,exist_ok=True)
 assert free()>1.2,'Insufficient free RAM';print('Simulate',dc,stall,'free GiB',round(free(),2),flush=True)
 commands=[f'"{V}/bin/xvlog.bat" -sv -d "DC={dc}" -d "STALL={stall}" "{P}/quotient_screen.sv" "{P}/tb_quotient_screen.sv"',
  f'"{V}/bin/xelab.bat" -mt off tb_quotient_screen -s sim',f'"{V}/bin/xsim.bat" sim -R']
 for i,cmd in enumerate(commands):
  z=subprocess.run(cmd,shell=True,cwd=wd,env=env(wd),capture_output=True,text=True)
  (wd/f'tool_{i}.log').write_text(z.stdout+z.stderr)
  assert z.returncode==0,z.stdout[-4000:]+z.stderr[-1000:]
 assert 'QUOTIENT PASS' in z.stdout,z.stdout[-4000:];assert stamps()==pin,'Source changed during simulation'
 lines=(wd/'quotient_out.txt').read_text().splitlines();assert len(lines)==65536
 for i,line in enumerate(lines):
  x,d,a,b,c,ac,rc=line.split();x,d,ac,rc=map(int,[x,d,ac,rc])
  assert x==-1024+i%2048 and d==(25 if dc==25 else i//2048),(i,line)
  expected=(x-(x*d)//256)&2047
  assert [int(v,16) for v in [a,b,c]]==[expected]*3,(i,line,expected)
  if not stall:assert rc-ac==4,(i,line)
 match=re.search(r'QUOTIENT PASS REQUESTS (\d+) CLOCKS (\d+) INPUT_STALLS (\d+) OUTPUT_STALLS (\d+)',z.stdout);assert match
 requests,clocks,ins,outs=map(int,match.groups())
 if not stall:assert clocks==requests+4,(clocks,requests)
 else:assert ins>0 and outs>0
 row=dict(dc=dc,stalled=bool(stall),requests=requests,comparisons=requests*3,clocks=clocks,input_stalls=ins,output_stalls=outs,mismatches=0,source_sha256=pin)
 (R/f'quotient_screen_{dc}_{stall}_checks.json').write_text(json.dumps(row,indent=2));print(row,flush=True);return row
def synth(top,pin):
 assert free()>2.3,'Insufficient free RAM';print('Synthesize',top,'free GiB',round(free(),2),flush=True)
 for dc in [25,-1]:
  check=json.loads((R/f'quotient_screen_{dc}_{int(dc<0)}_checks.json').read_text())
  assert check['source_sha256']==pin and check['mismatches']==0
 cmd=[str(V/'bin/vivado.bat'),'-mode','batch','-log',f'results/{top}_screen_vivado.log','-journal',f'results/{top}_screen_vivado.jou','-source','screen_pipeline_quotients.tcl','-tclargs',top]
 log=R/f'{top}_screen_build.log';t=time.time()
 with log.open('w') as f:z=subprocess.run(subprocess.list2cmdline(cmd),shell=True,cwd=P,env=env(R),stdout=f,stderr=subprocess.STDOUT)
 assert z.returncode==0,log.read_text()[-5000:];assert stamps()==pin,'Source changed during screen'
 text=(R/f'{top}_screen/util.rpt').read_text()
 def count(label):
  m=re.search(r'\|\s*'+re.escape(label)+r'\*?\s*\|\s*([\d.]+)',text);assert m,(top,label);return int(float(m[1]))
 row=dict(top=top,LUT=count('Slice LUTs'),FF=count('Slice Registers'),DSP=count('DSPs'),seconds=round(time.time()-t,1),source_sha256=pin,scope='scalar synthesized resource screen, not routed timing')
 assert row['DSP']==0,row;print(row,flush=True);return row
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--simulate',action='store_true');ap.add_argument('--synth',action='store_true');args=ap.parse_args()
 if not(args.simulate or args.synth):ap.error('Choose --simulate and/or --synth; default performs no tools')
 R.mkdir(exist_ok=True);pin=stamps();result=dict(source_sha256=pin)
 if args.simulate:result['checks']=[simulate(25,0,pin),simulate(-1,1,pin)]
 if args.synth:result['synthesis']=[synth(f'top_quotient_{v}_{c}',pin) for c in ['const','prog'] for v in ['full','digit','split']]
 (R/'quotient_screen_summary.json').write_text(json.dumps(result,indent=2))
if __name__=='__main__':main()
