"""Replay saved real-neuron windows and reconstruct all SNN states/spikes."""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'; os.environ['OMP_NUM_THREADS'] = '1'
from pathlib import Path
import json,sys
import numpy as np
from check_stream_pipeline_encoded import simulate

P = Path(__file__).resolve().parent; R = P/'results'
original = np.load(R/'adaptive_delta_model_25_1/expected.npz')['groups'].astype(np.int64)
ledger = json.loads((R/'adaptive_delta_model_input.json').read_text()); frames = []
for rec in ledger['ledger']:
    u = original[rec['start']:rec['start']+rec['blocks']].reshape(-1)[:rec['neurons']].tolist()
    frames.append((u,25,0))
cw = int(sys.argv[sys.argv.index('--cw')+1]) if '--cw' in sys.argv else 0
assert cw in (0,1)
prefix = 'stream_pipeline_encoded_centered' if cw else 'stream_pipeline_encoded'
tag = prefix+'_models'; result = simulate(tag,frames,25,0,cw=cw)
for row in result['rows']:
    e = row['engine']; membranes = [[] for f in frames]
    for line in (R/tag/f'stream_out{e}.txt').read_text().splitlines():
        fid,pos,n,d,p,*rest = line.split(); fid,pos,n = map(int,[fid,pos,n]); p = int(p,16)
        assert len(membranes[fid]) == pos
        vals = [(p>>(11*l))&2047 for l in range(n)]
        membranes[fid].extend(v-2048 if v >= 1024 else v for v in vals)
    state_bad = spike_bad = 0
    counts = {m['seed']:np.zeros((48,10),np.int64) for m in ledger['metadata']}
    for rec,leak in zip(ledger['ledger'],membranes):
        state = np.array(leak)+np.array(rec['current']); fire = state >= rec['threshold']
        state -= fire*rec['threshold']
        state_bad += int(np.count_nonzero(state != rec['expected_state']))
        spike_bad += int(np.count_nonzero(fire != rec['expected_spikes']))
        if rec['layer'] == 1: counts[rec['seed']][rec['image']] += fire
    assert state_bad == spike_bad == 0
    accuracies = []
    for metadata in ledger['metadata']:
        got = counts[metadata['seed']]; assert np.array_equal(got,metadata['expected_counts'])
        accuracy = float(np.mean(got.argmax(1) == metadata['labels']))
        assert accuracy == metadata['sampled_reference_accuracy']
        accuracies.append(dict(seed=metadata['seed'],images=48,accuracy=accuracy,spike_counts_matched=True))
    row.update(state_mismatches=state_bad,spike_mismatches=spike_bad,model_rows=accuracies)
(R/(tag+'_checks.json')).write_text(json.dumps(result,indent=2))
print('STREAM PIPELINE ENCODED MODEL STATES/SPIKES PASS',flush=True)
stress = np.load(R/'adaptive_delta_stress_25_1/expected.npz')['groups'].astype(np.int64)
simulate(prefix+'_stress',[(u.tolist(),25,0) for u in stress],25,0,cw=cw)
