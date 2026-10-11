# Fixed16 evidence closure outline

This is a source-only handoff and acceptance map, not a declaration that all experiments have finished. All main hardware comparisons use signed16 membrane ports and fixed stored integer units, coefficients0..256 in Q8,12ns, Artix7 xc7a100tcsg324-1, two advancing edges of core latency and a common94FF launch/capture fixture. Signed9 is an internal pair-admission domain; it is not a change of stored precision. Exactness is relative to each declared integer neuron update. Float-to-integer conversion remains a separate accuracy measurement.

## Arithmetic and fixed-domain coverage

- `domain_acceptance_glif_v2.json` pins general signed16 scalar/fixed-split exhaustion, beta128 shift exhaustion, original narrow-pair proof and all prepared cohorts. Scalar and split cases each cover16,842,752 U/β combinations; shift covers65,536 U values. `sequential_paper_trial/stage3_algebra.json` retains67,371,008 exact post-correction pair cases.
- `preparation_v2.json` is the current main source pin set. `preparation.json` is an earlier precompile preparation and must not substitute forv2. The original E2 LUT block remains byte-identical in `leak_core16.sv`.
- `hardware/native_general_s0_a0/acceptance.json` and `native_general_s1_a0/acceptance.json` must pass every independent arithmetic/count/protocol check. Native source/reference data hashes, rows, natural unstalled latency2 and stalled output stability are required.
- `native_shift128_s0_a0` and `native_shift128_s1_a0` separately validate E6. E6 is legal only forbeta128; the generic coefficient controls must remain in the comparison.

## Public model fidelity and width

- GLIF ResNet18/CIFAR10T2: `sequential_paper_trial/stage2_acceptance.json` reports10,000-image declared-integer validation, old-state bounds[-1378,1529] and next-state bounds[-2038,1752], so this workload fits fixed16 without rescaling. Its integer conversion differs from the floating model on371 predicted classes; this is not packing error. `stage3_results.json` and `stage3_logits.npz` supply64-image separate packed-feedback equality and every checked state/spike arithmetic result. These are different fidelity gates and must not be conflated.
- Vanilla LIF: `benchmarks/ottt_contract.md`, `ottt_source_manifest.json` and `cifar10_T6_n64_a2/results.json` pin published OTTT VGG11/CIFAR10T6, tau2, unit256, beta128, threshold≥, immediate subtractive reset, and no input decay. Separate integer and packed executions agree on all64-image logits/states/spikes. The observed membranes exceed signed12, so hardware uses signed16 for this and GLIF alike.
- `benchmarks/cifar10_full10000_a0/plan.json` and eventual `results.json` are the full OTTT test gate. `progress.json` is progress only and cannot supply final accuracy, zero-width-exception or completed-run claims. `benchmark_acceptance.json` must be refreshed only after final source/logit/data checks.
- `benchmarks/profile16_a0/actual_operand_frames.txt` is a7,335-operand wide-value coverage/stress sample. It is deliberately selected and is not representative energy. Its sidecar preserves original batch/time/layer/neuron locations.
- Public CIFAR10 is a dataset used by FireFly papers; OTTT and GLIF checkpoints are not reproduced FireFly checkpoints. AdEx nonlinear/adaptation terms are not validated by this leakage kernel.

## Representative activity

- `activity/random_stratified_v2/plan.json`, `results.json`, `acceptance.json` and `representativeness_acceptance.json` are the accepted bounded GLIF activity gate. The complete64-image stream supplies159,383,552 raw updates;262,528 selected nonzero operands span2,176 seeded ordered windows. Independent source order, scalar outputs, coefficients, context, logits, histograms, weights and boundary-pair effects are retained.
- The predeclared representativeness gates pass: weighted coefficient/context/coarse-membrane variation, narrow fraction, layer/time sampling and adaptive/fixed issue-overhead difference. This supports the declared64-image arithmetic capture after common zero filtering, not all10,000-image energy or memory/filter cost.
- The previous17,408 prefix operands have coefficient variation34.6%; their energy remains historical sample evidence. The midpoint window method failed its distribution gates and remains retained as a sampling failure, not a hardware failure.
- `activity/capture_ottt_representative.py` and `ottt_capture_preparation.json` prepare a future seeded64-image capture with layer counters and accepted-logit fidelity gate. Preparation is not capture acceptance; current OTTT energy is stress only. No further inference is authorized by this outline while the full OTTT run occupies the coordinated RAM/CPU window.

## Matched routes and retained retries

- Original `route_acceptance_a0.json` and `route_progress_a0.json` must be retained. An E2 Synth20-411 opt_design failure is a vendor route failure, distinct from the original signed12 E2 delayed-SDF numerical discrepancy.
- `resolve_routes16.py` may retry failed routes from source-identical completed synthesis, saving original checkpoint origin and a fresh attempt. New `route_resolved_acceptance_<attempt>.json` selects one explicit directory per E0..6, preserves original acceptance, and verifies part/top,55/39/94FF, expected DSP count and finite nonnegative setup/hold/boundary slack. Resource or power values never choose the attempt.
- Every selected `hardware.json` must bind unchanged arithmetic/constraint sources, synthesis checkpoint and routed `design.dcp`. Core area excludes94fixtureFFs. Occupied slices use actual site sets; subtracting occupied slice totals is invalid.
- Do not mix12-bit historical area/energy with16-bit main comparisons. Passing12ns is a matched operating point, not a board Fmax measurement.

## Exact LUT controls and original discrepancy

- `lut_isolation/isolation_audit.json`, `isolation_report.md`, `internal_a0/diagnostic.json` and `run_a1/diagnostic.json` retain the bounded original E2 diagnostic. The wrong settled value is localized to an annotated CARRY4 output. The minimally isolated annotated bench passes10checks and does not reproduce the full-netlist error. Exact event/path scheduling cause is still unresolved. The invalid run_a0 ignored SDF annotation and is functional-only evidence.
- A failed original E2 replay never supplies accepted energy. Successful STA or functional simulation does not replace numerical delayed-replay acceptance, and pulse/timing options must not be weakened.
- E7 under `lutceil_e7` is an explicitly identified alternate exact LUT topology: floor quotient plus nonzero-remainder increment, beta256 bypass. Its16,842,752-case proof does not establish original E2 root cause. Require E7 general unstalled/stalled native, captured actualGLIF native, matched route, golden fixture, original-strength SDF replay and strict activity/power audit before reporting it as the stronger implemented LUT control.
- E7 native index6 maps to engine7. E6 remains beta128 shift; never confuse the indices. Original E2 may remain as a retained failed control if E7 succeeds, with the unresolved original diagnostic stated separately.

## Routed activity and energy

- `run_energy_closure_sequence_v2.py` owns serial orchestration after a resolved route acceptance. Per-engine child tags avoid progress-file collisions. Stage acceptance receipts, source/artifact hashes and dependency skips are required; child returncode0 alone is insufficient because energy runners retain failures internally.
- GLIF required primary energy controls are E0..5 plus E7. OTTT current stress controls are E0..6, including exact shiftE6. For each engine require `golden_checks.json`, exported routed netlist/SDF pins, `replay_checks.json`, raw SAIF, normalized name sidecar, `evidence.json` and reproducible `power_audit.json`.
- `audit_power16_12.py` and E7 counterpart independently bind every accepted operand/frame end to expected arrays, exact take/output/mode/count, natural2 latency and exact ROI duration. All physical activity aliases must be known and accounted for; missing activity or a replay mismatch prevents energy acceptance.
- Each reported energy audit names `routed_hardware_file` and itsSHA. Use that same selected route for the associated area figure. `aggregate_hardwareclosure.py` checks completeness and reruns power audits, but its latest-route/latest-power selection is a snapshot convenience; a final report must explicitly bind selected comparison records to the resolved manifest.
- Energy is vendor-estimated dynamic energy of the full common fixture per captured scalar leakage result. It is not measured board energy, core-only energy, full-neuron energy or accelerator speed. Dataset accuracy and useful operations/issue are separate metrics.

## Restricted E8 cost ablation

- E8 under `static9_e8` retains E5's exact post-correction body and coefficient-match pair rule. It removes actual-range detectors and full16 fallback. All inputs must lie in[-256,255] and signextend on16-bitports; it is not a legal full16 primary baseline.
- `preparation.json` pins131,584 signed9 scalar cases, reused pair proof and271,866 native cohort operands; `scalar_cohort.json` declares131,584 scalar-single frames. All four pair/scalar stalled/unstalled native acceptances and the selected matched E8 route are required.
- `static9_e8/audit_closure_static9.py` accepts explicit paths to those four acceptances plus selected E8 and E5 `hardware.json`. It independently rechecks outputs/counts, pins, legal domains and route contracts. E8 route must bind the explicit pair/s0 acceptance. It saves `closure_<label>.json/md` without selecting latest attempts.
- E5−E8 LUT/FF/DSP resources measure combined membrane admission plus full-width support cost. Synthesis can merge logic, so the difference is not literal controller-only overhead. E8 energy and wide correctness are outside this ablation.

## Contribution and equivalence limits

- `candidate_contribution.json/md` preserves closed-form issue-policy ablations. GLIF full64 has1.084% more E5 issues than fixedsplit; OTTT full64 has55.50% more issues than fixedtwo lanes and admits only53.34% of nonzero values into signed9. These adverse applicability results remain in the paper.
- `prior_art/equivalence_audit.json/md` and `targeted_followup/followup_manifest.json` document primary-method and released-source checking. Generic DSP packing, range utilization, actual-value narrowness admission and exact spill reconstruction are established ideas. Signed16 fallback is a width extension, not fresh arithmetic novelty.
- Access-limited full methods for Ou2024, Cui2024, UDP paper and McKeown2008 leave complete method equivalence unresolved. Author UDP source has been inspected; its released multiplication interface lacks this range-selected pair/full policy. A coauthor EUSIPCO2009 primary paper strengthens earlier range-utilization overlap. Failure to obtain a paper does not prove non-equivalence.
- Defensible scope: an exact rounded leakage specialization with actual-membrane admission, fixed stored precision and measured implementation trade-offs on public SNN traces. Neither first-ever adaptive packing nor universal superiority is established. Publication-strength judgment requires final matched baseline hardware/energy and the explicit unresolved prior-work statement.

## Final acceptance boundary

Hardware closure, public-model completion, representative sampling, original E2 diagnosis and prior-work equivalence each have their own status. A successful stronger LUT alternative can close the fair-baseline comparison while the original discrepancy stays unresolved. A bounded public-source search can be complete while method equivalence remains open. The final manuscript must reflect these distinctions and list outstanding gates directly; missing or failed evidence must not become a favorable number.
