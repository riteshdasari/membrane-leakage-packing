"""Create an additive K2 consumer; retain every native/timing/power gate."""
from pathlib import Path
import ast,hashlib,importlib.util,json,sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;W=P.parent;A=W.parent/'activity'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    source=P/'prepare_and_run_profiled.py';target=P/'prepare_and_run_profiled_capture_v2.py'
    text=source.read_text();new=text
    old="""    capturesource=str((W.parent/'activity/capture_ottt_representative.py').resolve())
    assert r['source_sha256'][capturesource]==known['source_sha256'][capturesource]==sha(capturesource)"""
    revised="""    activity=W.parent/'activity'
    protocolfile=activity/'ottt_capture_preparation_v2.json'
    reviewfile=activity/'ottt_capture_v2_independent_source_review.json'
    protocol=read(protocolfile);review=read(reviewfile)
    assert review['status']=='pass_independent_second_capture_source_review'
    verify(review['source_sha256']);verify(review['artifact_sha256'])
    assert protocol['status']=='predeclared_before_second_capture' and protocol['windows_per_nonzero_frame']==2
    assert protocol['fixed_seed']==417839 and protocol['target_scalar_operands']==262144 and protocol['distribution_gates']==GATES
    verify(protocol['unchanged_prior_pins'])
    basecapture=str((activity/'capture_ottt_representative.py').resolve())
    capturesource=str((activity/'capture_ottt_representative_v2.py').resolve())
    assert known['source_sha256'][basecapture]==protocol['base_source_sha256']==sha(basecapture)
    assert r['source_sha256'][capturesource]==protocol['new_source_sha256']==sha(capturesource)
    assert set(r['source_sha256'])==set(protocol['unchanged_prior_pins'])|{capturesource}
    for filename,pin in protocol['unchanged_prior_pins'].items():assert r['source_sha256'][filename]==pin"""
    assert new.count(old)==1;new=new.replace(old,revised)
    changes=[dict(original=old,replacement=revised)]
    for old,newtext in [('K=min(8,source[\'nonzero\'])','K=min(2,source[\'nonzero\'])'),
        ("len(js)==min(8,sourceframes[key]['nonzero'])","len(js)==min(2,sourceframes[key]['nonzero'])"),
        ("Path(__file__),resultfile,routefile,W/'domain_acceptance_glif_v2.json'",
         "Path(__file__),resultfile,routefile,W/'domain_acceptance_glif_v2.json',W.parent/'activity/ottt_capture_preparation_v2.json',W.parent/'activity/ottt_capture_v2_independent_source_review.json',P/'capture_v2_consumer_source_checks.json'"),
        ("Path(__file__),P/'cohort_acceptance.json'","Path(__file__),P/'capture_v2_consumer_source_checks.json',P/'cohort_acceptance.json'")]:
        assert new.count(old)==1,(old,new.count(old));new=new.replace(old,newtext);changes.append(dict(original=old,replacement=newtext))
    ast.parse(new)
    if target.exists():assert target.read_text()==new
    else:target.write_text(new,encoding='utf-8')
    reverse=new
    for c in reversed(changes):
        assert reverse.count(c['replacement'])==1;reverse=reverse.replace(c['replacement'],c['original'])
    assert reverse==text
    spec=importlib.util.spec_from_file_location('capture_v2_consumer_source_test',target)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    first=A/'ottt_random_stratified_a0/results.json'
    try:module.verify_capture(first)
    except AssertionError as error:
        assert 'No representative energy from failed distribution capture.' in str(error)
        rejected_first=True
    else:raise AssertionError('First failed capture was incorrectly admitted.')
    assert not(P/'cohort_acceptance.json').exists() and not(P/'domain_acceptance_ottt_representative.json').exists()
    protocol=A/'ottt_capture_preparation_v2.json';review=A/'ottt_capture_v2_independent_source_review.json'
    report=dict(status='pass_additive_K2_capture_consumer_source_checks',changes=changes,
        exact_reverse_substitutions_reproduce_frozen_profiled_consumer=True,
        first_failed_capture_rejected_before_native_or_energy_admission=rejected_first,
        old_consumer_and_all_old_evidence_unmodified=True,
        all_six_distribution_thresholds_unchanged=True,source_model_and_route_pins_unchanged=True,
        native_engine_index_mapping_unchanged=[5,1,6],native_or_timing_or_power_checks_changed=False,
        admitted_second_capture=False,inference_launched=False,vendor_jobs_launched=False,
        source_sha256={str(Path(__file__).resolve()):sha(__file__),str(source):sha(source),str(protocol):sha(protocol),str(review):sha(review),str(first):sha(first)},
        artifact_sha256={str(target):sha(target)},
        limitation='Source-only preparation. The new capture must still pass exact feedback and every unchanged distribution gate before any native or energy job.')
    receipt=P/'capture_v2_consumer_source_checks.json';assert not receipt.exists();receipt.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],runner=str(target),receipt=str(receipt),failed_a0_admitted=False)))


if __name__=='__main__':main()
