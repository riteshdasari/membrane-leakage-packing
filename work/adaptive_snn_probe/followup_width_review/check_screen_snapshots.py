"""Validate archived schedule snapshot fields without modifying the screen."""
from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent
source=P.parent/'range_horizon_trial/results.json'
screen=json.loads(source.read_text())
passed=[];failed=[]
for row in screen['rows']:
    for name,stats in row['policy_stats'].items():
        count=sum(stats['take_histogram'].values())
        updates=sum(int(take)*n for take,n in stats['take_histogram'].items())
        value=dict(seed=row['seed'],beta=row['beta'],timesteps=row['timesteps'],policy=name,
                   requests=stats['requests'],updates=stats['updates'],histogram_requests=count,
                   histogram_updates=updates)
        (passed if (count==stats['requests'] and updates==stats['updates']) else failed).append(value)
        assert stats['service_clocks_one_edge_analytic']==stats['requests']+stats['groups']
        assert stats['updates']==48*row['timesteps']*138
        assert stats['groups']==48*row['timesteps']*2
    fixed=row['fixed8']
    assert fixed['service_clocks_one_edge_analytic']==fixed['requests']+fixed['groups']
    assert fixed['updates']==48*row['timesteps']*138
    assert fixed['groups']==48*row['timesteps']*2
    assert fixed['requests']==48*row['timesteps']*(16+2)
assert len(passed)==72 and len(failed)==144
assert {r['timesteps']for r in passed}=={256}
assert {r['timesteps']for r in failed}=={32,128}
target=P/'screen_snapshot_checks.json'
assert not target.exists()
result=dict(status='partial_reporting_failure',valid_policy_histograms=len(passed),
            invalid_policy_histograms=len(failed),invalid=failed,
            requests_service_updates_group_fields='Internally consistent in all 72 rows; scalar snapshots unaffected by nested histogram aliasing',
            source_sha256={str(source):hashlib.sha256(source.read_bytes()).hexdigest(),
                           str(Path(__file__).resolve()):hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
target.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items()if k not in('invalid','source_sha256')},indent=2))
print('EXAMPLE',json.dumps(next(r for r in failed if r['seed']==0 and r['beta']==248 and r['timesteps']==32 and r['policy']=='absolute_U8')))
