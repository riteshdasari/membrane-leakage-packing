# Selective-correction energy pilot contract

Status: measurement plan prepared on 2026-10-10. No energy result has been measured.

This is a measurement-only continuation of the completed matched fixed study.
Preserve the frozen RTL, routed checkpoints, retirement traces and publications.
Compare fixed I8 residue V2 against shared adaptive correction V3 first. The DSP
layout and six low-part lanes remain fixed; adaptation selects correction work.

## Frozen evidence and useful work

Inputs are in ../common_layout_trial:

- guard_add_selective.sv, SHA256 b5c7d724d642b2310c4e447eabccaf965a3aa520aaf2e04c5f93accd5dbb9e48.
- tb_guard_add_selective.sv (reuse its native driver without changing the file).
- results/selective_models_p1_0/stream_stim.txt and the matching check JSON.
- results/top_guard_add_selective_v2_route/design.dcp.
- results/top_guard_add_selective_v3_route/design.dcp.

Use a 6 ns clock throughout. Both variants must complete the same ordered
110,592 requests and 635,904 scalar updates with exact saved-reference outputs.
Expected native service is 110,596 clocks for V2 and 110,710 for V3. V3 must
reproduce 1,008 correction jobs and 114 correction freezes. The saved leakage
reference differs from original training; no trained-accuracy claim follows.

## Execution and success gates

1. Add a native trace top with an always #3 clock and PROFILE=1. Instantiate
   the frozen native driver as local V0/V1, corresponding to frozen V2/V3.
   Record every core input/control/output clock, reset prelude and useful-work
   interval. Recheck arithmetic, retirement hashes, service and correction counts.
2. Export each complete matching routed DCP to a timing Verilog netlist and slow
   SDF with one Vivado thread. Preserve original DCPs and source/report hashes.
3. Replay each native pin trace through its existing registered fixture. Drive
   top inputs at falling edges and verify the launch/capture cycle offsets against
   the full native trace. The 219-FF fixture is not a ready/valid adapter: never
   schedule requests from its delayed ready output. Include glbl initialization
   and required primitive libraries; no timing-check suppression.
4. Gate-level replay must have no useful-output unknowns, control/result
   mismatches or SDF timing violations. If it fails, stop the measurement and
   diagnose before collecting comparative power. The negative raw-port hold
   budgets remain a limitation; replay does not validate a production interface.
5. Collect whole-fixture routed-netlist SAIF after initialization over an audited
   work interval. Include all controller, stall and exceptional clocks, plus the
   same explicitly recorded fixture settling convention. Record actual SAIF
   duration instead of inferring it from native service clocks. Close collection
   before simulator termination.
6. Annotate each SAIF onto its exact matching DCP. Audit annotation coverage,
   unmatched nets, unknown time, 6 ns clock, DSP enables and controller activity.
   Preserve warnings and identical operating/report settings. RTL-only activity
   and default toggle assumptions cannot establish the comparative result.

Estimated dynamic energy per scalar update is average dynamic power times
audited activity duration divided by 635,904. Report whole-fixture estimates and
any trustworthy core hierarchy breakdown separately. Do not subtract power using
resource counts or the 219-FF fraction. Keep static device power and OOC clock
limitations explicit; this is not a board power measurement.

Run heavy tools serially. Check RAM immediately before each job; use the proven
1.2 GiB free gate for native RTL simulation and a conservative 2.3 GiB gate for
the unmeasured routed/SAIF pilot, recording actual peak memory. Do not close user
applications or lower gates to force progress.

Only after a valid pilot, repeat saved backpressure and unfavorable stress cases.
Then compare the matched I8 hybrid and LUT-only routes from ../i8_fixed_trial.
A V3-versus-V2 energy benefit alone would not establish superiority over those
alternatives. A negative result is evidence; do not change the workload to hide it.

## Installed-flow references

- [AMD timing simulation](https://docs.amd.com/r/en-US/Vivado-Design-Suite-User-Guide-Design-Flows-Overview-UG892/Timing-Simulation)
- [AMD SAIF collection](https://docs.amd.com/r/en-US/ug900-vivado-logic-simulation/Generating-SAIF-Dumping)
- [AMD read_saif](https://docs.amd.com/r/2025.2-English/ug835-vivado-tcl-commands/read_saif)
- [AMD report_power](https://docs.amd.com/r/2025.2-English/ug835-vivado-tcl-commands/report_power)

Implementation remains to be written and independently audited. No adaptive
energy benefit is presumed from the 99.84% fast-path fraction.
