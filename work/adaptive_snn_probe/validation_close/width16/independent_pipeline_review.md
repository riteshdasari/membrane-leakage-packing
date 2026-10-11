# Independent fixed16 and E7 pipeline review

The source and software review found no serious correctness issue that requires stopping the prepared vendor runs. This is a review of the prepared pipeline and operand evidence; it is **not** acceptance of routes, delayed replay, or power jobs that have not finished.

## Independently checked evidence

`independent_pipeline_checks.py` uses an independent quotient/remainder expression to regenerate all scalar leakage outputs and recomputes frame-respecting greedy request counts. All **705,277** prepared operations pass across general coverage, shift128 coverage, actual128, and actual GLIF cohorts. Every stimulus line's U, beta, and frame-end field matches the pinned expected operand data. All **74** file-hash checks in the five current preparation/domain manifests match. The six reviewed native/energy/auditor Python files parse successfully.

The actual GLIF cohort contains262,528 scalar leakage operations and2,176 frames. Its independently reproduced request counts for E0..E5 are141,985;140,465;131,328;131,328;262,528;141,985. E7's fixed two-lane admission therefore expects131,328 requests. These counts show that E5 does not claim lower issue count than the fixed two-lane controls for this cohort; any benefit must come from accepted area/energy/resource evidence and its declared comparison.

## E7 identity and mapping

The E7 testbench has seven native slots, with `.E(g==6?7:g)`. Slots0..5 retain their original identity; native slot6 instantiates implementation E7, not the beta128-only E6. The v2 native acceptance row records `engine=7,native_index=6`. The E7 energy runner and independent auditor both bind that row to `trace6.txt`. The expected request count comes from fixed2 oracle index2. Metadata and narrow-mode checks treat E7 as fixed packing, never as adaptive E5.

E7 extracts the signed product's quotient bits and adds reduction-OR of its remainder byte. Its unsigned B-bit addition is intentionally modular and is valid here: the extracted bits are the B-bit two's-complement floor quotient, adding zero or one produces the exact B-bit ceiling result, and the beta0..256 contract proves the output remains in the signed16 range. Beta256 bypasses the low-byte multiplier. The independent full-domain proof in `../lut_isolation/ceil_identity.json` covers16,842,752 cases with zero mismatches. The new E7 control changes exact rounding topology; it does not relax original E2's timing replay requirements or explain its unresolved timing-model behavior.

## Scalar, admission, and payload checks

Both independent power auditors compare **each accepted source operand** and beta with the pinned NPZ workload. They verify frame-end availability before pairing; E1 additionally requires equal coefficients, E0/E5 require both actual membranes in signed9, and E0 retains its coefficient restriction. Every retired payload is compared against independent integer ceil arithmetic, with count, order, narrow metadata, natural two-edge latency, request totals, and scalar totals verified. E6 is accepted only for the actual128 cohort with every beta=128.

The main and E7 route fixtures both preserve55 launch FFs plus39 capture FFs. Core area excludes these94 fixture FFs, while energy includes the complete matched fixture. Golden replay proves the two-row fixture offset before delayed replay. All known native rows are compared, including controls and invalid-row payload values; valid-output counts are checked independently.

## SAIF interval and energy denominator

At12 ns, SAIF begins1 ps before the replay falling edge for first native acceptance:

```
start = 132000 + first_accept * 12000 - 1 ps
duration = (last_retire - first_accept + 3) * 12000 ps
```

The extra fixture rows include the final captured output. The independent auditor reconstructs first/last from accepted and retired traffic, matches the exact interval and SAIF duration, checks the full clock transition count, and requires a drained scoreboard. No zero-valued operations are removed from the denominator. Estimated dynamic energy per scalar update is `dynamic_W * duration_ps / scalar_updates`, which has pJ units. The reported scope correctly includes fixture clock/register activity and excludes claims about measured board energy or an entire SNN neuron update.

Delayed replay must successfully annotate the unchanged routed SDF, reproduce all rows, and pass timing-diagnostic checks. The auditor explicitly checks max-delay and transport-interconnect options, the four zero pulse options, and absence of `notimingchecks`, `nospecify`, or SDF warning/error suppression. Failed runs cannot reach accepted energy.

## Physical activity completeness

The power auditor requires every physical design net to map and every physical alias to appear in the activity report. Sampled source(S) activity is checked against SAIF static probability, transitions, and interval; unknown physical activity is rejected. Clock source(C) requires the connected clock with the correct rate. Default source(D) is allowed only when primitive connectivity proves a constant, including a directly clocked, enabled FF fed by a proved constant with inactive reset. Other activity-source classes are rejected. DSP clock/CE sources are checked explicitly. Name normalization is verified to preserve times, transition counts, instance paths, and duration, and to change only the documented escaped-name tokens.

## Provenance hardening and limits

The current numerical inputs, RTL, testbenches, export/power Tcl, route checkpoints, replay outputs, and audits are pinned or transitively verified. The native/energy job manifests do not consistently include hashes of the imported execution helper `run_selective_energy.py` and installed `glbl.v`. This is a reproducibility hardening gap, rather than a detected arithmetic or activity error. `independent_execution_source_snapshot.json` records their **review-time** hashes and those of the normalization/audit helpers; it does not retroactively prove which helper bytes ran in an earlier job. Frozen preparation/runners were left unchanged.

Acceptance still requires actual job completion and all strict auditors to pass. The review does not claim complete FPGA model inference merely because captured model operands pass a primitive. Public benchmark model accuracy, integerized update equivalence, and sampling representativeness remain separate evidence.

## Prior-work conclusion retained

The completed primary-source audit is `../prior_art/equivalence_audit.md`. Generic DSP packing, exact spill correction, and operand-value-driven width admission have substantial prior art. E5's specialized membrane-leakage quotient extraction, modulo2 spill recovery, admission policy, and measured implementation must be described narrowly. A full first-ever/no-equivalent claim is not supported: the ICFPT2024 six-signed paper and some dynamic-packing papers' complete methods remain access-limited, and the UDP repository review cannot replace inaccessible paper sections. A narrow contribution may remain plausible; priority and hardware benefit must be stated with these boundaries.
