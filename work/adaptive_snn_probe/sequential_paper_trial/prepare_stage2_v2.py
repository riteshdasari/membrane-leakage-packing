"""Equivalent int32 arithmetic under the unchanged signed24/Q8 contract."""
from pathlib import Path
import hashlib,json
import numpy as np
P=Path(__file__).resolve().parent
assert not(P/'integer_glif_int32_v2.py').exists()
source=(P/'integer_glif.py').read_text(encoding='utf-8')
assert 'Python' not in source # this is a source transform, not a document replacement
updated=source.replace('torch.int64','torch.int32')
old='a,b,c = u.numpy(),coefficient.numpy(),current.numpy()'
assert old in updated
updated=updated.replace(old,'a,b,c = u.numpy().astype(np.int64),coefficient.numpy().astype(np.int64),current.numpy().astype(np.int64)')
old="assert (p['k1']>=0).all() and (p['k1']<=256).all()"
updated=updated.replace(old,old+"\n        assert all((p[k]>=-LIMIT).all() and (p[k]<LIMIT).all() for k in ('bias','reset','threshold'))")
(P/'integer_glif_int32_v2.py').write_text(updated,encoding='utf-8')
# beta*U+255 fits signed32 throughout signed24 U and beta0..256.
extrema=[]
for beta in range(257):
    u=np.array([-2**23,-2**23+1,-1,0,1,2**23-2,2**23-1],dtype=np.int64)
    wide=beta*u+255
    assert wide.min()>=-2**31 and wide.max()<2**31
    narrow=u.astype(np.int32)*np.int32(beta)+np.int32(255)
    assert np.array_equal(narrow.astype(np.int64),wide)
    extrema.append(dict(beta=beta,minimum=int(wide.min()),maximum=int(wide.max())))
# The four signed24 terms L + I - B - R*p are bounded inside signed26,
# hence do not overflow signed32 before the next-state signed24 gate.
proof=dict(status='pass',contract_unchanged=True,scalar_boundary_cases=257*7,
    product_add255_min=-2**31+255,product_add255_max=2**31-1,
    next_expression_absolute_bound=4*2**23,
    explanation='All old states/current/bias/reset are signed24; coefficient is0..256. Output still fails on any signed24 escape. NumPy audit promotes to int64 before independent division.',
    extrema=extrema,source_sha256=hashlib.sha256(source.encode()).hexdigest(),
    generated_sha256=hashlib.sha256(updated.encode()).hexdigest())
(P/'stage2_v2_arithmetic_proof.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
runner=(P/'run_stage2.py').read_text(encoding='utf-8')
runner=runner.replace('from integer_glif import','from integer_glif_int32_v2 import')
runner=runner.replace("P/'integer_glif.py'","P/'integer_glif_int32_v2.py'")
runner=runner.replace('stage2_', 'stage2_v2_')
# Performance replacement requires the unchanged old pilot's exact logits.
runner=runner.replace("save('stage2_v2_pilot.json',", "assert np.array_equal(prefix,np.load(P/'stage2_int64_pilot_logits.npz')['logits'])\n            save('stage2_v2_pilot.json',")
runner=runner.replace("source_commit='60638b28ff8b688b51867e7dd44f1e065d4892b0')", "source_commit='60638b28ff8b688b51867e7dd44f1e065d4892b0',equivalent_arithmetic='signed32 with verified signed24/Q8 bounds; no precision or rounding change')")
(P/'run_stage2_v2.py').write_text(runner,encoding='utf-8')
print('PREPARED EXACT INT32 REPLACEMENT',flush=True)
