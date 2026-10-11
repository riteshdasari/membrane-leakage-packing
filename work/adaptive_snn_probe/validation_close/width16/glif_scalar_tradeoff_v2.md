# Accepted GLIF scalar controls: E3, E4 and E5

This additive receipt preserves v1 and every raw output. E4's certified power audit independently reproduces identically, all v1 evidence pins remain valid, and E4/E5 bind the same262,528 scalar operands/reference results, signed16 domain,12ns clock and94-FF fixture. E4 route SHA256:`a1998ec14d20073e437bc8c0d60322a507d9d681202426ee73f6aa067be0fea3`; common NPZ SHA256:`07f68efe215e9e0dd8c70a009f97cca8c6a7cf8d3c7bc5de33062a4302b2d3eb`. Detailed source receipts and exact serialized fractions are in `glif_scalar_tradeoff_v2.json`.

E4 uses13 LUTs,29 FFs and one DSP, estimates24.6483755485pJ/scalar, and retires262,528 requests in3.150384ms. E5 uses62 LUTs,44 FFs and one DSP, estimates21.5994968308pJ/scalar, and retires141,985 requests in1.703868ms. At the same one-DSP budget, E5 therefore gives:

- **12.36949150% lower estimated dynamic energy**, saving3.048878718pJ/scalar.
- **45.91624512% fewer requests** and45.91554553% shorter audited activity interval.
- **1.84896013 times the captured no-stall scalar-result rate**, with49 additional LUTs and15 additional FFs.

This is a primitive fixture rate comparison. Both individual requests retain two advancing-edge latency; no complete-neuron, memory-aware or burst-latency improvement is inferred. E5's average dynamic power is higher,3.328 versus2.054mW, but its shorter activity interval gives lower energy.

The E4/E5 energy gap exceeds combined XML serialization bounds:3.048878718pJ versus0.051796308pJ. The serialization-only E5-minus-E4 interval is[−3.100675026,−2.997082410]pJ. These bounds describe report rounding, not vendor-model or physical uncertainty.

E3 remains a legitimate competing point:35 LUTs,56 FFs,two DSPs and21.3710653340pJ/scalar. E5 halves its DSP count while adding27 LUTs/removing12 FFs, with1.06888212% higher estimated energy and8.11479654% more requests. Thus E5 is not globally best across every resource/rate/energy dimension.

The supported paper result is now a focused, exact one-DSP leakage primitive with a measured conditional trade-off: it improves captured GLIF rate and estimated energy over the scalar one-DSP control, lowers fabric and estimated energy against fixed one-DSP split packing, and lowers estimated energy against the validated general LUT pair. The two-DSP control, unfavorable vanilla-LIF ranges and cheap constant controls define its limits. This is enough to present a concrete circuit result; it does not establish strong-publication acceptance or broad superiority. Generic adaptation remains prior art, so novelty must rest on the particular leakage decoder/admission implementation and its evaluation.

All energy is vendor-estimated dynamic energy of the complete fixture at25 C junction/typical process, after common zero filtering. Chip static, memory, full SNN updates and board measurements are excluded. GLIF E2 is still running/pending; OTTT stress E2 remains a retained failed attempt without accepted energy. This successful scalar comparison does not declare all-attempted-control closure or resolve the historical delayed-model discrepancy. No vendor, inference or editor action was performed by this audit.
