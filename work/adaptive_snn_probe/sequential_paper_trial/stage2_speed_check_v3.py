"""Exact-state and performance gate for a NumPy implementation of the same model."""
from pathlib import Path
import hashlib,json,time
import numpy as np
import torch
import integer_glif as original
import integer_glif_numpy_v3 as vector
P=Path(__file__).resolve().parent
torch.set_num_threads(8);torch.set_num_interop_threads(1)
data=np.load(original.PUBLIC/'original_test64.npz');results=[];reference=None;streams=[]
with torch.inference_mode():
    for label,module in [('torch_int64',original),('numpy_int64',vector)]:
        hashes=[]
        def observe(name,step,u,coefficient,current,leak,new,spikes,previous,p):
            h=hashlib.sha256()
            for a in(u,coefficient,current,leak,new,spikes,previous):h.update(a.numpy().tobytes())
            hashes.append((name,step,h.hexdigest()))
        model=module.load_model();rows=module.install(model,observer=observe,audit_first_batch=True)
        started=time.monotonic();logits=[]
        for i in range(0,64,4):logits.append(model(module.normalized(data['images'][i:i+4])).numpy().copy())
        full=np.concatenate(logits)
        assert all(r['independent_state_mismatches']==r['independent_spike_mismatches']==0 for r in rows.values())
        if reference is None:reference=full;streams=hashes
        assert np.array_equal(full,reference)
        assert hashes==streams
        row=dict(arithmetic=label,elapsed_seconds=time.monotonic()-started,correct=int((full.argmax(1)==data['labels']).sum()),
            all_logits_bit_identical=True,all_544_state_current_leak_spike_hashes_identical=True,
            independent_first_batch_state_spike_audit=True,updates=sum(r['updates']for r in rows.values()))
        results.append(row);print(row,flush=True);del model
assert np.array_equal(reference,np.load(P/'stage2_int64_pilot_logits.npz')['logits'])
(P/'stage2_speed_check_v3.json').write_text(json.dumps(dict(status='pass',rows=results,hashes=streams),indent=2)+'\n',encoding='utf-8')
# Prepare, but do not launch, a separate full runner. Preserve all earlier files.
runner=(P/'run_stage2.py').read_text(encoding='utf-8').replace('from integer_glif import','from integer_glif_numpy_v3 import')
runner=runner.replace("P/'integer_glif.py'","P/'integer_glif_numpy_v3.py'").replace('stage2_','stage2_v3_')
runner=runner.replace("save('stage2_v3_pilot.json',", "assert np.array_equal(prefix,np.load(P/'stage2_int64_pilot_logits.npz')['logits'])\n            save('stage2_v3_pilot.json',")
(P/'run_stage2_v3.py').write_text(runner,encoding='utf-8')
