# Folded operand-isolation audit

This is a separate trial after the first isolated route failed its 6 ns setup
gate. The archived fixed and adaptive power references remain read-only. The
same read-only audit helper was copied here, retaining its frozen dependency
hashes, functional-equivalence gate, exact ROI math, complete physical activity
coverage, primitive-connectivity checks and power-model comparison.

The candidate source folds the zero default into one-hot lane selection.
It ORs membrane high bits and current sign through selected_mask, and sets
the ±1 adjustment to zero when selected_mask is zero. Unlike the first trial,
it adds no separate late v2/any-work gate after the binary lane-selection mux.
This description is an RTL hypothesis; it does not prove how synthesis maps it.

The four functional suites passed. The registered route failed 6 ns setup:
167 LUTs, 268 FFs, one DSP, WNS -0.114 ns and WHS +0.105 ns. Its worst path
runs from a DSP residue carry through work_mask and priority-derived selection,
then an isolated_hu bit and arithmetic/output logic to an out_data register D.
Its 5.974 ns data delay contains 1.054 ns logic and 4.920 ns routing (82.356%).
This is a different path from the first attempt's pipeline clock-enable path.

The timing path confirms a physical isolated_hu net before the output arithmetic;
it does not prove the zero-default truth or switching benefit. No 6 ns routed
replay or energy is accepted for this failed route. Full mapped corrector cone
review, physical SAIF annotation and energy remain unmeasured.
Corrector source names disappearing is not evidence of a switching reduction;
the mapped connectivity and recorded physical activity must support that claim.
No board-power or core-only energy result is asserted.
