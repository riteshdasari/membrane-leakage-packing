"""Inventory completed vendor jobs; distinguish energy acceptance from tool success."""
from pathlib import Path
import hashlib,json,sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;ROOT=P.parent.parent
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    rows=[]
    for file in ROOT.rglob('*.job.json'):
        d=json.loads(file.read_text());argv=d.get('argv',[])
        if not argv or d.get('returncode')!=0:continue
        exe=Path(argv[0]).name.lower()
        stage={'xelab.bat':'xelab','xsim.bat':'xsim','xvlog.bat':'xvlog'}.get(exe)
        if exe=='vivado.bat':stage={'annotation.job.json':'power_annotation','export.job.json':'export'}.get(file.name)
        if not stage:continue
        log=file.with_name(file.name.replace('.job.json','.log'))
        if not log.exists() or sha(log)!=d.get('log_sha256'):continue
        keys=('sampled_peak_tool_tree_RSS_sum_GiB','sampled_min_free_GiB','free_GiB_at_start')
        if not all(k in d for k in keys):continue
        acceptance=None
        for name in ('power_audit.json','replay_checks.json','golden_checks.json','native_checks.json','acceptance.json'):
            f=file.parent/name
            if f.exists() and json.loads(f.read_text()).get('status') in ('pass','timing_pass_activity_pending','pass_timing_and_saif'):
                acceptance=f;break
        rows.append(dict(stage=stage,job_file=str(file),job_sha256=sha(file),log_file=str(log),log_sha256=sha(log),
            returncode=0,peak_RSS_sum_GiB=d[keys[0]],min_free_GiB=d[keys[1]],start_free_GiB=d[keys[2]],
            seconds=d['seconds'],samples=d['memory_samples'],scope=d['memory_scope'],
            independent_acceptance_file=str(acceptance) if acceptance else None,
            independent_acceptance_sha256=sha(acceptance) if acceptance else None,
            energy_accepted_by_this_inventory=False))
    summary={}
    for stage in sorted({r['stage'] for r in rows}):
        rr=[r for r in rows if r['stage']==stage]
        summary[stage]=dict(completed_successful_jobs=len(rr),largest_peak_job=max(rr,key=lambda r:r['peak_RSS_sum_GiB']),
            smallest_start_free_job=min(rr,key=lambda r:r['start_free_GiB']),smallest_free_job=min(rr,key=lambda r:r['min_free_GiB']))
    report=dict(status='pass_completed_vendor_job_memory_inventory',summary=summary,all_jobs=rows,
        source_sha256={str(Path(__file__).resolve()):sha(__file__)},artifact_sha256={r['job_file']:r['job_sha256'] for r in rows},
        thresholds_changed=False,vendor_jobs_launched=False,
        limitations=['All rows have returncode zero and unchanged saved logs; this does not establish complete energy acceptance.',
            'RSS sums may double-count shared pages; one-second sampling may miss short peaks.',
            'No unseen run is guaranteed to fit based on history; the launch profile must reserve headroom and record its new observations.'])
    dest=P/'completed_stage_memory_audit_a0.json';assert not dest.exists();dest.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],summary={k:dict(completed_jobs=v['completed_successful_jobs'],peak_GiB=v['largest_peak_job']['peak_RSS_sum_GiB'],peak_job=v['largest_peak_job']['job_file'],minimum_start_free_GiB=v['smallest_start_free_job']['start_free_GiB'])for k,v in summary.items()},report=str(dest)),indent=2))


if __name__=='__main__':main()
