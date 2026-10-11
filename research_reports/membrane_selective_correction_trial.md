# Membrane-aware selective exact correction trial

This is one coordinated common-layout study: first establish a strong fixed exact reference, then adapt its high-part correction using actual membrane/current values and DSP carry. All outputs remain exact signed12 U+I; the generic domain is signed11 U and signed11 I, and the separately certified specialization uses signed11 U and signed8 I.

## Mechanism and scope

Every DSP request uses six fixed eight-bit fields containing unsigned7 residues. For U=128hU+rU and I=128hI+rI, the DSP returns s=rU+rI, c=s[7], and low=s[6:0]. The exact high result is H=hU+hI+c and the output is {H[4:0],low[6:0]}. Field positions never change and no significant bit is discarded.

If both operands fit signed8, H=c-signU-signI fits signed2. If current fits signed8 and c equals signI, H=hU exactly even for a wider membrane. The union of these certificates selects a cheap exact recovery; otherwise one shared full high corrector repairs the exceptional lanes in order. Its first correction is fused into the normal output stage; k bad lanes add max(k-1,0) globally frozen clocks. Output backpressure, input retention, reset cancellation and ordered output assembly are part of the RTL.

For example, U=-257 and I=-1 have residue carry one, equal to the current sign, so the exact high part can be copied and the result is -258. U=-256 with the same current has residue carry zero and needs a high-part decrement to produce -257. Both membranes are outside signed8; the current/carry certificate distinguishes whether the update crosses a residue boundary. Monitoring membrane magnitude alone would send both through the general corrector. Neither path changes a threshold decision because both produce the same exact integer sum as the reference.

The adaptive choice concerns correction work. The DSP still issues a constant six-field layout for every accepted request. This is membrane-aware adaptive exact correction for packed DSP addition, rather than a claim that DSP lane count changes.

The common fixed V0 reference precomputes five-bit hU+hI at acceptance and applies the DSP residue carry later. V1 retains both four-bit highs until the output merge. Selective V0/V1 compare fixed versus shared full-current correction. Selective V2/V3 compare fixed versus shared correction with a declared static signed8-current contract.

## Measured hardware and service

Routes use Vivado 2025.2, xc7a100tcsg324-1, one thread and a 6 ns target with the same registered OOC fixture. Core counts exclude 219 fixture FFs (138 launch and 81 capture). Core/fixture slice sets overlap; their occupied slices are not additive.

- Common fixed V0: 82 LUT / 262 FF / 1 DSP, registered WNS +1.903 ns / WHS +0.103 ns; passes registered timing. Core touches 60 slices; 110,596 saved service clocks.
- Common fixed V1: 50 LUT / 316 FF / 1 DSP, registered WNS +1.280 ns / WHS +0.108 ns; passes registered timing. Core touches 79 slices; 110,596 saved service clocks.
- Selective V0, Fixed six high corrections, full signed11 current: 50 LUT / 316 FF / 1 DSP, registered WNS +1.600 ns / WHS +0.128 ns; passes registered timing. Core touches 63 slices; 110,596 saved service clocks, 0 shared-corrector steps and 0 internal freeze clocks. Separate raw-port WNS +1.600 ns / WHS -1.074 ns.
- Selective V1, Shared exact correction, full signed11 current: 177 LUT / 322 FF / 1 DSP, registered WNS -0.794 ns / WHS +0.103 ns; fails registered timing. Core touches 77 slices; 110,710 saved service clocks, 1,008 shared-corrector steps and 114 internal freeze clocks. Separate raw-port WNS -0.794 ns / WHS -1.075 ns.
- Selective V2, Fixed six high corrections, statically signed8 current: 43 LUT / 262 FF / 1 DSP, registered WNS +2.141 ns / WHS +0.130 ns; passes registered timing. Core touches 54 slices; 110,596 saved service clocks, 0 shared-corrector steps and 0 internal freeze clocks. Separate raw-port WNS +1.750 ns / WHS -1.146 ns.
- Selective V3, Shared exact correction, statically signed8 current: 147 LUT / 268 FF / 1 DSP, registered WNS +0.108 ns / WHS +0.132 ns; passes registered timing. Core touches 68 slices; 110,710 saved service clocks, 1,008 shared-corrector steps and 114 internal freeze clocks. Separate raw-port WNS +0.108 ns / WHS -1.072 ns.

The saved model stream offers 110,592 windows covering 635,904 scalar pairs. The union certificate handles 634,896 pairs (99.84%); 1,008 pairs require shared correction in 894 windows. Only 96 windows contain two exceptions and nine contain three, so the fused controller adds 114 clocks. This gives 0.103% more service clocks than always-six fixed correction/hybrid/LUT kernels, and 30.61% fewer than native4 with its ordered identity copies. These are physical RTL service clocks with continuously offered inputs and ready output, not arrival-burst latency or full-neuron-update latency.

The carry certificate materially strengthens a membrane range check. A software signed8 range-only screen leaves 8,631 exceptional pairs; the union leaves 1,008 (88.32% fewer exceptional jobs). For the same fused control model, range-only would predict 3,672 freezes and 114,268 clocks, whereas the implemented union measures 114 freezes and 110,710 clocks. The range-only case is an arithmetic/controller diagnostic, not a measured hardware baseline. The extension is exact because it recognizes when the high part of a wide actual membrane is unchanged by the residue carry/current sign.

All 46,336 zero-current pairs satisfy exact high copy, but the fast path also handles 588,560 of 589,568 nonzero-current updates (99.829%). The same 1,008 exceptions remain after excluding identity updates, so the high recovery result is broader than zero-current skipping.

The shared saved-stream physical-latency histograms are:

- V1: 110,288 requests at 4 clocks, 270 requests at 5 clocks, 30 requests at 6 clocks, 4 requests at 7 clocks.
- V3: 110,288 requests at 4 clocks, 270 requests at 5 clocks, 30 requests at 6 clocks, 4 requests at 7 clocks.

A request can wait for preceding windows to finish correction; its latency is not determined only by its own bad-lane count. Stress tests include full-range negative and positive sums, poisoned unavailable tails, range/carry transitions, reset interruption and output stalls. Observed no-backpressure stress statistics are:

- Profile 0: 147,709 correction steps, 113,116 correction freezes; maximum internal freeze run 5 clocks, physical request latency 4–19 clocks and 250,076 shared versus 137,454 fixed service clocks (+81.934%). Source gaps are present in these stress streams.
- Profile 1: 39,324 correction steps, 14,102 correction freezes; maximum internal freeze run 5 clocks, physical request latency 4–16 clocks and 151,229 shared versus 137,454 fixed service clocks (+10.022%). Source gaps are present in these stress streams.

Independent arithmetic/control models also cover sustained six-exception windows in both domains: each adds five freeze clocks. A 64-window all-bad burst predicts 388 clocks in that control model; this particular burst figure is not an RTL or arrival-queue measurement. Wide membranes with zero current use exact high copy and need no exceptional correction. The much higher stress penalties than the saved model penalty expose the workload dependence: sharing pays latency when exceptional lanes are frequent.

## Strong fixed comparisons and interpretation

Immutable local references remain: native4 at 25 LUT/240 FF/1 DSP and 159,540 saved clocks; retimed hybrid6 at 66 LUT/248 FF/1 DSP and 110,596 clocks; retimed LUT6 at 79 LUT/304 FF/0 DSP and 110,596 clocks. The prior adaptive layout is 130 LUT/247 FF/1 DSP and 115,758 clocks. These are matched arithmetic kernels, not reproduced FireFly accelerators.

- Shared V1 versus matched fixed V0: +127 LUT / +6 FF / +0 DSP; +114 saved service clocks (+0.103%).
- Shared V1 versus fixed common V0: +95 LUT / +60 FF / +0 DSP; +114 saved service clocks (+0.103%).
- Shared V1 versus retimed hybrid6: +111 LUT / +74 FF / +0 DSP; +114 saved service clocks (+0.103%).
- Shared V1 versus retimed LUT6: +98 LUT / +18 FF / +1 DSP; +114 saved service clocks (+0.103%).
- Shared V3 versus matched fixed V2: +104 LUT / +6 FF / +0 DSP; +114 saved service clocks (+0.103%).
- Shared V3 versus fixed common V0: +65 LUT / +6 FF / +0 DSP; +114 saved service clocks (+0.103%).
- Shared V3 versus retimed hybrid6: +81 LUT / +20 FF / +0 DSP; +114 saved service clocks (+0.103%).
- Shared V3 versus retimed LUT6: +68 LUT / -36 FF / +1 DSP; +114 saved service clocks (+0.103%).

For the certified current8 workload, original shared V3 versus matched fixed V2 costs +104 LUT / +6 FF / +0 DSP and 114 extra saved service clocks. The corrector units being shared are small: current8 high recovery is an exact increment, decrement or copy. The controller additionally needs range predicates, priority/operand selection, retained operands and partial-output patching. Its mapped cost must be compared with the mapped fixed recovery, rather than counting abstract adder units removed. The fast-path certificate and its bounded exception cost are established; a practical benefit from that hardware tradeoff is a separate question.

The resource differences above decide whether sharing supplies a useful bounded tradeoff. LUTs, FFs, DSPs, timing and service are separate axes; no weighted total area or replicated throughput is measured. Fixed6 already consumes every supplied window in one issue, so adaptive sharing trades any measured arithmetic/resource saving for exception latency. A stronger adaptive capability does not by itself establish a hardware benefit.

The signed8-current specialization is essential: independently summed negative and positive weights certify all binary-spike currents in [-100,70], for these saved matrices. Thus H=hU+c-signI can be statically implemented without an I8 detector. V2 is the matched static correction baseline; V3 must be judged against it. The general retimed hybrid/LUT kernels additionally support full I11, so their resource comparison with I8-only V2/V3 has this explicit contract difference. Independently specializing hybrid/LUT hardware to I8 could strengthen them further and remains unmeasured. No global best-fixed claim follows.

99.84% fast-path membership means that most valid outputs do not require an exceptional corrector step. It does not mean 99.84% less circuit activity, power or energy: combinational shared-adder inputs and selection logic can still toggle when no correction step retires. Controller/mux/retained-register overhead is included in the routed core; switching power is not measured.

## Separately verified provisional-high decode optimization

The optional decode cohort changes one provisional-data expression: fast_small ? small_extension : (fast_copy ? hU : 0) becomes fast_small ? small_extension : hU. The fast_copy predicate remains in the bad-lane mask. For an exceptional lane, the provisional high bits are hidden while output valid is zero and are overwritten by exact correction before the completed window is visible. Fixed variants use their unchanged parallel answer. The source and evidence of the four original selective variants remain intact.

All eight decode suites reproduce their parent retirement files byte for byte, including physical clock columns, and match every parent row. They add 23,158,640 repeated scalar checks without a new workload or domain. Sixteen decode SNN replays match the same parent states, spikes, counts and sampled classifications. The separate read-only invariant audit is a reasoning artifact; simulation and routing provide the separate measured evidence.

Only shared decode V1/V3 are routed. Fixed decode V0/V2 are functionally checked; their existing parent fixed routes remain the cost comparators.

- Decode V1: 179 LUT / 322 FF / 1 DSP, change from original shared V1 +2 LUT / +0 FF / +0 DSP; registered WNS -0.795 ns / WHS +0.023 ns, fails registered timing. Saved physical service remains 110,710 clocks. Raw-port WNS -0.795 ns / WHS -1.057 ns.
- Decode V1 versus matched parent fixed V0: +129 LUT / +6 FF / +0 DSP; +114 saved service clocks (+0.103%).
- Decode V1 versus fixed common V0: +97 LUT / +60 FF / +0 DSP; +114 saved service clocks (+0.103%).
- Decode V1 versus retimed hybrid6: +113 LUT / +74 FF / +0 DSP; +114 saved service clocks (+0.103%).
- Decode V1 versus retimed LUT6: +100 LUT / +18 FF / +1 DSP; +114 saved service clocks (+0.103%).
- Decode V3: 158 LUT / 268 FF / 1 DSP, change from original shared V3 +11 LUT / +0 FF / +0 DSP; registered WNS +0.143 ns / WHS +0.012 ns, passes registered timing. Saved physical service remains 110,710 clocks. Raw-port WNS +0.143 ns / WHS -1.154 ns.
- Decode V3 versus matched parent fixed V2: +115 LUT / +6 FF / +0 DSP; +114 saved service clocks (+0.103%).
- Decode V3 versus fixed common V0: +76 LUT / +6 FF / +0 DSP; +114 saved service clocks (+0.103%).
- Decode V3 versus retimed hybrid6: +92 LUT / +20 FF / +0 DSP; +114 saved service clocks (+0.103%).
- Decode V3 versus retimed LUT6: +79 LUT / -36 FF / +1 DSP; +114 saved service clocks (+0.103%).

The provisional-high simplification increases routed LUT count in both tested profiles. Registers, DSP count and physical service are unchanged. The original current8 shared variant remains the lower-LUT choice at this target; the general-current decode variant still fails the 6 ns registered constraint. This is a verified implementation experiment without an area saving or a repair of the general-current timing failure.

This isolates a hardware implementation change within the same exact adaptive policy. It supplies no new lane-count adaptation or service-count gain. Any LUT/FF/timing difference is measured for these routed OOC cores. Hidden provisional values may change activity, so output equivalence does not establish a power or energy reduction. The current-I8 specialization and stronger fixed-comparator qualifications above still apply.

Decode evidence: [isolated source](<C:/Users/Ritesh/Documents/Codex/2026-10-08/oka/work/adaptive_snn_probe/common_layout_trial/guard_add_selective_decode.sv>), [invariant audit](<C:/Users/Ritesh/Documents/Codex/2026-10-08/oka/work/adaptive_snn_probe/common_layout_trial/decode_audit.md>), [two decode routes](<C:/Users/Ritesh/Documents/Codex/2026-10-08/oka/work/adaptive_snn_probe/common_layout_trial/results/selective_decode_hardware.json>).

## Exactness and evidence boundaries

Eight selective suites check 23,158,640 repeated scalar outputs across two domains, stress/model sets, four local variants and both backpressure settings. Four common fixed suites additionally check 11,579,320 repeated outputs. The selective arithmetic sequences match the direct retimed hybrid/LUT references in numeric order, while clock columns differ for shared correction. Fixed output files are byte-identical within each suite. This is repeated checking, not exhaustive six-neuron vectors.

The independent common arithmetic screen covers 4,194,304 scalar pairs and 100,000 packed cases. The policy screen covers the same full scalar domain and 18,432 packed/tail cases, including 524,288 signed11-U/signed8-I pairs. All report zero mismatches. Profile0 stress retains the original U11/I11 data. Profile1 maps stress currents by signed8 modular projection and explicitly changes the declared test domain; it is not lossless requantization of the original full-current stress operation. Saved model operands are identical in both profiles.

Sixteen selective saved-output replays and eight common-output replays match every reference state, spike, spike count and sampled classification for the same 144 images across three seeds. Leakage at beta 231/256 and threshold/subtractive reset execute in Python; exact U+I executes in RTL. Integer-equivalent sums preserve that declared threshold behavior. The leakage was changed from original training, so this is equivalence to the saved integer reference, not preservation of original trained-model accuracy or a complete RTL SNN.

The considered temporal cache stores 13 payload bits per live neuron: 1,794 bits for one 138-neuron image before valid/ports, rather than the sum across all offline image identities. It was screened without RTL and is not part of this implementation. Signed13–15 widening and alternative leakage ranges are outside this measured trial; no padded saved data are used to manufacture a wider-baseline advantage.

Registered timing is OOC fixture timing. Raw ports have a separate 1 ns setup/0.1 ns minimum budget; a negative raw-port hold result is not production interface closure. No board Fmax is inferred from target minus WNS. Memory supply, dependent-neuron scheduling, host work, full threshold/reset RTL, arrival-burst latency, power and energy remain unmeasured. This trial establishes no first-ever claim.

Evidence: [selective RTL](<C:/Users/Ritesh/Documents/Codex/2026-10-08/oka/work/adaptive_snn_probe/common_layout_trial/guard_add_selective.sv>), [four routes](<C:/Users/Ritesh/Documents/Codex/2026-10-08/oka/work/adaptive_snn_probe/common_layout_trial/results/selective_hardware.json>), [policy/control proofs](<C:/Users/Ritesh/Documents/Codex/2026-10-08/oka/work/adaptive_snn_probe/common_layout_trial/common_adaptation_policy_results.json>), [known-weight current certificate](<C:/Users/Ritesh/Documents/Codex/2026-10-08/oka/work/adaptive_snn_probe/common_layout_trial/common_i8_current_bounds.json>), [complete streamed manifest](<C:/Users/Ritesh/Documents/Codex/2026-10-08/oka/outputs/membrane_selective_correction_trial.manifest.json>).
