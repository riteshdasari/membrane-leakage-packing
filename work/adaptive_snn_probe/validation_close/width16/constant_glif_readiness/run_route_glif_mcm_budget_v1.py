"""One root-controlled matched12ns route; requires completed native receipts."""
from pathlib import Path
import argparse,hashlib,json,math,re,sys,time
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;W=P.parent;ROOT=W.parent.parent
sys.path.insert(0,str(ROOT/'selective_energy_trial'))
import run_selective_energy as b
sys.path.insert(0,str(ROOT/'common_layout_trial'))
import run_guard_add_selective_route as helper



def wait_memory(threshold):
 budget_file=P/'operational_budget_v1.json'
 assert b.sha(budget_file)=='0f2f4a6ff959619b8d6f7bbc6081a8506d18bdff5677f025483ebac637dc4019'
 b.verify(b.read(budget_file)['source_sha256'])
 deadline=time.monotonic()+600
 while b.free()<=threshold:
  assert time.monotonic()<deadline,('Bounded memory wait expired',threshold,b.free())
  print('MEMORY WAIT free GiB',round(b.free(),3),'required',threshold,flush=True)
  time.sleep(5)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--exhaustive-acceptance',required=True);ap.add_argument('--actual-acceptance',required=True);ap.add_argument('--attempt',required=True)
 args=ap.parse_args();assert re.fullmatch(r'[a-zA-Z0-9_-]+',args.attempt)
 prep=b.read(P/'preparation.json');b.verify(prep['source_sha256']);sources=prep['source_sha256']|b.pins([P/'preparation.json',Path(__file__)])
 for cohort,path in [('exhaustive',args.exhaustive_acceptance),('actual_glif',args.actual_acceptance)]:
  path=Path(path).resolve();receipt=b.read(path);assert receipt['status']=='pass' and receipt['cohort']==cohort and receipt['stall']==0
  b.verify(receipt['source_sha256']);b.verify(receipt['artifact_sha256']);sources|=receipt['source_sha256']|receipt['artifact_sha256']|b.pins([path])
 top='top_sequential_leak16_glif_mcm';wd=P/'hardware'/f'route12_{args.attempt}';assert not wd.exists();wd.mkdir(parents=True)
 prov=hashlib.sha256(json.dumps(dict(top=top,period_ns=12,part='xc7a100tcsg324-1',sources=sources),sort_keys=True).encode()).hexdigest()
 b.write(wd/'source_provenance.json',sources)
 try:
  b.verify(sources)
  wait_memory(2.15)
  cmd=[b.VIVADO/'bin/vivado.bat','-mode','batch','-log','vivado.log','-journal','vivado.jou','-source',P/'route_glif_mcm.tcl','-tclargs',top,12,prov,'fresh',wd]
  log=b.job([str(x).replace('\\','/')for x in cmd],wd,'route',sources,2.1)
  assert f'FRONTIER_TIMING_ROUTED {top}'in log.read_text()
  full=helper.util(wd/'util.rpt');core=helper.util(wd/'core_util.rpt',False)
  account={k:int(v)for k,v in(line.split()for line in(wd/'fixture_accounting.txt').read_text().splitlines())}
  assert (account['launch_FF'],account['capture_FF'],account['fixture_FF'])==(55,39,94)
  assert full['FF']-core['FF']==94 and full['LUT']==core['LUT']and full['DSP']==core['DSP']==0
  slack=list(map(float,(wd/'slack.txt').read_text().splitlines()));boundary=list(map(float,(wd/'boundary_slack.txt').read_text().splitlines()))
  assert len(slack)==len(boundary)==2 and all(math.isfinite(v)for v in slack+boundary)
  fields=(wd/'provenance.txt').read_text().splitlines();assert fields[0]==prov and 'VIVADO 2025.2' in fields
  b.verify(sources)
  record=dict(status='pass'if min(slack+boundary)>=0 else 'timing_failed',B=16,label='shared_GLIF_checkpoint_MCM_LUT2',top=top,
       core=core,full_fixture=full,fixture_FF=94,slice_accounting=account,WNS_ns=slack[0],WHS_ns=slack[1],boundary_WNS_ns=boundary[0],boundary_WHS_ns=boundary[1],
       clock_period_ns=12,latency_advancing_edges=2,part='xc7a100tcsg324-1',beta_domain=prep['domain']['beta'],source_sha256=sources,provenance_sha256=prov,
       artifact_sha256=b.pins(p for folder in(wd,wd/'synth')for p in folder.iterdir()if p.is_file()),
       scope='Shared checkpoint-coefficient restricted zero-DSP fullsigned16 pair primitive; all33 coefficients accepted; common94FF excluded area. No full-neuron or board claim, energy pending strict capture/export/replay.')
  b.write(wd/'hardware.json',record);print(json.dumps(record|dict(source_sha256=f'{len(sources)} bindings',artifact_sha256='saved'),indent=2),flush=True)
 except Exception as exc:
  b.write(wd/'failure.json',dict(status='retained_failure',reason=repr(exc),source_sha256=sources));raise


if __name__=='__main__':main()
