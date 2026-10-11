"""Additive stage-specific RAM profile and explicit accepted-replay reuse.

Imports the frozen certified recovery child. Arithmetic, SDF timing controls,
golden rows, SAIF interval, physical-net annotation and power checks are intact.
Every vendor job retains the standard sampled memory metadata plus its profile.
"""
from pathlib import Path
import argparse,importlib.util,json,sys,time
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parent.parent/'selective_energy_trial'))
import run_selective_energy as b


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def checked(d):b.verify(d.get('source_sha256',{}));b.verify(d.get('artifact_sha256',{}))


def main():
    parser=argparse.ArgumentParser(add_help=False)
    parser.add_argument('--representative',action='store_true')
    parser.add_argument('--reuse-derived-export-dir')
    parser.add_argument('--reuse-replay-dir')
    options,remaining=parser.parse_known_args()
    assert bool(options.reuse_replay_dir)==bool(options.reuse_derived_export_dir)
    sys.argv=[sys.argv[0],*remaining]
    childfile=P/('run_energy_recovery_representative_child.py' if options.representative else 'run_energy_recovery_child.py')
    child=load(childfile,'frozen_profiled_recovery_child')
    inventoryfile=P/'completed_stage_memory_audit_a0.json';inventory=b.read(inventoryfile);checked(inventory)
    assert inventory['status']=='pass_completed_vendor_job_memory_inventory'
    thresholds={'export':1.70,'power_annotation':1.70,'xelab':.80,'xsim':.80,'xvlog':.45}
    for stage,threshold in thresholds.items():
        assert threshold-inventory['summary'][stage]['largest_peak_job']['peak_RSS_sum_GiB']>=.20
    pins=b.pins([Path(__file__).resolve(),childfile,inventoryfile,P/'certify_energy_export.py'])
    original_bind=child.bind
    def bind(args):
        m,root,reused,extra=original_bind(args)
        extra=extra|pins
        original_sources=m.sources;m.sources=lambda:original_sources()|pins
        if options.reuse_replay_dir:
            replay=Path(options.reuse_replay_dir).resolve();export=Path(options.reuse_derived_export_dir).resolve()
            assert replay.is_relative_to(root/'hardware') and export.is_relative_to(root/'hardware')
            assert replay!=m.path('replay',args.engine) and export!=m.path('export',args.engine)
            d=b.read(replay/'replay_checks.json');checked(d)
            assert d['status']=='timing_pass_activity_pending' and d['B']==16 and d['engine']==args.engine and d['clock_period_ns']==12
            check,row,trace,total=m.native(args.engine);rd,hw=m.route(args.engine)
            assert Path(d['native_check_file']).resolve()==check and d['native_check_sha256']==b.sha(check)
            assert d['native_row']==row and d['trace_sha256']==b.sha(trace) and d['replay_rows_checked']==d['trace_count']==total
            assert d['valid_rows_checked']==row['requests'] and Path(d['hardware_file']).resolve()==rd/'hardware.json'
            assert Path(d['export_artifacts_file']).resolve()==export/'artifacts.json'
            assert Path(d['golden_check_file']).resolve()==m.path('golden',args.engine)/'golden_checks.json'
            binder=load(P/'certify_energy_export.py','profiled_export_reuse_gate');exportgate=binder.verify(export)
            auditfile=root/('audit_power16_rep3_12_certified.py' if options.representative else ('audit_power16_lutceil_12_certified.py' if args.engine==7 else 'audit_power16_12_certified.py'))
            auditor=load(auditfile,'profiled_replay_reuse_gate')
            interval=auditor.replay(replay)
            assert interval['status']=='pass' and interval['engine']==args.engine and interval['scalar_updates']==row['neurons'] and interval['requests']==row['requests']
            jobs=[replay/f'tool_{i}.job.json' for i in range(4)]
            for jobfile in jobs:
                job=b.read(jobfile);b.verify(job['source_sha256'])
                assert job['returncode']==0 and job['log_sha256']==b.sha(jobfile.with_name(jobfile.name.replace('.job.json','.log')))
            # Every original launch pin remains identical to the selected source.
            producer=str(Path(m.__file__).resolve())
            assert d['source_sha256'][producer]==b.sha(producer)
            extra=extra|b.pins([replay/'replay_checks.json',export/'artifacts.json',export/'export_binding_certificate.json',export/'sdf_structure_certificate.json',
                              replay/'activity_named.saif',replay/'activity_named.names.json',*jobs,*map(Path,d['artifact_sha256'])])
            current_sources=m.sources;m.sources=lambda:current_sources()|extra
            original_path=m.path
            m.path=lambda label,e:replay if label=='replay' and e==args.engine else(export if label=='export' and e==args.engine else original_path(label,e))
            reused+= [dict(stage='export',directory=str(export),accepted_export_gate=exportgate),
                      dict(stage='replay',directory=str(replay),replay_receipt_file=str(replay/'replay_checks.json'),
                           replay_receipt_sha256=b.sha(replay/'replay_checks.json'),independent_replay_gate=interval,vendor_jobs_rerun=False)]
        def tool(command,wd,label,stamps,gate=1.2):
            executable=Path(command[0]).name.lower()
            if executable=='vivado.bat':stage='export' if label=='export' else 'power_annotation'
            else:stage={'xelab.bat':'xelab','xsim.bat':'xsim','xvlog.bat':'xvlog'}.get(executable)
            threshold=thresholds.get(stage,gate)
            baseline=inventory['summary'][stage]['largest_peak_job'] if stage else None
            profile=dict(status='profile_selected_before_launch',stage=stage,original_requested_gate_GiB=gate,
                required_free_GiB_at_launch=threshold,extra_wait_margin_GiB=0,
                observed_historical_peak_RSS_sum_GiB=baseline['peak_RSS_sum_GiB'] if baseline else None,
                reserve_above_observed_peak_GiB=threshold-baseline['peak_RSS_sum_GiB'] if baseline else None,
                historical_peak_job_file=baseline['job_file'] if baseline else None,
                historical_peak_job_sha256=baseline['job_sha256'] if baseline else None,
                inventory_file=str(inventoryfile),inventory_sha256=b.sha(inventoryfile),
                profile_adapter_file=str(Path(__file__).resolve()),profile_adapter_sha256=b.sha(__file__),
                route_threshold_changed=False,arithmetic_or_timing_checks_changed=False,
                limitation='Historical one-second sampled RSS sums may miss short peaks and double-count shared pages; reserve is empirical, not a fit guarantee.')
            profilefile=Path(wd)/(label+'.memory_profile.json');assert not profilefile.exists();b.write(profilefile,profile)
            stamps=stamps|pins|b.pins([profilefile])
            while b.free()<=threshold:time.sleep(5)
            result=b.job([str(x).replace('\\','/') for x in command],wd,label,stamps,threshold)
            return result
        m.tool=tool
        return m,root,reused,extra
    child.bind=bind
    print('ADDITIVE RAM PROFILE',thresholds,'GiB; no route threshold changes',flush=True)
    child.main()


if __name__=='__main__':main()
