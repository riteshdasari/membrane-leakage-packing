# Guarded membrane-plus-current addition trial

Against the native four-lane DSP with the same identity-copy policy, the adaptive kernel uses 115,758 rather than 159,540 supplied-window clocks (27.44% fewer). Its measured core is 157 LUT / 267 FF / 1 DSP versus 25 LUT / 240 FF / 1 DSP (+132 LUT, +27 FF, +0 DSP). Both pass registered setup and hold at the common 6 ns target, so this is a supported primitive service-clock tradeoff for the replayed trace.

The always-six hybrid and LUT kernels need 110,596 supplied-window clocks; the adaptive schedule is 4.67% longer. Their cores are 66 LUT / 268 FF / 1 DSP and 79 LUT / 364 FF / 0 DSP, respectively. Adaptive differences are +91 LUT, -1 FF, +0 DSP versus hybrid and +78 LUT, -97 FF, +1 DSP versus LUT6. The hybrid uses fewer LUTs and the same DSP count for a shorter schedule, at the cost of one extra FF. The adaptive one-FF saving alone does not establish a useful practical advantage over this hybrid.

The operation is exact signed 11-bit membrane U plus signed 11-bit synaptic current I, returning a signed 12-bit sum. This ordered addition primitive changes the DSP arithmetic format according to the actual operand values; it is distinct from the earlier leakage multiplication trial.

The compared mechanisms are:

- E0 uses a DSP with immutable ONE48 mode. When all presented U and I values fit signed 7 bits, it can add five or six neurons in six 8-bit fields with guard bits. Otherwise it uses four 12-bit guarded fields. Sign metadata reconstructs the exact signed sums.
- E0 and E1 share the ordered identity-copy optimization for zero-current fifth/sixth lanes. A copy that consumes the whole window is preferred; a partial fifth copy does not prevent E0 from accepting an eligible six-lane narrow request.
- E1 uses the DSP's native FOUR12 mode for four full-range additions plus eligible identity copies. E2 uses the same native four lanes plus two LUT additions and accepts all six. E3 uses six LUT additions and accepts all six.

All four are placed and routed for xc7a100tcsg324-1 at 6 ns with Vivado 2025.2 and one thread. Core resources exclude the identical 219 preserved fixture FFs (138 launch + 81 capture). The fixture registers raw U, I, availability, valid, ready and reset, and captures every output unconditionally. It is a timing fixture, not a working production handshake wrapper. Retained hierarchy prevents optimization across the core boundary and limits conclusions about a fully integrated design.

The final measured resource and timing vectors are:

- E0 Adaptive guarded DSP: core 157 LUT / 267 FF / 1 DSP; full fixture 157 LUT / 486 FF / 1 DSP, 108 occupied slices. Registered WNS +1.036 ns, WHS +0.013 ns; passes registered setup/hold. Separate raw-port audit WNS +1.036 ns / WHS -1.138 ns. Model 115,754 requests, 115,758 supplied-window clocks.
- E1 Native DSP four-lane + identity copies: core 25 LUT / 240 FF / 1 DSP; full fixture 25 LUT / 459 FF / 1 DSP, 109 occupied slices. Registered WNS +2.074 ns, WHS +0.108 ns; passes registered setup/hold. Separate raw-port audit WNS +1.754 ns / WHS -1.084 ns. Model 159,536 requests, 159,540 supplied-window clocks.
- E2 Native DSP four-lane + two LUT lanes: core 66 LUT / 268 FF / 1 DSP; full fixture 66 LUT / 487 FF / 1 DSP, 105 occupied slices. Registered WNS +2.320 ns, WHS +0.103 ns; passes registered setup/hold. Separate raw-port audit WNS +1.827 ns / WHS -1.089 ns. Model 110,592 requests, 110,596 supplied-window clocks.
- E3 Six LUT lanes: core 79 LUT / 364 FF / 0 DSP; full fixture 79 LUT / 583 FF / 0 DSP, 138 occupied slices. Registered WNS +2.007 ns, WHS +0.080 ns; passes registered setup/hold. Separate raw-port audit WNS +1.749 ns / WHS -1.151 ns. Model 110,592 requests, 110,596 supplied-window clocks.

Occupied core and fixture slice sets overlap, so touched-slice counts cannot be added or subtracted as independent area. The separate raw-port audit uses declared 1 ns setup and 0.1 ns minimum budgets; any negative port hold slack is not production interface closure. No maximum operating frequency is inferred from target minus WNS.

The trace accounting helps explain the primary comparison:

- The saved 635,904-neuron trace contains 589,568 changing additions (I ≠ 0). E0 and E1 perform all of them in the DSP: 5.093284 versus 3.695517 changing additions per issue (37.82% higher for E0). This is semantic work per issued request, not clock utilization, switching, power or energy.
- E0 uses 92,384 narrow requests and copies 1,689 neurons; E1 copies 12,257. Different grouping changes the number of copies without changing the exact scalar results.
- E2 performs 400,061 changing additions in the DSP and 189,507 in LUTs; E3 performs all 589,568 in LUTs. Their shorter always-six schedules remain necessary practical comparisons.
- The workload screen field named issued_dsp_lane_capacity counts the issued valid lane operations for this screen; it is not a denominator for physical lane utilization, because unused tail capacity is excluded.

The four current checksets cover 11,579,320 checked scalar outputs: 811,511 stress inputs and 635,904 saved model inputs, each replayed across four engines with and without backpressure. These are repeated inputs across configurations, not unique exhaustive multi-neuron cases. All output, ordering, tail, reset-cancellation, stall-stability and four-advancing-clock checks pass. There is no exhaustive claim over all combinations of four signed 11-bit operand pairs.

The independent saved SNN replay matches every reference state, spike, output spike count and sampled classification for three seeds with 48 images each (144 images total). It computes leakage in Python using beta = 231/256 (Q8 coefficient 231), adds membrane/current in RTL, then applies threshold and subtractive reset in Python. This reference uses a changed leakage coefficient; it does not establish preservation of the models' original trained accuracy, new training, or a full SNN RTL implementation.

The final measured source retains the presented payload in its input registers. Earlier masking of unconsumed payload lanes was verified separately, but that snapshot was not routed. No measured area or timing improvement is attributed to removing the mask.

Optional earlier masked evidence: [snapshot manifest](<C:/Users/Ritesh/Documents/Codex/2026-10-08/oka/work/adaptive_snn_probe/results/guard_add_masked_4d098563a894/manifest.json>). It has no hardware measurements.

A further fixed alternative remains unmeasured: six guarded 7-bit residue additions in ONE48 with exact high-part reconstruction in fabric. For each signed 11-bit operand, U = 128 hU + rU and I = 128 hI + rI with unsigned 7-bit residues. The DSP can compute six residue sums without interlane carry; fabric high-part addition and the residue carry recover each full signed 12-bit sum. This stateless design differs from the earlier persistent spill/carry recovery experiments. Its resource and timing cost is unknown here, so the native-four comparison cannot establish superiority over fixed packing generally or the best one-DSP implementation.

Memory supply, gather/scatter, a state memory controller, threshold/reset hardware, burst arrival latency, host performance, board timing and power remain outside this primitive trial. FireFly accelerator results were not reproduced or compared by RTL here. The fixed DSP and LUT kernels are local implementations of this same addition operation; exact mechanism novelty remains unproved.

Evidence: [four route results](<C:/Users/Ritesh/Documents/Codex/2026-10-08/oka/work/adaptive_snn_probe/results/guard_add_hardware.json>), [SNN replay](<C:/Users/Ritesh/Documents/Codex/2026-10-08/oka/work/adaptive_snn_probe/results/guard_add_snn_checks.json>), [work accounting](<C:/Users/Ritesh/Documents/Codex/2026-10-08/oka/work/adaptive_snn_probe/results/guard_add_workload_screen.json>), [current core](<C:/Users/Ritesh/Documents/Codex/2026-10-08/oka/work/adaptive_snn_probe/guard_add.sv>), [source/report/checkpoint manifest](<C:/Users/Ritesh/Documents/Codex/2026-10-08/oka/outputs/guarded_membrane_addition_trial.manifest.json>).
