"""Trace accounting for useful scalar leakage work per accepted DSP issue.

This is a numerical/schedule audit, not a toggle, power, or clock-utilization
measurement. It counts the actual DSP lane subset; a hybrid's third LUT lane is
reported separately. No core, checker, stimulus, or simulation output is edited.
"""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'; os.environ['OMP_NUM_THREADS'] = '1'
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import hashlib, json
import numpy as np
from check_stream_pipeline_whole import policy
from check_stream_pipeline import free

P = Path(__file__).resolve().parent; R = P/'results'
ENGINES = {0:'adaptive int7/int6 triple or wide pair',
           6:'adaptive int6 triple or wide pair',
           1:'fixed DSP pair',4:'fixed DSP triple',5:'fixed DSP pair plus LUT third'}
FIELDS = ['frames','requests','neurons','arithmetic_issues','narrow_requests',
          'bypass_requests','bypassed_neuron_operations','dsp_issues',
          'dsp_capacity_slots','dsp_valid_lane_operations','dsp_nonzero_operations',
          'dsp_changing_operations','narrow_three_lane_issues','wide_two_lane_issues',
          'fixed_three_lane_issues','hybrid_two_lane_issues','zero_third_copy_operations',
          'lut_third_operations','lut_third_nonzero_operations','lut_third_changing_operations',
          'all_nonzero_membranes','all_changing_membranes']
PIN_FILES = [Path(__file__).name,'stream_pipeline_whole_leak.sv',
             'check_stream_pipeline_whole.py','check_stream_pipeline.py',
             'results/adaptive_delta_model_25_1/expected.npz',
             'results/adaptive_delta_model_input.json',
             'results/adaptive_delta_stress_25_1/expected.npz',
             'results/adaptive_delta_stress_input.json',
             'results/stream_pipeline_models_checks.json',
             'results/stream_pipeline_stress_checks.json']

def pins():
    return {n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in PIN_FILES}

def leak(u):
    return -((-231*u)//256)

def finish(c,e):
    row = {k:int(c[k]) for k in FIELDS}
    row.update(engine=e,name=ENGINES[e])
    issues = row['dsp_issues']; capacity = row['dsp_capacity_slots']
    row['dsp_empty_lane_slots'] = capacity-row['dsp_valid_lane_operations']
    row['dsp_zero_lane_operations'] = row['dsp_valid_lane_operations']-row['dsp_nonzero_operations']
    row['dsp_unchanged_nonzero_operations'] = row['dsp_nonzero_operations']-row['dsp_changing_operations']
    row['dsp_nonzero_operations_per_issued_dsp'] = row['dsp_nonzero_operations']/issues if issues else None
    row['dsp_changing_operations_per_issued_dsp'] = row['dsp_changing_operations']/issues if issues else None
    row['nonzero_fraction_of_issued_lane_capacity'] = row['dsp_nonzero_operations']/capacity if capacity else None
    row['changing_fraction_of_issued_lane_capacity'] = row['dsp_changing_operations']/capacity if capacity else None
    row['valid_fraction_of_issued_lane_capacity'] = row['dsp_valid_lane_operations']/capacity if capacity else None
    assert row['arithmetic_issues'] == issues
    assert row['dsp_changing_operations']+row['lut_third_changing_operations'] == row['all_changing_membranes']
    assert row['dsp_nonzero_operations']+row['lut_third_nonzero_operations'] == row['all_nonzero_membranes']
    assert row['dsp_empty_lane_slots'] >= 0 and row['dsp_unchanged_nonzero_operations'] >= 0
    return row

def analyze(frames,labels,reference):
    totals = {e:defaultdict(int) for e in ENGINES}
    sub = {label:{e:defaultdict(int) for e in ENGINES} for label in sorted(set(labels))}
    for u,label in zip(frames,labels):
        nonzero = [int(x != 0) for x in u]
        changing = [int(x != leak(x)) for x in u]
        for e in ENGINES:
            c = defaultdict(int,frames=1,neurons=len(u),
                            all_nonzero_membranes=sum(nonzero),all_changing_membranes=sum(changing))
            pos = 0
            while pos < len(u):
                take,narrow,bypass = policy(u[pos:],25,e)
                c['requests'] += 1; c['narrow_requests'] += narrow
                if e == 5 and take == 3:
                    c['lut_third_operations'] += 1
                    c['lut_third_nonzero_operations'] += nonzero[pos+2]
                    c['lut_third_changing_operations'] += changing[pos+2]
                capacity = 3 if e == 4 or (e in (0,6) and narrow) else 2
                if take == 3 and capacity == 2 and e != 5:
                    assert u[pos+2] == 0
                    c['zero_third_copy_operations'] += 1
                if bypass:
                    c['bypass_requests'] += 1
                    c['bypassed_neuron_operations'] += take
                else:
                    c['arithmetic_issues'] += 1; c['dsp_issues'] += 1
                    c['dsp_capacity_slots'] += capacity
                    used = min(take,capacity)
                    c['dsp_valid_lane_operations'] += used
                    c['dsp_nonzero_operations'] += sum(nonzero[pos:pos+used])
                    c['dsp_changing_operations'] += sum(changing[pos:pos+used])
                    mode = ('fixed_three_lane_issues' if e == 4 else
                            'hybrid_two_lane_issues' if e == 5 else
                            'narrow_three_lane_issues' if narrow else 'wide_two_lane_issues')
                    c[mode] += 1
                pos += take
            assert pos == len(u)
            for k,v in c.items(): totals[e][k] += v; sub[label][e][k] += v
    rows = [finish(totals[e],e) for e in ENGINES]
    ref = json.loads((P/reference).read_text())
    assert ref['constant_delta'] == 25 and not ref['backpressure']
    expected = {r['engine']:r for r in ref['rows']}
    match_keys = ['requests','neurons','arithmetic_issues','narrow_requests','bypass_requests']
    for row in rows:
        refrow = expected[row['engine']]
        assert all(row[k] == refrow[k] for k in match_keys), (row['engine'],row,refrow)
        assert refrow['mismatches'] == 0
        row['original_simulation_schedule_crosscheck'] = {k:refrow[k] for k in match_keys}
        row['original_simulation_schedule_matched'] = True
    by_engine = {r['engine']:r for r in rows}
    comparisons = []
    for e in (0,6):
        for baseline in (1,4,5):
            a,b = by_engine[e],by_engine[baseline]
            comparisons.append(dict(engine=e,baseline=baseline,
                issued_dsp_request_reduction_fraction=1-a['dsp_issues']/b['dsp_issues'],
                changing_operations_per_issued_dsp_ratio=a['dsp_changing_operations_per_issued_dsp']/b['dsp_changing_operations_per_issued_dsp'],
                changing_capacity_fraction_ratio=a['changing_fraction_of_issued_lane_capacity']/b['changing_fraction_of_issued_lane_capacity'],
                note='Hybrid processes some changing operations in its separate LUT lane.'))
    return dict(frames=len(frames),real_neurons=sum(map(len,frames)),delta=25,beta_q8=231,
                scalar_nonzero_membranes=sum(int(x != 0) for u in frames for x in u),
                scalar_changing_membranes=sum(int(x != leak(x)) for u in frames for x in u),
                rows=rows,comparisons=comparisons,
                breakdown=[dict(label=label,rows=[finish(sub[label][e],e) for e in ENGINES]) for label in sub],
                reference_simulation=reference)

if __name__ == '__main__':
    print('TRACE ACCOUNTING free GiB',round(free(),2),flush=True)
    assert free() > .5, 'Trace accounting requires at least 0.5 GiB free RAM'
    stamp = pins()
    model = np.load(R/'adaptive_delta_model_25_1/expected.npz')['groups'].astype(np.int64)
    ledger = json.loads((R/'adaptive_delta_model_input.json').read_text())
    frames = [model[r['start']:r['start']+r['blocks']].reshape(-1)[:r['neurons']].tolist() for r in ledger['ledger']]
    labels = [f"seed_{r['seed']}" for r in ledger['ledger']]
    models = analyze(frames,labels,'results/stream_pipeline_models_checks.json')
    stress = np.load(R/'adaptive_delta_stress_25_1/expected.npz')['groups'].astype(np.int64)
    stress_meta = json.loads((R/'adaptive_delta_stress_input.json').read_text())
    stress_labels = [None]*len(stress)
    for rec in stress_meta:
        label = 'hard_reset' if rec['hard_reset'] else 'soft_subtract_reset'
        for i in range(rec['start'],rec['start']+rec['groups']):
            assert stress_labels[i] is None; stress_labels[i] = label
    assert all(x is not None for x in stress_labels)
    stresses = analyze([u.tolist() for u in stress],stress_labels,'results/stream_pipeline_stress_checks.json')
    assert pins() == stamp, 'Pinned inputs or sources changed during the audit'
    result = dict(created_utc=datetime.now(timezone.utc).isoformat(),source_hashes=stamp,
        definitions={
            'changing_operation':'U != ceil(231*U/256); positive U=0..10 are exact fixed points.',
            'issued_dsp':'accepted request whose bypass is false; counted from the exact core policy, not from toggle instrumentation.',
            'dsp_lanes':'E0/E6 narrow:3 otherwise first2; E1:first2; E4:3; E5:first2, third is separate LUT.',
            'capacity_denominator':'Sum of physical 2/3 lane capacity over issued requests, including unused tail slots and zero/unchanged valid lanes.',
            'nonzero':'Input membrane U is nonzero. It may still remain numerically unchanged.',
            'bypass':'No DSP issue when delta=0 or the available raw window is all zero; these traces use delta25.',
            'identity_pair_policy':'Three only for fixed triple/hybrid, an eligible narrow triple, or a real zero third lane.',
            'clock_utilization':'Not reported: this audit is useful operations per issued DSP and per issued lane capacity.',
        },limitations=[
            'Numerical schedule accounting, not measured toggles, energy, power, DSP utilization over clock time, host latency, or full neuron-update latency.',
            'Uses saved beta231 model traces without retraining; these differ from the models original trained leakage parameters.',
            'Hybrid LUT third-lane operations are excluded from DSP usefulness and listed separately.',
            'Schedule counts are crosschecked against completed original delta25 primitive simulations; WHOLE arithmetic verification is a separate gate.',
            'CW0/CW1 use the same policy and traces, so the accounting applies to both encodings.'
        ],models=models,stress=stresses)
    out = R/'stream_pipeline_whole_activity.json'; out.write_text(json.dumps(result,indent=2))
    print('TRACE ACCOUNTING PASS',out,flush=True)
    for name,dataset in [('models',models),('stress',stresses)]:
        for row in dataset['rows']:
            print(name,'E',row['engine'],'DSP issues',row['dsp_issues'],
                  'changed/issue',round(row['dsp_changing_operations_per_issued_dsp'],6),
                  'changed/capacity',round(row['changing_fraction_of_issued_lane_capacity'],6),flush=True)
