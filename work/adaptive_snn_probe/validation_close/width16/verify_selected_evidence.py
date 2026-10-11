"""Read-only explicit route/power binding and independent power audit reproduction."""
from pathlib import Path
from decimal import Decimal
from fractions import Fraction
import argparse,hashlib,importlib.util,json,math,re,sys,xml.etree.ElementTree as ET
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;ALT=P/'lutceil_e7';C=P.parent
DSP={0:1,1:1,2:0,3:2,4:1,5:1,6:0,7:0}
REQUIRED_PRIMARY={'glif':[0,1,3,4,5,7],'ottt':[0,1,3,4,5,6]}
ALL_ATTEMPTED={'glif':[0,1,2,3,4,5,7],'ottt':[0,1,2,3,4,5,6]}
CACHE={};AUDITORS={}

def sha(path):
    path=Path(path);s=path.stat();key=(str(path.resolve()),s.st_size,s.st_mtime_ns)
    if key not in CACHE:
        h=hashlib.sha256()
        with path.open('rb')as stream:
            for chunk in iter(lambda:stream.read(1048576),b''):h.update(chunk)
        CACHE[key]=h.hexdigest()
    return CACHE[key]
def read(path):return json.loads(Path(path).read_text())
def verify(d):
    for key in('source_sha256','artifact_sha256','source_artifact_sha256','sha256'):
        values=d.get(key,{})
        if isinstance(values,dict):
            for path,pin in values.items():assert sha(path)==pin,('changed evidence',path)
def accepted(path):
    path=Path(path).resolve();d=read(path);assert d['status']=='pass',(str(path),d['status']);verify(d);return d
def route(path,e):
    path=Path(path).resolve();d=accepted(path)
    assert d['engine']==e and d['B']==16 and d['clock_period_ns']==12
    assert d['top']==(f'top_sequential_leak16_lutceil_e7'if e==7 else f'top_sequential_leak16_e{e}')
    assert d['part']=='xc7a100tcsg324-1'and d['latency_advancing_edges']==2
    a=d['slice_accounting'];assert(a['launch_FF'],a['capture_FF'],a['fixture_FF'])==(55,39,94)
    assert d['fixture_FF']==94 and d['full_fixture']['FF']-d['core']['FF']==94
    assert d['full_fixture']['LUT']==d['core']['LUT']and d['full_fixture']['DSP']==d['core']['DSP']==DSP[e]
    for k in('WNS_ns','WHS_ns','boundary_WNS_ns','boundary_WHS_ns'):assert math.isfinite(d[k])and d[k]>=0
    return dict(file=str(path),sha256=sha(path),record=d)
def load_auditor(e):
    path=ALT/'audit_power16_lutceil_12.py'if e==7 else P/'audit_power16_12.py'
    if str(path)not in AUDITORS:
        spec=importlib.util.spec_from_file_location('explicit_selected_'+str(e),path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);AUDITORS[str(path)]=module
    return path,AUDITORS[str(path)]
def workload_from_audit(path):
    evidence=read(Path(path).parent/'evidence.json');replay=read(Path(evidence['replay_dir'])/'replay_checks.json')
    native=read(replay['native_check_file']);assert sha(replay['native_check_file'])==replay['native_check_sha256']
    assert native['cohort']in('actual_glif','actual128')
    return 'glif'if native['cohort']=='actual_glif'else'ottt'
def input_powers(args):
    entries={};failures=[];sourcefiles=[]
    if args.power_map:
        path=Path(args.power_map).resolve();d=read(path);verify(d);sourcefiles.append(path)
        groups=d.get('power_paths',d)
        for w in('glif','ottt'):
            assert isinstance(groups.get(w,{}),dict)
            for key,value in groups.get(w,{}).items():
                e=int(key);assert e in ALL_ATTEMPTED[w]
                if isinstance(value,dict):
                    filename=value.get('path',value.get('power_audit_file'));assert filename
                    if 'sha256'in value:assert sha(filename)==value['sha256']
                else:filename=value
                entries[w,e]=Path(filename).resolve()
        failures.extend(d.get('retained_failures',[]))
    else:
        path=Path(args.sequence).resolve();d=read(path);verify(d);sourcefiles.append(path)
        assert d['B']==16
        for step in d['steps']:
            if step.get('status')!='accepted_stage_gate':
                failures.append(dict(category='sequence_retained_stage',stage=step.get('label'),record=step));continue
            for receipt in step.get('acceptance_gates',[]):
                file=Path(receipt['path']).resolve();assert sha(file)==receipt['sha256'],('changed sequence receipt',str(file))
                if file.name!='power_audit.json':continue
                a=read(file);w=workload_from_audit(file);e=a['engine'];assert e in ALL_ATTEMPTED[w]
                assert(w,e)not in entries,('duplicate explicit power selection',w,e);entries[w,e]=file
    return entries,failures,sourcefiles
def power(path,w,e,selected):
    path=Path(path).resolve();saved=accepted(path)
    assert saved['engine']==e and saved['clock_period_ns']==12 and saved['fixture_FF']==94
    assert Path(saved['directory']).resolve()==path.parent and workload_from_audit(path)==w
    wanted=selected[e];assert Path(saved['routed_hardware_file']).resolve()==Path(wanted['file'])
    assert saved['routed_hardware_sha256']==wanted['sha256']==sha(wanted['file'])
    assert saved['core_resources']==wanted['record']['core']
    auditpath,auditor=load_auditor(e);assert saved['auditor_sha256']==sha(auditpath)
    actual=auditor.annotation(path.parent);assert actual==saved,'Saved strict power audit does not reproduce independently.'
    assert saved['physical_activity_unknown_records']==0
    interval=saved['native_interval_audit'];duration=interval['duration_ps'];N=interval['scalar_updates']
    assert isinstance(duration,int)and duration>0 and isinstance(N,int)and N>0
    assert interval['requests']==interval['retirements']and interval['requests']>0
    assert interval['clock_transitions']==duration//6000
    dynamic=saved['dynamic_power_W'];assert math.isfinite(dynamic)and dynamic>=0
    assert math.isclose(saved['dynamic_energy_J'],dynamic*duration*1e-12,rel_tol=1e-14,abs_tol=1e-30)
    assert math.isclose(saved['estimated_dynamic_energy_pJ_per_scalar_update'],dynamic*duration/N,rel_tol=1e-14,abs_tol=1e-12)
    tree=ET.parse(path.parent/'power_xpe.xml');sources=tree.getroot().findall('ENVIRONMENT/VOLTAGESOURCES/SOURCE')
    exact_dynamic=sum((Fraction(Decimal(x.attrib['voltage']))*Fraction(Decimal(x.attrib['icc']))for x in sources),Fraction(0))
    exact_pJ=exact_dynamic*duration/N;assert math.isclose(float(exact_dynamic),dynamic,rel_tol=1e-12,abs_tol=1e-12)
    assert math.isclose(float(exact_pJ),saved['estimated_dynamic_energy_pJ_per_scalar_update'],rel_tol=1e-12,abs_tol=1e-9)
    evidence=read(path.parent/'evidence.json');replay=read(Path(evidence['replay_dir'])/'replay_checks.json')
    nativefile=Path(replay['native_check_file']).resolve();native=accepted(nativefile)
    expectedfile=Path(replay['cohort_expectation_file']).resolve();expectation=read(expectedfile);verify(expectation)
    co=expectation['cohorts'][native['cohort']];verify(co)
    assert co['operations']==N
    return dict(workload=w,engine=e,power_audit_file=str(path),power_audit_sha256=sha(path),auditor_file=str(auditpath),auditor_sha256=sha(auditpath),
                routed_hardware_file=wanted['file'],routed_hardware_sha256=wanted['sha256'],core_resources=wanted['record']['core'],
                dynamic_power_W=dynamic,ROI_duration_ps=duration,scalar_updates=N,requests=interval['requests'],retirements=interval['retirements'],
                energy_formula='dynamic_power_W * ROI_duration_ps / scalar_updates = pJ per scalar leakage result',
                serialized_exact_dynamic_W_fraction=dict(numerator=exact_dynamic.numerator,denominator=exact_dynamic.denominator),
                serialized_exact_energy_pJ_fraction=dict(numerator=exact_pJ.numerator,denominator=exact_pJ.denominator),
                estimated_dynamic_energy_pJ_per_scalar_update=saved['estimated_dynamic_energy_pJ_per_scalar_update'],
                dynamic_energy_J=saved['dynamic_energy_J'],export_rounding_bound_pJ=saved['energy_rounding_bound_pJ_per_scalar_update'],
                native_acceptance_file=str(nativefile),native_acceptance_sha256=sha(nativefile),cohort=native['cohort'],
                source_operand_expectation_file=str(expectedfile),source_operand_expectation_sha256=sha(expectedfile),
                expected_outputs_file=co['expected_outputs_file'],expected_outputs_sha256=sha(co['expected_outputs_file']),
                scope='Bounded representative GLIF64 arithmetic capture after common zero filtering'if w=='glif'else'Deliberately selected OTTT16 wide-value stress/coverage capture; not representative energy')

def context():
    result={};paths=[]
    for key,file in [('original_E2',C/'lut_isolation/isolation_audit.json'),('prior_work',C/'prior_art/targeted_followup/followup_manifest.json'),('public_models',C/'benchmarks/benchmark_acceptance.json')]:
        if not file.exists():result[key]=dict(status='missing_context_file',path=str(file));continue
        try:
            d=read(file);verify(d);paths.append(file)
            if key=='original_E2':
                result[key]=dict(status=d['status'],original_timing_replay_accepted=d['original_E2_timing_replay_accepted'],
                                scope='Localized wrong annotated CARRY4 output; minimal bench does not reproduce full-netlist error. E7 acceptance does not resolve this diagnostic.',file=str(file),sha256=sha(file))
            elif key=='prior_work':
                result[key]=dict(status=d['status'],method_equivalence_closed=False,absence_proof=False,access_limited_methods=d['remaining_full_method_access_gaps'],file=str(file),sha256=sha(file))
            else:
                result[key]=dict(status=d['status'],file=str(file),sha256=sha(file),scope='Model-agent acceptance status snapshot; this script audits selected hardware energy, not model inference or full-test accuracy.')
        except Exception as exc:result[key]=dict(status='context_verification_failure',reason=repr(exc),file=str(file))
    return result,paths

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--route-acceptance',required=True);ap.add_argument('--e7-hardware',required=True)
    group=ap.add_mutually_exclusive_group(required=True);group.add_argument('--power-map');group.add_argument('--sequence')
    ap.add_argument('--label',required=True);ap.add_argument('--strict-primary',action='store_true');args=ap.parse_args()
    assert re.fullmatch(r'[a-zA-Z0-9_-]+',args.label)
    out=P/f'selected_evidence_{args.label}.json';md=P/f'selected_evidence_{args.label}.md';assert not out.exists()and not md.exists(),'Retain earlier audits.'
    routes={};accepted_power={};issues=[];retained=[];sourcefiles=[Path(__file__).resolve()]
    try:
        routefile=Path(args.route_acceptance).resolve();manifest=accepted(routefile);sourcefiles.append(routefile)
        assert manifest['B']==16 and manifest['period_ns']==12 and set(manifest['selected_routes'])==set(map(str,range(7)))
        for key,directory in manifest['selected_routes'].items():routes[int(key)]=route(Path(directory)/'hardware.json',int(key))
        routes[7]=route(args.e7_hardware,7)
        entries,retained,inputs=input_powers(args);sourcefiles+=inputs
        for(w,e),path in sorted(entries.items()):
            try:accepted_power[w,e]=power(path,w,e,routes)
            except Exception as exc:
                item=dict(workload=w,engine=e,path=str(path),category='selected_power_rejected',reason=repr(exc),accepted_energy=False)
                issues.append(item);retained.append(item)
    except Exception as exc:issues.append(dict(category='selection_or_route_dependency_failure',reason=repr(exc),accepted_energy=False))
    ctx,contextpaths=context();sourcefiles+=contextpaths
    missing_primary=[f'{w}/e{e}'for w,engines in REQUIRED_PRIMARY.items()for e in engines if(w,e)not in accepted_power]
    missing_all=[f'{w}/e{e}'for w,engines in ALL_ATTEMPTED.items()for e in engines if(w,e)not in accepted_power]
    primary_complete=not missing_primary and not any(x.get('category')=='selection_or_route_dependency_failure'for x in issues)
    # E2 remains diagnostic-only if rejected. That cannot make the all-control gate complete.
    all_complete=primary_complete and not missing_all and not issues
    comparisons={}
    for w in('glif','ottt'):
        for baseline in([1,3,4,7]if w=='glif'else[1,3,4,6]):
            if(w,5)not in accepted_power or(w,baseline)not in accepted_power:continue
            a=accepted_power[w,5];b=accepted_power[w,baseline]
            assert a['scalar_updates']==b['scalar_updates']and a['source_operand_expectation_sha256']==b['source_operand_expectation_sha256']
            va=a['estimated_dynamic_energy_pJ_per_scalar_update'];vb=b['estimated_dynamic_energy_pJ_per_scalar_update']
            comparisons[f'{w}_E5_vs_E{baseline}']=dict(adaptive_pJ=va,baseline_pJ=vb,energy_fraction_change=(va/vb-1)if vb else None,
                adaptive_hardware_file=a['routed_hardware_file'],baseline_hardware_file=b['routed_hardware_file'],
                adaptive_core=a['core_resources'],baseline_core=b['core_resources'],same_declared_scalar_operands=True,
                scope=a['scope'])
    result=dict(status='pass_selected_primary_hardware_energy_comparisons'if primary_complete else'incomplete_selected_evidence_snapshot',
                B=16,clock_ns=12,fixture_FF=94,part='xc7a100tcsg324-1',
                selection_policy='Explicit main resolved manifest and supplied E7 hardware; explicit power map or accepted sequence receipts. No latest/best attempt selection.',
                required_primary=REQUIRED_PRIMARY,all_attempted=ALL_ATTEMPTED,missing_primary=missing_primary,missing_all_attempted=missing_all,
                primary_comparison_status='pass'if primary_complete else'incomplete',all_attempted_control_status='pass'if all_complete else'incomplete_or_retained_E2_failure',
                selected_routes={str(e):dict(file=v['file'],sha256=v['sha256'],core=v['record']['core'])for e,v in routes.items()},
                accepted_power={f'{w}/e{e}':v for(w,e),v in accepted_power.items()},comparisons=comparisons,evidence_issues=issues,retained_failures=retained,
                nonhardware_closure_context=ctx,publication_ready=False,
                limitations=['Original E2 discrepancy is a separate unresolved diagnostic; E7 may close the fair generic LUT comparison only after its own full acceptance.',
                             'Method equivalence remains access-limited; this hardware audit does not establish first-ever novelty.',
                             'Current OTTT energy is stress/coverage only; GLIF energy is bounded representative64-image arithmetic activity.',
                             'Energy is vendor-estimated dynamic energy of common94FF fixture, not measured board or complete-neuron energy.',
                             'Serialized-source exact fractions and rounding bounds concern report serialization, not physical/model accuracy.'],
                source_sha256={str(f):sha(f)for f in sourcefiles},
                artifact_sha256={str(f):sha(f)for f in[*(Path(v['file'])for v in routes.values()),*(Path(v['power_audit_file'])for v in accepted_power.values())]})
    out.write_text(json.dumps(result,indent=2)+'\n')
    lines=['# Explicit selected fixed16 evidence','',f"Primary comparison gate: **{result['primary_comparison_status']}**. All attempted controls: **{result['all_attempted_control_status']}**.",'',
           'Every accepted energy audit was reproduced independently and binds path plusSHA to the exact route used for its area. Failed evidence supplies no accepted energy.','']
    for key,v in result['accepted_power'].items():
        lines.append(f"- {key}: {v['estimated_dynamic_energy_pJ_per_scalar_update']:.6f} pJ/scalar; numerator uses {v['dynamic_power_W']:.12g} W × {v['ROI_duration_ps']} ps, denominator {v['scalar_updates']} scalar outputs. {v['scope']}.")
    if missing_primary:lines+=['','Missing mandatory primary comparisons: '+', '.join(missing_primary)+'.']
    if missing_all:lines+=['','Missing all-control comparisons: '+', '.join(missing_all)+'.']
    lines+=['','Original E2 diagnosis, full public-model completion and prior-work method equivalence have separate statuses in JSON. This report never declares publication readiness.','',f'Exact evidence: `{out}`.']
    md.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=result['status'],accepted_power=len(accepted_power),missing_primary=missing_primary,missing_all=missing_all,report=str(md))))
    if args.strict_primary and not primary_complete:raise SystemExit(2)
if __name__=='__main__':main()
