# Final decision: retain the exact adaptive leakage primitive

The five-stage trial produced a positive adaptive hardware result. Retain the **post-corrected signed9 pair / signed12 fallback leakage primitive, E5**, as the paper candidate. It computes `ceil(beta*U/256)` exactly. On the evaluated GLIF stream it uses substantially less fabric than the full-domain fixed one-DSP split implementation, while requiring 1.08% more arithmetic issues. This supports a focused primitive paper direction. It does **not** yet establish a submission-ready strong ISCAS paper.

The decisive equal-DSP comparison is:

- Adaptive E5: **53 LUTs, 40 FFs, one DSP**.
- Exact fixed split E1: **122 LUTs, 63 FFs, one DSP**.
- Adaptive saves **56.6% of LUTs and 36.5% of FFs**; these counts include its local range/format selection, pipeline and correction.
- On the complete 64-image recorded stream, adaptive requires **42,785,698 issues versus 42,327,032**, a **1.0836% increase**.
- On the separately captured 17,408-operand activity sample, estimated dynamic energy is **19.87 versus 30.30 pJ per scalar result**, a **34.4% reduction**. This is a Vivado estimate including the common fixture, not measured board energy or full-model energy.

## What is adaptive, and why it helps

The hardware examines two consecutive actual membrane values U. If both lie in [-256,255] and share beta, it performs two exact leakage operations in one DSP issue. Otherwise it consumes one signed12 operand. It preserves order, the membrane unit and the full legal numerical domain. The controller does not halve membranes, discard bits, change an exponent, or predict spike bursts.

The fixed split control can always handle two full-width operands with matching coefficients, using a packed low-residue DSP product plus two fabric high-part products. Adaptation removes those two general fabric products. It pays for that simplification by processing wide values singly. The measured advantage is therefore **less fabric and lower sampled estimated dynamic energy at almost the same stream service count**, rather than better accuracy or lower latency than fixed split.

99.02% of nonzero arithmetic operands fit signed9 in this stream. That does not make adaptation unused: narrow pairs enable the cheaper implementation, while the fallback keeps wide membranes exact. Nevertheless, rarity of wide cases makes a narrow-only specialization a relevant secondary control where a caller can prove a narrow domain. Here it cannot replace the full-domain baseline: old states reached [-1378,1529] on the full test set. A useful ablation would separately price a static narrow core, mandatory exact wide recovery, and their selection overhead.

The kernel is **leakage multiplication within a neuron update**, broadening the original synaptic-accumulation goal. DSP packing remains the central operation. LUTs and registers implement its control and exact reconstruction; their presence does not invalidate the research question. Their cost is included in the comparison.

## Completed stages and evidence

**1. Prior work.** The final leakage-specific audit is saved in stage1_leakage_addendum.md. Our bounded review has not identified the exact actual-U pair/full leakage policy. Generic multiplication packing and exact spill correction are established techniques, so the novelty claim must concern the specific policy, exact contract and measured implementation trade-off. A standalone novel fixed-packing contribution is not established.

**2. Public model and integer contract.** The source is the official channelwise GLIF ResNet18 CIFAR-10 model with two time steps, pinned to commit `60638b28ff8b688b51867e7dd44f1e065d4892b0`. Original test images and normalization were retained. Convolution, batch normalization and readout remain FP32. Neuron state and arithmetic use a declared integer contract without retraining or coefficient substitution.

The scalar integer-neuron reference was evaluated on all **10,000 images**, with **24,903,680,000 neuron updates**. It obtains **94.05%**, versus **94.03%** for the saved floating reference. There are **371 changed predictions**: 160 become correct and 158 become incorrect. This is the effect of neuron quantization, not an adaptive accuracy improvement. Independent first-batch state/spike checks passed. Observed states and currents fit the hardware domain; this is an observed workload bound, not a proof for every possible input.

Actual learned leakage coefficients span **153..170** in the previous-no-spike context and **74..88** in the previous-spike context. The earlier illustrative coefficient231 was not substituted. GLIF is a gated LIF-family model, not a vanilla LIF or AdEx validation.

**3. Exact arithmetic and fed-back execution.** Exhaustive algebra checks passed for **67,371,008 post-corrected signed9 pair cases**, **50,593,792 precompensated pair cases**, and **1,052,672 signed12 cases each for scalar and fixed split**. The pair checks cover both signed9 operands and every legal coefficient in their respective domains.

Packed leakage was fed back into the declared integer neuron update for the first **64 images**, covering **159,383,552 raw neuron updates**. All logits match the scalar integer reference bit for bit. The fed-back execution uses the precompensated packed path; the post-corrected results are independently checked against it on every admitted pair and across the exhaustive algebra domain. This is not a full 10,000-image packed RTL model execution.

Common zero bypass leaves **79,246,135 arithmetic operations** after **80,137,417 zero operations**. It is granted to all controls. Adaptive achieves **1.852 useful arithmetic results per DSP issue** and saves **46.0% of issues against a single scalar DSP**. Two independent DSP or LUT lanes require **39,623,132 issues**, so adaptive is **7.98% slower in issue count** than those two-lane controls. All-wide bursts favor fixed split, which returns two results while adaptive returns one. No universal burst-latency claim survives.

**4. Native RTL, route and activity.** Six controls implement the same signed12 U / beta0..256 operation with a two-stage elastic interface. Native tests pass for **294,856 operations per engine**, both with and without stalls, plus the 17,408 actual-model operand sample. Held outputs, order and consumed counts are checked.

The routed Artix-7 `xc7a100tcsg324-1` results use Vivado2025.2. Core counts exclude a common **78-FF launch/capture fixture**. The six results are:

- E0 adaptive precompensation: 61 LUT / 40 FF / 1 DSP; 20.13 pJ/result estimate.
- E1 exact fixed split: 122 LUT / 63 FF / 1 DSP; 30.30 pJ/result estimate.
- E2 two LUT multipliers: 290 LUT / 72 FF / 0 DSP; energy excluded.
- E3 two scalar DSPs: 29 LUT / 48 FF / 2 DSP; 19.97 pJ/result estimate.
- E4 one scalar DSP: 11 LUT / 25 FF / 1 DSP; 22.96 pJ/result estimate.
- E5 adaptive post-correction: 53 LUT / 40 FF / 1 DSP; 19.87 pJ/result estimate.

Energy comparisons use a common **9 ns clock**, slow/max routed delay simulation, exact known-pin replay, verified SAIF timing and complete physical-net activity annotation, at25C. Routes were originally optimized at6ns and reused without changing physical cells or connections. All six pass static setup/hold at9ns. The five DSP-containing controls also pass exact delayed replay. At6ns, the LUT control has negative setup slack; the other controls have positive setup and hold slack.

The LUT control passes native and mapped functional replay but fails delayed replay at the same two rows at9ns and12ns. No LUT energy estimate is accepted. Its failure does not prove LUT arithmetic is intrinsically unsuitable. Slowing again is not justified by the identical mismatches. The saved diagnosis identifies the affected carry/result bit and proposes a targeted waveform check. The remaining12ns energy cohort was explicitly gated after this failure. No timing checks were waived.

The energy sample is the predeclared first64 nonzero operands per recorded layer/time-step/batch frame, in original order. It is neither random nor a complete workload capture. Energy includes the common fixture and its drain; static chip, memory, bypass integration, threshold/reset, and full-model energy are outside scope. The small E5/E3 energy difference is not a robust claim of superiority over a two-DSP design.

**5. Evidence and writing.** The final decision record and working manuscript are saved. The closing integrity audit checked **96 JSON records and544 unique pinned files**, with no mismatch. Earlier unfavorable addition hardware, tool failures, interrupted attempts, route retries and failed LUT replays remain saved. Results from the old addition or constant-coefficient trials are not mixed into the leakage result.

## Research claim and publication decision

The defensible claim is:

> Actual-membrane range admission enables exact pair/full DSP leakage computation with substantially lower fabric cost than a full-domain fixed split implementation at the same one-DSP budget, with a small issue-count penalty on the evaluated learned-coefficient SNN stream.

This is a positive adaptive result, so rejecting the research direction is no longer warranted. It also explains why the earlier addition mechanisms struggled: cheap FPGA additions made the controller/reconstruction hard to amortize. The final experiment targets genuine variable-coefficient multiplication, where removing duplicated fabric products matters. This is a change in operation, not a retroactive victory for the old accumulation datapaths.

Before calling the paper strong and ready, close four specific gaps:

1. Resolve the LUT delayed-replay discrepancy and obtain its accepted activity comparison. Keep its functional/area results visible meanwhile.
2. Validate another public vanilla LIF workload, preferably with more recurrent time steps and nontrivial leakage. Shift/identity leakage requires a shift/add control and may remove the DSP benefit. AdEx needs its own arithmetic contract and is not automatically covered.
3. Use complete-workload activity or an independently designed representative sample to test the energy result. Include a static narrow-plus-exact-fallback ablation; consider constant or coefficient-bank fabric specialization when that deployment contract applies.
4. Finish method-level related-work comparison, especially the two abstract-only papers. Claim a narrow application policy and hardware trade-off, not first-ever adaptive DSP packing or spill tracking.

These are validation tasks around a retained architecture. A complete accelerator, model retraining and a new approximate representation are not required to write the current primitive draft. No acceptance guarantee is implied.

## Relation to FireFly and prior work

The fixed split baseline here is **our matched leakage control**, not FireFly. FireFly's four12-bit SIMD additions use a different operation. Whole-accelerator throughput/accuracy numbers cannot establish a primitive win. [FireFly](https://arxiv.org/html/2301.01905v5), [FireFly-S](https://arxiv.org/html/2408.15578v1), and [DSP-Packing](https://arxiv.org/html/2203.11028) remain relevant context, not numerical replacements for the controls.

[Arithmetic Packing on Wide Integer Datapaths](https://arxiv.org/html/2606.11065) establishes exact modulo-based spill handling. [XtraMAC](https://arxiv.org/html/2605.06052) establishes runtime datatype-dependent packing outside SNNs. The benchmark comes from [GLIF's official repository](https://github.com/CAS-CLab/Gated-LIF). The related-work review leaves a plausible specific opportunity, while detailed equivalence and workload breadth remain open.

## Files

- Working manuscript: `outputs/membrane_leakage_paper_draft.tex`.
- Machine-readable decision: `outputs/membrane_leakage_final.summary.json`.
- Final audit: `work/adaptive_snn_probe/sequential_paper_trial/stage4_final_integrity.json`.
- Exact RTL: `work/adaptive_snn_probe/sequential_paper_trial/leak_core.sv` and `leak_dsp.sv`.
- All stages and failed attempts: `work/adaptive_snn_probe/sequential_paper_trial/`.
