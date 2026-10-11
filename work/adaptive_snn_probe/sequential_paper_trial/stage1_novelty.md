# Stage 1: final-mechanism novelty audit

Completed 2026-10-10. This is a bounded prior-work audit, not proof that no other publication exists.

## Mechanisms actually evaluated

The certified addition kernel computes a post-leak membrane contribution plus an already-reduced signed-eight-bit current. It does not implement complete synaptic accumulation, leak, reset, threshold, or memory. Its adaptive form keeps eight radix-32 residue fields in a fixed DSP layout; five positions retain full high-part metadata and three positions admit only membranes fitting signed eight bits. Deferred values later use full positions. Its fixed-eight control uses full high metadata in every position. Both reconstruct exact sums in fabric.

The strongest native control combines four independent twelve-bit DSP additions with four fabric additions. This is a strong engineering baseline, not an established novel contribution of this project. Eight residues in a DSP must not be described as eight complete wide DSP-only additions.

## Closest primary sources

- [DSP-Packing, Section VII](https://arxiv.org/html/2203.11028#S7) already describes addition packing for SNNs and carry-isolating guard bits. Its multiplication sections cover exact correction and approximate overpacking. Therefore generic exact packing, guards, and external correction are not new claims.
- [FireFly](https://arxiv.org/html/2301.01905v5) uses four fixed twelve-bit SIMD addition lanes and runtime spike-controlled DSP multiplexers. Its dynamic mux control is not evidence of membrane-range-driven packing. Whole-accelerator results cannot be compared directly with our isolated kernel.
- [FireFly-S](https://arxiv.org/html/2408.15578v1) implements its quantized spike arithmetic in LUTs without DSP slices. A LUT control is technically justified independently of whether FireFly-S is reproduced.
- [XtraMAC](https://arxiv.org/html/2605.06052) changes packing for runtime datatypes in LLM MACs. Broad adaptive DSP packing is already claimed outside SNNs.
- [Arithmetic Packing on Wide Integer Datapaths, Sections III-B/C](https://arxiv.org/html/2606.11065) handles signed packing with the DSP pre-adder and tracks lane spill-over exactly using modulo-four references and external high accumulators. Consequently, exact spill tracking is related work, not an unclaimed invention here. Its application is packed DNN multiplication/MAC rather than the present membrane admission rule.
- [UDP](https://doi.org/10.1145/3748173.3779194) describes general low-bitwidth MAC mapping and continuous packing. The accessible abstract supports broad overlap only; its full method was not available for detailed equivalence checking in this audit.
- [Efficient DSP Packing Method for Neural Network Accelerator](https://doi.org/10.1109/ICFPT64416.2024.11113473) claims lossless packing of six signed multiplications. The accessible abstract is insufficient to rule out detailed overlap with an arbitrary fixed multiplication construction.

## Searches and limits

Searches combined SNN, membrane potential, adaptive DSP packing, lossless accumulation, exact spill, and guard-bit terms. The review did not identify the exact five-full/three-narrow ordered membrane admission policy. This supports a narrow potential novelty claim, not a first-ever assertion. No exhaustive database or patent search is claimed. The unresolved mentor reference is not silently treated as a different paper from the identified 2026 spill-tracking work.

## Decision

The membrane-dependent admission/recovery policy remains a candidate contribution. The fixed-eight residue construction is a candidate implementation detail with substantial overlap with established splitting and guard arithmetic; a strong standalone fixed-packing paper is not established by this audit.

The measured certified addition results are adaptive 121 LUT/47 FF/1 DSP, custom fixed-eight 130 LUT/53 FF/1 DSP, and native fixed hybrid 87 LUT/49 FF/1 DSP. Thus the current fixed fallback has neither established distinctive novelty nor a hardware advantage over the strongest control.

Proceed to one application-backed integer leakage benchmark. Do not replace its learned coefficients with 231. A possible new claim must identify an exact membrane-driven format decision and show a net advantage including its controller and correction cost.
