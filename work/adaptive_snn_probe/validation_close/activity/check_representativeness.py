"""Apply predeclared distribution gates to the single selected random-stratified seed."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    planpath=HERE/'representativeness_gate_plan.json'
    plan=json.loads(planpath.read_text());g=plan['distribution_gates']
    root=HERE/'random_stratified_v2'
    r=json.loads((root/'results.json').read_text());a=json.loads((root/'acceptance.json').read_text())
    assert r['status']==a['status']=='pass'
    assert a['result_sha256']==sha(root/'results.json')
    d=r['distribution_comparisons'];s=r['sample_issues_by_engine'];f=r['full']['issues']
    sample_overhead=s[5]/s[1]-1
    full_overhead=f['adaptive_post']/f['fixed_split2']-1
    observed=dict(weighted_beta_total_variation_at_most=d['beta']['weighted_total_variation'],
        weighted_previous_spike_total_variation_at_most=d['previous_spike']['weighted_total_variation'],
        weighted_membrane_coarse64_total_variation_at_most=d['U_coarse']['weighted_total_variation'],
        absolute_narrow9_fraction_difference_at_most=abs(r['sample_narrow9_fraction']-r['full_narrow9_fraction']),
        unweighted_layer_time_context_total_variation_at_most=d['layer_time_context']['unweighted_total_variation'],
        absolute_adaptive_vs_fixed_split_issue_overhead_fraction_difference_at_most=abs(sample_overhead-full_overhead))
    checks={key:dict(observed=value,limit=g[key],pass_gate=value<=g[key])for key,value in observed.items()}
    passed=all(v['pass_gate']for v in checks.values())
    result=dict(status='pass'if passed else'fail_distribution_representativeness',checks=checks,
        sample_adaptive_vs_fixed_split_issue_overhead_fraction=sample_overhead,
        complete64_adaptive_vs_fixed_split_issue_overhead_fraction=full_overhead,
        sample_operations=r['sample_operations'],sample_windows=r['sample_windows'],
        boundary_totals=r['boundary_totals'],selected_method='random_stratified_v2 fixed seed417839',
        interpretation=plan['interpretation'],
        source_sha256={str(p):sha(p)for p in[Path(__file__),planpath,HERE/'random_v2_preparation.json',root/'plan.json',root/'results.json',root/'acceptance.json']})
    (root/'representativeness_acceptance.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)
if __name__=='__main__':main()
