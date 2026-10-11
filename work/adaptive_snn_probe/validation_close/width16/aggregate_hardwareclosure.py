"""Read-only evidence aggregation for fixed16 closure; no vendor tools or waivers."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,math,re,sys,time
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;ALT=P/'lutceil_e7';TRIAL=P.parent.parent/'sequential_paper_trial'
LABELS={0:'adaptive precomp',1:'fixed split2',2:'original LUT2',3:'scalar DSP2',4:'scalar DSP1',5:'adaptive post',6:'beta128 shift2',7:'optimized LUT2 quotient ceil'}
DSP={0:1,1:1,2:0,3:2,4:1,5:1,6:0,7:0}
CACHE={}
def sha(path):
    path=Path(path);stat=path.stat();key=(str(path.resolve()),stat.st_size,stat.st_mtime_ns)
    if key not in CACHE:
        h=hashlib.sha256()
        with path.open('rb')as stream:
            for chunk in iter(lambda:stream.read(1048576),b''):h.update(chunk)
        CACHE[key]=h.hexdigest()
    return CACHE[key]
def read(path):return json.loads(Path(path).read_text())
def verify(record):
    for key in('source_sha256','artifact_sha256'):
        for path,pin in record.get(key,{}).items():assert sha(path)==pin,('changed evidence',path)
def evidence(recordpath):
    record=read(recordpath);verify(record);return record
def load_auditor(path):
    spec=importlib.util.spec_from_file_location('closure_auditor_'+path.parent.name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def fraction(a,b):return a/b-1
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--label',required=True);ap.add_argument('--strict-complete',action='store_true');args=ap.parse_args()
    assert re.fullmatch(r'[a-zA-Z0-9_-]+',args.label)
    destination=P/f'hardwareclosure_{args.label}.json';report=P/f'hardwareclosure_{args.label}.md'
    assert not destination.exists()and not report.exists(),'Retain prior snapshots.'
    started=time.monotonic();issues=[];retained_failures=[];native_records=[];route_records=[];power_records=[]
    allpaths=[]
    for root in(P/'hardware',ALT/'hardware'):
        if not root.exists():continue
        for path in sorted(root.glob('*/acceptance.json')):
            try:
                n=evidence(path);assert n['status']=='pass'and n['B']==16
                assert n['stall']in(0,1)and n['capture']in(0,1)
                assert len(n['rows'])in(6,7)
                for row in n['rows']:
                    e=row['engine'];assert e in DSP and row['requests']==row['retirements']and row['neurons']>0
                    assert row['min_latency']>=2
                    if n['stall']==0:assert row['min_latency']==row['max_latency']==2 and row['service_clocks']==row['requests']+2
                native_records.append(dict(path=str(path),path_sha256=sha(path),family='E7'if root.parent==ALT else'main',record=n))
                allpaths.append(path)
            except Exception as exc:issues.append(dict(path=str(path),reason=repr(exc),category='native_evidence_failure'))
        for path in sorted(root.glob('*/hardware.json')):
            try:
                hw=evidence(path);assert hw['B']==16 and hw['engine']in DSP
                e=hw['engine'];account=hw['slice_accounting']
                assert(account['launch_FF'],account['capture_FF'],account['fixture_FF'])==(55,39,94)
                assert hw['full_fixture']['FF']-hw['core']['FF']==94 and hw['full_fixture']['LUT']==hw['core']['LUT']
                assert hw['full_fixture']['DSP']==hw['core']['DSP']==DSP[e]
                assert hw['part']=='xc7a100tcsg324-1'and hw['clock_period_ns']==12
                assert hw['latency_advancing_edges']==2
                assert all(math.isfinite(hw[k])for k in('WNS_ns','WHS_ns','boundary_WNS_ns','boundary_WHS_ns'))
                if hw['status']=='pass':assert min(hw[k]for k in('WNS_ns','WHS_ns','boundary_WNS_ns','boundary_WHS_ns'))>=0
                else:retained_failures.append(dict(path=str(path),status=hw['status'],category='route_timing'))
                route_records.append(dict(path=str(path),path_sha256=sha(path),record=hw));allpaths.append(path)
            except Exception as exc:issues.append(dict(path=str(path),reason=repr(exc),category='route_evidence_failure'))
        for path in sorted(root.glob('*/power_audit.json')):
            try:
                auditpath=ALT/'audit_power16_lutceil_12.py'if root.parent==ALT else P/'audit_power16_12.py'
                saved=read(path);assert saved['status']=='pass'and saved['engine']in DSP
                assert saved['auditor_sha256']==sha(auditpath)
                actual=load_auditor(auditpath).annotation(path.parent)
                assert actual==saved,'Saved power audit does not reproduce independently.'
                assert saved['fixture_FF']==94 and saved['clock_period_ns']==12 and saved['physical_activity_unknown_records']==0
                workload='glif'if '_glif_'in path.parent.name else'ottt'if '_ottt_'in path.parent.name else None
                assert workload is not None
                power_records.append(dict(path=str(path),path_sha256=sha(path),workload=workload,record=saved));allpaths.append(path)
            except Exception as exc:issues.append(dict(path=str(path),reason=repr(exc),category='power_evidence_failure'))
    for path in sorted(list(P.glob('*progress*.json'))+list(ALT.glob('*progress*.json'))):
        d=read(path)
        for failure in d.get('failures',[]):retained_failures.append(dict(path=str(path),failure=failure,category='runner_retained_failure'))
        if d.get('status')=='retained_failure':retained_failures.append(dict(path=str(path),reason=d.get('reason'),category='runner_retained_failure'))
    required=[];missing=[]
    for family,cohort,stall,capture in [('main','general',0,False),('main','general',1,False),('main','shift128',0,False),('main','shift128',1,False),('main','actual128',0,True),('main','actual_glif',0,True),('E7','general',0,False),('E7','general',1,False),('E7','actual_glif',0,True)]:
        key=f'native/{family}/{cohort}/stall{stall}'+('/capture'if capture else'');required.append(key)
        if not any(n['family']==family and n['record']['cohort']==cohort and n['record']['stall']==stall and(not capture or n['record']['capture']==1)for n in native_records):missing.append(key)
    # If multiple accepted retries exist, take the latest evidence file transparently;
    # no resource or power value is used to select an implementation attempt.
    selected_routes={}
    for e in DSP:
        candidates=[r for r in route_records if r['record']['engine']==e and r['record']['status']=='pass']
        key=f'route/engine{e}/12ns';required.append(key)
        if candidates:selected_routes[e]=max(candidates,key=lambda r:Path(r['path']).stat().st_mtime_ns)
        else:missing.append(key)
    selected_power={}
    for workload,engines in [('glif',list(range(6))+[7]),('ottt',list(range(7)))]:
        for e in engines:
            candidates=[r for r in power_records if r['workload']==workload and r['record']['engine']==e]
            key=f'energy/{workload}/engine{e}/12ns';required.append(key)
            if candidates:selected_power[workload,e]=max(candidates,key=lambda r:Path(r['path']).stat().st_mtime_ns)
            else:missing.append(key)
    comparisons={}
    if 5 in selected_routes and 1 in selected_routes:
        a=selected_routes[5]['record']['core'];b=selected_routes[1]['record']['core']
        comparisons['fixed16_post_vs_fixed_split_area']=dict(LUT_fraction_change=fraction(a['LUT'],b['LUT']),FF_fraction_change=fraction(a['FF'],b['FF']),same_DSP=a['DSP']==b['DSP'])
    for workload in('glif','ottt'):
        if(workload,5)in selected_power and(workload,1)in selected_power:
            a=selected_power[workload,5]['record']['estimated_dynamic_energy_pJ_per_scalar_update'];b=selected_power[workload,1]['record']['estimated_dynamic_energy_pJ_per_scalar_update']
            comparisons[f'{workload}_post_vs_fixed_split_energy']=dict(dynamic_energy_fraction_change=fraction(a,b),adaptive_pJ=a,fixed_split_pJ=b,scope='Common94FF estimated dynamic energy of declared captured operands; not board or whole-neuron energy')
        baseline=7 if workload=='glif' else 6
        if(workload,5)in selected_power and(workload,baseline)in selected_power:
            a=selected_power[workload,5]['record']['estimated_dynamic_energy_pJ_per_scalar_update'];b=selected_power[workload,baseline]['record']['estimated_dynamic_energy_pJ_per_scalar_update']
            comparisons[f'{workload}_post_vs_LUT_or_shift_energy']=dict(baseline_engine=baseline,dynamic_energy_fraction_change=fraction(a,b),adaptive_pJ=a,baseline_pJ=b)
    complete=not missing and not issues
    answer=dict(status='pass_complete_fixed16_hardware_closure'if complete else'incomplete_snapshot',B=16,narrow_internal_B=9,
        coefficient_domain=[0,256],membrane_storage_precision='fixed16 throughout all new model/hardware comparisons; internal narrow packing does not rescale or changestoredunits',
        clock_period_ns=12,fixture_FF=94,part='xc7a100tcsg324-1',native=native_records,routes=route_records,power=power_records,
        required_gates=required,missing_gates=missing,evidence_issues=issues,retained_failures=retained_failures,
        selected_routes={str(e):dict(path=r['path'],sha256=r['path_sha256'],record=r['record'])for e,r in selected_routes.items()},
        selected_power={f'{w}/e{e}':dict(path=r['path'],sha256=r['path_sha256'],record=r['record'])for(w,e),r in selected_power.items()},
        selection_policy='Latest accepted evidence file bymodificationtime when retriesexist, allattemptsretained; resource/energy performance notusedtochooseattempt',
        comparisons=comparisons,publication_scope=['Arithmetic kernel OOC evidence only; full accelerator, board power, memory/filtercost and whole-neuron latency unmeasured.',
            'GLIF activity haspredeclared distributionchecks againstcomplete64imagestream; OTTTactual128 sampleis stress/coverage, notunbiased representativeenergy.',
            'E6shift control appliesonlybeta128 model; cannotreplacegeneral0..256 leakagecontrol.',
            'Earlier12bit 53LUT/122LUT and34.4percent capturedenergy claims are retainedhistorical implementationevidence, notcross-width mainresults.',
            'A routed E7pass doesnotbyitself establishrootcauseofthe retainedoriginalE2SDF discrepancy.'],
        source_sha256={str(Path(__file__)):sha(Path(__file__))},evidence_sha256={str(p):sha(p)for p in allpaths},elapsed_seconds=time.monotonic()-started)
    destination.write_text(json.dumps(answer,indent=2)+'\n')
    lines=['# Fixed16 leakage hardware closure', '', f"Status: **{answer['status']}**. All new comparisons use signed16 full membrane inputs, signed9 internal pair packing, 12 ns clock and a common 94-FF fixture.", '',
        'The full stored membrane precision is fixed. Adaptation changes how many operations share one DSP issue, without changing voltage units or losing integer bits.', '',
        f'Accepted native cohorts: {len(native_records)}. Accepted route records: {sum(r["record"]["status"]=="pass"for r in route_records)}. Independently reproduced power audits: {len(power_records)}.', '']
    if selected_routes:
        lines+=['Verified core resources (fixture FFs excluded):','']
        for e,r in sorted(selected_routes.items()):
            hw=r['record'];c=hw['core'];lines.append(f'- E{e} {LABELS[e]}: {c["LUT"]} LUT, {c["FF"]} FF, {c["DSP"]} DSP; setup {hw["WNS_ns"]:+.3f} ns, hold {hw["WHS_ns"]:+.3f} ns.')
        lines.append('')
    if selected_power:
        lines+=['Verified vendor estimated dynamic energy of the complete common fixture:','']
        for(w,e),r in sorted(selected_power.items()):lines.append(f'- {w.upper()} E{e}: {r["record"]["estimated_dynamic_energy_pJ_per_scalar_update"]:.6f} pJ per captured scalar leakage result.')
        lines.append('')
    if missing:lines+=['Required gates still missing:','']+[f'- {key}'for key in missing]+['']
    if issues:lines+=['Evidence issues requiring resolution:','']+[f'- {item["path"]}: {item["reason"]}'for item in issues]+['']
    lines+=['All failed attempts are retained in the JSON evidence snapshot. Failed or absent audits never supply accepted power values.', '',
        'GLIF energy is a bounded representative capture of the complete 64-image arithmetic stream after common zero filtering. OTTT energy from the current wide-value coverage sample is a stress result. Neither constitutes board or full-neuron energy.', '',
        'Earlier signed12 resource/energy results remain separate. Publication readiness also depends on broader model results and prior-work equivalence checks managed by the parent task.', '',f'JSON evidence: `{destination.name}`. Snapshot SHA256: `{sha(destination)}`.', '']
    report.write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(dict(status=answer['status'],native=len(native_records),routes=len(route_records),power=len(power_records),missing=missing,issues=issues,report=str(report))),flush=True)
    if args.strict_complete and not complete:raise SystemExit(2)
if __name__=='__main__':main()
