"""Serial RAM-gated quad routes; require reviewed/full exact RTL evidence.

This never runs automatically when imported. The timing fixture has103 FF and
is not a production handshake adapter. Registered OOC timing is not board Fmax.
"""
from pathlib import Path
import argparse,ctypes,hashlib,json,os,re,subprocess,time
P=Path(__file__).resolve().parent;R=P/'results';V=Path('C:/AMDDesignTools/2025.2/Vivado/bin/vivado.bat')
SOURCES=['quad_leak.sv','tb_quad_leak.sv','check_quad.py','check_quad_snn.py','quad_timing.sv','route_quad.tcl','run_quad_route.py']
ENGINES=dict(adaptive6=0,adaptive7=1,fixed3=2,fixed4=3,lut4=4)
MODEL_INPUTS=['adaptive_delta_model_25_1/expected.npz','adaptive_delta_model_input.json']
def sha(path):
 h=hashlib.sha256()
 with path.open('rb')as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
def hashes():return {n:hashlib.sha256((P/n).read_bytes()).hexdigest()for n in SOURCES}
def free():
 class M(ctypes.Structure):
  _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong),('total',ctypes.c_ulonglong),('free',ctypes.c_ulonglong),('rest',ctypes.c_ulonglong*5)]
 m=M();m.length=ctypes.sizeof(m);assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m));return m.free/2**30
def functional(top,pin):
 name=top.removeprefix('top_quad_');assert top=='top_quad_'+name and name in ENGINES
 evidence={}
 for check in ['quad_main_0_checks.json','quad_main_1_checks.json','quad_models_0_checks.json','quad_models_1_checks.json']:
  d=json.loads((R/check).read_text());assert d['delta']==25 and d['frames']>0
  assert d['acceptance_to_handshake_advances']==4 and d['expected_engines']==list(range(5))
  assert sorted(r['engine']for r in d['rows'])==list(range(5)),(check,'Expected exactly five engines')
  assert set(d['source_hashes'])=={'quad_leak.sv','tb_quad_leak.sv','check_quad.py'}
  for n,h in d['source_hashes'].items():assert pin[n]==h,(check,n,'Functional source pin differs')
  assert d['backpressure']==check.endswith('_1_checks.json')
  expected_stimulus=check.removesuffix('_checks.json')+'/stream_stim.txt'
  assert d['stimulus_file']==expected_stimulus and sha(R/expected_stimulus)==d['stimulus_sha256'],(check,'Stimulus pin differs')
  if check.startswith('quad_models'):
   assert d['validation_kind']=='saved_model_raw_replay'and d['frames']==9216
   assert d['model_input_sha256']=={n:sha(R/n)for n in MODEL_INPUTS},(check,'Saved model inputs changed')
  else:assert d['validation_kind']=='full_integer_stress'and d['model_input_sha256']is None
  for row in d['rows']:
   assert row['mismatches']==0 and row['neurons']>0 and row['latency_checks']==row['requests']>0
  evidence[check]=sha(R/check)
 snn_check=R/'quad_snn_checks.json';d=json.loads(snn_check.read_text())
 assert d['source_hashes']=={n:pin[n]for n in ['quad_leak.sv','tb_quad_leak.sv','check_quad.py']}
 assert d['reconstruction_script_sha256']==pin['check_quad_snn.py']
 assert d['reference_hashes']==dict(ledger=sha(R/MODEL_INPUTS[1]),raw_membranes=sha(R/MODEL_INPUTS[0]))
 assert sorted((r['engine'],r['backpressure'])for r in d['rows'])==[(e,b)for e in range(5)for b in (False,True)]
 for row in d['rows']:
  assert row['state_mismatches']==row['spike_mismatches']==0 and row['neurons']>0
  assert len(row['model_rows'])==3 and all(m['spike_counts_matched']and m['images']==48 for m in row['model_rows'])
 expected_outputs={str(Path('results')/f'quad_models_{b}'/f'stream_out{e}.txt')for b in (0,1)for e in range(5)}
 assert set(d['output_hashes'])==expected_outputs
 for name,h in d['output_hashes'].items():assert sha(P/name)==h,(name,'SNN replay output pin differs')
 evidence[snn_check.name]=sha(snn_check)
 return evidence
def util(path,need_slices=True):
 t=path.read_text()
 def get(label):
  m=re.search(r'\|\s*'+re.escape(label)+r'\*?\s*\|\s*([\d.]+)',t);assert m,(path,label);return int(float(m[1]))
 m=re.search(r'\|\s*Slice\s*\|\s*([\d.]+)',t)
 if need_slices:assert m,(path,'Slice')
 return dict(LUT=get('Slice LUTs'),FF=get('Slice Registers'),DSP=get('DSPs'),RAMB18=get('RAMB18'),RAMB36=get('RAMB36/FIFO*'),occupied_slices=int(float(m[1]))if m else None)
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('tops',nargs='+');ap.add_argument('--target',type=float,default=6.0);ap.add_argument('--min-free-gib',type=float,default=2.3);args=ap.parse_args()
 assert args.target>0 and args.min_free_gib>=2.3;pin=hashes();summary=R/'quad_hardware.json';rows=json.loads(summary.read_text())if summary.exists()else[]
 for top in args.tops:
  assert hashes()==pin,'Queue source changed';checks=functional(top,pin)
  provenance=hashlib.sha256(json.dumps(dict(top=top,target_ns=args.target,sources=pin,checks=checks,part='xc7a100tcsg324-1'),sort_keys=True).encode()).hexdigest()
  if any(r['top']==top and r['provenance_sha256']==provenance for r in rows):print('Already complete',top,flush=True);continue
  memory=free();print(top,'free GiB',round(memory,2),flush=True);assert memory>args.min_free_gib,'Insufficient free RAM'
  tmp=R/'quad_tmp';tmp.mkdir(exist_ok=True);env=os.environ.copy();env['TEMP']=str(tmp);env['TMP']=str(tmp)
  pre=R/f'{top}_synth';prepin=pre/'provenance.txt'
  if prepin.exists():prepin.unlink()
  start=time.time();retried=False
  for attempt in range(2):
   assert hashes()==pin;tail='_resume'if attempt else'';log=R/f'{top}{tail}_build.log'
   cmd=[str(V),'-mode','batch','-log',f'results/{top}{tail}_vivado.log','-journal',f'results/{top}{tail}_vivado.jou','-source','route_quad.tcl','-tclargs',top,str(args.target),provenance,'resume'if attempt else'fresh']
   with log.open('w')as f:z=subprocess.run(subprocess.list2cmdline(cmd),shell=True,cwd=P,env=env,stdout=f,stderr=subprocess.STDOUT)
   if z.returncode==0:break
   failure=log.read_text()
   if attempt==0 and 'ERROR: [Synth 20-411]'in failure and (pre/'design.dcp').exists()and prepin.exists()and prepin.read_text().strip()==provenance:retried=True;continue
   raise RuntimeError(failure[-5000:])
  assert hashes()==pin and functional(top,pin)==checks,'Sources/evidence changed during route'
  dest=R/f'{top}_route';assert(dest/'provenance.txt').read_text().splitlines()[0]==provenance
  full=util(dest/'util.rpt');core=util(dest/'core_util.rpt',False)
  acc={k:int(v)for k,v in(line.split()for line in(dest/'fixture_accounting.txt').read_text().splitlines())}
  assert acc['launch_FF']==50 and acc['capture_FF']==53 and acc['fixture_FF']==103
  assert full['FF']-core['FF']==103 and full['LUT']==core['LUT']and full['DSP']==core['DSP']
  core['occupied_slices_reported']=core['occupied_slices'];core['occupied_slices']=acc['core_slices_touched']
  slack=list(map(float,(dest/'slack.txt').read_text().splitlines()));boundary=list(map(float,(dest/'boundary_slack.txt').read_text().splitlines()));assert len(slack)==len(boundary)==2
  row=dict(top=top,target_ns=args.target,core=core,full_fixture=full,fixture_overhead=dict(LUT=0,FF=103,DSP=0),slice_accounting=acc,
   WNS_ns=slack[0],WHS_ns=slack[1],clock_to_clock_period_estimate_ns=args.target-slack[0],boundary_WNS_ns=boundary[0],boundary_WHS_ns=boundary[1],
   source_sha256=pin,functional_check_sha256=checks,provenance_sha256=provenance,retried_checkpoint=retried,seconds=round(time.time()-start,1),
   scope='Constant25 raw four-input arithmetic primitive in registered OOC fixture; no board, memory, SNN accuracy, power or full latency measurement')
  rows=[r for r in rows if r['top']!=top]+[row];summary.write_text(json.dumps(rows,indent=2));print(json.dumps(row),flush=True)
if __name__=='__main__':main()
