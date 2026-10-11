# Gate before the next adaptive RTL trial

The present eight-addition implementation does not establish an advantage over
the strongest exact native-SIMD/LUT hybrid. Its fixed8 control already reaches
the request-count lower bound for this interface. A different spike workload
cannot reverse that capacity bound. Preserve this result and the exact
arithmetic, range proofs, stall tests and hardware controls.

The downloaded official GLIF CIFAR10 checkpoint supplies a real learned-LIF
workload. It does not supply our signed8-current integer operation: its
currents, learned coefficients, linear leak and previous-spike reset factors
must be included in a numerical contract. The four pilot unit choices are
observational screens, not accuracy-preserving quantization. The old
coefficient231 near-identity leakage case cannot be substituted for this
checkpoint's coefficients to improve packing.

The next small-operation candidate must clear the following gates in order:

1. Declare the integer LIF leakage operation, coefficient precision, rounding,
   threshold, reset and current width from an application or explicit
   quantization of a pinned trained model. Report float-to-integer accuracy
   separately. Packing must preserve this same integer reference exactly.
2. Screen all actual coefficient groups and membrane streams, retaining
   original neuronal order, positive and negative ranges, reset cases and
   bursts. Give zero-operation bypass to every baseline. Coefficient231 and
   a chosen burst subset cannot stand in for the full model.
3. Test exact packing/recovery against full-precision scalar arithmetic,
   including exceptional formats and stalled retirement. Count completed
   leakage operations, not only low-field DSP arithmetic. No threshold or
   reset may occur between pieces of one mathematical update.
4. Compare the same operation with fixed wider DSP packing, fixed split/high
   correction, LUT multiplication and the best factorized constant or
   table implementation where coefficients are constant. Runtime-programmed
   coefficients need equally programmable controls. Earlier generic and
   constant leakage experiments remain controls; they are not new trials.
5. Start a new Vivado trial only when the stream screen shows a meaningful
   possible resource/energy or service advantage after strong bypasses and
   static bounds. Include detector, layout, decoding, registers and natural
   latency. Close setup/hold and timed replay before accepting power.

This remains a primitive/controller paper direction. It does not require a
new full accelerator. The measurable claim must be a net benefit in energy,
throughput/latency under a fair resource budget, or a useful resource frontier.
Exactness is a requirement; it cannot become an accuracy improvement over an
already exact fixed baseline. Novelty remains a literature question and does
not replace this benefit gate.

The Lava MNIST reference was also inspected as a possible integer benchmark.
Its documented voltage-decay configuration is dv=0 in all classifier layers,
so it does not justify a nontrivial membrane-leak multiplication claim.
This is a source inspection, not an executed Lava benchmark:
https://lava-nc.org/lava/notebooks/end_to_end/tutorial01_mnist_digit_classification.html
