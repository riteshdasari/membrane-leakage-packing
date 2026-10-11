"""Read-only independent delivery closure and cross-result consistency checks."""
from pathlib import Path
import hashlib,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'outputs';STEM='membrane_adaptive_extended_checks_v2'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb')as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
manifest=read(OUT/f'{STEM}.manifest.json');assert manifest['status']=='pass_hash_closure'
for path,item in manifest['files'].items():
    assert Path(path).stat().st_size==item['bytes'],path
    assert sha(path)==item['sha256'],path
summary=read(OUT/f'{STEM}.summary.json')
assert sha(OUT/f'{STEM}.md')==manifest['report_sha256']
assert sha(OUT/f'{STEM}.summary.json')==manifest['summary_sha256']
hardware={r['engine']:r for r in summary['certified_hardware']['rows']}
assert set(hardware)==set(range(5))
expected_ff={0:47,1:53,2:49,3:93,4:87}
for e,r in hardware.items():
    actual=read(r['hardware_file']);assert actual['core']==r['core']
    assert r['status']=='pass'and min(r['WNS_ns'],r['WHS_ns'])>=0
    assert r['fixture_FF']==r['full_fixture']['FF']-r['core']['FF']==290
    assert r['core']['DSP']==(1 if e<3 else 0)
    assert r['core']['FF']==expected_ff[e]
native=summary['certified_native'];assert native['status']=='pass'and len(native['cohorts'])==6
for c in native['cohorts']:
    rows={r['engine']:r for r in c['rows']};assert set(rows)==set(range(5))
    assert len({r['numeric_retirement_sha256']for r in rows.values()})==1
    assert all(r['neurons']==635904 for r in rows.values())if c['kind']!='main'else c['exhaustive_scalar_pairs']==238592
    assert len({rows[e]['service_clocks']for e in(1,2,3)})==1
    assert rows[0]['requests']==rows[4]['requests']and rows[0]['service_clocks']==rows[4]['service_clocks']
    if c['kind']!='main':
        assert all(r['original_LIF_numeric_retirements_match']for r in rows.values())
        assert all(v['state_spike_count_class_disagreements']==0 for r in rows.values()for v in r['actual_retired_feedback'])
energy={r['engine']:r for r in summary['original_generic_U11_energy']['engines']}
assert set(e for e,r in energy.items()if r['accepted_energy'])=={0,2,3,4}
assert energy[1]['status']=='timed_functional_failure'
for e in(0,2,3,4):
    r=energy[e];a=read(r['power_audit_file'])
    assert sha(r['power_audit_file'])==r['power_audit_sha256']
    calculated=a['dynamic_power_W']*a['native_interval_audit']['duration_ps']/635904
    assert abs(calculated-r['estimated_dynamic_energy_pJ_per_scalar_update'])<1e-12
    assert a['fixture_FF']==290
assert summary['histogram_repair']['every_other_result_value_exactly_preserved']
assert summary['histogram_repair']['policy_histograms_validated']==216
assert all(c['fixed8_service_clocks']<=c['union_service_clocks']<=c['absolute_service_clocks']for c in summary['software_range_cohorts'])
adex=summary['adex_component_screen'];assert len(adex['rows'])==8
assert len(adex['failures'])==7 and sum(r['scalar_vector_spike_steps_equal']for r in adex['rows'])==6
diag=summary['fixed8_mapped_functional_diagnostic'];assert not diag['accepted_energy']and not diag['accepted_timing_result']
assert len(summary['current_width_screen']['rows'])==48
result=dict(status='pass_independent_extended_delivery_verification',files_verified=len(manifest['files']),
    manifest_sha256=sha(OUT/f'{STEM}.manifest.json'),summary_sha256=sha(OUT/f'{STEM}.summary.json'),
    adaptive_core=hardware[0]['core'],strongest_fixed_native_hybrid=hardware[2]['core'],
    accepted_original_energy_engines=[0,2,3,4],retained_timed_failure_engine=1,
    new_specialized_energy_measured=False,broader_trained_model_benchmarks_executed=False,
    scope='Closed preserved evidence and consistency of reported results; no new board/full-SNN/AdEx or publication-readiness claim')
print(json.dumps(result,indent=2),flush=True)
