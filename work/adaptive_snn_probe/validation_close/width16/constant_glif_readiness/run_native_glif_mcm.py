"""Root-controlled source-pinned RTL validation for the shared GLIF LUT control."""
from pathlib import Path
import argparse, hashlib, json, re, shutil, sys
sys.dont_write_bytecode=True
import numpy as np
P=Path(__file__).resolve().parent;W=P.parent;ROOT=W.parent.parent
sys.path.insert(0,str(ROOT/'selective_energy_trial'))
import run_selective_energy as b


def main():
 ap=argparse.ArgumentParser();ap.add_argument('--cohort',choices=['exhaustive','actual_glif'],required=True)
 ap.add_argument('--stall',type=int,choices=[0,1],default=0);ap.add_argument('--capture',action='store_true');ap.add_argument('--attempt',required=True)
 args=ap.parse_args();assert re.fullmatch(r'[a-zA-Z0-9_-]+',args.attempt)
 prep=b.read(P/'preparation.json');assert prep['status']=='prepared_no_vendor_launch';b.verify(prep['source_sha256'])
 sources=prep['source_sha256']|b.pins([P/'preparation.json',Path(__file__)])
 wd=P/'hardware'/f'native_{args.cohort}_s{args.stall}_{args.attempt}';assert not wd.exists();wd.mkdir(parents=True)
 if args.cohort=='actual_glif':shutil.copyfile(W/'actual_glif_stim.txt',wd/'stim.txt')
 b.write(wd/'source_provenance.json',sources)
 try:
  flags=['-d',f'STALL={args.stall}','-d',f'EXHAUSTIVE={int(args.cohort=="exhaustive")}','-d',f'CAPTURE={int(args.capture)}']
  xvlog=b.VIVADO/'bin/xvlog.bat';xelab=b.VIVADO/'bin/xelab.bat';xsim=b.VIVADO/'bin/xsim.bat'
  b.job([str(xvlog),'-sv',*flags,str(P/'leak_glif_mcm.sv'),str(P/'tb_glif_mcm.sv')],wd,'xvlog',sources,1.2)
  b.job([str(xelab),'-mt','off','-debug','all','work.tb_sequential_leak16_glif_mcm','-s','sim'],wd,'xelab',sources,1.2)
  log=b.job([str(xsim),'sim','-runall'],wd,'xsim',sources,1.2)
  txt=log.read_text();assert 'GLIF_MCM_NATIVE PASS' in txt and not re.search(r'FATAL|ERROR:',txt)
  m=re.search(r'GLIF_MCM_NATIVE REQUESTS (\d+) RETIREMENTS (\d+) NEURONS (\d+) CLOCKS (\d+) MIN_LATENCY (\d+) MAX_LATENCY (\d+) FIRST (\d+) LAST (\d+)',txt)
  assert m;fields=dict(zip(['requests','retirements','scalars','clocks','min_latency','max_latency','first','last'],map(int,m.groups())))
  output=np.loadtxt(wd/'out.txt',dtype=str,ndmin=2);assert output.shape==(fields['requests'],4)
  expected=np.load(W/'actual_glif_expected.npz')['expected_leak'] if args.cohort=='actual_glif' else None
  legal=prep['domain']['beta'];at=0
  for row in output:
   cycle,n,data,latency=int(row[0]),int(row[1]),int(row[2],16),int(row[3]);assert n in (1,2) and latency>=2
   for lane in range(n):
    i=at+lane
    value=int(expected[i]) if expected is not None else -((-(i%65536-32768)*legal[i//65536])//256)
    assert (data>>(lane*16))&65535 == value&65535,(i,data,value)
   if n==1:assert data>>16==0
   at+=n
  want=262528 if args.cohort=='actual_glif' else 2162688
  assert at==fields['scalars']==want and fields['requests']==fields['retirements']
  if args.cohort=='actual_glif':assert fields['requests']==131328
  else:assert fields['requests']==1081344
  if args.stall==0:assert fields['min_latency']==fields['max_latency']==2
  b.verify(sources)
  result=dict(status='pass',B=16,label='shared_GLIF_checkpoint_MCM_LUT2',cohort=args.cohort,stall=args.stall,capture=args.capture,
       beta_domain=legal,fields=fields,independent_scalar_output_check='pass',clock_period_ns=6,latency_advancing_edges=2,
       source_sha256=sources,artifact_sha256=b.pins(p for p in wd.iterdir() if p.is_file()),
       scope='Native RTL all declared coefficients, full signed16 domain or unchanged full representative arithmetic stream; no physical/energy result.')
  b.write(wd/'acceptance.json',result);print(json.dumps(result|dict(source_sha256=f'{len(sources)} bindings',artifact_sha256='saved'),indent=2),flush=True)
 except Exception as exc:
  b.write(wd/'failure.json',dict(status='retained_failure',reason=repr(exc),source_sha256=sources));raise


if __name__=='__main__':main()
