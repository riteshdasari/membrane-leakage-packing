"""Final additive manuscript/evidence integrity and scope audit; no execution reruns."""
from pathlib import Path
from fractions import Fraction
import datetime, hashlib, json, math, os, re, sys
import numpy as np
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;W=P/'width16';S=P.parent/'sequential_paper_trial';ROOT=P.parents[2]
sys.path.insert(0,str(P))
import prepare_fixed16_final_report_v1 as evidence

def atomic_write(path,data):
    path=Path(path).resolve();assert not path.exists(),'Preserve earlier audit.'
    temp=path.with_name(path.name+f'.owned_tmp_{os.getpid()}')
    with temp.open('xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
    try:
        assert os.name=='nt';os.rename(temp,path)
    finally:
        if temp.exists():temp.unlink()

def main():
    out=P/'manuscript_scope_audit_v4.json';md=P/'manuscript_scope_audit_v4.md'
    assert not out.exists() and not md.exists(),'Retain previous scope audit.'
    draft=ROOT/'outputs/membrane_leakage_paper_draft.tex';raw=draft.read_bytes();draft_sha=hashlib.sha256(raw).hexdigest()
    text=raw.decode('utf-8');lines=text.splitlines()
    def where(needle):
        matched=[i for i,line in enumerate(lines,1) if needle in line];assert matched,needle;return matched
    evidence.bind(__file__);evidence.bind(draft,draft_sha)
    prior=evidence.read(P/'manuscript_scope_audit_v2.json',{'pass_bounded_manuscript_scope_audit_with_pending_publication_gates'})
    reused=prior['evidence_sha256']
    assert str(draft.resolve()) not in reused,'Old draft bytes must never be substituted for final draft.'
    for file,pin in reused.items():evidence.bind(file,pin)
    assert not prior['material_factual_or_numerical_errors_found'] and not prior['draft_changed_during_audit']
    routes=evidence.all_routes(W/'route_resolved_acceptance_a1.json',W/'lutceil_e7/hardware/route12_e7_close_a0/hardware.json')
    algebra=evidence.arithmetic(W/'domain_acceptance_glif_v2.json')
    narrow=evidence.e8(W/'static9_e8/closure_measured_close_a1.json',routes['selected'])
    selected_path=W/'selected_evidence_partitioned_all_a0.json'
    selected_record=evidence.read(selected_path,{'pass_selected_primary_hardware_energy_comparisons'})
    selected=evidence.selected_energy(selected_path,routes['selected'])
    required={f'glif/e{e}' for e in (0,1,3,4,5,7)}|{f'ottt/e{e}' for e in (0,1,3,4,5,6)}
    assert set(selected['accepted_power'])==required and len(required)==12
    assert selected_record['primary_comparison_status']=='pass' and not selected_record['missing_primary']
    assert set(selected_record['missing_all_attempted'])=={'glif/e2','ottt/e2'}
    assert selected_record['all_attempted_control_status']=='incomplete_or_retained_E2_failure'
    assert not selected_record['evidence_issues'] and len(selected_record['retained_failures'])==2
    assert {r['label'] for r in selected_record['retained_failures']}=={'GLIF_energy_e2','OTTT_energy_e2'}
    aggregate=evidence.read(W/'energy_partition_aggregate_partitioned_all_a0.json',{'incomplete_or_retained_control_failure'})
    assert aggregate['accepted_control_count']==12 and aggregate['all14_verifier_invoked']
    assert aggregate['selected_audit_returncode']==0 and not aggregate['complete_all14_energy_claim']
    assert set(aggregate['missing_all14'])=={'glif/e2','ottt/e2'}
    combined_e2=evidence.read(W/'fixed16_E2_combined_failures_a0.json',{'audited_both_fixed16_E2_numerical_replay_failures'})
    assert combined_e2['B']==16 and len(combined_e2['observed_attempts'])==2
    assert all(r['full_known_golden_replay_pass'] and not r['full_known_delayed_replay_pass'] for r in combined_e2['observed_attempts'].values())
    original=evidence.read(W/'energy_recovery_sequence_profiled_all_a0_preserved_before_partition.json',{'running'})
    partitions=[]
    for name,attempt,expected_engines in [('glif_remaining','glif_remaining_a0',[0,3,4,2]),('ottt_stress','ottt_stress_a0',[5,1,6,0,3,4,2])]:
        path=W/f'energy_recovery_partition_{name}_{attempt}.json'
        record=evidence.read(path,{'completed_partition_with_retained_failures_or_missing_controls'})
        assert record['partition']==name and [s['engine'] for s in record['plan']]==expected_engines
        assert len(record['steps'])==len(expected_engines) and len(record['failures'])==1
        assert record['failures'][0]['label'].endswith('_e2') and record['failures'][0]['accepted_energy'] is False
        assert record['accepted_control_count']==len(expected_engines)-1 and not record['complete_all14_energy_claim']
        assert all(s['status'] in ('accepted_stage_gate','retained_stage_failure') for s in record['steps'])
        partitions.append(record)
    attempted=[s['label'] for r in [original,*partitions] for s in r['steps']]
    assert len(attempted)==len(set(attempted))==14
    rep=evidence.rep_energy(W/'ottt_representative/closure_profiled_capture_v2_a0.json',routes['selected'])
    tradeoff=evidence.read(W/'glif_scalar_tradeoff_v2.json',{'pass_independent_certified_GLIF_E3_E4_E5_tradeoffs'})
    unsafe=evidence.read(W/'fixed_narrow_domain_counterfactual_v1.json',{'pass_explicitly_unsafe_fixed_narrow_domain_diagnostic'})
    access=evidence.read(P/'prior_art/bounded_final_access_20261011/access_closure.json',{'bounded_access_attempt_complete_equivalence_still_unresolved'})
    # Earlier access receipt remains immutable historical evidence.
    assert len(access['papers'])==4 and all(not x['full_method_retrieved'] for x in access['papers'])
    A=P/'prior_art/pending_closure_20261011'
    D=P/'lut_isolation/pending_closure_20261011'
    udp=evidence.read(A/'udp_full_reader_inspection_v1.json',{'completed_full_rendered_primary_method_inspection'})
    normal=evidence.read(A/'normal_publisher_access_receipt_v1.json',{'normal_browser_publisher_access_checked_three_methods_still_unread'})
    ou_cui=evidence.read(A/'ou_cui_access_equivalence_report_v1.json',{'completed_fresh_primary_route_check_two_full_method_gaps_unresolved'})
    mc=evidence.read(A/'udp_mckeown_closure_v1.json',{'bounded_new_primary_routes_complete_original_full_method_still_unresolved'})
    diag=evidence.read(D/'pending_closure_independent_audit_v2.json',{'audited_pending_LUT_closure_signed16_cell_output_inconsistency'})
    diag12=evidence.read(D/'signed12_controls_independent_audit_v1.json')
    probe=evidence.read(D/'run_signed16_probe/a0/diagnostic.json',{'completed_observation_only_signed16_probe'})
    assert udp['full_method_retrieved'] and not udp['original_pdf_file_acquired']
    assert len(udp['rendered_page_characters'])==12 and all(n>2000 for n in udp['rendered_page_characters'])
    assert udp['configured_widths_distinct_from_runtime_correction'] and not udp['equivalent_actual_membrane_admission_described']
    assert not udp['first_ever_established'] and not udp['Cui_original_method_closed_by_secondary_description']
    remaining=[r['id'] for r in normal['papers']]
    assert set(remaining)=={'Ou2024','Cui2024','McKeown2008'} and all(not r['full_method_retrieved'] for r in normal['papers'])
    assert not normal['login_attempted'] and not normal['access_controls_bypassed']
    assert len(ou_cui['papers'])==2 and all(not r['full_method_retrieved'] for r in ou_cui['papers'])
    assert not mc['original_full_method_retrieved']
    assert all(probe['gates'].values()) and probe['original_failure_reproduced']
    assert not probe['cause_established'] and not probe['full_trace_energy_acceptance']
    settled=[]
    for line in probe['snapshots']:
        m=re.search(r'AGE([0-9.]+) S0 DI0 CI0 CY0 SI0 DII0 CII0 CYI0 CO0 FB0 O2 PARENT_O2 UPSTREAM_CI0 EXPECT_O0 EXPECT_CO0',line)
        if m:settled.append(float(m.group(1)))
    assert settled and max(settled)>19
    assert diag['error_limit_control']['first_failure_row']==5 and not diag['error_limit_control']['accepted_as_remedy']
    assert diag['signed16']['original_first_failure_reproduced'] and diag['signed16']['all_observation_gates_pass']
    for needle in ['Disabling simulator optimization also retains row 914', 'replay fails later at row 2836',
        'forcing can affect connected nets', 'more than 19 ns of stable inputs',
        'Full methods for three relevant originals remain unread', 'runtime sign and most-negative-value corrections']:
        where(needle)
    assert 'Full methods for four relevant papers remain access-limited' not in text
    evidence.bind(A/'udp_full_reader_inspection_v1.md')
    evidence.bind(A/'ou_cui_access_equivalence_report_v1.md')
    evidence.bind(A/'udp_mckeown_closure_v1.md')
    evidence.bind(D/'pending_closure_independent_audit_v2.md')
    evidence.bind(D/'signed12_controls_independent_audit_v1.md')
    evidence.bind(P/'prepare_manuscript_scope_v4.py')
    boundary=evidence.bind(P/'prior_art/final_contribution_boundary.md')
    full_glif=evidence.read(S/'stage2_results.json',{'complete_integer_neuron_public_test'})
    packed_glif=evidence.read(S/'stage3_results.json',{'pass_exact_packed_feedback_and_stream_screen'})
    ottt=evidence.read(P/'benchmarks/benchmark_acceptance.json',{'full_evaluation_passed'})
    bntt=evidence.read(P/'benchmarks/bntt_acceptance.json',{'bounded_results_audited'})
    total=packed_glif['total'];issues=total['issues']
    full_ottt=ottt['runs']['cifar10_full10000_a0'];tiny=bntt['runs']['tiny_T30_n64_a2']
    assert full_glif['observed_neuron_updates']==24903680000
    assert (full_glif['integer_correct_float_wrong'],full_glif['float_correct_integer_wrong'])==(160,158)
    assert packed_glif['all_logits_bit_identical_to_integer_reference'] and packed_glif['state_spike_arithmetic_mismatches']==0
    assert total['raw_operations']==159383552 and total['arithmetic_operations']==79246135
    assert (issues['adaptive_post'],issues['fixed_split2'],issues['fixed_scalar1'])==(42785698,42327032,79246135)
    assert full_ottt['status']=='passed' and full_ottt['raw_updates']==24576000000 and full_ottt['packing_local_mismatches']==0
    assert full_ottt['correct']=={'float':9349,'integer':9345}
    assert tiny['status']=='passed' and tiny['raw_updates']==1171783680 and tiny['correct']=={'float':42,'integer':41,'packed':41}
    assert tiny['state_mismatches']==tiny['spike_mismatches']==0 and tiny['fixed16_hardware_domain_supported']
    glif_powers={key.split('/e')[1]:r for key,r in selected['accepted_power'].items() if key.startswith('glif/')}
    glif_energies={key:r['estimated_fixture_dynamic_pJ_per_scalar'] for key,r in glif_powers.items()}
    rep_energies={key:r['estimated_fixture_dynamic_pJ_per_scalar'] for key,r in rep['accepted_power'].items()}
    assert all(r['scalar_updates']==262528 for r in glif_powers.values())
    assert len({r['expected_operand_sha256'] for r in glif_powers.values()})==1
    for key,record in tradeoff['records'].items():
        fraction=record['energy_exact_fraction'];exact=float(Fraction(fraction['numerator'],fraction['denominator']))
        assert math.isclose(exact,glif_energies[key],rel_tol=0,abs_tol=1e-10)
        assert record['core_resources']==routes['selected'][key]['core']
        assert record['requests']==glif_powers[key]['requests'] and record['ROI_duration_ps']==glif_powers[key]['duration_ps']
    numbers={
        'GLIF_E5_vs_E4_energy_reduction_percent':100*(1-glif_energies['5']/glif_energies['4']),
        'GLIF_E5_vs_E3_energy_increase_percent':100*(glif_energies['5']/glif_energies['3']-1),
        'GLIF_E5_vs_E1_energy_reduction_percent':100*(1-glif_energies['5']/glif_energies['1']),
        'GLIF_E5_vs_E7_energy_reduction_percent':100*(1-glif_energies['5']/glif_energies['7']),
        'GLIF_E5_vs_E1_full_stream_issue_penalty_percent':100*(issues['adaptive_post']/issues['fixed_split2']-1),
        'GLIF_E5_vs_E4_full_stream_issue_reduction_percent':100*(1-issues['adaptive_post']/issues['fixed_scalar1']),
        'GLIF_E5_vs_E3_capture_issue_penalty_percent':100*(glif_powers['5']['requests']/glif_powers['3']['requests']-1),
        'GLIF_E5_vs_E4_capture_issue_reduction_percent':100*(1-glif_powers['5']['requests']/glif_powers['4']['requests']),
        'OTTT_representative_E5_vs_E1_energy_reduction_percent':100*(1-rep_energies['5']/rep_energies['1']),
        'OTTT_representative_E5_vs_E6_energy_increase_percent':100*(rep_energies['5']/rep_energies['6']-1),
        'OTTT_full_issue_penalty_percent':100*(full_ottt['adaptive_issues']/full_ottt['fixed_two_lane_issues']-1),
        'BNTT64_issue_penalty_percent':100*(tiny['adaptive_issues']/tiny['fixed_two_lane_issues']-1),
    }
    assert math.isclose(numbers['GLIF_E5_vs_E4_energy_reduction_percent'],100*tradeoff['E5_vs_E4']['energy_saving_fraction'],abs_tol=1e-10)
    assert math.isclose(numbers['GLIF_E5_vs_E3_energy_increase_percent'],100*tradeoff['E5_vs_E3']['energy_change_fraction'],abs_tol=1e-10)
    literals=[('12.3695','GLIF_E5_vs_E4_energy_reduction_percent',4),('1.0689','GLIF_E5_vs_E3_energy_increase_percent',4),
        ('60.9472','GLIF_E5_vs_E1_energy_reduction_percent',4),('82.6089','GLIF_E5_vs_E7_energy_reduction_percent',4),
        ('1.0836','GLIF_E5_vs_E1_full_stream_issue_penalty_percent',4),('46.0091','GLIF_E5_vs_E4_full_stream_issue_reduction_percent',4),
        ('8.1148','GLIF_E5_vs_E3_capture_issue_penalty_percent',4),('27.7876','OTTT_representative_E5_vs_E1_energy_reduction_percent',4),
        ('94.6139','OTTT_representative_E5_vs_E6_energy_increase_percent',4),('54.9444','OTTT_full_issue_penalty_percent',4),('27.0303','BNTT64_issue_penalty_percent',4)]
    for literal,key,precision in literals:
        assert f'{numbers[key]:.{precision}f}'==literal,(key,numbers[key],literal)
        where(literal)
    tables=re.findall(r'\\begin\{table\}.*?\\end\{table\}',text,re.S)
    assert len(tables)==2
    table_checks=[]
    for block in tables:
        is_energy='dynamic energy in pJ' in block
        for row in block.splitlines():
            if not re.match(r'^E\d ',row):continue
            cells=[c.strip() for c in row.removesuffix('\\\\').split('&')];assert len(cells)==4,row
            key=re.match(r'E(\d)',cells[0]).group(1)
            if is_energy:
                assert int(cells[1])==routes['selected'][key]['core']['DSP']
                assert cells[2]==(f'{glif_energies[key]:.3f}' if key in glif_energies else '--')
                assert cells[3]==(f'{rep_energies[key]:.3f}' if key in rep_energies else '--')
            else:
                core=narrow['E8_core'] if key=='8' else routes['selected'][key]['core']
                assert [int(x) for x in cells[1:]]==[core[x] for x in ('LUT','FF','DSP')]
            table_checks.append(dict(engine=int(key),table='energy' if is_energy else 'area',status='supported'))
    assert len(table_checks)==16
    unsafe_results={}
    for key,record in unsafe['records'].items():
        file=evidence.bind(record['hardware_scalar_NPZ_file'],record['hardware_scalar_NPZ_sha256'])
        with np.load(file) as a:U=a['U'].astype(np.int64);beta=a['beta'].astype(np.int64);saved=a['expected_leak'].astype(np.int64)
        exact=(U*beta+255)//256;wrapped=((U+256)%512)-256;wrong=(wrapped*beta+255)//256
        assert np.array_equal(exact,saved)
        count=int(np.count_nonzero((U<-256)|(U>255)));mismatches=int(np.count_nonzero(exact!=wrong))
        assert count==mismatches==record['signed9_domain_exclusion_count']==record['unsafe_leakage_mismatch_count']
        unsafe_results[key]=dict(operations=len(U),excluded_signed9=count,unsafe_mismatches=mismatches)
    assert unsafe_results['GLIF']['excluded_signed9']==2493
    first=unsafe['records']['GLIF']['first_mismatch']
    assert (first['U'],first['beta'],first['declared_full16_leakage'],first['unsafe_wrapped_leakage'])==(381,78,117,-39)
    # Reinspect counted datapath admission and the externally supplied source protocol.
    rtl=(W/'leak_core16.sv').read_text();bench=(W/'tb_native16.sv').read_text()
    assert all(x in rtl for x in ['wire fits0=','wire fits1=','wire same=coef0==coef1;',
        'wire pair_ok=(available==2)&&fits0&&fits1&&same&&((E==5)||(coef0>=64));',
        'else if(E==0||E==5)a_q<=pair_ok?packed9:full_a;','wire spill=p[16]^ref2;'])
    assert 'pos[e]=pos[e]+take[e];' in bench
    for needle in ['source queues, operand memory','re-present an unconsumed operand','not literal isolated controller area',
        'this is not a packing accuracy gain','not a network-accuracy experiment','fixed per channel except for previous-spike selection between two values',
        'specialized constant multiplier bank or CSD','does not establish absence or priority',
        'not an independently established novelty claim','We do not claim universal burst-latency improvement',
        'twelve passed, while both original-LUT E2','their energy is rejected','near energy parity is a resource trade-off']:
        where(needle)
    assert not re.search(r'comparisons are running|energy remain pending|scalar-DSP comparisons are running',text)
    assert narrow['combined_admission_and_wide_support_cost']=={'LUT':15,'FF':8,'DSP':0}
    verdict=('The final evidence supports one focused exact membrane-leakage primitive contribution: compact signed rounded decoding combined with real range-selected pair/full execution at fixed signed16 precision, and measured resource/rate/estimated-energy trade-offs. E4 closes the equal-one-DSP comparison with 12.37% lower estimated GLIF energy and fewer issues at added fabric; E3 preserves a two-DSP competing point near energy parity. This is credible material for an ISCAS primitive paper, not demonstrated universal superiority or a guaranteed strong-publication result. Generic value adaptation and fixed splitting are prior art; constant-specialized model hardware, external source integration, three unavailable full methods and failed E2 evidence remain explicit limits.')
    result=dict(status='pass_final_manuscript_scope_audit_with_explicit_failed_controls_and_limits',
        review_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),draft_file=str(draft.resolve()),audited_draft_sha256=draft_sha,
        draft_changed_during_audit=False,manuscript_edited=False,vendor_or_model_jobs_launched=False,process_control_performed=False,
        material_factual_or_numerical_errors_found=[],model_and_area_prior_pins_rehashed=len(reused),checked_evidence_hash_count=len(evidence.PINS),
        verification_scope='Rehashed unchanged prior model/area/source evidence; recomputed saved numeric/resource/accounting relations and unsafe scalar arithmetic; no inference, native, route, vendor or physical-SAIF rerun.',
        primary_comparison_gate=dict(status='pass',accepted=12,missing_primary=[],all14_attempted=True,all14_energy_accepted=False,failed_controls=['glif/e2','ottt/e2'],failed_energy_excluded=True),
        historical_scheduler_sequence_completion_claim=False,final_selected_evidence_file=str(selected_path),
        recomputed_numbers=numbers,GLIF_energy_pJ_per_scalar=glif_energies,OTTT_representative_energy_pJ_per_scalar=rep_energies,
        table_checks=table_checks,unsafe_narrow_counterfactual=unsafe_results,counterfactual_accuracy_or_energy_claim=False,
        one_integrated_contribution='Exact compact rounded-leakage decoder plus actual-membrane pair admission/full16 fallback and matched measured evaluation.',
        supporting_contribution_sentences=[
            'An overlapping signed DSP48E1 layout reconstructs exact rounded shared-coefficient leakage using a one-bit borrow reference and narrow quotient correction, with exhaustive signed9-pair and signed16-domain checks.',
            'The counted core selects eligible signed9 membrane pairs or exact full16 singleton execution using actual range and coefficient equality while retaining fixed integer storage; combined admission/wide-support overhead is15LUT/8FF against a restricted ablation.',
            'Matched accepted GLIF measurements expose one-DSP improvements versus scalar/fixed-split controls and a near-energy-parity half-DSP alternative to two scalar DSPs, while vanilla-LIF constant controls demonstrate the applicability boundary.'
        ],
        novelty_bounds=dict(fixed_split_independently_novel=False,generic_actual_value_packing_novel=False,first_ever_established=False,full_method_equivalence_closed=False,full_method_access_gaps=remaining,UDP_complete_method_inspected=True,UDP_original_PDF_acquired=False),
        fresh_closure=dict(UDP_method_inspected=True,remaining_originals=remaining,signed16_settled_wrong_max_age_ns=max(settled),original_LUT_precise_cause_resolved=False,original_LUT_energy_accepted=False),
        required_caveats=['Energy is vendor-estimated dynamic energy including common94FF fixture; not physical, static, board, memory or full-neuron energy.',
            'GLIF activity is a bounded64-image distribution-gated capture, not full-test or full-stream energy.',
            'GLIF has two precomputed coefficients per channel; a constant-bank/CSD alternative remains unmeasured.',
            'Source queues, zero filtering, window endpoints and variable-consumption integration are outside counted core resources.',
            'E5/E8 delta combines admission and wide support and is not isolated controller area.',
            'Exact packing preserves the declared integer neuron; FP32 conversion can change predictions; no packing accuracy gain.',
            'OTTTbeta128 shift wins energy; BNTTbeta253 exact shift/add hardware is unmeasured; AdEx is unvalidated.',
            'E3 is a competing resource/rate point; no universal superiority, complete-neuron burst latency or full-accelerator claim.',
            'Both original E2 controls fail delayed replay and supply no accepted energy; original causal diagnosis remains unresolved.'],
        conditional_paper_verdict=verdict,strong_ISCAS_acceptance_established=False,evidence_sha256=dict(sorted(evidence.PINS.items())))
    for file,pin in evidence.PINS.items():
        assert evidence.sha(file)==pin,('Evidence changed during audit',file)
    assert hashlib.sha256(draft.read_bytes()).hexdigest()==draft_sha,'Draft changed during audit; do not freeze mixed evidence.'
    prose=(f'This final additive audit binds the exact draft SHA256 `{draft_sha}`. It rehashed {len(reused)} unchanged prior model/area/source evidence bindings and {len(evidence.PINS)} total bindings, without editing the draft or rerunning inference, native execution, vendor tools or the physical activity audit. No material numerical or scope error was found.\n\n'
        'The final selection independently binds twelve accepted mandatory primary comparisons. All fourteen controls were attempted; GLIF/E2 and OTTT-stress/E2 failed delayed replay and have no accepted energy. The original interrupted scheduler snapshot is historical context, not a completed sequence. The selected primary gate passes, while complete all-control energy acceptance remains false.\n\n'
        'GLIF E5/E4/E3/E1/E7 energies are respectively21.5995/24.6484/21.3711/55.3084/124.1983pJ per scalar result. E5 reduces estimated energy12.3695% against the same-one-DSP E4, adding49LUT/15FF, and60.9472% against E1; it reduces82.6089% against E7. Versus E3, DSP count halves but estimated energy increases1.0689% and captured issues increase8.1148%. The complete64-image GLIF stream has46.0091% fewer issues than E4, distinct from the capture-specific45.9162%. Both energy and area tables agree with the explicit accepted routes and powers.\n\n'
        'The unsafe narrow-domain arithmetic diagnostic was independently recomputed from saved operands:2493GLIF exclusions each change their leakage result under forced low9-bit reinterpretation. It supports keeping exact full16 fallback, not a network-accuracy or energy claim. Exact integer arithmetic, packed model feedback and FP32 conversion remain distinct. The unfavorable94.6139% energy increase against the OTTT exact shift control is retained.\n\n'
        'Actual range/equality admission, packed/scalar selection and correction are inside the62LUT/44FF/one-DSP core. Source queues, operand presentation, re-presentation, stable zero filtering and boundary integration remain excluded. The15LUT/8FF E5-minus-E8 difference is combined admission and wide-support cost, not isolated controller area. GLIF selects two precomputed constants per channel; unmeasured constant-bank/CSD hardware limits model-specific superiority claims.\n\n'
        +verdict+'\n\n'
        'One integrated contribution is supported: the exact rounded leakage implementation/admission contract and measured applicability trade-offs. Fixed-split arithmetic and generic actual-value operation packing are not independently new contributions. Three original full methods remain unread; UDP complete rendered methods were inspected; priority or full equivalence closure is not established. Citation metadata and final ISCAS template cleanup remain submission tasks, not scientific novelty evidence.\n')
    atomic_write(out,(json.dumps(result,indent=2)+'\n').encode('utf-8'));atomic_write(md,prose.encode('utf-8'))
    print(json.dumps(dict(status=result['status'],audited_draft_sha256=draft_sha,rehashed_prior_pins=len(reused),total_pins=len(evidence.PINS),primary_accepted=12,failed_controls=result['primary_comparison_gate']['failed_controls'],numerical_errors=[],report=str(md))))

if __name__=='__main__':main()
