# Leakage-specific novelty addendum

Evidence closed on 10 October 2026. This addendum concerns the final leakage primitive, whereas stage1_novelty.md concerns the earlier addition experiments.

The candidate evaluates `ceil(beta*U/256)` for signed12 membrane U and unsigned Q8 beta0..256. It uses the actual values of two consecutive membranes to admit a signed9 pair into one DSP when both fit [-256,255] and their coefficients match. Otherwise the same DSP returns one signed12 result. The selected E5 implementation recovers the low-field borrow through a modulo-two reference and an exact upper-field boundary correction. Stored membrane values and units never change.

The potential contribution is the particular membrane-dependent admission policy, its exact leakage contract, and the measured trade-off against a full-domain fixed one-DSP implementation. Runtime activity here means numerical membrane range and coefficient compatibility. It does not mean spike-rate prediction, precision shrinking, stochastic rounding, or adaptive voltage scaling.

[DSP-Packing](https://arxiv.org/html/2203.11028) establishes multiplication packing, exact correction and SNN addition packing. [Arithmetic Packing on Wide Integer Datapaths](https://arxiv.org/html/2606.11065) uses modulo references and exact spill tracking. Generic packing, guards, modulo reconstruction, and external correction therefore cannot be claimed as inventions. The present borrow proof specializes known arithmetic ideas to a bounded ceil-leakage operation.

[FireFly](https://arxiv.org/html/2301.01905v5) uses fixed twelve-bit SIMD additions with spike-controlled DSP multiplexers; its operation is different from this leakage multiplication. [FireFly-S](https://arxiv.org/html/2408.15578v1) motivates evaluating fabric arithmetic, but our LUT control is independently built for the same leakage operation, not a reproduction of FireFly-S. [XtraMAC](https://arxiv.org/html/2605.06052) supports runtime datatype packing for LLM arithmetic, precluding a broad claim that adaptive DSP packing itself is new.

The bounded review has not identified the exact actual-U signed9-pair/signed12-fallback leakage policy. This is an opportunity, not proof of first use. The full methods of [UDP](https://doi.org/10.1145/3748173.3779194) and [Efficient DSP Packing Method for Neural Network Accelerator](https://doi.org/10.1109/ICFPT64416.2024.11113473) remain to be checked for detailed equivalence. Further methods that dynamically exploit operand magnitude could overlap even without using the phrase membrane potential.

The fixed split implementation is an essential control derived from the established identity U=256h+r. A standalone novel fixed-packing contribution is not established. The positive final result is adaptive area and sampled estimated dynamic-energy savings at equal one-DSP budget, with a small measured issue penalty. No universal latency or accuracy improvement is claimed.
