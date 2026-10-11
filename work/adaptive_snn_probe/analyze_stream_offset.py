"""Operation counts, frame-drain proxies, and an identity-aware fixed schedule."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
from pathlib import Path
import json,numpy as np
from check_stream_offset import policy
P=Path(__file__).resolve().parent;R=P/'results'
ledger=json.loads((R/'adaptive_delta_model_input.json').read_text());old=np.load(R/'adaptive_delta_model_25_1/expected.npz')['groups']
frames=[old[r['start']:r['start']+r['blocks']].reshape(-1)[:r['neurons']].tolist()for r in ledger['ledger']]
nonzero=sum(sum(v!=0 for v in u)for u in frames)
changed=sum(sum(v-(25*v//256)!=v for v in u)for u in frames)
identity_req=0
for u in frames:
 pos=0
 while pos<len(u):
  window=u[pos:pos+3];n=len(window)
  copied=all(0<=v<=10 for v in window)
  take=3 if n==3 and(copied or window[2]==0)else min(2,n)
  identity_req+=1;pos+=take
rows=[]
for variant in ['offset','centered']:
 checks=json.loads((R/f'stream_{variant}_models_checks.json').read_text())
 for r in checks['rows']:
  fcounts=[0]*len(frames)
  for line in(R/f'stream_{variant}_models'/f"stream_out{r['engine']}.txt").read_text().splitlines():
   fid=int(line.split(' ',1)[0]);fcounts[fid]+=1
  assert sum(fcounts)==r['requests']
  seeds=[]
  for m in ledger['metadata']:
   req=sum(n for n,rec in zip(fcounts,ledger['ledger'])if rec['seed']==m['seed'])
   nf=sum(rec['seed']==m['seed']for rec in ledger['ledger'])
   seeds.append(dict(seed=m['seed'],requests=req,continuous_clock_proxy=req+3,frame_drained_clock_proxy=req+3*nf,frames=nf))
  rows.append(dict(variant=variant,engine=r['engine'],requests=r['requests'],measured_continuous_clocks=r['clocks'],
   frame_drained_clock_proxy=r['requests']+3*len(frames),nonzero_products_per_arithmetic_issue=nonzero/r['arithmetic_issues'],
   changed_membranes_per_arithmetic_issue=changed/r['arithmetic_issues'],seeds=seeds))
stress=[];s=np.load(R/'adaptive_delta_stress_25_1/expected.npz')['groups']
for variant in ['offset','centered']:
 for engine in [0,1,2,3,4,6]:
  req=[0,0]
  for line in(R/f'stream_{variant}_stress'/f'stream_out{engine}.txt').read_text().splitlines():req[int(line.split(' ',1)[0])//320]+=1
  for hard,r in enumerate(req):stress.append(dict(variant=variant,engine=engine,hard_reset=bool(hard),requests=r,
   continuous_clock_proxy=r+3,frame_drained_clock_proxy=r+3*320))
out=dict(model_frames=len(frames),model_neurons=sum(map(len,frames)),model_nonzero_membranes=nonzero,model_changed_membranes=changed,
 rows=rows,stress=stress,identity_aware_fixed2_requests=identity_req,identity_aware_fixed2_continuous_clock_proxy=identity_req+3,
 notes=['Frame-drained proxies add three clocks per neuron-array frame; no RTL frame barrier or synaptic/threshold schedule was built',
 'The no-change interval for delta25 is U in[0,10]; an identity-aware two-lane schedule can return three copies for such windows. Its extra monitor is not implemented or routed',
 'Nonzero products and changed updates are two declared usefulness measures, not DSP power estimates',
 'Raw three-value windows require state ports/lookahead handling outside the measured core. No memory controller, pointer update or bank rotation is included',
 'At most two state reads/writes per clock caps sustained updates at two neurons per clock for all cores; three-lane issue savings need sufficient bandwidth'])
(R/'stream_offset_schedule_audit.json').write_text(json.dumps(out,indent=2))
print(json.dumps(dict(model_neurons=out['model_neurons'],nonzero=nonzero,changed=changed,identity_fixed2_requests=identity_req,rows=rows[:2]),indent=2),flush=True)
