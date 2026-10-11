"""Preserve accepted golden/export artifacts; run a fresh strict energy attempt.

The frozen original runner supplies every simulation, SDF, SAIF and power check.
This adapter only binds explicit reused directories and records their checked
provenance. No jobs run without --run. No original evidence is modified.
"""
from pathlib import Path
import argparse, importlib.util, math, re, sys, time
sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent
ALT = P / 'lutceil_e7'
REP = P / 'ottt_representative'
ROOT = P.parent.parent
sys.path.insert(0, str(ROOT / 'selective_energy_trial'))
import run_selective_energy as b


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def checked(record):
    b.verify(record.get('source_sha256', {}))
    b.verify(record.get('artifact_sha256', {}))


def bind(args):
    root = REP if args.workload == 'ottt_representative' else (ALT if args.engine == 7 else P)
    producer = root / ('run_energy16_rep3_12.py' if args.workload == 'ottt_representative' else ('run_energy16_lutceil_12.py' if args.engine == 7 else 'run_energy16_12.py'))
    m = load(producer, 'unchanged_energy_recovery_producer')
    m.ARGS = argparse.Namespace(workload=args.workload, native_acceptance=str(Path(args.native_acceptance).resolve()),
        route_dir_template=args.route_dir_template, engines=str(args.engine), attempt=args.attempt)
    assert '{engine}' in args.route_dir_template and args.engine in range(8)
    assert args.workload != 'glif' or args.engine != 6
    assert args.workload != 'ottt' or args.engine != 7
    assert args.workload != 'ottt_representative' or args.engine in (5,1,6)
    rd, hw = m.route(args.engine)
    assert hw['part'] == 'xc7a100tcsg324-1' and hw['latency_advancing_edges'] == 2
    assert hw['full_fixture']['FF'] - hw['core']['FF'] == 94
    assert all(math.isfinite(hw[k]) and hw[k] >= 0 for k in ('WNS_ns','WHS_ns','boundary_WNS_ns','boundary_WHS_ns'))
    check, row, trace, total = m.native(args.engine)
    oldsources = m.sources
    basepins = oldsources()
    selected = {}
    receipts = []
    extra = [Path(__file__).resolve(), producer, root / ('audit_power16_rep3_12_certified.py' if args.workload == 'ottt_representative' else ('audit_power16_lutceil_12_certified.py' if args.engine == 7 else 'audit_power16_12_certified.py')),
             P/'cached_energy_auditor_source_equivalence.json',P/'certified_energy_auditor_source_checks.json',P/'certify_energy_export.py',
             rd/'hardware.json', rd/'design.dcp']
    for manifestfile in (P/'cached_energy_auditor_source_equivalence.json',P/'certified_energy_auditor_source_checks.json'):
        manifest=b.read(manifestfile);checked(manifest)
        extra += [*map(Path,manifest['source_sha256']),*map(Path,manifest['artifact_sha256'])]
    for label, argument in [('golden',args.reuse_golden_dir), ('export',args.reuse_export_dir)]:
        if not argument:
            continue
        directory = Path(argument).resolve()
        assert directory.is_relative_to(root/'hardware') and directory != m.path(label,args.engine)
        if label == 'golden':
            f = directory/'golden_checks.json'
            d = b.read(f); checked(d)
            assert (d['status'],d['B'],d['engine']) == ('pass',16,args.engine)
            assert d['trace_sha256'] == b.sha(trace)
            assert d['source_sha256'][str(check)] == b.sha(check)
            assert d['source_sha256'][str(producer)] == b.sha(producer)
            assert d['replay_rows_checked'] == total and d['valid_rows_checked'] == row['requests']
            start = 132000 + row['first_accept']*12000 - 1
            duration = (row['last_retire']-row['first_accept']+3)*12000
            assert (d['roi_start_ps'],d['roi_end_ps'],d['roi_duration_ps']) == (start,start+duration,duration)
            jobs = [directory/f'tool_{i}.job.json' for i in range(4)]
            for j in jobs:
                job = b.read(j); b.verify(job['source_sha256'])
                assert job['returncode'] == 0 and Path(job['cwd']).resolve() == directory
                assert job['log_sha256'] == b.sha(j.with_name(j.name.replace('.job.json','.log')))
            text = (directory/'tool_3.log').read_text(errors='replace')
            assert f'FRONTIER_ROUTE_REPLAY PASS E{args.engine} ROWS {total} CHECKED {total} VALID_ROWS {row["requests"]}' in text
            for name,pin in basepins.items():
                assert d['source_sha256'].get(name) == pin, ('Golden source differs',name)
            extra += [f,*jobs,*map(Path,d['artifact_sha256'])]
            receipt = dict(stage=label,directory=str(directory),acceptance_file=str(f),sha256=b.sha(f),
                           rows=total,valid_rows=row['requests'],trace_file=str(trace),trace_sha256=b.sha(trace))
        else:
            f = directory/'artifacts.json'; artifacts = b.read(f); b.verify(artifacts)
            provenance = b.read(directory/'provenance.json'); b.verify(provenance)
            assert provenance[str(rd/'hardware.json')] == b.sha(rd/'hardware.json')
            assert provenance[str(rd/'design.dcp')] == b.sha(rd/'design.dcp')
            for name,pin in basepins.items():
                assert provenance.get(name) == pin, ('Export source differs',name)
            jobfile = directory/'export.job.json'; job = b.read(jobfile); b.verify(job['source_sha256'])
            assert job['returncode'] == 0 and Path(job['cwd']).resolve() == directory
            assert job['log_sha256'] == b.sha(directory/'export.log')
            assert str(rd/'design.dcp').replace('\\','/') in job['argv']
            assert 'FRONTIER_EXPORT PASS' in (directory/'export.log').read_text(errors='replace')
            assert f'module {hw["top"]}' in (directory/'routed.v').read_text()
            assert set(artifacts) == {str(directory/name) for name in ('routed.v','routed.sdf','provenance.json')}
            extra += [f,jobfile,directory/'export.log',*map(Path,artifacts)]
            receipt = dict(stage='export_raw',directory=str(directory),artifact_manifest=str(f),sha256=b.sha(f),
                           hardware_file=str(rd/'hardware.json'),hardware_sha256=b.sha(rd/'hardware.json'),
                           dcp_file=str(rd/'design.dcp'),dcp_sha256=b.sha(rd/'design.dcp'))
        if label=='golden': selected[label] = directory
        else: selected['export_raw']=directory
        receipts.append(receipt)
    extra = b.pins(extra)
    original_path = m.path
    exporting_raw=[False]
    def revised_path(label,e):
        if e==args.engine and label=='export' and exporting_raw[0]:return original_path('export_raw',e)
        return selected[label] if e==args.engine and label in selected else original_path(label,e)
    m.path = revised_path
    m.sources = lambda: oldsources() | extra
    original_export=m.export
    def certified_export(e):
        if 'export_raw' in selected:
            raw=selected['export_raw']
        else:
            exporting_raw[0]=True
            try:original_export(e)
            finally:exporting_raw[0]=False
            raw=original_path('export_raw',e)
        binder=load(P/'certify_energy_export.py','energy_recovery_export_binder')
        binder.create(raw,original_path('export',e),rd/'hardware.json',m.sources())
        print('ENERGY RECOVERY CERTIFIED EXPORT PASS',args.workload,e,flush=True)
    m.export=certified_export
    def certified_power(e):
        routed,hardware=m.route(e);rp=m.path('replay',e);d=b.read(rp/'replay_checks.json')
        assert d['status']=='timing_pass_activity_pending';checked(d)
        wd=m.directory('power',e);named=rp/'activity_named.saif'
        stamps=m.sources()|b.pins([named,named.with_suffix('.names.json'),rp/'replay_checks.json',routed/'hardware.json',routed/'design.dcp'])
        b.write(wd/'provenance.json',stamps)
        m.tool([b.VIVADO/'bin/vivado.bat','-mode','batch','-log','vivado.log','-journal','vivado.jou','-source',root/'power16_12.tcl',
            '-tclargs',e,routed/'design.dcp',named,wd],wd,'annotation',stamps,2.3)
        b.write(wd/'evidence.json',dict(status='reports generated; independent audit required',B=16,engine=e,design_top=hardware['top'],
            replay_dir=str(rp),hardware_file=str(routed/'hardware.json'),saif_file=str(named),source_sha256=stamps,
            artifact_sha256=b.pins(p for p in wd.iterdir() if p.is_file()),duration_seconds=d['saif']['duration_seconds'],neurons=d['neurons']))
        auditor=load(root/('audit_power16_rep3_12_certified.py' if args.workload == 'ottt_representative' else ('audit_power16_lutceil_12_certified.py' if e==7 else 'audit_power16_12_certified.py')),'certified_recovery_power_auditor')
        audit=auditor.annotation(wd);b.write(wd/'power_audit.json',audit)
        print('ENERGY RECOVERY POWER AUDIT PASS',args.workload,e,audit['estimated_dynamic_energy_pJ_per_scalar_update'],flush=True)
    m.power=certified_power
    m.sources()
    return m,root,receipts,extra


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--workload',choices=['ottt_representative'],required=True)
    ap.add_argument('--engine',type=int,required=True)
    ap.add_argument('--native-acceptance',required=True)
    ap.add_argument('--route-dir-template',required=True)
    ap.add_argument('--attempt',required=True)
    ap.add_argument('--reuse-golden-dir')
    ap.add_argument('--reuse-export-dir')
    ap.add_argument('--run',action='store_true')
    args = ap.parse_args(); assert re.fullmatch(r'[a-zA-Z0-9_-]+',args.attempt)
    m,root,reused,extra = bind(args)
    progress = root/f'energy_recovery_{args.workload}_e{args.engine}_{args.attempt}_progress.json'
    assert not progress.exists(), 'Retain all original attempts.'
    stages = ['golden','export','replay','power']
    for stage in stages:
        if stage not in {r['stage'] for r in reused}:
            assert not m.path(stage,args.engine).exists(), ('Use a fresh attempt directory',str(m.path(stage,args.engine)))
    if not args.run:
        print('ENERGY RECOVERY READ-ONLY BINDING PASS',dict(workload=args.workload,engine=args.engine,
            reused=reused,future_progress_file=str(progress),future_stages=[x for x in stages if x not in {r['stage'] for r in reused}],
            launch_gate_GiB=2.3,simulation_gate_GiB=1.2,vendor_jobs_launched=False),flush=True)
        return
    state = dict(status='running',B=16,workload=args.workload,clock_ns=12,engines=[args.engine],stages=[],failures=[],
        explicitly_reused=reused,source_sha256=m.sources(),recovery_adapter_file=str(Path(__file__).resolve()),
        original_producer_file=str(root/('run_energy16_rep3_12.py' if args.workload == 'ottt_representative' else ('run_energy16_lutceil_12.py' if args.engine==7 else 'run_energy16_12.py'))))
    for label in stages:
        state['current_stage']=[label,args.engine]; b.write(progress,state)
        if label in {r['stage'] for r in reused}:
            b.verify(extra); state['stages'].append([label,args.engine]); b.write(progress,state); continue
        start=time.time()
        try:
            getattr(m,label)(args.engine)
            if label == 'power':
                audit=m.path('power',args.engine)/'power_audit.json'; a=b.read(audit); checked(a)
                assert a['status']=='pass' and a['engine']==args.engine and a['fixture_FF']==94 and a['physical_activity_unknown_records']==0
                assert Path(a['routed_hardware_file']).resolve()==Path(args.route_dir_template.format(engine=args.engine)).resolve()/'hardware.json'
                assert a['routed_hardware_sha256']==b.sha(a['routed_hardware_file'])
                state['accepted_power_audit_file']=str(audit); state['accepted_power_audit_sha256']=b.sha(audit)
            b.verify(extra)
        except Exception as exc:
            state['status']='completed_with_retained_failures'
            state['failures'].append(dict(engine=args.engine,stage=label,reason=repr(exc),accepted_energy=False))
            b.write(progress,state); print('ENERGY RECOVERY RETAINED FAILURE',args.workload,args.engine,label,repr(exc),flush=True)
            raise SystemExit(2)
        state['stages'].append([label,args.engine]); b.write(progress,state)
        print('ENERGY RECOVERY STAGE',args.workload,args.engine,label,'seconds',round(time.time()-start,1),flush=True)
    state['status']='pass'; b.write(progress,state)


if __name__ == '__main__': main()
