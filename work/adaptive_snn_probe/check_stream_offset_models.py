"""Replay real-neuron windows, without padded lanes, and reconstruct SNN outputs."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
from pathlib import Path
import numpy as np,json,sys
from check_stream_offset import simulate
P=Path(__file__).resolve().parent;R=P/'results'
original=np.load(R/'adaptive_delta_model_25_1/expected.npz')['groups'].astype(np.int64)
ledger=json.loads((R/'adaptive_delta_model_input.json').read_text());frames=[]
for rec in ledger['ledger']:
 u=original[rec['start']:rec['start']+rec['blocks']].reshape(-1)[:rec['neurons']].tolist();frames.append((u,25,0))
variant='centered'if '--centered'in sys.argv else'offset'
tag=f'stream_{variant}_models';result=simulate(tag,frames,25,0,variant=variant)
for row in result['rows']:
 e=row['engine'];membranes=[[]for f in frames]
 for line in(R/tag/f'stream_out{e}.txt').read_text().splitlines():
  fid,pos,n,d,p,*rest=line.split();fid,pos,n=map(int,[fid,pos,n]);p=int(p,16)
  assert len(membranes[fid])==pos
  vals=[(p>>(11*l))&2047 for l in range(n)];membranes[fid].extend(v-2048 if v>=1024 else v for v in vals)
 state_bad=spike_bad=0;counts={m['seed']:np.zeros((48,10),np.int64)for m in ledger['metadata']}
 for r,leak in zip(ledger['ledger'],membranes):
  state=np.array(leak)+np.array(r['current']);fire=state>=r['threshold'];state-=fire*r['threshold']
  state_bad+=int(np.count_nonzero(state!=r['expected_state']));spike_bad+=int(np.count_nonzero(fire!=r['expected_spikes']))
  if r['layer']==1:counts[r['seed']][r['image']]+=fire
 assert state_bad==spike_bad==0
 accuracies=[]
 for m in ledger['metadata']:
  got=counts[m['seed']];assert np.array_equal(got,m['expected_counts'])
  accuracy=float(np.mean(got.argmax(1)==m['labels']));assert accuracy==m['sampled_reference_accuracy']
  accuracies.append(dict(seed=m['seed'],images=48,accuracy=accuracy,spike_counts_matched=True))
 row.update(state_mismatches=state_bad,spike_mismatches=spike_bad,model_rows=accuracies)
(R/(tag+'_checks.json')).write_text(json.dumps(result,indent=2))
print('STREAM MODEL STATES/SPIKES PASS',flush=True)
# The synthetic six-neuron burst frames remain separate timesteps.
stress=np.load(R/'adaptive_delta_stress_25_1/expected.npz')['groups'].astype(np.int64)
simulate(f'stream_{variant}_stress',[(u.tolist(),25,0)for u in stress],25,0,variant=variant)
