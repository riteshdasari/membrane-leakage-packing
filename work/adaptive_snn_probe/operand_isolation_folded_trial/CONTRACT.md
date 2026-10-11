# Folded operand-isolation experiment

One implementation change: fold zero isolation into the existing one-hot
selected_mask. OR the six masked membrane-high operands and current signs;
mask the ±1 adjustment to zero when selected_mask is zero. No separate late v2
gate is added. Stale invalid exceptional metadata and backpressured exceptions
may keep the corrector active. Actual output writes require a selected bit.
No new registers, lanes, precision, layout, scheduler or workload selection.

The first postselection trial remains unchanged in ../operand_isolation_trial:
152 LUT / 268 FF / 1 DSP, WNS -0.230 ns at 6 ns. Its worst path is classifier to
advance/metadata CE, predominantly routing, so no direct adder-delay cause is
claimed. Its timing-failed checkpoint cannot supply a valid 6 ns energy result.

Keep the frozen V2/V3 RTL, checkpoints, activity, power and publications read-only.
Use a separate renamed trial core with V=3, ISOLATE=1. The first candidate uses
natural RTL without preservation attributes. Inspect mapped one-hot isolated operands
and corrector activity to determine whether synthesis retained the mechanism.
If synthesis eliminates it, report that before choosing a minimal explicit
preservation option; never claim activity suppression from source code alone.

Verify every settled output/control and correction/busy/advance against the
frozen V3 under identical pins. Run full stress and saved-model suites both
without and with output backpressure. Require identical archived retirement
bytes including clocks, 635,904 saved scalar updates, 1,008 corrections and
114 extra clocks for the no-backpressure saved workload. Input-domain, four
advances, ordering, reset and output-tail contracts are unchanged.

Route the same 219-FF fixture on xc7a100tcsg324-1 at 6 ns, one thread, with the
same OOC clock source. Retain negative raw-port hold budgets as a limitation.
Use saved V3 native pins only after cycle equivalence is verified. Perform slow
SDF gate replay including reset prelude, all useful work and two equal fixture
settling cycles. No timing checks or output unknowns may be waived.

Use routed SAIF and the matching checkpoint. Apply the already audited name-only
normalizer, preserving raw files and every numeric activity value. Require full
physical-net match and directly verify critical DSP/controller/corrector activity.
The power flow, nominal rails, typical process, 25 C user junction temperature
and clock remain equal. Actual SAIF duration determines energy per completed
scalar update. Static power and whole-fixture estimates stay separate from
board or core-only energy. Compare against both frozen adaptive V3 and fixed V2.

The shared corrector is small; isolation may not recover the full fixed gap.
Report area/timing/energy tradeoffs without assuming a win. This is a bounded
optimization of adaptive correction, not runtime lane-count DSP packing.

Root launches heavy jobs serially, gates native jobs at 1.2 GiB free and Vivado/
routed jobs at 2.3 GiB. Preserve sampled RAM logs. Do not close user applications,
download packages/models or change baseline evidence.
