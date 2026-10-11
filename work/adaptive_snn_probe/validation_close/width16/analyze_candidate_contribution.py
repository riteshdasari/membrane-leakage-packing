"""Source-only exact issue/admission ablations from retained whole64-image streams."""
from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent;TRIAL=P.parent.parent/'sequential_paper_trial'
BENCH=P.parent/'benchmarks';ACTIVITY=P.parent/'activity'
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
inputs=[Path(__file__),TRIAL/'stage3_results.json',TRIAL/'stage3_algebra.json',P/'domain_acceptance.json',BENCH/'cifar10_T6_n64_a2/results.json',ACTIVITY/'random_stratified_v2/results.json',ACTIVITY/'random_stratified_v2/representativeness_acceptance.json']
assert not(P/'candidate_contribution.json').exists()
glif=json.loads((TRIAL/'stage3_results.json').read_text());g=glif['total'];gi=g['issues']
ottt=json.loads((BENCH/'cifar10_T6_n64_a2/results.json').read_text());o=ottt['operation_counts']
assert glif['all_logits_bit_identical_to_integer_reference']and ottt['packed_vs_integer_logits_equal']
def row(name,raw,zero,N,narrow,adaptive,fixed_split,fixed2,scalar,pairs):
    assert raw-zero==N and scalar==N and adaptive==N-pairs
    return dict(workload=name,raw_updates=raw,zero_filtered=zero,arithmetic_operations=N,narrow9_operations=narrow,
        narrow9_fraction=narrow/N,adaptive_pairs=pairs,issues_adaptive=adaptive,issues_fixed_split=fixed_split,
        issues_fixed2=fixed2,issues_scalar=scalar,operations_per_adaptive_issue=N/adaptive,
        adaptive_issue_saving_vs_scalar=1-adaptive/scalar,
        adaptive_issue_overhead_vs_fixed_split=adaptive/fixed_split-1,
        adaptive_issue_overhead_vs_fixed2=adaptive/fixed2-1,
        coefficient_compatibility_issue_penalty=fixed_split-fixed2,
        membrane_admission_issue_penalty=adaptive-fixed_split,
        all_unfavorable_counts_retained=True)
rows=[row('GLIF ResNet18 CIFAR10 T2 channelwise',g['raw_operations'],g['zero_bypassed'],g['arithmetic_operations'],g['narrow9_arithmetic_operations'],gi['adaptive_post'],gi['fixed_split2'],gi['fixed_scalar2'],gi['fixed_scalar1'],g['post_pairs']),
      row('OTTT VGG11 CIFAR10 T6 vanilla LIF tau2',o['raw'],o['zero'],o['nonzero'],o['narrow'],o['issues_adaptive'],o['issues_fixed_split'],o['issues_LUT2'],o['issues_scalar'],o['pairs'])]
answer=dict(status='exact_count_ablation_no_new_hardware_claim',main_full_width=16,internal_pair_width=9,unchanged_unit=256,
    legal_domains=dict(U=[-32768,32767],beta=[0,256],pair_U=[-256,255],DSP_A_bits=25,DSP_B_bits=18,DSP_P_bits=48),
    source_sha256={str(p):sha(p)for p in inputs},workloads=rows,
    arithmetic_proof=dict(full16_product_range=[-32768*256,32767*256],ceil_output_fits_signed16=True,
         full_mode='sign-extend U16 into A25; P=A*beta+255; signed quotient P[23:8]',
         pair_mode='A=(U0+256)+(U1<<16), signed25; C=255-256beta+(255<<16); exact post spill recoveredfromP16 and modulo2reference',
         pair_admission='original-order head2 available, same beta, both U fit signed9. Otherwise consumeone signed16 value.',
         zero_filter='IdenticalstableU0orbeta0bypassgrantedallcontrolsoutsideprimitive',
         storage='full16 retained; narrow pair format neitherclipsnorchangesmembraneunit',
         fixed_split='U=(signed high8)*256+unsignedlow8; compute bothlow8 products inoneDSP plus2 fullhigh8 LUTproducts; exact ceil reconstruction'),
    publication_claim='A membrane-dependent exact pair/full mapping may reduce fabric corrections versus the general fixed one-DSP split control, at measured issue overhead. Generic DSP packing, exact spill tracking and basic carry recovery are established prior art.',
    policy_ablation_limits=['These are arithmetic issue counts, not end-to-end neuron latency; memory,filter throughputandhostoverheads excluded.',
        'The coefficient and range issue penalties are differences between complete greedy policies; they include matching-phase changes and are not independent per-edge probabilities.',
        'Costofrange detector alone isnotisolated by E5-versus-scalar hardware; thedifference includeslayoutanddecoderstorageandcannotbe calledpurecontrolleroverhead.',
        'OTTT beta128 arithmetic hasanexactzero-DSPshiftcontrol; beating a generalvariable multiplier there isinsufficient.'],
    needed_physical_ablation='Ifcontroller-only costisclaimed, synthesize a separate always-pair signed9-only admittedcaller datapath withsame94FFfixtureandnarrowlegalcontract; itsresourcescannotreplacefull16strongbaseline. Notrunhere.',
    applicability='Coefficient-controlled leakage usefulonlywheretrained dynamicsrequiremultiplication. Shift-only tau2 isretainednegativecontrol; nocoefficient/modelretuningforbenefit.')
(P/'candidate_contribution.json').write_text(json.dumps(answer,indent=2)+'\n')
lines=['# Candidate contribution and exact policy ablations','',
    'The candidate keeps a fixed signed16 membrane interface and unchanged voltage units. It packs two signed9 membrane leakage operations when both actual values fit and their coefficients match; otherwise it issues one full signed16 operation. Range-aware admission is membrane-potential-aware here because it examines the actual stored state.', '',
    'The full mode is exact for U in [-32768,32767] and beta in [0,256]. The product is in [-8388608,8388352]; adding255 and dividing by256 with arithmetic shift implements ceil without widening the stored membrane. The resulting leakage fits signed16. The existing signed9 packed algebra remains unchanged.', '',
    'The two-lane multiplicand fits the DSP48E1 signed25 input: nine upper lane bits start at bit16, while the lower biased membrane occupies nine bits. Full16 mode simply sign-extends into the same physical DSP port. The fixed split control instead uses two low8 products in the DSP and two signed high8 products in LUTs. The widening from the historical signed12 interface increases those high-part fabric products; their actual resource cost must be measured.', '']
for r in rows:
    lines += [f'For {r["workload"]}, the complete64-image stream contains {r["arithmetic_operations"]:,} arithmetic updates after the common zero bypass. {100*r["narrow9_fraction"]:.4f}% fit signed9.', '',
        f'- Adaptive: {r["issues_adaptive"]:,} issues; {r["operations_per_adaptive_issue"]:.6f} results per DSP issue.',
        f'- Fixed split: {r["issues_fixed_split"]:,} issues; adaptation adds {100*r["adaptive_issue_overhead_vs_fixed_split"]:.4f}%.',
        f'- Independent fixed two-lane control: {r["issues_fixed2"]:,} issues; adaptation adds {100*r["adaptive_issue_overhead_vs_fixed2"]:.4f}%.',
        f'- Scalar DSP: {r["issues_scalar"]:,} issues; adaptation removes {100*r["adaptive_issue_saving_vs_scalar"]:.4f}%.', '',
        f'Coefficient compatibility costs {r["coefficient_compatibility_issue_penalty"]:,} issues relative to independent fixed two-lane operations. Membrane admission costs another {r["membrane_admission_issue_penalty"]:,} issues relative to fixed split. These differences include greedy matching phase; they are policy ablations, not independent event probabilities.', '']
lines += ['The GLIF stream is favorable to pair admission, while the vanilla LIF stream has many wider states. The vanilla model also uses beta128, for which ceil(U/2) has an exact shift-only implementation. Its shift baseline is essential; the paper must retain the unfavorable result if adaptation loses to it.', '',
    'The possible contribution is the exact membrane-driven admission policy and implementation trade-off under a general coefficient contract. Carry correction and generic DSP packing should not be claimed as inventions. Measured signed16 area/energy results and the final equivalence audit must support the claim before describing it as a hardware advantage.', '',
    'Controller overhead has not been isolated. E5-versus-scalar resource differences include admission, operand layout, result decoding and registers. A dedicated always-pair signed9-only ablation could isolate admission cost, but it would have a narrower caller contract and could not replace the signed16 controls.', '',
    f'Evidence: `candidate_contribution.json`, SHA256 `{sha(P/"candidate_contribution.json")}`.', '']
(P/'candidate_contribution.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps(dict(status=answer['status'],workloads=rows),indent=2),flush=True)
