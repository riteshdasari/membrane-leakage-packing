"""Read-only independent scalar audit; output goes only to this new folder."""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
from pathlib import Path
import hashlib
import json
import sys
import numpy as np
sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent
ROOT = P.parent

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def bits(lo, hi):
    return next(n for n in range(1, 64) if -(2 ** (n-1)) <= lo <= hi < 2 ** (n-1))

def postleak(value, beta):
    return (beta * value + 255) // 256

def reset(value, threshold):
    return value - threshold if value >= threshold else value

def hull(lo, hi, threshold):
    # Only endpoints and the reset discontinuity can attain extrema.
    points = [lo, hi]
    points += [v for v in (threshold - 1, threshold) if lo <= v <= hi]
    values = [reset(v, threshold) for v in points]
    return min(values), max(values)

def selected(lo, hi):
    points = {lo, hi}
    for v in (lo, hi, 0):
        for q in (v // 32 - 1, v // 32, v // 32 + 1):
            points.update(q * 32 + r for r in (0, 1, 30, 31))
    return sorted(v for v in points if lo <= v <= hi)

def storage(u_bits, sum_bits, base_bits):
    lanes = 4 if max(u_bits, sum_bits, 8) <= 12 else 2 if max(u_bits, sum_bits, 8) <= 24 else 0
    return dict(native_DSP_lanes=lanes, fixed8_DSP_FF=5+8*base_bits,
                adaptive_absolute_DSP_FF=5+5*base_bits+3*4,
                adaptive_union_DSP_FF=5+5*base_bits+3*4+3,
                native_hybrid_FF=5+(8-lanes)*sum_bits,
                full_LUT8_FF=5+8*sum_bits,
                adaptive_minus_native_FF=5*base_bits+12-(8-lanes)*sum_bits)

def main():
    target = P / 'independent_checks.json'
    assert not target.exists()
    screen_path = ROOT / 'range_horizon_trial/results.json'
    cert_path = ROOT / 'sum_width_trial/certificates.json'
    plan_path = ROOT / 'sum_width_trial/plan.json'
    screen = json.loads(screen_path.read_text())
    cert = json.loads(cert_path.read_text())
    plan = json.loads(plan_path.read_text())
    assert len(screen['rows']) == len(cert['rows']) == 72
    for record in (screen, cert, plan):
        for path, expected in record['source_sha256'].items():
            assert sha(path) == expected, path
    assert cert['plan_sha256'] == sha(plan_path)
    assert screen['predeclared_plan_sha256'] == sha(ROOT / 'range_horizon_trial/predeclared_plan.json')
    cfg_path = ROOT / 'results/final_selected.json'
    configurations = json.loads(cfg_path.read_text())['models']
    inputs = [Path(__file__), screen_path, cert_path, plan_path, cfg_path,
              ROOT / 'range_horizon_trial/predeclared_plan.json',
              *(ROOT / f'results/model_seed{s}.npz' for s in range(3))]
    source = {str(path): sha(path) for path in inputs}
    reset_cases = 0
    for threshold in (1, 2, 7, 31):
        for lo in range(-32, 33):
            for hi in range(lo, 33):
                actual = [reset(v, threshold) for v in range(lo, hi + 1)]
                assert hull(lo, hi, threshold) == (min(actual), max(actual))
                reset_cases += 1
    recomputed = []
    pair_cases = 0
    mode_changes = []
    assert {r['beta'] for r in cert['rows']} == {128,224,231,240,248,252,254,256}
    assert {r['timesteps'] for r in cert['rows']} == {32,128,256}
    for seed in range(3):
        config = next(c for c in configurations if c['seed'] == seed and c['leak_shift'] == 3)
        data = np.load(ROOT / f'results/model_seed{seed}.npz')
        weights = [data['w0'], data['w1']]
        neurons = []
        for layer, matrix in enumerate(weights):
            threshold = int(config['thresholds'][layer])
            assert threshold > 0
            for column in matrix.T:
                currents = [int(v) for v in column]
                lower = sum(v for v in currents if v < 0)
                upper = sum(v for v in currents if v > 0)
                assert -128 <= lower <= 0 <= upper <= 127
                neurons.append((lower, upper, threshold))
        for beta in (128,224,231,240,248,252,254,256):
            state = [(0,0) for _ in neurons]
            bounds = []
            for imin, imax, threshold in neurons:
                if beta == 256:
                    bounds.append(None)
                else:
                    decay = 256-beta
                    lower = -((-imin*256 + decay-1)//decay)
                    upper = max(threshold-1, (max(imax-threshold,0)*256+decay-1)//decay)
                    actual = hull(postleak(lower,beta)+imin, postleak(upper,beta)+imax, threshold)
                    assert lower <= 0 <= upper
                    assert lower <= actual[0] <= actual[1] <= upper
                    bounds.append((lower,upper))
            extrema = [0,0,0,0,0,0]
            for timestep in range(1,257):
                next_state = []
                for index, ((lo,hi),(imin,imax,threshold)) in enumerate(zip(state,neurons)):
                    plo, phi = postleak(lo,beta), postleak(hi,beta)
                    slo, shi = plo+imin, phi+imax
                    blo, bhi = plo//32+imin//32, phi//32+imax//32
                    for j, value in enumerate((plo,phi,slo,shi,blo,bhi)):
                        extrema[j] = min(extrema[j],value) if j%2==0 else max(extrema[j],value)
                    rl, rh = hull(slo,shi,threshold)
                    if bounds[index] is not None:
                        rl = max(rl,bounds[index][0]); rh = min(rh,bounds[index][1])
                    assert rl <= rh
                    # Original screen's lo=slo is exact in this domain because
                    # all current minima and all propagated lower states <= 0.
                    assert slo <= 0 < threshold and rl == max(slo,bounds[index][0] if bounds[index] else slo)
                    next_state.append((rl,rh))
                    if timestep in (32,128,256):
                        for u in selected(plo,phi):
                            for current in selected(imin,imax):
                                base = u//32 + current//32
                                field = u%32 + current%32
                                reconstructed = 32*(base+field//32)+field%32
                                assert reconstructed == u+current
                                pair_cases += 1
                state = next_state
                if timestep not in (32,128,256):
                    continue
                key = (seed,beta,timestep)
                old = next(r for r in screen['rows'] if (r['seed'],r['beta'],r['timesteps'])==key)
                new = next(r for r in cert['rows'] if (r['seed'],r['beta'],r['timesteps'])==key)
                ulo,uhi,slo,shi,blo,bhi = extrema
                assert [ulo,uhi] == old['certified_postleak_U_range'] == new['certified_U_range']
                u_bits = bits(ulo,uhi)
                assert u_bits == old['required_signed_U_bits'] == new['U_bits']
                word_lo,word_hi = -(2**(u_bits-1)),2**(u_bits-1)-1
                domains = {
                    'generic_full_word': ((word_lo-128,word_hi+127),(word_lo//32-4,word_hi//32+3)),
                    'uniform_U_any_I8': ((ulo-128,uhi+127),(ulo//32-4,uhi//32+3)),
                    'per_neuron_model': ((slo,shi),(blo,bhi))}
                for name,(sum_range,base_range) in domains.items():
                    actual = new['contracts'][name]
                    sb,bb = bits(*sum_range),bits(*base_range)
                    assert actual['sum_range'] == list(sum_range)
                    assert actual['precomputed_high_base_range'] == list(base_range)
                    assert actual['sum_bits'] == sb and actual['high_base_bits'] == bb
                    assert actual['storage'] == storage(u_bits,sb,bb)
                generic = new['contracts']['generic_full_word']['storage']['native_DSP_lanes']
                specialized = new['contracts']['uniform_U_any_I8']['storage']['native_DSP_lanes']
                if generic != specialized:
                    mode_changes.append(dict(seed=seed,beta=beta,timesteps=timestep,
                                             generic_native_lanes=generic,specialized_native_lanes=specialized))
                assert new['unchanged_original_control'] == old['unchanged_original_control'] == (beta==224 and timestep==32)
                recomputed.append(dict(seed=seed,beta=beta,timesteps=timestep,U_range=[ulo,uhi],sum_range=[slo,shi],base_range=[blo,bhi]))
    assert len(recomputed)==72
    for path,expected in source.items():
        assert sha(path)==expected,path
    result = dict(status='qualified_pass',rows_recomputed=72,contract_rows_verified=216,
                  scalar_reset_interval_cases=reset_cases,directed_residue_pairs=pair_cases,
                  mode_changes=mode_changes,source_sha256=source,recomputed=recomputed,
                  scope='Read-only independent scalar endpoint/certificate/storage audit; no native/vendor route or new benchmark replay.')
    target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('source_sha256','recomputed','mode_changes')},indent=2))
    print('CONTRACT-MODE CHANGES',len(mode_changes))

if __name__=='__main__':
    main()
