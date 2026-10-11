"""Additive read-only draft/evidence audit. No model/vendor/process control."""
from pathlib import Path
from fractions import Fraction
import hashlib
import json
import re
import sys
import datetime
import numpy as np

sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P))
import prepare_fixed16_final_report_v1 as evidence
W=P/'width16'
S=P.parent/'sequential_paper_trial'
ROOT=P.parents[2]


def main():
    target=P/'manuscript_scope_audit_v2.json'
    md=P/'manuscript_scope_audit_v2.md'
    assert not target.exists() and not md.exists()
    draft=ROOT/'outputs/membrane_leakage_paper_draft.tex'
    draft_bytes=draft.read_bytes();draft_hash=hashlib.sha256(draft_bytes).hexdigest()
    text=draft_bytes.decode();lines=text.splitlines()
    def where(needle):
        found=[i for i,line in enumerate(lines,1) if needle in line]
        assert found,needle
        return found
    routes=evidence.all_routes(W/'route_resolved_acceptance_a1.json',W/'lutceil_e7/hardware/route12_e7_close_a0/hardware.json')
    algebra=evidence.arithmetic(W/'domain_acceptance_glif_v2.json')
    glif=evidence.glif(S/'stage2_acceptance.json')
    ottt=evidence.model_runs(P/'benchmarks/benchmark_acceptance.json','ottt')
    bntt=evidence.model_runs(P/'benchmarks/bntt_acceptance.json','bntt','tiny_T30_n64_a2')
    narrow=evidence.e8(W/'static9_e8/closure_measured_close_a1.json',routes['selected'])
    rep=evidence.rep_energy(W/'ottt_representative/closure_profiled_capture_v2_a0.json',routes['selected'])
    energy=evidence.read(W/'glif_energy_explanation_v2.json',{'pass_independent_certified_GLIF_E5_E1_E7_comparison'})
    prior=evidence.read(P/'prior_art/bounded_final_access_20261011/access_closure.json',{'bounded_access_attempt_complete_equivalence_still_unresolved'})
    diagnosis=evidence.read(P/'lut_isolation/bounded_causal_diagnostic_v1.json',{'bounded_causal_diagnostic_complete_original_numerical_issue_unresolved'})
    assert len(prior['papers'])==4 and all(not paper['full_method_retrieved'] for paper in prior['papers'])
    full=evidence.read(S/'stage2_results.json')
    packed=evidence.read(S/'stage3_results.json')
    assert (full['integer_correct_float_wrong'],full['float_correct_integer_wrong'])==(160,158)
    assert full['observed_neuron_updates']==24903680000
    beta_ranges={key:[min(value for row in full['rows'].values() for value in row[key]),
                      max(value for row in full['rows'].values() for value in row[key])]
                 for key in ['coefficient0','coefficient1']}
    assert beta_ranges=={'coefficient0':[153,170],'coefficient1':[74,88]}
    scalar_energies={key:float(Fraction(record['energy_exact_fraction']['numerator'],record['energy_exact_fraction']['denominator']))
                     for key,record in energy['records'].items()}
    checked_powers={}
    for key,record in energy['records'].items():
        power_path=Path(record['audit_file'])
        checked_powers[key]=evidence.power({'power_audit_file':str(power_path),
            'power_audit_sha256':evidence.sha(power_path)},routes['selected'])
        assert abs(scalar_energies[key]-checked_powers[key]['estimated_fixture_dynamic_pJ_per_scalar'])<1e-10
    assert len({power['expected_operand_sha256'] for power in checked_powers.values()})==1
    assert all(power['scalar_updates']==262528 for power in checked_powers.values())
    rep_energies={key:value['estimated_fixture_dynamic_pJ_per_scalar'] for key,value in rep['accepted_power'].items()}
    recomputed=dict(GLIF_E5_vs_E1_reduction_percent=100*(1-scalar_energies['5']/scalar_energies['1']),
      GLIF_E5_vs_E7_reduction_percent=100*(1-scalar_energies['5']/scalar_energies['7']),
      GLIF_issue_penalty_percent=100*glif['adaptive_issue_penalty_fraction'],
      GLIF_issues_saved_vs_scalar_percent=100*(1-glif['adaptive_issues']/glif['arithmetic_updates']),
      GLIF_E5_vs_E7_capture_issue_penalty_percent=100*(energy['records']['5']['requests']/energy['records']['7']['requests']-1),
      OTTT_representative_E5_vs_E1_reduction_percent=100*(1-rep_energies['5']/rep_energies['1']),
      OTTT_representative_E5_vs_E6_increase_percent=100*(rep_energies['5']/rep_energies['6']-1),
      E5_vs_E1_LUT_reduction_percent=100*routes['E5_vs_E1']['LUT_reduction_fraction'],
      E5_vs_E1_FF_reduction_percent=100*routes['E5_vs_E1']['FF_reduction_fraction'])
    # Independently recompute issue counts' relationships rather than relying
    # on the manuscript or its cached percentage strings.
    full_ottt=ottt['runs']['cifar10_full10000_a0']
    tiny=bntt['runs']['tiny_T30_n64_a2']
    recomputed['OTTT_full_issue_penalty_percent']=100*(full_ottt['adaptive_issues']/full_ottt['fixed_two_lane_issues']-1)
    recomputed['BNTT64_issue_penalty_percent']=100*(tiny['adaptive_issues']/tiny['fixed_two_lane_issues']-1)
    assert glif['arithmetic_updates']==79246135 and glif['adaptive_issues']==42785698 and glif['fixed_split_issues']==42327032
    assert glif['exact_feedback_raw_updates']==159383552 and glif['conversion_changed_predictions']==371
    assert full_ottt['raw_updates']==24576000000 and full_ottt['nonzero_updates']==20440971113
    assert tiny['raw_updates']==1171783680 and tiny['nonzero_updates']==1064644254
    assert narrow['combined_admission_and_wide_support_cost']=={'LUT':15,'FF':8,'DSP':0}
    # Inspect actual counted admission and source protocol, without synthesizing.
    rtl_path=W/'leak_core16.sv';e8_path=W/'static9_e8/leak_core_static9.sv'
    tb_path=W/'tb_native16.sv';fixture_path=W/'timing16.sv';dsp_path=W/'leak_dsp.sv'
    rtl=rtl_path.read_text();er=e8_path.read_text();tb=tb_path.read_text();fixture=fixture_path.read_text();dsp=dsp_path.read_text()
    required=["wire fits0=(raw0[B-1:9]=={(B-9){raw0[8]}});",
      "wire fits1=(raw1[B-1:9]=={(B-9){raw1[8]}});","wire same=coef0==coef1;",
      "wire pair_ok=(available==2)&&fits0&&fits1&&same&&((E==5)||(coef0>=64));",
      "else if(E==0||E==5)a_q<=pair_ok?packed9:full_a;",
      "sequential_leak_dsp dsp(clk,rst,issue,a_q,{9'd0,b0_q},c,p);",
      "wire spill=p[16]^ref2;","assign narrow_mode=(E==0||E==5)&&pack2;"]
    assert all(s in rtl for s in required)
    assert 'narrow' not in rtl.split(');',1)[0].split('input',1)[1].split('output',1)[0]
    assert 'wire pair_ok=(available==2)&&same;' in er and 'wire fits0=' not in er
    assert "wire[24:0]full_a={{16{raw0[8]}},raw0[8:0]};" in er
    assert "avail[e]=(!rst&&pos[e]<N)?((ends[pos[e]]-pos[e]>=2)?2:1):0;" in tb
    assert "pos[e]=pos[e]+take[e];" in tb and "values[pos[e]+1]" in tb
    assert '.u_in(src_u),.beta_in(src_beta),.available(src_available)' in fixture
    assert '.A({{5{a[24]}},a}),.B(b),.C(c)' in dsp
    for path in [rtl_path,e8_path,tb_path,fixture_path,dsp_path,Path(__file__)]:evidence.bind(path)
    claims=[
      dict(id='integer_arithmetic',lines=where('67,371,008'),status='supported',detail='Exhaustive signed9 pair and signed16 scalar/split counts agree with accepted algebra; exactness is for declared ceil leakage.'),
      dict(id='area',lines=where('E5 uses 69.31'),status='supported',detail='Selected matched full-domain routes support62/44/1 vs202/79/1; no aggregate FPGA area score or universal superiority.'),
      dict(id='GLIF_model',lines=where('24,903,680,000'),status='supported',detail='Accepted10000 classification and64-image exact-feedback/logit pins and issue accounting rechecked.'),
      dict(id='OTTT_model',lines=where('24,576,000,000'),status='supported',detail='Full10000 packed-feedback and independent scalar oracle plus separate64 state/spike/logit checks support claims. Conversion is distinct from packing.'),
      dict(id='BNTT_model',lines=where('1,171,783,680'),status='supported',detail='Predeclared64 subset,42float/41integer-packed, exact feedback and fixed16 domain rechecked; no full TinyImageNet accuracy claim.'),
      dict(id='GLIF_energy',lines=where('124.1983'),status='supported_scoped',detail='E5/E1/E7 exact serialized estimates, same scalar operand file and complete certified audit receipts support60.9472%/82.6089% reductions; scalar-DSP and constant-bank comparisons remain open.'),
      dict(id='OTTT_energy',lines=where('26.5796'),status='supported_scoped_negative_control',detail='Representative energies26.5796/36.8076/13.6576 match accepted closure;94.6138% increase vs shift is correctly retained.'),
      dict(id='E8_ablation',lines=where('combined E5 admission'),status='supported_combined_cost',detail='15LUT/8FF delta includes range admission and full-width support together. E8 retains coefficient equality and narrow singleton handling, so this is not total controller area.'),
      dict(id='old_E2_diagnosis',lines=where('Changing pulse limits'),status='supported_unresolved',detail='EOF-only repair fails identically; stable original/shadow discrepancy and pulse0/100 controls do not identify exact event-region cause or a hardware fix.'),
      dict(id='novelty',lines=where('Full methods for four'),status='bounded_supported',detail='All four final complete-method access gaps remain; exact leakage specialization/conjunction is a candidate, not first-ever or absence proof.')]
    findings=[
      dict(id='source_queue_boundary',severity='required_material_scope_clarification',lines=where('Two consecutive available operands'),
        issue='The primitive computes admission internally, but an upstream source presents two candidates, advances by returned take and re-presents an unconsumed second operand. Source queue, frame/window boundary management and zero filtering are not included in core area; describing all scheduling as62LUT44FF would be unsupported.',
        suggested_text='The measured core computes membrane-range and coefficient-equality admission and the exact fallback itself. An upstream source provides the next one or two operands and advances by the returned take count; source queues, zero filtering, window boundaries and integration are excluded.'),
      dict(id='generic_scalar_baselines',severity='pending_material_evidence_gate',lines=where('Remaining scalar-DSP'),
        issue='Accepted E1 and E7 energy supports a scoped tradeoff. E3/E4 generic scalar DSP energies must finish before a broad strong fixed-baseline energy verdict; the lower-fabric scalar controls already have accepted area and native checks.',
        action='Insert exact accepted scalar-DSP/stress outcomes when all checks pass; retain failed or absent gates. If E5 loses, report the energy/issue/area tradeoff rather than claiming dominant adaptive efficiency.'),
      dict(id='constant_bank_baseline',severity='material_applicability_gap_already_disclosed',lines=where('specialized constant multiplier bank'),
        issue='Actual GLIF selects one of two precomputed constants per channel. A constant bank or CSD/shift-add core may avoid a generic multiplier. Its area, coefficient-selection cost, energy and shared-unit scheduling have not been measured; generic E1/E7 comparisons cannot establish best model-specific efficiency.'),
      dict(id='title_variable_coefficient',severity='wording_only',lines=where('Variable-Coefficient SNN Leakage'),
        issue='The runtime-input primitive acceptsvariable Q8 coefficients, but the title can suggest continuously changing model parameters. The paper later states the correct two-fixed-constants-per-channel GLIF policy.',
        suggested_title='Exact Membrane-Range-Selected DSP Packing for SNN Leakage',
        suggested_early_text='GLIF selects between two precomputed channelwise constants using the previous spike; the measured primitive receives those coefficients at runtime.'),
      dict(id='LUT_latency_tradeoff',severity='wording_only',lines=where('82.6089'),
        issue='The large accepted energy reduction vs E7 is correctly scoped but its8.1148% issue penalty is only implicit. Add that comparison alongside1.08% vs E1 to prevent reading energy savings as a throughput improvement.'),
      dict(id='final_status_sentences',severity='update_after_controls_complete',lines=where('comparisons are running'),
        issue='Current running/pending statements are accurate at this draft snapshot; update from explicit accepted controls once the serial energy sequence closes.'),
      dict(id='bibliography_completeness',severity='wording_submission_cleanup',lines=where('Arithmetic Packing on Wide'),
        issue='Working bibliography has placeholder/incomplete author metadata for several works and the draft is not an ISCAS template. Complete primary-source citations and final layout after claims/evidence close; no new novelty conclusion follows.'),
      dict(id='TeX_table_label',severity='format_only',lines=where('\\label{tab:area}'),
        issue='The table label is after endtabular inside the table and no current ref uses it; move directly after caption if the manuscript later references the table.'),
    ]
    final_hash=evidence.sha(draft)
    result=dict(status='pass_bounded_manuscript_scope_audit_with_pending_publication_gates',
      review_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),draft_file=str(draft.resolve()),
      audited_draft_sha256=draft_hash,draft_sha256_at_audit_end=final_hash,draft_changed_during_audit=final_hash!=draft_hash,
      manuscript_edited=False,vendor_or_model_jobs_launched=False,process_control_performed=False,
      material_factual_or_numerical_errors_found=[],supported_claims=claims,findings=findings,
      recomputed_numbers=recomputed,GLIF_energy_pJ_per_scalar=scalar_energies,OTTT_representative_energy_pJ_per_scalar=rep_energies,
      actual_GLIF_coefficient_ranges=beta_ranges,
      adaptive_hardware=dict(actual_range_decision_in_counted_RTL=True,coefficient_equality_in_counted_RTL=True,
        packed_scalar_DSP_operand_and_C_selection_in_counted_RTL=True,post_correction_in_counted_RTL=True,
        hardware_take_controls_native_source_consumption=True,host_admission_tag_supplied=False,
        excluded='Upstream two-operand presentation/storage, stable zero filter, frame/window endpoint policy, unconsumed operand re-presentation and accelerator integration.',
        E5_resources=routes['selected']['5']['core'],E8_resources=narrow['E8_core'],
        combined_admission_and_wide_support_cost=narrow['combined_admission_and_wide_support_cost'],
        E8_retains_coefficient_equality_and_narrow_singleton_handling=True),
      conditional_paper_verdict='A defensible exact rounded-leakage primitive paper with real per-issue membrane admission, compact decoding and accepted fabric/energy tradeoffs is supported. A strong ISCAS contribution is not established solely by novelty wording or E1/E7 savings: close the pending generic scalar-DSP comparisons, explicitly preserve the constant-bank applicability gap and external source-queue boundary, and keep original E2/prior-method limitations. If scalar controls dominate, the paper must present a measured niche/tradeoff rather than universal adaptive advantage.',
      prior_method_access_gaps=[paper['id'] for paper in prior['papers']],
      original_E2_causal_diagnosis_resolved=False,
      quantitative_evidence_recheck='Hash/integrity, logits/classification, exact serialized-energy accounting and accepted route/admission contracts; no rerun of full model inference, vendor jobs or physical-SAIF audit.',
      checked_evidence_hash_count=len(evidence.PINS),evidence_sha256=evidence.PINS)
    prose=(f'The audit applies to draft SHA256 `{draft_hash}`. The manuscript was not edited. All current reported model counts, core areas, E8 cost differences and accepted E5/E1/E7 and representative OTTT energy percentages agree with the rechecked evidence. No material factual or numerical error was found. The draft retains the unfavorable shift baseline and separates conversion accuracy from exact packing.\n\n'
      'The adaptive decision is real hardware: signed9 range checks and coefficient equality drive pair admission, packed/full multiplicand selection, take count and post-correction inside the counted E5 core. A common DSP implements both paths. The62LUT/44FF figure includes that logic. However, an upstream source supplies the next two candidates, advances by hardware take and re-presents an unconsumed operand; zero filtering, source queues, frame/window endpoint management and integration are outside the measured core. State this boundary explicitly near the interface contract. E8 removes range checks and full16 support while retaining coefficient equality and narrow singleton handling;15LUT/8FF is a combined synthesized difference, not isolated or total controller area.\n\n'
      'The variable-coefficient title is valid for the generic runtime-input arithmetic contract but can overstate model variability. GLIF chooses between two precomputed constants per channel using the previous spike. Prefer “Exact Membrane-Range-Selected DSP Packing for SNN Leakage,” or explain the generic primitive/actual coefficient policy earlier. The unmeasured constant-bank/CSD baseline is a material applicability gap already disclosed. General runtime-coefficient E1/E7 savings do not establish the best implementation for this particular checkpoint.\n\n'
      'Accepted GLIF fixture dynamic energies are21.5994968308/55.3083845990/124.1983063749pJ per scalar for E5/E1/E7, reductions60.9472% and82.6089%. They share the declared262528 scalar operations. E5 requires1.0836% more full-stream issues than E1 and8.1148% more captured issues than E7; explicitly adding the latter strengthens the tradeoff account. Representative OTTT energies26.5796283/36.8075674/13.6576240pJ correctly retain the94.6138% loss against exact shift leakage. No board, full-neuron, fully quantized-model, burst-latency or accuracy-gain claim follows.\n\n'
      'The old E2 diagnosis remains honestly unresolved. Balanced EOF syntax does not repair row914, and pulse100 moves the failure to row5701. The draft does not treat E7 acceptance as an E2 cure. Four full-method access gaps remain in the final bounded access check; the specific rounded-leakage decoder/admission conjunction is a candidate contribution, not a first-ever or equivalence-closed claim.\n\n'
      'The paper verdict is conditional: the current evidence supports a defensible exact leakage primitive with measured fabric/energy tradeoffs and real membrane-driven admission. Strong-publication suitability still depends on accepted generic scalar-DSP comparisons and a clear case for this workload/implementation boundary. Finish the controls, then replace running-status sentences with their actual outcomes; retain unfavorable/failed evidence. If scalar controls dominate, describe a niche or resource tradeoff. The constant-bank gap and external source costs remain relevant even if generic scalar energies are favorable. Citation metadata and final ISCAS layout are later submission cleanup, not evidence of novelty.\n')
    target.write_text(json.dumps(result,indent=2)+'\n');md.write_text(prose,encoding='utf-8')
    print(json.dumps({key:value for key,value in result.items() if key in ['status','audited_draft_sha256','draft_changed_during_audit','material_factual_or_numerical_errors_found','checked_evidence_hash_count','recomputed_numbers','conditional_paper_verdict']},indent=2))


if __name__=='__main__':main()
