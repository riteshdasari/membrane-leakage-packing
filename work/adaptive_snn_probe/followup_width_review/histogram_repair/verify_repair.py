"""Require exact equality of all retained non-histogram screen data."""
from pathlib import Path
from copy import deepcopy
import hashlib,json
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()
target=P/'acceptance.json'
assert not target.exists()
plan=json.loads((P/'repair_plan.json').read_text())
for path,expected in plan['source_sha256'].items():assert sha(path)==expected,path
original=json.loads((ROOT/'range_horizon_trial/results.json').read_text())
corrected=json.loads((P/'results.json').read_text())
old_plan=json.loads((ROOT/'range_horizon_trial/predeclared_plan.json').read_text())
new_plan=json.loads((P/'predeclared_plan.json').read_text())
assert corrected['predeclared_plan_sha256']==sha(P/'predeclared_plan.json')
for record in(original,corrected,old_plan,new_plan):
    for path,expected in record['source_sha256'].items():assert sha(path)==expected,path
for key in old_plan:
    if key!='source_sha256':assert canonical(old_plan[key])==canonical(new_plan[key]),key
assert set(original)==set(corrected)
for key in original:
    if key not in('rows','source_sha256','predeclared_plan_sha256'):
        assert canonical(original[key])==canonical(corrected[key]),key
assert len(original['rows'])==len(corrected['rows'])==72
differences=[]
for old,new in zip(original['rows'],corrected['rows']):
    stripped=deepcopy(old);new_stripped=deepcopy(new)
    key=(old['seed'],old['beta'],old['timesteps'])
    assert key==(new['seed'],new['beta'],new['timesteps'])
    for policy in old['policy_stats']:
        old_hist=stripped['policy_stats'][policy].pop('take_histogram')
        hist=new_stripped['policy_stats'][policy].pop('take_histogram')
        stats=new['policy_stats'][policy]
        assert sum(hist.values())==stats['requests'],(key,policy)
        assert sum(int(n)*count for n,count in hist.items())==stats['updates'],(key,policy)
        if hist!=old_hist:
            assert old['timesteps']in(32,128)
            differences.append(dict(seed=key[0],beta=key[1],timesteps=key[2],policy=policy,
                                    original_requests_from_histogram=sum(old_hist.values()),
                                    corrected_requests_from_histogram=sum(hist.values())))
    assert canonical(stripped)==canonical(new_stripped),key
assert len(differences)==144
sources=dict(plan['source_sha256'])
sources[str((P/'repair_plan.json').resolve())]=sha(P/'repair_plan.json')
artifacts={str((P/n).resolve()):sha(P/n)for n in('results.json','predeclared_plan.json','repair.log')}
result=dict(status='pass',rows_replayed=72,policy_histograms_validated=216,
            corrected_earlier_horizon_histograms=144,unchanged_T256_histograms=72,
            every_other_result_value_exactly_preserved=True,
            unchanged_fields=['Requests and analytic service','Shared-wide tail update scalar counts','All360 and first48 variant accuracies',
                              'All finite/indefinite range certificates','Numeric retirement hashes','Analytic storage and fixed8 controls'],
            corrections=differences,source_sha256=sources,artifact_sha256=artifacts,
            scope='Software snapshot repair; no new architecture/native/route/power claim; fixed8 histogram remains an unpopulated zero placeholder')
target.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items()if k not in('corrections','source_sha256','artifact_sha256')},indent=2),flush=True)
