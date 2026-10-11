# Fixed16 membrane leakage evidence

Adaptive packing selects two signed9 membrane operations or one full signed16 operation from actual membrane values. Stored precision and integer units stay fixed.

Closure: **explicit_evidence_report_with_open_or_failed_gates**. The report does not certify ISCAS strength or first-ever novelty.

E5 uses 62 LUTs, 44 fabric FFs and 1 DSP; E1 fixed split uses 202 LUTs, 79 FFs and 1 DSP. This is 69.31% fewer LUTs and 44.30% fewer FFs under the common16bit/12ns/94FF fixture.

Zero arithmetic mismatches across 67,371,008 exhaustive narrow pairs, 16,842,752 full16 scalar cases and 16,842,752 fixed-split cases. Hardware protocol/timing and neural feedback are separately audited.

GLIF/CIFAR10: FP32 9403/10000, integer 9405/10000, 371 changed predictions from conversion. The64-image packed feedback has zero state/spike mismatches and identical integer logits. E5 uses 42,785,698 issues versus E1 42,327,032 (1.084% more).

OTTT/cifar10_T6_n64_a2: FP32 60/64, integer 60/64; exact packing preserves the declared integer outputs. Adaptive issue penalty against fixed two-lane: 55.500%. Full10k classification plus separate64 exact feedback.

OTTT/cifar10_full10000_a0: FP32 9349/10000, integer 9345/10000; exact packing preserves the declared integer outputs. Adaptive issue penalty against fixed two-lane: 54.944%. Full10k classification plus separate64 exact feedback.

BNTT/tiny_T30_n64_a2: FP32 42/64, integer 41/64; exact packing preserves the declared integer outputs. Adaptive issue penalty against fixed two-lane: 27.030%. Predeclared64 held-out subset, never full TinyImageNet accuracy.

Combined membrane admission/full16 support adds +15 LUTs, +8 FFs and +0 DSPs relative to restricted signed9 E8. This is not controller-only area.

Accepted representative energy comparisons:

- GLIF_E5_vs_E1: E5 21.599497 pJ/scalar; baseline 55.308385 pJ/scalar; E5 60.95% lower.
- GLIF_E5_vs_E3: E5 21.599497 pJ/scalar; baseline 21.371065 pJ/scalar; E5 1.07% higher.
- GLIF_E5_vs_E4: E5 21.599497 pJ/scalar; baseline 24.648376 pJ/scalar; E5 12.37% lower.
- GLIF_E5_vs_E7: E5 21.599497 pJ/scalar; baseline 124.198306 pJ/scalar; E5 82.61% lower.
- OTTT_representative_E5_vs_E1: E5 26.579628 pJ/scalar; baseline 36.807567 pJ/scalar; E5 27.79% lower.
- OTTT_representative_E5_vs_E6: E5 26.579628 pJ/scalar; baseline 13.657624 pJ/scalar; E5 94.61% higher.

These are vendor-estimated dynamic values for the common fixture and bounded arithmetic capture.

Open/rejected gates:

- main_energy: all_attempted_control_energy_incomplete; .
- original_E2_diagnostic: original_numerical_discrepancy_remains_unresolved; Both controls fail with the same first mismatch. The syntax defect is real but does not close the numerical discrepancy..

Both controls fail with the same first mismatch. The syntax defect is real but does not close the numerical discrepancy.

Prior-work review remains bounded by four inaccessible full methods. The plausible contribution is the exact rounded leakage decoder, actual-membrane admission, fixed stored precision and measured trade-offs. Neither packing alone nor equal integer accuracy establishes a strong paper.

The scope excludes board measurements, memory/filter costs, complete-neuron latency and AdEx. Beta128 shift and beta253 shift/add controls constrain where DSP packing is useful.

All explicit records and SHA256 bindings: `C:\Users\Ritesh\Documents\Codex\2026-10-08\oka\outputs\membrane_leakage_final_evidence_20261011.json`.
