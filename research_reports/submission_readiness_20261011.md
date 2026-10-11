# Focused ISCAS submission readiness review

This independent review concerns a circuit primitive paper, not a complete SNN accelerator. It reviews the existing draft and selected accepted model, route, activity and manuscript-audit records. No model, vendor job, manuscript edit or process interruption was performed. The companion JSON records hashes for this snapshot.

## Decision

**Proceed with a focused submission.** The specific exact leakage decoder combined with actual-membrane pair admission and a full-width singleton fallback is a legitimate candidate circuit contribution. Research can contribute a new specialization or combination of established ideas; it does not need an entirely new category of arithmetic. The evidence already supports a concrete circuit result. It cannot prove acceptance, generic first-ever adaptive packing, universal model superiority or a complete accelerator benefit.

**Technical evidence is sufficient for a defensible bounded paper; the current document is not yet submission-ready.** Its custom `article` layout and placeholder authors do not satisfy the official template/author requirements. Its compiled page count, final PDF fonts, size and visual layout have not been checked in this review. The manuscript also needs a compact datapath/admission figure and cleaner final references. These are actionable finishing tasks, rather than grounds to restart the research.

## Evidence that survives review

- The fixed contract is signed16 state/interfaces, unsigned Q8 beta in [0,256], and exact ceiling(beta U/256). Adaptation changes operations per issue from two admitted signed9 membranes to one full16 membrane. It does not change voltage units or state precision.
- All range/equality tests, arithmetic selection and correction are included in E5's 62 LUTs, 44 FFs and one DSP. The E5-minus-E8 15-LUT/eight-FF difference combines admission and full-width support; it is not an isolated controller cost.
- E1 uses 202 LUTs/79 FFs/one DSP over the same general input domain. E5 saves 69.31% LUTs and 44.30% FFs while the complete 64-image GLIF stream pays 1.0836% more issues. E4 and E3 remain legitimate competing resource points.
- E5, E1, E3 and E4 all use the common 12 ns constraint and two advancing-edge request latency. Selected E5 setup/hold slack is 6.054/0.129 ns, E1 3.437/0.130 ns, E3 6.052/0.103 ns and E4 6.041/0.159 ns. These are successful matched routes, not an FMAX sweep. A FMAX claim is unnecessary and must not be inferred from subtracting slack from the constraint without path/clock analysis.
- Accepted GLIF fixture dynamic energy is 21.5995 pJ/scalar for E5, 24.6484 for E4, 55.3084 for E1, 21.3711 for E3 and 124.1983 for the exact general LUT pair E7. E5's 12.37% estimated-energy advantage over E4 accompanies extra fabric. E3 is near energy parity with two DSPs and fewer issues. The E7 comparison is accepted independently of E2.
- The representative GLIF capture contains 262,528 nonzero operands from 2,176 stratified ordered windows in a complete 64-image stream and passes predeclared distribution gates. The representative OTTT capture contains 262,144 operands in 1,280 windows and passes its unchanged gates after retaining an independently explained failed first capture. These are bounded captures, not full-test energy or statistical confidence intervals.
- GLIF and OTTT have full 10,000-image declared integer references. GLIF exact packed feedback is checked on 64 images; OTTT has full-test packed feedback and independent scalar leakage checks. The independent BNTT thirty-step checkpoint validates 64 selected images. Packed/scalar integer exactness is separate from FP32-to-integer conversion accuracy.
- Vanilla LIF with beta=128 is an important negative case: zero-DSP shift leakage beats adaptation. BNTT beta=253 also has an exact constant-specific shift/add identity. Retaining these prevents an unjustified claim that any non-power-of-two coefficient needs a DSP.

## What is necessary before submission

1. State one integrated contribution: the compact exact rounded leakage decoder, the membrane-driven pair/singleton contract and its measured implementation trade-off. Credit generic value packing, signed spill correction and fixed splitting. Say the bounded review has not identified the exact conjunction, without claiming proven absence of prior work.
2. Convert the same draft in place to IEEEtran conference format, supply actual authors/affiliations, and fit technical material into four pages. Keep an optional fifth page exclusively for references. Replace lengthy simulator history with a short excluded-evidence note and retain full diagnostic details in the evidence record.
3. Show a readable admission/datapath diagram, a concise arithmetic proof, common-domain baseline definitions, a matched area/issue/energy table and the positive/negative workload conditions. Explicitly label the external variable-consumption source, queues, zero filtering and memory as outside measured core cost.
4. Use only accepted E5/E1/E3/E4/E7 and representative OTTT energies. Do not accept E2's partial SAIF. Give the exact replay/activity protocol and tool/device/clock/fixture conditions. Keep model-specific constant hardware as a stated applicability limit unless its measurement is added.
5. Finish complete citation metadata, verify template compilation, rendered layout/page count, embedded non-Type-3 fonts, file size and consistency of claims. Produce a concise reproducibility entry point linking the source/contract, exhaustive checker, native stall checks, selected routes, model/checkpoint hashes, capture protocol and accepted energy audits. A private lab artifact can be prepared before public release; public release is not presumed authorized by this review.

## Stronger evidence, with claim-dependent priority

**Highest-value scientific extension:** measure the GLIF checkpoint's two-coefficient-per-channel constant bank/CSD control under the same signed16 interface and workload. It is necessary to support a claim of superiority over checkpoint-specialized hardware. It is not necessary to establish the scoped general runtime-coefficient circuit comparison. Likewise, route and measure the beta253 zero-DSP control before claiming a BNTT hardware win. This review does not predict either outcome.

**Useful low-cost presentation extension:** provide an operating-envelope plot from saved issue statistics, showing how accepted-pair fraction determines useful results per DSP issue and where fixed full-domain packing wins. Per-layer/time admission profiles would clarify why GLIF helps and wider-range OTTT/BNTT hurts.

**Optional for the current scope:** multiple route seeds, broader representative energy replicates, an FMAX sweep, a minimal integrated source queue, board power, full-neuron timing and AdEx validation. These strengthen particular claims but are not universal requirements for a small FPGA primitive paper. A board experiment is required only for a measured-board-energy claim. No burst-latency, memory-integrated speedup or AdEx claim is supported now.

## Retained issues that are not automatic submission blockers

Original E2's timed carry-cell discrepancy remains unresolved and its energy is excluded. This prevents accepting E2 energy; it does not invalidate the independently validated exact E7 fabric baseline or E5's accepted replay. The paper can use E7 and preserve the diagnostic transparently.

Three original full-method papers remain inaccessible. This limits priority/equivalence confidence and warrants qualified wording plus targeted comparison if copies become available. It does not logically require withholding every contribution claim until the absence of all prior work is proved. Submission still carries the usual risk that a reviewer knows a closer method. The relevant issue is a clearly described technical distinction, rather than the phrase "first-ever."

## Official ISCAS 2027 requirements checked on 11 October 2026

The [official author portal](https://epapers2.org/iscas2027/ESR/authorinfo1.php) requires at most four technical pages, with an optional fifth page for references only; author information is included. The PDF limit is 5 MB and fonts must be embedded without Type 3 fonts. Its submission deadline is 13 October 2026, 23:59 UTC-0500, which converts to **14 October 2026, 10:29 IST**. The [official template page](https://epapers2.org/iscas2027/ESR/samples.php) specifies IEEEtran in conference mode. The [conference scope](https://2027.ieee-iscas.org/call-for-papers) includes digital circuits, DSP and neuromorphic engineering, so a focused implemented leakage primitive fits the advertised subject areas. The conference CFP and portal disagree on notification dates; no notification-date conclusion is needed here.

The conference does not provide a rule that a paper needs an entirely new class of mechanism, all-positive workloads, board energy or a complete accelerator. Technical quality, significance and originality of the specific result remain reviewer judgments. This review recommends preparing the scoped submission now, with the model-specialized baseline as the strongest additional science if time permits.
