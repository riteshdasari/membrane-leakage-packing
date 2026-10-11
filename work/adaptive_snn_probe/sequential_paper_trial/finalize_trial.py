"""Read-only audit of saved experiments; generate the final decision record."""
from pathlib import Path
import hashlib, json, re, sys
P = Path(__file__).resolve().parent
OUT = P.parents[2] / 'outputs'
OUT.mkdir(exist_ok=True)
def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))
def digest(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(4*1024*1024), b''):
            h.update(b)
    return h.hexdigest()
roots = [P/x for x in ['stage2_results.json','stage2_acceptance.json',
    'stage3_results.json','stage3_algebra.json','stage3_acceptance.json',
    'stage4_native_acceptance_v4.json','stage4_common9_acceptance.json',
    'stage4_common12_acceptance.json','stage4_energy9_progress.json',
    'stage4_energy12_progress.json']]
for e in range(6):
    roots += [P/f'hardware/common9_e{e}_a0/hardware.json',
              P/f'hardware/golden9_e{e}_a0/golden_checks.json']
    if e != 2:
        roots += [P/f'hardware/replay9_e{e}_a0/replay_checks.json',
                  P/f'hardware/power9_e{e}_a0/power_audit.json']
roots += [P/'hardware/lut_functional_diagnostic_a0/diagnostic.json']
queue = roots[:]
visited, expected, actual, failures = set(), {}, {}, []
def pins(obj):
    if isinstance(obj, dict):
        for k,v in obj.items():
            if (isinstance(v,str) and re.fullmatch('[0-9a-f]{64}',v)
                and re.match(r'^[A-Za-z]:[\\/]', k)):
                yield Path(k),v
            else:
                yield from pins(v)
    elif isinstance(obj,list):
        for v in obj: yield from pins(v)
while queue:
    p = queue.pop().resolve()
    if p in visited: continue
    visited.add(p)
    d = read(p)
    for target, want in pins(d):
        target = target.resolve()
        expected.setdefault(target,set()).add(want)
        if target not in actual:
            try: actual[target] = digest(target)
            except OSError as ex: failures.append(dict(path=str(target),reason=str(ex))); continue
        if actual[target] != want:
            failures.append(dict(path=str(target),expected=want,actual=actual[target],record=str(p)))
        if target.suffix.lower()=='.json' and target not in visited:
            queue.append(target)
integrity = dict(status='pass' if not failures else 'fail',
    json_records_checked=len(visited),unique_pinned_files=len(actual),failures=failures,
    roots=[str(x) for x in roots],
    artifact_sha256={str(x):actual[x] for x in sorted(actual)})
(P/'stage4_final_integrity.json').write_text(json.dumps(integrity,indent=2)+'\n')
assert not failures, failures[:5]
s2,s3,a = [read(P/x) for x in ('stage2_results.json','stage3_results.json','stage3_algebra.json')]
assert s2['samples']==10000 and s3['all_logits_bit_identical_to_integer_reference']
native = read(P/'hardware/native_actual_s0_a3/acceptance.json')
assert native['status']=='pass'
rows=[]
for e in range(6):
    h=read(P/f'hardware/common9_e{e}_a0/hardware.json')
    assert h['status']=='pass' and h['WNS_ns']>=0 and h['WHS_ns']>=0
    original=read(h['original_hardware_file'])
    n=next(x for x in native['rows'] if x['engine']==e)
    row=dict(engine=e,label=h['label'],core=h['core'],
        WNS9_ns=h['WNS_ns'],WHS9_ns=h['WHS_ns'],WNS6_ns=original['WNS_ns'],
        original6_status=original['status'],sample_requests=n['requests'],
        sample_service_clocks=n['service_clocks'],hardware_file=str(P/f'hardware/common9_e{e}_a0/hardware.json'))
    if e!=2:
        replay=read(P/f'hardware/replay9_e{e}_a0/replay_checks.json')
        power=read(P/f'hardware/power9_e{e}_a0/power_audit.json')
        assert replay['replay_rows_checked']==17413 and power['status']=='pass'
        assert power['native_interval_audit']['scalar_updates']==17408
        row.update(timed_replay='pass',energy='accepted_vendor_dynamic_estimate',
            energy_pJ=power['estimated_dynamic_energy_pJ_per_scalar_update'],
            power_audit_file=str(P/f'hardware/power9_e{e}_a0/power_audit.json'))
    else:
        row.update(timed_replay='failed_at9ns_and12ns',energy='excluded',energy_pJ=None)
    rows.append(row)
post,split=rows[5],rows[1]
t=s3['total']; issue=t['issues']['adaptive_post']/t['issues']['fixed_split2']-1
metrics=dict(LUT_saving_fraction=1-post['core']['LUT']/split['core']['LUT'],
    FF_saving_fraction=1-post['core']['FF']/split['core']['FF'],
    stream_issue_overhead_fraction=issue,
    sample_issue_overhead_fraction=post['sample_requests']/split['sample_requests']-1,
    sample_estimated_dynamic_energy_saving_fraction=1-post['energy_pJ']/split['energy_pJ'],
    useful_operations_per_DSP_issue=t['arithmetic_operations']/t['issues']['adaptive_post'],
    LUT_issue_product_saving_fraction=1-(post['core']['LUT']/split['core']['LUT'])*(1+issue))
summary=dict(status='positive_adaptive_primitive_result_with_open_validation_gap',
    preferred_engine=5,operation='ceil(beta*U/256), signed12 U, beta0..256',
    policy='Two signed9 membranes with shared beta; otherwise one signed12 result per DSP issue',
    scope='Runtime membrane-range packing of leakage; integer state units unchanged; not synaptic accumulation or complete accelerator',
    stage2=dict(samples=10000,integer_accuracy_percent=s2['accuracy_percent'],float_accuracy_percent=s2['float_accuracy_percent'],
        prediction_disagreements=s2['class_disagreements'],full_packed_test=False),
    stage3=dict(samples=64,raw_neuron_updates=t['raw_operations'],arithmetic_operations=t['arithmetic_operations'],
        zero_bypassed=t['zero_bypassed'],packed_logits_identical=True,issues=t['issues'],
        exhaustive_algebra=a,all_wide_bursts_favor_fixed=True),
    stage4=dict(clock_period_ns=9,part='xc7a100tcsg324-1',tool='Vivado2025.2',
        rows=rows,energy_scalar_sample=17408,fixture_FF=78,
        energy_scope='Vendor dynamic estimate including common fixture, sampled actual operands,25C; not board/core-only/full-SNN energy'),
    adaptive_vs_exact_fixed_split=metrics,
    submission_ready=False,
    remaining_before_strong_paper=['Resolve LUT baseline routed timing-simulation discrepancy',
        'Validate another public vanilla LIF workload with relevant nontrivial leakage',
        'Collect complete-workload or independently designed representative activity estimates',
        'Complete related-work method equivalence audit; no first-ever assertion'],
    excluded_claims=['Accuracy improvement','Universal burst latency improvement','Whole-model hardware acceleration',
        'Full10000-image packed implementation execution','Measured board energy','Novel generic spill correction',
        'Fair LUT energy victory'],
    integrity_file=str(P/'stage4_final_integrity.json'),
    artifact_sha256={str(x):digest(x) for x in roots+[Path(__file__),P/'stage4_final_integrity.json']})
(P/'stage4_final_acceptance.json').write_text(json.dumps(summary,indent=2)+'\n')
(OUT/'membrane_leakage_final.summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(dict(status=summary['status'],integrity_records=len(visited),pinned_files=len(actual),
    rows=[{k:r[k] for k in ('engine','core','energy_pJ','timed_replay')} for r in rows],metrics=metrics)),flush=True)
