"""Screen real learned decay coefficients against the old near-identity trial."""
from pathlib import Path
import numpy as np,json,hashlib
P=Path(__file__).resolve().parent;w=np.load(P/'checkpoint_arrays_v3.npz')
def sigmoid(x):return 1/(1+np.exp(-x.astype(np.float64)))
rows=[]
for key in w.files:
    if not key.endswith('.tau'):continue
    name=key[:-4];alpha=sigmoid(w[name+'.alpha']);gamma=sigmoid(w[name+'.gamma']);tau=sigmoid(w[key])
    for previous_spike in(0,1):
        coefficient=(1-alpha*(1-tau))*(1-gamma*previous_spike)
        beta=np.rint(256*coefficient).astype(np.int64);delta=256-beta
        rows.append(dict(layer=name,previous_spike=previous_spike,channels=len(beta),
            real_coefficient_min=float(coefficient.min()),real_coefficient_max=float(coefficient.max()),
            illustrative_nearest_Q8_beta_min=int(beta.min()),illustrative_nearest_Q8_beta_max=int(beta.max()),
            old_full_width_delta_0_to_25_regime_channels=int(((delta>=0)&(delta<=25)).sum()),
            old_delta_0_to_31_regime_channels=int(((delta>=0)&(delta<=31)).sum()),
            illustrative_Q8_rounding_max_coefficient_error=float(np.abs(beta/256-coefficient).max())))
result=dict(status='completed_coefficient_scope_screen',rows=rows,
    channel_contexts=sum(r['channels']for r in rows),
    covered_by_old_near_identity_full_width_regime=sum(r['old_full_width_delta_0_to_25_regime_channels']for r in rows),
    covered_by_old_delta_0_to_31_regime=sum(r['old_delta_0_to_31_regime_channels']for r in rows),
    conclusion='The old coefficient231/delta25 near-identity leakage candidate does not directly cover these learned GLIF coefficients. Do not set the model coefficient to231 to make the hardware fit. General narrow3/fixed/split arithmetic experiments are separate retained controls.',
    scope='Real learned coefficient inspection and illustrative nearest-Q8 compatibility only. No Q8 model was executed, no accuracy-preserving quantization, natural decoder cost or new packing benefit is established.',
    pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in[Path(__file__),P/'checkpoint_arrays_v3.npz',P.parent/'screen_mixed_third_leakage.py',P.parent/'check_packed_leak.py']})
(P/'coefficient_scope_screen.json').write_text(json.dumps(result,indent=2)+'\n')
print({k:v for k,v in result.items()if k not in('rows','pins')},flush=True)
