"""Record completed E0 reports after strict source restoration, then audit."""
from pathlib import Path
import importlib.util
import sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P))
import run_energy as run
wd=run.R/'power_e0_a0';stamps=run.read(wd/'provenance.json');run.verify(stamps)
job=run.read(wd/'annotation.job.json');assert job['returncode']==0
assert 'FRONTIER_ANNOTATION_POWER PASS E0'in(wd/'annotation.log').read_text()
assert not(wd/'evidence.json').exists()
route,hw=run.route_data(0);replaydir=run.R/'replay_e0_a0'
d=run.read(replaydir/'replay_checks.json');run.verify(d['source_sha256']);run.verify(d['artifact_sha256'])
named=replaydir/'activity_named.saif';names=run.read(named.with_suffix('.names.json'))
assert names['target_sha256']==run.sha(named)and names['source_sha256']==d['saif']['saif_sha256']
assert run.sha(run.J/'run_trial.py')=='390c6cb743299d9bb7b695582e644d5c5754996f52542396524851218312a160'
stamps|=run.pins([Path(__file__),P/'audit_power_v2.py',P/'repair_v2_preparation.json'])
run.write(wd/'evidence.json',dict(status='reports generated; independent audit required',engine=0,
    design_top=hw['top'],replay_dir=str(replaydir),hardware_file=str(route/'hardware.json'),
    saif_file=str(named),source_sha256=stamps,artifact_sha256=run.pins(p for p in wd.iterdir()if p.is_file()),
    duration_seconds=d['saif']['duration_seconds'],neurons=635904,
    record_recovery='Vendor annotation returned0 and complete marker before transient runner hash failed. Exact original source bytes restored; all original sources and simulator artifacts reverified. New record only; reports unchanged.'))
spec=importlib.util.spec_from_file_location('strict_energy_e0_v2',P/'audit_power_v2.py')
auditor=importlib.util.module_from_spec(spec);spec.loader.exec_module(auditor)
checked=auditor.annotation(wd)
target=wd/'power_audit_v2.json';assert not target.exists();run.write(target,checked)
print('STRICT E0 RECOVERED ENERGY',checked['estimated_dynamic_energy_pJ_per_scalar_update'],flush=True)
