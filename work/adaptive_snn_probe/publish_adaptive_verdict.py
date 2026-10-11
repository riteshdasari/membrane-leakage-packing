"""Publish a bounded research verdict, preserving failed verification as failures."""
from pathlib import Path
import json,hashlib,re,sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
OUT=P.parents[1]/'outputs'
STEM='membrane_adaptive_packing_verdict'
O=P/'residue_frontier_trial';F=P/'residue_frontier_f5_trial';W=P/'residue_frontier_u13_trial'
N=P/'natural_lut_baseline_trial'
Q=P/'natural_frontier_trial';A=P/'adaptive_natural_lut_trial'
J=P/'natural_u11_trial'
sys.path.insert(0,str(O))
import run_frontier as run
import audit_frontier_power_v4 as audit
sys.path.insert(0,str(W))
import run_u13_physical as wider
import audit_u13_power as wide_audit
pins={}
def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            digest.update(block)
    return digest.hexdigest()
read=lambda p:json.loads(Path(p).read_text())
def add_file(path):
    path=Path(path).resolve();key=str(path);digest=sha(path)
    assert key not in pins or pins[key]['sha256']==digest
    pins[key]=dict(sha256=digest,bytes=path.stat().st_size)
    return path
def scan(data):
    if isinstance(data,dict):
        for file_key,digest_key in (('retirement_file','retirement_sha256'),('trace_file','trace_sha256'),('checked_file','checked_sha256')):
            if file_key in data and digest_key in data:
                assert sha(data[file_key])==data[digest_key],('Changed referenced evidence',data[file_key])
                add_file(data[file_key])
        for key,value in data.items():
            if isinstance(key,str) and re.match(r'^[A-Za-z]:[\\/]',key) and isinstance(value,str) and re.fullmatch('[a-f0-9]{64}',value):
                assert sha(key)==value,('Changed pinned evidence',key)
                add_file(key)
            else:scan(value)
    elif isinstance(data,list):
        for value in data:scan(value)
def load(path):
    add_file(path);data=read(path);scan(data);return data
def native_family(folder):
    records=[]
    for kind in ('models','main'):
        for stall in (0,1):
            paths=list((folder/'results').glob(f'native_{kind}_{stall}_a*/frontier_checks.json'))
            assert len(paths)==1
            d=load(paths[0]);assert d['status']=='pass'
            assert {r['engine'] for r in d['rows']}==set(range(6)) and all(r['status']=='pass' for r in d['rows'])
            load(paths[0].parent/'provenance.json')
            records.append(d|dict(check_file=str(paths[0])))
    return records
def hardware(folder,engine):
    path=folder/'results'/f'route_e{engine}_a0/hardware.json'
    d=load(path);assert d['engine']==engine and d['clock_period_ns']==6
    assert d['full_fixture']['FF']-d['core']['FF']==(338 if folder==W else 290)
    return d|dict(file=str(path))
def failure(folder,engine,attempt):
    wd=folder/'results'/f'replay_e{engine}_a{attempt}'
    log=wd/'tool_3.log';add_file(log)
    text=log.read_text();match=re.search(r'Fatal: ([^\n]+)',text)
    assert match and not (wd/'replay_checks.json').exists()
    for path in sorted(wd.glob('tool_*.job.json')):load(path)
    return dict(engine=engine,log_file=str(log),reason=match[1],accepted_energy=False)
def short(row):
    return {key:row[key] for key in ('engine','requests','service_clocks','neurons','take_histogram')}
def ratio(a,b):return (a/b-1)*100
def natural_family(folder):
    d=load(folder/'native_acceptance.json')
    assert d['status']=='pass' and len(d['cohorts'])==4
    for check in d['cohorts']:
        assert check['status']=='pass' and all(r['status']=='pass' for r in check['rows'])
        load(check['check_file'])
        load(Path(check['check_file']).parent/'provenance.json')
    return d
def routed_functional_diagnostic():
    wd=F/'results/diagnostic_routed_functional_a0'
    load(wd/'export.job.json')
    check=wd/'diagnostic_checks.json'
    if check.exists():
        d=load(check)
        assert not d['accepted_timing_result'] and not d['accepted_energy']
        return d
    job=load(wd/'tool_3.job.json')
    assert job['returncode'] is not None, 'Wait for the functional diagnostic to finish'
    log=add_file(wd/'tool_3.log').read_text()
    match=re.search(r'Fatal: ([^\n]+)',log)
    assert match, 'Unclassified functional diagnostic failure must be investigated'
    return dict(status='failed',reason=match[1],accepted_timing_result=False,accepted_energy=False,
                log_file=str(wd/'tool_3.log'))
def main():
    targets=[OUT/(STEM+s) for s in ('.md','.summary.json','.manifest.json')]
    assert not any(path.exists() for path in targets),'Preserve prior publications'
    completion=load(W/'results/completion_progress.json')
    assert completion['status'] in ('all_checks_passed','completed_with_retained_failures')
    assert set(completion['routes'])==set(range(6)), 'All matched routes required'
    load(W/'results/completion_provenance.json')
    ram_retries=load(W/'results/ram_retry_progress.json')
    assert ram_retries['status'] in ('all_checks_passed','completed_with_retained_failures')
    assert ram_retries['engines']==[3,4]
    remaining_power=load(W/'results/remaining_power_completion.json')
    assert remaining_power['status'] in ('all_checks_passed','completed_with_retained_failures')
    supply=load(W/'results/supply2_models_0_a0/supply_control_acceptance.json')
    assert supply['status']=='pass'
    original=native_family(O);f5=native_family(F);wide=native_family(W)
    original_hw=[hardware(O,e) for e in range(6)]
    f5_hw=hardware(F,5);wide_hw=[hardware(W,e) for e in range(6)]
    natural=natural_family(N)
    natural_hw=load(N/'route_a0/hardware.json')
    assert natural_hw['status']=='pass' and natural_hw['latency_advancing_edges']==1
    assert natural_hw['full_fixture']['FF']-natural_hw['core']['FF']==338
    natural_model,=[d for d in natural['cohorts'] if d['kind']=='models' and not d['backpressure']]
    natural_row,=natural_model['rows']
    assert natural_row['service_clocks']==92160 and natural_row['saved_states_spikes_counts_classes_match']
    lean=natural_family(Q);lean_hw=load(Q/'hardware_acceptance.json')
    assert lean_hw['status']=='routes_complete' and len(lean_hw['routes'])==6
    lean_hardware=[load(Q/f'route_e{e}_a0/hardware.json') for e in range(6)]
    assert all(d['full_fixture']['FF']-d['core']['FF']==338 for d in lean_hardware)
    lean_model,=[d for d in lean['cohorts'] if d['kind']=='models' and not d['backpressure']]
    lean_stress,=[d for d in lean['cohorts'] if d['kind']=='main' and not d['backpressure']]
    adaptive_lut=natural_family(A);adaptive_lut_hw=load(A/'route_a0/hardware.json')
    for kind in ('models','main'):
        for stall in (False,True):
            qr,=[d for d in lean['cohorts'] if d['kind']==kind and d['backpressure']==stall]
            ar,=[d for d in adaptive_lut['cohorts'] if d['kind']==kind and d['backpressure']==stall]
            nr,=[d for d in natural['cohorts'] if d['kind']==kind and d['backpressure']==stall]
            for x,y in ((qr['rows'][5],ar['rows'][0]),(qr['rows'][4],nr['rows'][0])):
                for key in ('requests','service_clocks','neurons','numeric_retirement_sha256','take_histogram'):
                    assert x[key]==y[key],('Natural-latency ablation mismatch',kind,stall,key)
    mapped_functional=routed_functional_diagnostic()
    static_hw=load(P/'trained_reference_native_trial/static_u8_physical/hardware.json')
    restored=[]
    for shift in (1,3):
        for stall in (0,1):
            path=P/'trained_reference_native_trial/results'/f'native_shift{shift}_stall{stall}_a1/native_checks.json'
            d=load(path);assert d['status']=='pass' and all(r['status']=='pass' for r in d['rows'])
            load(path.parent/'provenance.json');restored.append(d)
    restoration=load(P/'trained_reference_admission_study/restored_reference_summary.json')
    if_profile=load(W/'original_if/profile.json')
    attribution=load(W/'admission_attribution.json')
    diagnostic=load(F/'results/timing_diagnostic_f5_o0_a0/settled_carry_consistency.json')
    assert not diagnostic['settled_boolean_consistency'] and diagnostic['same_full_replay_assertion_failed']
    add_file(F/'final_independent_review.md');add_file(W/'MECHANISM_PROOF.md')
    add_file(P/'NATURAL_LATENCY_PROOF.md')
    lane_sweep=load(P/'full_lane_policy_sweep_trial/sweep_results.json')
    assert lane_sweep['status']=='pass'
    lif=load(P/'natural_lif_feedback_trial/acceptance.json')
    assert lif['status']=='pass' and len(lif['cohorts'])==4
    assert {(d['shift'],d['backpressure']) for d in lif['cohorts']}=={(1,False),(1,True),(3,False),(3,True)}
    for check in lif['cohorts']:
        assert check['status']=='pass' and len(check['rows'])==4
        assert all(r['status']=='pass' and r['neurons']==635904 for r in check['rows'])
        load(check['check_file']);load(Path(check['check_file']).parent/'provenance.json')
    natural_supply=load(P/'natural_supply2_trial/acceptance.json')
    assert natural_supply['status']=='pass'
    natural_supply_check=load(natural_supply['checked_file'])
    assert len(natural_supply_check['rows'])==7
    assert all(r['requests']==317952 and r['service_clocks']==327168 for r in natural_supply_check['rows'])
    u11=load(J/'native_acceptance.json');u11_hw=load(J/'hardware_acceptance.json')
    assert u11['status']=='pass' and len(u11['cohorts'])==6 and len(u11_hw['rows'])==5
    assert {(d['kind'],d['backpressure']) for d in u11['cohorts']}=={(k,s) for k in ('main','shift1','shift3') for s in (False,True)}
    for check in u11['cohorts']:
        assert check['status']=='pass' and len(check['rows'])==5
        load(check['check_file']);load(Path(check['check_file']).parent/'provenance.json')
    for row in u11_hw['rows']:
        assert row['full_fixture']['FF']-row['core']['FF']==290 and row['clock_period_ns']==6
        load(row['hardware_file'])
    load(J/'ram_gate_continuation.json');load(J/'completion_resume_progress.json')
    # Preserve the unsuccessful no-cell-path diagnostic without accepting it.
    rejected_diagnostic=F/'results/timing_diagnostic_cell_paths_a0'
    if not rejected_diagnostic.exists():
        rejected_diagnostic=F/'results/timing_diagnostic_no_cell_paths_a0'
    cell_path_attempts=list(F.glob('results/*cell*paths*'))
    cell_path_failure=[]
    for wd in cell_path_attempts:
        for path in sorted(wd.glob('tool_*.job.json')):load(path)
        for path in sorted(wd.glob('tool_*.log')):
            add_file(path)
            if 'Fatal:' in path.read_text():
                cell_path_failure.append(dict(log_file=str(path),accepted_timing_result=False,accepted_energy=False))
    add_file(W/'CONTRACT.md');add_file(Path(__file__))
    add_file(P/'verify_published_adaptive_verdict.py')
    for name in ('streaming_offset_trial.md','membrane_adaptive_packing_followup.md'):
        add_file(OUT/name)
    baseline_energy=[]
    for e in (0,1,3,4):
        wd=O/'results'/f'power_e{e}_a1'
        checked=audit.annotation(wd)
        assert checked==load(wd/'power_audit.json')
        scan(checked);load(wd/'evidence.json')
        baseline_energy.append(checked)
    original_failures=[failure(O,e,3) for e in (2,5)]+[failure(F,5,1)]
    wide_energy=[];wide_failures=[]
    for e in range(6):
        if e in completion['powers']:
            wd=W/'results'/f'power_e{e}_a0';checked=wide_audit.annotation(wd)
            assert checked==load(wd/'power_audit.json')
            load(wd/'evidence.json');wide_energy.append(checked)
        elif (W/'results'/f'replay_e{e}_a0/tool_3.log').exists() and not (W/'results'/f'replay_e{e}_a0/replay_checks.json').exists():
            wide_failures.append(failure(W,e,0))
        else:
            wide_failures.append(dict(engine=e,accepted_energy=False,
                retained_failure=[x for x in completion['failures'] if x['engine']==e]))
    for e in ram_retries['powers']:
        assert e not in completion['powers']
        wd=W/'results'/f'power_e{e}_a1';checked=wide_audit.annotation(wd)
        assert checked==load(wd/'power_audit.json')
        load(wd/'evidence.json');wide_energy.append(checked)
    for item in ram_retries['failures']:
        wide_failures.append(dict(engine=item['engine'],accepted_energy=False,retry_failure=item))
    for e in remaining_power['powers']:
        if e in ram_retries['powers']:continue
        assert e not in completion['powers']
        wd=W/'results'/f'power_e{e}_a1';checked=wide_audit.annotation(wd)
        assert checked==load(wd/'power_audit.json')
        load(wd/'evidence.json');wide_energy.append(checked)
    wide_energy_by_engine={r['engine']:r for r in wide_energy}
    energy_pair=None
    if {2,5}<=wide_energy_by_engine.keys():
        ep,bp=wide_energy_by_engine[5],wide_energy_by_engine[2]
        def total_estimate(record):
            duration=record['native_interval_audit']['duration_ps']*1e-12
            return (record['dynamic_power_W']+record['device_static_W'])*duration/635904*1e12
        et,bt=total_estimate(ep),total_estimate(bp)
        energy_pair=dict(adaptive_engine=5,fixed_engine=2,
            adaptive_dynamic_pJ=ep['estimated_dynamic_energy_pJ_per_scalar_update'],
            fixed_dynamic_pJ=bp['estimated_dynamic_energy_pJ_per_scalar_update'],
            dynamic_change_percent=ratio(ep['estimated_dynamic_energy_pJ_per_scalar_update'],bp['estimated_dynamic_energy_pJ_per_scalar_update']),
            adaptive_device_including_static_pJ=et,fixed_device_including_static_pJ=bt,
            device_including_static_change_percent=ratio(et,bt),
            scope='Derived from accepted common338FFfixture vendor estimates and complete native intervals. Device static power belongs to wholeFPGA, not isolatedcore; no board/inference measurement.')
    for folder in (O,F):
        paths=list((folder/'results').glob('supply2_models_0_a*/frontier_checks.json'))
        assert len(paths)==1;d=load(paths[0]);assert d['status']=='pass'
    # Explicitly retain the RAM-gate resume and failed diagnostic.
    load(W/'results/native_main_0_a0/ram_gate_resume_provenance.json')
    for path in (F/'diagnose_timing_f5_o0.py',W/'resume_native_after_ram_gate.py',
                 W/'run_u13_native.py',W/'finish_u13_trial.py',W/'run_u13_supply2.py'):
        add_file(path)
    model,=[x for x in wide if x['kind']=='models' and not x['backpressure']]
    stress,=[x for x in wide if x['kind']=='main' and not x['backpressure']]
    rows=model['rows'];c=wide_hw[5]['core'];b=wide_hw[2]['core'];hy=wide_hw[3]['core'];lut=wide_hw[4]['core']
    nc=natural_hw['core']
    dominated=(nc['LUT']<=c['LUT'] and nc['FF']<=c['FF'] and nc['DSP']<=c['DSP']
               and natural_row['service_clocks']<rows[5]['service_clocks'])
    assert dominated, 'A different four-edge natural-baseline outcome requires a revised conclusion'
    lean_c=lean_hardware[5]['core'];lean_b=lean_hardware[2]['core'];lean_hy=lean_hardware[3]['core']
    lean_rows=lean_model['rows'];alc=adaptive_lut_hw['core']
    assert lean_rows[5]['service_clocks']==95186 and lean_rows[2]['service_clocks']==92160
    def dominates(left,right):
        keys=('LUT','FF','DSP')
        return (all(left['core'][key]<=right['core'][key] for key in keys)
                and left['service_clocks']<=right['service_clocks']
                and (any(left['core'][key]<right['core'][key] for key in keys)
                     or left['service_clocks']<right['service_clocks']))
    legal_comparators=[dict(label=f'natural_E{e}',core=lean_hardware[e]['core'],service_clocks=lean_rows[e]['service_clocks'])
                       for e in range(5) if lean_hardware[e]['status']=='pass']
    legal_comparators+=[dict(label='natural_LUT',core=nc,service_clocks=natural_row['service_clocks'])]
    if adaptive_lut_hw['status']=='pass':
        legal_comparators.append(dict(label='adaptive_LUT',core=alc,service_clocks=lean_rows[5]['service_clocks']))
    lean_point=dict(core=lean_c,service_clocks=lean_rows[5]['service_clocks'])
    lean_dominators=[d['label'] for d in legal_comparators if dominates(d,lean_point)]
    lean_passes=lean_hardware[5]['status']=='pass'
    u11_by_id={r['engine']:r for r in u11_hw['rows']}
    u11_model,=[d for d in u11['cohorts'] if d['kind']=='shift3' and not d['backpressure']]
    u11_model_by_id={r['engine']:r for r in u11_model['rows']}
    u11_point=dict(core=u11_by_id[0]['core'],service_clocks=u11_model_by_id[0]['service_clocks'])
    u11_dominators=[u11_by_id[e]['label'] for e in range(1,5) if u11_by_id[e]['status']=='pass'
        and dominates(dict(core=u11_by_id[e]['core'],service_clocks=u11_model_by_id[e]['service_clocks']),u11_point)]
    natural_attribution={key:value|dict(service_clocks=value['requests']+value['groups'])
                         for key,value in attribution['policies'].items()}
    assert natural_attribution['runtime_U8_tail']['service_clocks']==lean_rows[5]['service_clocks']
    assert rows[5]['service_clocks']==122834 and rows[2]['service_clocks']==119808
    assert all(r['saved_states_spikes_counts_classes_match'] for r in rows)
    register_model=[]
    for label,width,k,hw in [('U8 static',8,0,static_hw),('U11 fixed8',11,8,original_hw[2]),
                           ('U11 F6',11,6,original_hw[5]),('U11 F5',11,5,f5_hw),
                           ('U13 fixed8',13,8,wide_hw[2]),('U13 F5',13,5,wide_hw[5])]:
        expected=268+4*k*(width-8)
        register_model.append(dict(label=label,expected_FF=expected,mapped_FF=hw['core']['FF'],
                                   matches=expected==hw['core']['FF']))
    summary=dict(status='bounded_study_completed_with_explicit_verification_limits',
        verdict=('The four-edge core is resource/service dominated by natural LUT. Natural-latency adaptation provides a qualified resource/service tradeoff, not yet a demonstrated strong-paper contribution or measured natural-latency energy advantage'
                 if lean_passes and not lean_dominators else
                 'The four-edge core is dominated by natural LUT; the lean adaptive trial does not establish an undominated clock-feasible contribution'),
        actual_mechanism='Ordered5full+up-to3actual-U8-tail admission; invariant eight-field radix32 DSP residue layout',
        mentor_model_scope=dict(primary='LIF',possible_extension='AdEx',equation_supplied=False,
            leakage_coefficient_supplied=False,time_constant_supplied=False,
            consequence='Do not introduce a coefficient or programmability merely to favor DSP arithmetic. Full AdEx is not implemented or tested.'),
        operation='One post-leak membrane U plus signed8 current I; no full synaptic reduction or leakage hardware',
        original_native=original,f5_native=f5,u13_native=wide,restored_native=restored,
        original_hardware=original_hw,f5_hardware=f5_hw,u13_hardware=wide_hw,static_U8_hardware=static_hw,
        natural_latency_LUT_native=natural,natural_latency_LUT_hardware=natural_hw,
        natural_latency_LUT_model_service=short(natural_row),
        natural_latency_LUT_dominates_current_adaptive_in_reported_metrics=dominated,
        natural_latency_frontier_native=lean,natural_latency_frontier_hardware=lean_hardware,
        natural_latency_adaptive_LUT_native=adaptive_lut,natural_latency_adaptive_LUT_hardware=adaptive_lut_hw,
        natural_latency_frontier_model_service=[short(r) for r in lean_rows],
        natural_latency_frontier_stress_service=[short(r) for r in lean_stress['rows']],
        natural_latency_adaptive_meets_clock=lean_passes,natural_latency_adaptive_dominators=lean_dominators,
        natural_latency_static_policy_attribution=natural_attribution,
        natural_latency_static_policy_scope='Analytically recomputed requests + one drain edge per group from the checked policy counts; runtime count matches native one-edge service. Static hardware is not measured; actual one-edge two-value-cap delivery is checked separately.',
        original_reference_restoration=restoration,original_IF_profile=if_profile,
        u13_model_service=[short(r) for r in rows],u13_stress_service=[short(r) for r in stress['rows']],
        admission_attribution=attribution,supply2=supply,register_storage_model=register_model,
        natural_LIF_feedback=lif,natural_supply2=natural_supply,natural_supply2_checks=natural_supply_check,
        full_lane_policy_sweep=lane_sweep,
        natural_U11_native=u11,natural_U11_hardware=u11_hw,
        natural_U11_adaptive_meets_clock=u11_by_id[0]['status']=='pass',
        natural_U11_adaptive_dominators=u11_dominators,
        natural_U11_changes=dict(
            LUT_vs_fixed8=ratio(u11_by_id[0]['core']['LUT'],u11_by_id[1]['core']['LUT']),
            FF_vs_fixed8=ratio(u11_by_id[0]['core']['FF'],u11_by_id[1]['core']['FF']),
            LUT_vs_native_hybrid=ratio(u11_by_id[0]['core']['LUT'],u11_by_id[2]['core']['LUT']),
            FF_vs_native_hybrid=ratio(u11_by_id[0]['core']['FF'],u11_by_id[2]['core']['FF']),
            unstalled_shift3_service_vs_fixed8=ratio(u11_model_by_id[0]['service_clocks'],u11_model_by_id[1]['service_clocks'])),
        LIF_paper_decision='Current addition/admission primitive lacks a demonstrated strong-paper advantage over the complete set of matched fixed/hybrid/LUT controls. Preserve qualified resource/service results; full-neuron and natural-latency energy benefits remain unmeasured.',
        original_accepted_baseline_energy=baseline_energy,original_timing_failures=original_failures,
        u13_accepted_energy=wide_energy,u13_timing_failures=wide_failures,
        u13_four_edge_adaptive_fixed8_energy_comparison=energy_pair,
        carry_diagnostic=diagnostic,mapped_functional_diagnostic=mapped_functional,
        failed_no_cell_path_diagnostic=cell_path_failure,completion=completion,ram_retries=ram_retries,remaining_power_completion=remaining_power,
        changes_percent=dict(LUT_vs_fixed8=ratio(c['LUT'],b['LUT']),FF_vs_fixed8=ratio(c['FF'],b['FF']),
            LUT_vs_hybrid=ratio(c['LUT'],hy['LUT']),FF_vs_hybrid=ratio(c['FF'],hy['FF']),
            service_vs_fixed8=ratio(rows[5]['service_clocks'],rows[2]['service_clocks']),
            service_vs_fixed6=ratio(rows[5]['service_clocks'],rows[0]['service_clocks']),
            LUT_vs_natural_LUT=ratio(c['LUT'],nc['LUT']),FF_vs_natural_LUT=ratio(c['FF'],nc['FF']),
            service_vs_natural_LUT=ratio(rows[5]['service_clocks'],natural_row['service_clocks']),
            natural_service_change_vs_adaptive=ratio(natural_row['service_clocks'],rows[5]['service_clocks']),
            lean_LUT_vs_fixed8=ratio(lean_c['LUT'],lean_b['LUT']),lean_FF_vs_fixed8=ratio(lean_c['FF'],lean_b['FF']),
            lean_LUT_vs_hybrid=ratio(lean_c['LUT'],lean_hy['LUT']),lean_FF_vs_hybrid=ratio(lean_c['FF'],lean_hy['FF']),
            lean_service_vs_fixed8=ratio(lean_rows[5]['service_clocks'],lean_rows[2]['service_clocks']),
            lean_LUT_vs_natural_LUT=ratio(lean_c['LUT'],nc['LUT']),lean_FF_vs_natural_LUT=ratio(lean_c['FF'],nc['FF']),
            adaptive_LUT_LUT_vs_natural_LUT=ratio(alc['LUT'],nc['LUT']),adaptive_LUT_FF_vs_natural_LUT=ratio(alc['FF'],nc['FF']),
            service_vs_static_time_policy=ratio(rows[5]['service_clocks'],attribution['policies']['static_timestep_interval_U8_tail']['service_clocks'])),
        evidence_scope=dict(models='Three seeds of one64-128-10convertedANN architecture, digits,32timesteps',
            hardware='Artix7 xc7a100tcsg324-1, 6ns internal OOC timing; 338 fixtureFF excluded from U13 core counts and 290 from U11. Separate post-route raw-port I/O hold violations remain; no complete external-I/O or board timing closure.',
            accuracy='Full360 software references restored; native primitive traces on first48images/seed with independent state/spike/count/class feedback',
            energy='Only complete functional slow/max replays with strict annotation audits accepted; commonfixture dynamic estimates, notcoreorboardenergy',
            static_specialization='StaticU8 valid forshift1. Static time-policy ablation is optimistic software-only; arbitrary weight/layer specialization or reordering notexhaustivelyoptimized',
            pipeline_constraint='Prior LUT register comparisons imposed four advancing edges. All new DSP/fixed/adaptive and same-policy adaptiveLUT cores use one advancing edge. The matched four-edge storage advantage is conditional, not an application requirement.',
            neuron_model='Original shift1/shift3 LIF native feedback passes atU13, but required state widths areU8/U11. U13 is justified only by the finite32-step IF certificate; AdEx is not implemented.',
            no_claims=['First ever adaptive DSP packing','Accuracy improvement over exact baselines','FireFly accelerator superiority','Burst-latency improvement over full8','Whole-accelerator speedup','Universal total-area reduction','Adaptive energy superiority across natural-latency or all strong baselines']))
    changes=summary['changes_percent']
    failures_exist=bool(original_failures or wide_failures)
    from adaptive_verdict_text import build_md
    add_file(P/'adaptive_verdict_text.py')
    md=build_md(summary)
    targets[0].write_text(md,encoding='utf-8')
    targets[1].write_text(json.dumps(summary,indent=2)+'\n')
    for path in targets[:2]:add_file(path)
    targets[2].write_text(json.dumps(dict(status='pass_hash_closure',files=pins,
        note='Hashes prove preserved evidence identity, not acceptance of failed or old-method results'),indent=2)+'\n')
    # Independent re-read of the delivered manifest after serialization.
    delivered=read(targets[2])
    for path,record in delivered['files'].items():assert sha(path)==record['sha256'] and Path(path).stat().st_size==record['bytes']
    print('ADAPTIVE VERDICT PUBLISHED',str(targets[0]),'FILES',len(pins),'WIDER_CHANGES',changes,flush=True)

if __name__=='__main__':main()
