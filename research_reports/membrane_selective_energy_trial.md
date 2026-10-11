# Frozen fixed versus adaptive correction: routed energy pilot

The adaptive V3 implementation uses **16.30% more estimated dynamic energy per completed scalar update** than the fixed V2 implementation on the unchanged saved workload. Both preserve the declared integer outputs exactly. This pilot establishes no energy benefit for the current shared-correction design.

## Equal-work results

Vivado 2025.2; Artix7 xc7a100tcsg324-1; 6 ns clock; routed timing-netlist activity; typical process; user junction temperature 25 C. Each variant completes 110,592 ordered requests containing 635,904 scalar additions. Both use the same signed11 membrane plus certified signed8 current domain and exact signed12 result.

- Fixed V2: **17.300 mW**, activity duration **663.588 us**, total dynamic energy **11.480072 uJ**, **18.05315 pJ/update**. Native service: 110,596 clocks. Core: 43 LUT / 262 FF / 1 DSP.
- Adaptive V3: **20.100 mW**, activity duration **664.272 us**, total dynamic energy **13.351867 uJ**, **20.99667 pJ/update**. Native service: 110,710 clocks. Core: 147 LUT / 268 FF / 1 DSP.

The extra 114 physical clocks increase native service by 0.1031%. Most of the energy difference comes from the higher average dynamic estimate, which increases by 16.18%. Energy is calculated as dynamic watts times actual SAIF seconds divided by completed updates; unequal service durations are retained.

The estimates cover the complete registered OOC fixture, including 219 launch/capture FFs. They are neither board measurements nor core-only values. Core resource counts above exclude those FFs. Static device estimates are 83.7162 mW for both designs and remain separate from dynamic energy. No fixture power has been subtracted using resource fractions.

## What adapts, and why correction avoidance is insufficient

The six eight-bit DSP fields and lane count remain fixed. The DSP performs unsigned seven-bit residue additions. Fixed V2 reconstructs every high part in parallel. V3 uses actual membrane high bits, current sign and residue carry to choose a cheap exact result or shared exact correction. It executes 1,008 exceptional scalar corrections, with 114 extra freeze clocks: **99.84149% of useful scalar updates avoid that general correction**.

That fraction measures arithmetic decisions, not switching suppression. The frozen RTL has no operand isolation around the fallback corrector: the default selected lane is zero, and the selected membrane high part still feeds its combinational arithmetic while no correction is used. The classifier, lane selector and output assembly also remain active.

Mapped routed activity directly shows corrected_high[1] at **153.269 million transitions/s** and corrected_high[2] at **149.692 million transitions/s**, while correction_step is **3.01985 million transitions/s**. The bad_mask[0] classifier net is **74.6351 million transitions/s**. These are specific net activities, including mapped timing glitches; they do not separately quantify each block's energy or conditional idle activity. They support testing operand isolation, rather than assuming correction avoidance already gates switching.

The DSP remains active for the ordinary low-part work in both designs. Its annotated enable is near one in each run. Sharing the high corrector does not skip the DSP computation or increase packed lane capacity. In this version the adaptive decision adds 104 LUT and 6 FF relative to a small fixed high-recovery circuit; the measured energy estimate also increases.

## Exactness, timing and annotation checks

Both native traces are rechecked against Python integer U+I, archived retirement bytes, clock columns and request order. Their numeric retirement hash is identical. Gate-level replays check all 110,642 fixed trace rows and 110,756 adaptive trace rows, including the reset prelude and exceptional clocks. Slow-corner SDF backannotation succeeds; no timing-check suppression, useful-result unknowns, mismatches or SDF timing violations are accepted.

Activity starts at 401,999 ps, one picosecond before the first useful replay drive. Each interval includes all native service clocks plus the same two launch/capture settling clocks. The actual recorded duration, root-clock transition count and every scalar state-time total are audited. Clock annotation uses the identical 6 ns constraint, as Vivado requires for its clock network.

XSim emitted escaped-name wrappers around some scalar net names. A deterministic name-only repair changes 47 fixed and 154 adaptive NET tokens, preserving instance hierarchy, duration and every ordered activity value. Both original and repaired SAIF files are retained. After repair, **726/726 fixed and 856/856 adaptive physical design nets match**, with no unmatched physical design nets. The audit verifies every reported simulated alias against its SAIF state probability and transition rate. Clock aliases come from the constraint; the only default-source aliases are verified constants. No fabric toggle fallback is accepted. DSP enable and controller nets are explicitly checked.

Raw SAIF files retain 1,369 fixed and 1,458 adaptive unknown-time records in simulator internals or optimized aliases. They are not globally discarded: every physical simulated activity record is independently checked to have zero unknown/high-impedance time. Constant physical aliases are separately audited. The expected clock-annotation warning and all original logs remain in the evidence. Vivado's medium activity advisories are retained and their named signals have measured, checked activity; no values are overridden to improve power.

Exported rail currents give the numeric dynamic values above. The ordinary power report displays 1 mW increments; even using its conservative half-increment endpoints, the adaptive/fixed energy ratio lies in **[1.1154, 1.2437]** and remains above one. This is a report-resolution check, not a physical error bar. Vendor-model accuracy, environmental assumptions and board measurement uncertainty are not bounded by the export's decimal precision.

Part, process, rail voltages, clock, user junction temperature, airflow, heatsink and board-model settings are equal. Under fixed user junction temperature, Vivado derives slightly different ambient temperatures: 24.539091 C and 24.526316 C. These are derived values, not independently changed inputs. Both registered routes pass at 6 ns; archived raw-port hold budgets remain negative (-1.146 ns fixed, -1.072 ns adaptive). This pilot does not validate a production board interface or board Fmax.

All heavy jobs ran serially with RAM gates. Successful power jobs started with 4.43/4.46 GiB free; sampled descendant working-set sums peaked near 1.37 GiB. This sampling can double-count shared pages and is not a unique-physical-memory peak. User applications were not closed.

## Research decision and next bounded experiment

This result removes energy as the justification for the frozen V3 implementation on this workload. Accuracy cannot offset the overhead here: both implementations already match the same exact outputs. Fewer exceptional correction jobs also do not establish faster service, since fixed V2 handles all high parts in parallel.

The next small implementation hypothesis is to isolate the fallback corrector's operands whenever no correction is required, then measure whether saved switching exceeds the new gating cost without worsening timing or changing exactness/service. That optimization is not implemented or measured in this pilot. It does not alone solve the 104-LUT gap or establish variable-width DSP packing. The current contribution should be described as membrane/current/carry-aware adaptive exact correction over a fixed DSP layout.

The saved workload uses beta231 leakage and differs from original training. Equivalence is to its declared saved integer reference; this is not an original trained-model accuracy result. No FireFly RTL is reproduced. The matched I8 hybrid and LUT routes remain valid resource comparators, but their energy is unmeasured here. Backpressure energy, unfavorable workloads, burst latency and complete neuron-update energy remain unmeasured. They are needed before a broad adaptive superiority claim, and workload selection must retain unfavorable cases.

## Reproducible evidence

[Native checks](<C:/Users/Ritesh/Documents/Codex/2026-10-08/oka/work/adaptive_snn_probe/selective_energy_trial/results/native_models_0_a1/native_checks.json>); [fixed timing replay](<C:/Users/Ritesh/Documents/Codex/2026-10-08/oka/work/adaptive_snn_probe/selective_energy_trial/results/replay_v2_a1/replay_checks.json>); [adaptive timing replay](<C:/Users/Ritesh/Documents/Codex/2026-10-08/oka/work/adaptive_snn_probe/selective_energy_trial/results/replay_v3_a0/replay_checks.json>); [fixed activity/power audit](<C:/Users/Ritesh/Documents/Codex/2026-10-08/oka/work/adaptive_snn_probe/selective_energy_trial/results/annotated_power_v2_a1/power_audit.json>); [adaptive activity/power audit](<C:/Users/Ritesh/Documents/Codex/2026-10-08/oka/work/adaptive_snn_probe/selective_energy_trial/results/annotated_power_v3_a0/power_audit.json>); [audit notes](<C:/Users/Ritesh/Documents/Codex/2026-10-08/oka/work/adaptive_snn_probe/selective_energy_trial/audit_notes.md>); [numeric summary](<C:/Users/Ritesh/Documents/Codex/2026-10-08/oka/outputs/membrane_selective_energy_trial.summary.json>); [SHA256 manifest](<C:/Users/Ritesh/Documents/Codex/2026-10-08/oka/outputs/membrane_selective_energy_trial.manifest.json>).

The root reviewed and executed a separate read-only measurement audit. Delegated agents reached usage limits before completing an independent energy review; no completed agent review is claimed. Frozen architecture sources, routed checkpoints and prior publications are unchanged.

Flow references: [AMD SAIF collection](https://docs.amd.com/r/en-US/ug900-vivado-logic-simulation/Generating-SAIF-Dumping), [AMD read_saif](https://docs.amd.com/r/2025.2-English/ug835-vivado-tcl-commands/read_saif), [AMD report_power](https://docs.amd.com/r/2025.2-English/ug835-vivado-tcl-commands/report_power).
