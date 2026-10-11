# Retained LUT timing replay discrepancy: bounded diagnosis

Read-only audit performed on 2026-10-10. No Vivado runs or RTL changes were made by this audit. The 9 ns and 12 ns routed SDF replays remain failed and must not supply accepted LUT energy estimates. The mapped functional replay passing is useful diagnostic evidence, not a substitute for delayed replay.

## Reproducible numerical locus

Both periods fail at native row 914 with `got=6c0843fa`, `expected=6c085ffa`, and later row 2836 with `got=6dfec486`, `expected=6dfec086`. The 12 ns failures occur at 11126 ns and 34190 ns; the 9 ns failures at 8372 ns and 25670 ns. The identical data errors at identical transaction rows after increasing the period argue against continuing an arbitrary clock-slowing loop.

The packed comparison word is `{in_ready,take,out_valid,out_count,out_data,narrow_mode}`. Controls and upper lane match. At row 914, low-lane expected output is signed12 -3 (`0xffd`) but actual is +509 (`0x1fd`), a +512 error with bits 9--11 changing. The input causing that output is native row 912, U0=-6 and beta0=166: `ceil(-996/256)=-3`. At row 2836, the expected output is +67 (`0x043`) but actual is +579 (`0x243`), again +512. Its input is row 2834, U0=108 and beta0=157: `ceil(16956/256)=67`.

Thus low-lane result bit 9 is a common error locus. In the exported mapped netlist, rounded product bit `p_0_in[17]` reaches LUT3 `fixture/core/lut.lane[0].r[9]_i_1` and FDRE `fixture/core/lut.lane[0].r_reg[9]`. `p_0_in[17]` is O[0] of the final rounding CARRY4 `fixture/core/lut.lane[0].r_reg[11]_i_4`. The same carry produces rounded bits 18 and 19, which also differ in the first failure.

## What the evidence establishes

- The mapped functional diagnostic passes every 17,413 replay row with the same source trace.
- SDF backannotation reports success. The timing run uses max delay, transport interconnect delay, and zero pulse rejection/error thresholds. No timing checks are disabled in the inspected command.
- The 12 ns STA report has WNS +3.605 ns, minimum hold slack +0.138 ns, and zero unconstrained internal endpoints, zero no-clock pins, and zero combinational loops. This does not overrule failed delayed functional replay.
- The failing logs contain numerical failures rather than an accepted replay PASS marker. The simulator can return zero after `$fatal`; acceptance must continue to require the explicit PASS marker.
- Functional success plus period-independent SDF errors makes a carry-path delayed-model/glitch or capture-path issue a plausible hypothesis. The current evidence does not determine whether the first wrong signal is a CARRY4 output, a flip-flop input, the core result register, or the fixture capture. A root cause and corrected result have not been established.

## One bounded diagnostic for later work

Replay the first 950 rows at the existing 12 ns clock, retaining the same RTL, netlist, SDF, comparison, and all timing checks. Record a short waveform for rows 910--916 including U0 and beta0 state registers; final rounding CARRY4 CI, S, CO and O; `p_0_in[17:19]`; r_reg[9:11] D, Q and clock; fixture sink_data[9:11] D, Q and clock. Compare settled carry output with CI/S before capture and compare the register input with the captured Q.

This separates (1) wrong settled carry output, (2) a correct output arriving or glitching near capture, and (3) correct core Q with a fixture capture discrepancy. Only then select a targeted model/tool or implementation correction. Do not waive checks, accept the undelayed diagnostic as timed verification, infer that LUT arithmetic is intrinsically wrong, or claim LUT energy superiority from these failed traces.

## Evidence hashes (SHA-256)

- `hardware/replay9_e2_a0/tool_3.log`: `a6ce7d3b0823ffb07d7ea9d16856e9f59ceb6d1b41ba34a747de358b12448d93`
- `hardware/replay12_e2_a0/tool_3.log`: `1b7741c1883ec1430ebfe103e8313fded669b90e2ae92139ce241a7e4adcb7e9`
- `hardware/replay12_e2_a0/tool_2.log`: `a782d8755a63a903a662d7d5db586122ef0d5b1eef6bb5f3faf85f5793618616`
- `hardware/replay12_e2_a0/tool_2.job.json`: `eb2fdf3f71361521c83b59a95f72ee5f78df49d5b84903b5277a4280bb11a686`
- `hardware/export12_e2_a0/routed.v`: `193072bebe51a9dc6c9af342acbba155de1378d2bb49a3824f8e693ee8fe6712`
- `hardware/export12_e2_a0/routed.sdf`: `9b025cf32a05e1cbc9845d5a9f03ae7631c9197eb2f1f37b6136bc10dfcfe2a5`
- `hardware/native_actual_s0_a3/trace2.txt`: `000f7f466713ac6f020ab468be3b1f4c20553a68451dd3713e738d2adae86785`
- `hardware/lut_functional_diagnostic_a0/diagnostic.json`: `a4890fe9f54e40702889656016befe1c9cec744d557722015a8b67117b397b8c`
- `hardware/common12_e2_a0/timing.rpt`: `5dab7fe190c5d4b279a442b3c5996fc2619012030c3b035504e6c998df41d271`
- `hardware/common12_e2_a0/paths_max.rpt`: `8f6e219ec20ee36ad5bb88b9f441fe4bafd092ed912c640df3f22c0ecd596ab8`
- `hardware/common12_e2_a0/paths_min.rpt`: `97c1b9b3e8742eab1cc8f8efd2f1bc3cc18ebade79e1c4c36ae61a6c71bc8a4a`
- `leak_core.sv`: `a55839cc223ea88a859641686f409ef413c3be064463a11eef0915c9255e1bd7`
- `timing.sv`: `3e4700e10943509a9d36bfa426e029457e782af893637684902053a4a4203769`
- `tb_energy12.sv`: `bea1817f9d3d03a1d1f30b3b9d181883f5ee9e924fc8a14d970c1eded724e026`
