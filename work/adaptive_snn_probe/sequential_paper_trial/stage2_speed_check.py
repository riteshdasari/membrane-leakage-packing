"""Compare unchanged int64/int32 equations on exactly the original64 pilot."""
from pathlib import Path
import json,time
import numpy as np
import torch
import integer_glif as wide
import integer_glif_int32_v2 as narrow
P=Path(__file__).resolve().parent
torch.set_num_threads(8);torch.set_num_interop_threads(1)
data=np.load(wide.PUBLIC/'original_test64.npz');results=[];reference=None
with torch.inference_mode():
    for label,module in [('int64',wide),('int32',narrow)]:
        model=module.load_model();rows=module.install(model,audit_first_batch=True)
        started=time.monotonic();logits=[]
        for i in range(0,64,4):logits.append(model(module.normalized(data['images'][i:i+4])).numpy().copy())
        full=np.concatenate(logits)
        assert all(r['independent_state_mismatches']==r['independent_spike_mismatches']==0 for r in rows.values())
        if reference is None:
            reference=full
            np.savez_compressed(P/'stage2_int64_pilot_logits.npz',logits=full)
        assert np.array_equal(full,reference)
        result=dict(arithmetic=label,elapsed_seconds=time.monotonic()-started,
            correct=int((full.argmax(1)==data['labels']).sum()),all_logits_bit_identical=True,
            independent_state_spike_audit=True,updates=sum(r['updates']for r in rows.values()))
        results.append(result);print(result,flush=True)
        del model
(P/'stage2_speed_check.json').write_text(json.dumps(dict(status='pass',rows=results),indent=2)+'\n',encoding='utf-8')
