# Clarifying the three SNN packing ideas

Checked 8 October 2026 against the implemented checkpoint RTL, the membrane-seeded promotion numerical trials, and a new matched exponent comparison.

There are two independent choices: **what the controller observes** (current chunk or actual membrane), and **how it creates headroom** (checkpoint, wider processing, or exponent rescaling). Membrane awareness is a controller property, not a third numerical representation. We nevertheless have three concrete candidate implementations to compare.

1. **Current checkpoint, exact:** represent U as wide base plus packed current chunk. Watch chunk headroom, transfer the chunk into wide state before overflow, and clear it. Wide state exists throughout. Final RTL has functional simulations and routed reports; it saves DSPs but has not demonstrated better complete-accelerator latency. It is current-range-aware.
2. **Block exponent, approximate:** pack actual membrane mantissas and share an exponent among six neurons. Watch membrane mantissa range; when necessary, right-shift a group and increment its exponent. This is already membrane-potential-aware. Without residues, rounding can affect incoming weights, leakage, thresholds, reset and spikes. Numerical simulations exist; no exponent RTL/resource/latency result is established.
3. **Actual-membrane narrow/wide promotion, exact:** start with the leaked membrane in narrow packed fields when it fits. On a range warning, promote the group to wider processing for the rest of the timestep. This is membrane-potential-aware and can preserve values. **Update:** both exact versions now have matched 24-neuron RTL implementations, real-UNISIM verification and full 360-image numerical inference checks. The new promotion RTL includes exact migration and a serialized wide path; its latency is substantially worse than the earlier optimistic numerical model suggested. See [the implementation and baseline report](exact_snn_implementation_and_baselines.md) and [new source bundle](exact_snn_implementation.zip). This is one possible membrane-aware policy, not proof that every such policy fails.

The actual-membrane controller can also use checkpointing instead of whole-group promotion. The controller and recovery mechanism should not be conflated.

## Additional matched exponent experiment

Used saved seed-0 int4 64-128-10 digits model, all 360 test images, 32 timesteps, six signed8 mantissas per exponent group. Compared monotonically increasing exponents and optional downshifts after timestep reset, each with truncation or nearest rounding. Input RNG, calibrated thresholds, integer floor leakage at exponent zero, and spike-count classification match the checkpoint experiment's integer reference. At nonzero exponent the original mantissa-domain leak and rounded threshold/reset are approximate. These results characterize this implementation; they do not establish limits for every exponent policy.

Reference accuracy is 96.11% for each of the three tested leak settings.

- LIF beta=0.5: all four exponent variants stayed at exponent zero, with no rescaling and zero state/spike/prediction disagreements. This is not evidence of successful adaptation under overflow.
- LIF beta=0.875: nearest rounding gave 96.67% accuracy, but changed 8 predictions for monotonic exponents and 10 with downshifts. Across both layers and all timesteps it changed 2,683 and 2,635 spike decisions respectively. Truncation gave 89.17% accuracy and changed 26 predictions. Identical or slightly better task accuracy does not imply identical outputs.
- IF: nearest rounding gave 93.89% accuracy and changed 11 predictions; truncation gave 90.00% and changed 28. Spike differences were substantial. Truncation also drove the shared exponent to its allowed limit in some groups: at coarse scales, floor rounding of small negative weights to -1 creates a persistent negative bias. Large state errors can result even when classification degradation appears modest.

The exponent comparison is full autoregressive inference: hidden spike differences feed subsequent layers and timesteps. State/spike disagreement counts therefore include propagated differences, not just local rounding errors. No hardware overhead, power or matched scheduling latency was measured for the exponent design. One training seed is insufficient to establish an accuracy tradeoff robustly; the earlier exact checkpoint/promotion characterization used three seeds.

## Interpretation

For the stated exact-output objective, the checkpoint and exact promotion approaches remain eligible; the tested exponent variants do not. If approximation is permitted, exponent scaling remains a candidate and should be compared with calibrated fixed precision at the same accuracy and hardware budget. A membrane-aware description is appropriate whenever the actual membrane controls representation or scheduling, including an overflow-driven exponent scheme. Distance to firing threshold is an optional additional signal, not a prerequisite for that description.

The earlier checkpoint prototype monitored current chunks, which is why its controller received a narrower description. The mentor's proposed direction is broader and can incorporate either exact promotion/checkpointing or approximate exponent adjustment.

The updated ZIP includes compare_exponents.py and results/exponent_matched.json, along with the prior exact trials.

The newer `exact_snn_implementation.zip` contains the two selected exact implementations and their matched baseline measurements. The exponent comparison above remains a separate numerical experiment.
