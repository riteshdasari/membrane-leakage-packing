"""Read-only historical sampled memory accounting; no threshold changes or jobs."""
from pathlib import Path
import hashlib,json,re,sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;ROOT=P.parent.parent


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    rows=[];rejected=[]
    folders=['selective_energy_trial','natural_energy_trial','sequential_paper_trial','residue_frontier_f5_trial','validation_close/width16']
    for folder in folders:
        for file in (ROOT/folder).rglob('*.job.json'):
            d=json.loads(file.read_text());argv=d.get('argv',[])
            if not argv or d.get('returncode')!=0:continue
            executable=Path(argv[0]).name.lower()
            stage=None
            if executable=='vivado.bat' and file.name=='annotation.job.json':stage='power_annotation'
            elif executable=='vivado.bat' and file.name=='export.job.json':stage='export'
            elif executable=='xsim.bat':stage='xsim'
            elif executable=='xelab.bat':stage='xelab'
            elif executable=='xvlog.bat':stage='xvlog'
            if not stage:continue
            log=file.with_name(file.name.replace('.job.json','.log'))
            if not log.exists() or sha(log)!=d.get('log_sha256'):
                rejected.append(dict(file=str(file),reason='Missing or changed job log'));continue
            wd=file.parent;acceptance=None;meaningful=False
            if stage=='power_annotation':
                acceptance=wd/'power_audit.json'
                if acceptance.exists():
                    a=json.loads(acceptance.read_text());meaningful=a.get('status')=='pass'
            elif stage=='export':
                acceptance=wd/'artifacts.json'
                meaningful=acceptance.exists() and (wd/'routed.v').exists() and (wd/'routed.sdf').exists()
                if meaningful:
                    artifacts=json.loads(acceptance.read_text());meaningful=all(Path(path).exists() and sha(path)==pin for path,pin in artifacts.items())
            else:
                for name in ('replay_checks.json','golden_checks.json','native_checks.json','acceptance.json'):
                    if (wd/name).exists():
                        a=json.loads((wd/name).read_text());status=a.get('status')
                        if status in ('pass','timing_pass_activity_pending','pass_timing_and_saif'):
                            acceptance=wd/name;meaningful=True;break
            if not meaningful:continue
            if not all(key in d for key in ('sampled_peak_tool_tree_RSS_sum_GiB','sampled_min_free_GiB','free_GiB_at_start')):continue
            rows.append(dict(stage=stage,job_file=str(file),job_sha256=sha(file),log_file=str(log),log_sha256=sha(log),
                historical_acceptance_file=str(acceptance),historical_acceptance_sha256=sha(acceptance),
                peak_descendant_RSS_sum_GiB=d['sampled_peak_tool_tree_RSS_sum_GiB'],min_free_GiB=d['sampled_min_free_GiB'],
                free_at_start_GiB=d['free_GiB_at_start'],seconds=d['seconds'],sample_count=d['memory_samples'],
                sample_period_seconds=d['sample_period_seconds'],scope=d['memory_scope']))
    summary={}
    for stage in sorted({r['stage'] for r in rows}):
        values=[r for r in rows if r['stage']==stage]
        summary[stage]=dict(accepted_historical_jobs=len(values),largest_sampled_peak_job=max(values,key=lambda r:r['peak_descendant_RSS_sum_GiB']),
            lowest_sampled_free_job=min(values,key=lambda r:r['min_free_GiB']),
            lowest_starting_free_job=min(values,key=lambda r:r['free_at_start_GiB']))
    report=dict(status='pass_read_only_historical_sampled_memory_inventory',summary=summary,all_jobs=rows,rejected_logs=rejected,
        source_sha256={str(Path(__file__).resolve()):sha(__file__)},
        artifact_sha256={r['job_file']:r['job_sha256'] for r in rows},vendor_jobs_launched=False,thresholds_changed=False,
        limitations=['Sampled descendant RSS sums may double-count shared pages and may miss between-sample peaks.',
            'Historical acceptance records select completed functional stages, not current full evidence equivalence.',
            'These observations do not prove a lower RAM threshold safe for an unseen stage; source fixture scale and available memory headroom must also be considered.',
            'The same old 2.3 GiB numeric gate was used for route/export/annotation, but the sampled measurements show their memory demands separately.'])
    dest=P/'historical_stage_memory_audit_a0.json';assert not dest.exists();dest.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],summary={k:dict(jobs=v['accepted_historical_jobs'],max_peak_GiB=v['largest_sampled_peak_job']['peak_descendant_RSS_sum_GiB'],min_free_GiB=v['lowest_sampled_free_job']['min_free_GiB'],min_start_free_GiB=v['lowest_starting_free_job']['free_at_start_GiB'],max_peak_file=v['largest_sampled_peak_job']['job_file'])for k,v in summary.items()},report=str(dest)),indent=2))


if __name__=='__main__':main()
