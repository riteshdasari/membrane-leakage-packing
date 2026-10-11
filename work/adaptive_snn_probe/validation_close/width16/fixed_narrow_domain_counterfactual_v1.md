# Why a signed9-only kernel cannot replace the fixed16 contract

This is an explicitly unsafe, arithmetic-only counterfactual. It discards the upper membrane bits and interprets the low9 bits as signed9, then computes `ceil(beta*U_wrapped/256)`. That changes the declared operation. E8's legal input domain remains signed9; this is neither a fair E8 hardware baseline nor an SNN accuracy experiment. No counterfactual values feed a neuron model.

The saved accepted GLIF and OTTT representative scalar NPZs, cohort records, capture records and all their source/artifact hashes were verified. The hardware-cohort U/beta/reference arrays match the accepted capture NPZ arrays exactly. Ordinary Python integer ceiling arithmetic independently agrees with vectorized arithmetic for every one of the524,672 saved operands. Both captured workloads contain only arithmetic after common zero filtering, so U and beta are nonzero.

- **GLIF:**2,493 of262,528 captured operands (0.949613%) lie outside signed9. Forcing signed9 reinterpretation changes all2,493 leakage results; maximum absolute deviation is336 integer membrane units. The first case is U381, beta78: the declared leakage is117, while wrapped U−131 produces−39, a deviation of156. These are unweighted captured-window counts rather than fullnetwork prevalence.
- **OTTT:**123,385 of262,144 captured operands (47.067642%) lie outside signed9. Forcing signed9 reinterpretation changes all123,385 leakage results; maximum absolute deviation is3,328 units. The first case is U−321, beta128: the declared leakage is−160, while wrapped U191 produces96, a deviation of256.

The count identity has a direct arithmetic explanation. `U-U_wrapped=512*k`; therefore the exact leakage difference is `2*beta*k`, including negative U and ceiling boundaries. Nonzero beta makes every genuinely wide operand produce a different result under this wrapping counterfactual. This identity was checked for every saved operand.

Rare wide values still require correct handling. The GLIF sample is99.050387% signed9, yet dropping its wide fallback would change actual scalar leakage results. Full16 fixed split and LUT controls remain valid alternatives; the diagnostic does not establish that adaptation is the only solution. E5 retains exact scalar fallback, whereas E8 is useful solely as a restricted-domain area ablation.

Exact GLIF hardware scalar NPZ SHA256:`07f68efe215e9e0dd8c70a009f97cca8c6a7cf8d3c7bc5de33062a4302b2d3eb`. Exact OTTT hardware scalar NPZ SHA256:`104bd42a79584bb59525935844bbdfe521f2d0b72a0e84f1ba371bb9cf6b0af4`. The complete source receipts, first/max cases and independent counts are in `fixed_narrow_domain_counterfactual_v1.json`; its executable source is `check_fixed_narrow_domain_counterfactual_v1.py`.

No FP32 conversion, classification change, counterfactual state recurrence, hardware correctness, timing or energy is inferred from these arithmetic differences. No accepted result, source model, coefficient, unit, gate or final-report requirement was changed.
