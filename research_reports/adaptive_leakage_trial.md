# Membrane-aware adaptive leakage packing: completed RTL trial

The exact three-versus-two mechanism and a targeted retiming repair are implemented and tested. The best tested constant adaptive version uses 278 LUTs versus 176 for the retimed fixed DSP version, with a longer internal critical path. Its 5.39% sampled complete-unit cycle saving does not offset the timing penalty. This trial therefore demonstrates exactness, but **does not demonstrate a hardware benefit over the tested fixed DSP and LUT alternatives**.

## What was tested

The implemented unit reads six signed 11-bit membranes, computes exact integer leakage, and returns all six results. It chooses two three-neuron DSP issues when all six actual membranes fit [-16,15], otherwise three two-neuron full-range issues. Selection is causal and computed from the supplied membrane values, rather than a spike-rate estimate. Both adaptive and fixed units bypass all-zero groups and delta = 0 identity leakage.

The contract is U_leak=ceil((256-delta)*U/256)=U-floor(delta*U/256), shared delta in [0,31]. Constant delta = 25 means beta = 231. Programmable delta may change between accepted groups. The unit contains the raw membrane bank, range monitor, operand multiplexers, DSP encoding, exact corrections, metadata pipeline, output bank and ready/valid scheduler. No packing is delegated to a host. This remains a leakage primitive, not a full SNN accelerator.

## Exactness and safety

There are 56 engine/configuration runs and 3,598,368 checked six-neuron group outputs across the original and retimed implementations, including repeated requests across reference engines. All match the independent scalar integer oracle. Tests cover every signed 11-bit scalar value at every allowed delta, all int5 triples at delta = 25, random wider groups, format transitions, zero/identity bypass, input bubbles, and cancellation by reset. Both pipeline options are simulated. The previously completed arithmetic audit covers all 1,048,576 int5-triple/delta combinations; it is not confused with an exhaustive whole-controller proof.

The model replay covers 110,592 groups, every neuron including padded tails, first 48 held-out images from each of three saved seeds and 32 timesteps. Leakage runs in RTL; current integration, threshold/reset and classification are reconstructed in Python. Reconstructed states, output spikes and spike counts match exactly. This establishes the tested integer trajectory equality, not full-network FPGA execution.

Beta = 231 modifies the dynamics of the saved models, whose original beta was a shift/identity case. We do not claim unchanged accuracy relative to those original models, and we did not retrain. Accuracy equality here is between scalar beta = 231 and the RTL-assisted beta = 231 replay.

For all nine saved threshold/weight configurations, an inductive bound was checked at beta = 231. If N is the sum of negative-weight magnitudes and P the sum of positive weights for a neuron, choose L=-ceil(256*N/25) and H=max(theta-1,ceil(256*max(P-theta,0)/25)). Monotonic leakage gives leak(L)-N>=L and max(theta-1,leak(H)+P-theta)<=H. Initialization lies in the interval. Every allowed binary input prefix stays in the checked 11-bit range, including hard or one subtractive reset per timestep. This is an arithmetic range certificate for these coefficients and weights, not formal RTL verification or a bound for arbitrary SNNs.

## Measured cycles, rather than issue counts alone

With the registered multiplier enabled, the unit needs five clocks of service per nonzero narrow group and six per nonzero wider group, including accepting the group and producing its result. It uses four clocks for six parallel LUT lanes. A zero or identity group needs one clock. From the input-accept edge, corresponding result latencies are four, five, three and zero clocks. No intergroup overlap is implemented.

Across the sampled three-model replay, adaptive leakage takes **610,890 clocks versus 645,682** for fixed DSP packing: **5.39% fewer complete-unit clocks**. The six-parallel LUT core takes 431,646 clocks on exactly the same groups.

- Seed 0, first 48 images: adaptive 200,362 clocks versus fixed 214,939; leakage-unit saving 6.78%; reference and reconstructed classification 93.75%; exact spike counts matched.
- Seed 1, first 48 images: adaptive 207,205 clocks versus fixed 215,374; leakage-unit saving 3.79%; reference and reconstructed classification 95.83%; exact spike counts matched.
- Seed 2, first 48 images: adaptive 203,323 clocks versus fixed 215,369; leakage-unit saving 5.59%; reference and reconstructed classification 97.92%; exact spike counts matched.

The complete 360-image numerical profiles, all nine saved configurations and both reset policies, count every neuron and give 3.83-9.53% complete-group clock savings. These profiles apply the RTL-validated service equation; they are not 360-image RTL runs. Adding a common paired-event addition and threshold/reset schedule reduces the opportunity to 1.20-3.04% in that declared total-update proxy. The rest of the neuron datapath has not been routed, so this is not measured full-neuron latency.

The six-lane interface includes zero padding: 128 hidden neurons leave four padded lanes in the final group, and 10 output neurons leave two. Both tested cores bypass only completely zero groups. An additional optimistic fixed schedule that skips individual zero pairs reduces sampled fixed service from 645,682 to 631,000 clocks; the tested adaptive core's remaining saving would be 3.19%. Across the 18 full numerical profiles, that comparison ranges from -1.71% to 4.50% (negative means the current adaptive schedule takes more clocks). Pair-skipping control, output bypass and timing are not implemented, so these are analytic schedule estimates rather than measured stronger RTL results. An optimistic adaptive schedule that also skips zero triples and chooses the cheaper eligible format would save 4.84% versus that sparse fixed schedule. This audit makes explicit why padded-group savings are not sufficient evidence against every strong fixed implementation.

- Subtractive reset, 320 sparse/burst steps: adaptive 1881 leakage clocks, fixed 1910; saving 1.52%.
- Hard reset, 320 sparse/burst steps: adaptive 1649 leakage clocks, fixed 1670; saving 1.26%.

Bursts generally make the membranes wide. The adaptive unit then performs the same three issues as fixed packing, so this mechanism does not provide an inherent worst-case burst-latency reduction. Average leakage issue savings should not be advertised as burst acceleration.

## Hardware and the targeted repair

Vivado 2025.2, Artix-7 xc7a100tcsg324-1, single-thread out-of-context placement/routing, common 4 ns target. Initial and compact sources and all report files are preserved. The compact variant moves the exact high correction into the stage before final result extraction, narrows the residue-floor and int5 arithmetic, retains only required third-lane bits, and expresses the output selection as fixed cases. No additional service cycle is added. Full oracle, model and burst tests pass after the change.

- **initial, const:** adaptation adds 152 LUTs and 27 fabric FFs; internal period is 1.351 times the matched fixed DSP period. Internal timing multiplied by sampled trace cycles is 1.278 times fixed (diagnostic, not board latency).
- **initial, prog:** adaptation adds 176 LUTs and 43 fabric FFs; internal period is 1.098 times the matched fixed DSP period. Internal timing multiplied by sampled trace cycles is 1.038 times fixed (diagnostic, not board latency).
- **compact, const:** adaptation adds 102 LUTs and 26 fabric FFs; internal period is 1.163 times the matched fixed DSP period. Internal timing multiplied by sampled trace cycles is 1.100 times fixed (diagnostic, not board latency).
- **compact, prog:** adaptation adds 165 LUTs and 13 fabric FFs; internal period is 1.128 times the matched fixed DSP period. Internal timing multiplied by sampled trace cycles is 1.067 times fixed (diagnostic, not board latency).

- **const, compact adaptive versus top_delta_fixed_const:** internal timing multiplied by sampled trace cycles is 1.108 times fixed. This selects the faster of both tested fixed DSP versions, rather than requiring the reference to use an unfavorable repair.
- **prog, compact adaptive versus top_delta_fixed_prog:** internal timing multiplied by sampled trace cycles is 1.269 times fixed. This selects the faster of both tested fixed DSP versions, rather than requiring the reference to use an unfavorable repair.

- **top_delta_adapt_const:** 334 LUTs, 272 fabric FFs, 1 DSP, 0 RAMB18, 0 RAMB36; internal setup slack -1.398 ns, hold +0.117 ns; internal period estimate 5.398 ns. With the declared external-delay budget: setup -2.265 ns, hold -0.402 ns.
- **top_delta_fixed_const:** 182 LUTs, 245 fabric FFs, 1 DSP, 0 RAMB18, 0 RAMB36; internal setup slack +0.005 ns, hold +0.155 ns; internal period estimate 3.995 ns. With the declared external-delay budget: setup -0.913 ns, hold -0.402 ns.
- **top_delta_lut2_const:** 181 LUTs, 225 fabric FFs, 0 DSP, 0 RAMB18, 0 RAMB36; internal setup slack -0.307 ns, hold +0.146 ns; internal period estimate 4.307 ns. With the declared external-delay budget: setup -1.320 ns, hold -0.402 ns.
- **top_delta_lut6_const:** 223 LUTs, 379 fabric FFs, 0 DSP, 0 RAMB18, 0 RAMB36; internal setup slack +0.286 ns, hold +0.142 ns; internal period estimate 3.714 ns. With the declared external-delay budget: setup -0.846 ns, hold -0.402 ns.
- **top_delta_rom2_const:** 122 LUTs, 145 fabric FFs, 0 DSP, 0 RAMB18, 1 RAMB36; internal setup slack +0.660 ns, hold +0.155 ns; internal period estimate 3.340 ns. With the declared external-delay budget: setup -1.160 ns, hold -0.437 ns.
- **top_delta_adapt_prog:** 385 LUTs, 277 fabric FFs, 1 DSP, 0 RAMB18, 0 RAMB36; internal setup slack -2.525 ns, hold +0.110 ns; internal period estimate 6.525 ns. With the declared external-delay budget: setup -3.045 ns, hold -0.402 ns.
- **top_delta_fixed_prog:** 209 LUTs, 234 fabric FFs, 1 DSP, 0 RAMB18, 0 RAMB36; internal setup slack -1.945 ns, hold +0.170 ns; internal period estimate 5.945 ns. With the declared external-delay budget: setup -2.323 ns, hold -0.402 ns.
- **top_delta_lut2_prog:** 264 LUTs, 230 fabric FFs, 0 DSP, 0 RAMB18, 0 RAMB36; internal setup slack -1.632 ns, hold +0.172 ns; internal period estimate 5.632 ns. With the declared external-delay budget: setup -2.864 ns, hold -0.402 ns.
- **top_delta_lut6_prog:** 463 LUTs, 384 fabric FFs, 0 DSP, 0 RAMB18, 0 RAMB36; internal setup slack -1.351 ns, hold +0.159 ns; internal period estimate 5.351 ns. With the declared external-delay budget: setup -1.859 ns, hold -0.402 ns.
- **top_delta_compact_adapt_const:** 278 LUTs, 215 fabric FFs, 1 DSP, 0 RAMB18, 0 RAMB36; internal setup slack -0.680 ns, hold +0.144 ns; internal period estimate 4.680 ns. With the declared external-delay budget: setup -2.306 ns, hold -0.341 ns.
- **top_delta_compact_fixed_const:** 176 LUTs, 189 fabric FFs, 1 DSP, 0 RAMB18, 0 RAMB36; internal setup slack -0.024 ns, hold +0.159 ns; internal period estimate 4.024 ns. With the declared external-delay budget: setup -1.271 ns, hold -0.341 ns.
- **top_delta_compact_adapt_prog:** 392 LUTs, 207 fabric FFs, 1 DSP, 0 RAMB18, 0 RAMB36; internal setup slack -3.976 ns, hold +0.176 ns; internal period estimate 7.976 ns. With the declared external-delay budget: setup -3.976 ns, hold -0.402 ns.
- **top_delta_compact_fixed_prog:** 227 LUTs, 194 fabric FFs, 1 DSP, 0 RAMB18, 0 RAMB36; internal setup slack -3.074 ns, hold +0.157 ns; internal period estimate 7.074 ns. With the declared external-delay budget: setup -3.074 ns, hold -0.402 ns.

LUT and FF counts include state and control for this six-neuron unit. The prototype retains separate input and output banks; in-place bank reuse was not tested. Therefore these costs are for the measured architecture, not a lower bound on adaptive packing hardware. Fabric FF excludes DSP/BRAM internal registers. One RAMB36 is not interchangeable with zero memory resources. The six-parallel LUT baseline spends more parallel arithmetic/registers to reduce service clocks; its resource and latency tradeoff is included rather than comparing only identical issue counts.

Internal period estimates are 4 ns minus setup slack, not achieved operating frequencies. The separate boundary audit applies 1 ns maximum and 0.1 ns minimum input/output delays to the same routed netlists, including the raw-U range monitor input path. OOC port segments remain partially unrouted: these boundary results estimate the logical path under a declared interface budget and do not certify monitor/interface timing closure or board timing. Any negative hold slack in those audits must be fixed independently of changing clock period. No power, energy or host-speed results were measured.

## Memory bandwidth and another fixed-format possibility

The implemented interface transfers 66 bits atomically each way using registers. The bandwidth screen separately adds serialized state transfers and also evaluates an ideal overlapped issue pipeline. With only two state reads and writes per clock, both three-lane and two-lane issue pipelines require at least three memory clocks per six-neuron group. Additional buffering/ports would be needed to realize the issue-only lane advantage. These scenarios are analytic, not synthesized RAM wrappers; total memory bandwidth is not a measured accelerator result.

We also checked a stronger fixed-format possibility: U=32*h+r with signed int5 residue r. Three residue products fit the same DSP layout even for full int11 U, and exact leakage is U-floor((32*delta*h+delta*r)/256). All 165,536 arithmetic checks pass. Its wider high correction is not simulated/routed in this trial. Consequently, two full-range lanes is our measured fixed baseline, **not an absolute three-wide packing impossibility**. Any eventual positive adaptive claim must also assess this fixed three-wide resource tradeoff.

## Interpretation and scope

The adaptation is legitimately membrane-aware and its integer output preservation is supported by these tests. A small issue saving alone does not establish a useful hardware improvement. Assess the compact results against the matched fixed DSP, factored LUT and table alternatives, using both complete service clocks and the timing/resource costs above. This study supplies a tested mechanism and a targeted repair; it does not establish a publication-strength win or a first-ever novelty claim.

A specific remaining architectural hypothesis is an ordered input-window interface that accepts the next two or three membranes and continues issuing across groups, instead of copying and draining a six-neuron output bank each time. That could amortize startup/drain and reduce result selection. It would require sufficient state-read/write bandwidth and aligned per-request format/coefficient metadata. It is not implemented here and should be tested against an equally streaming fixed reference; these results do not prove that all membrane-aware packing implementations are poor.

## A checked next arithmetic hypothesis: exact shared offsets

Absolute magnitude need not determine eligibility. A triple such as [-300,-292,-289] can share base -320 and unsigned 5-bit residues [20,28,31]. No bits are discarded. For a triple that either fits the original signed int5 interval or has equal upper bits U//32, choose base b=-16 in the first case, otherwise b=32*(U0//32). Write U=b+r, 0<=r<32. The same one DSP can pack three delta*r products. A shared exact high correction reconstructs floor(delta*U/256).

Because b is a multiple of 16, let z=delta*(b/16), q=floor(z/16), s=z mod16. For packed product p_i=delta*r_i, the floor is q+(p_i>>8)+carry, where carry=(((p_i>>4)&15)+s)>>4. Only a 4-bit carry calculation is required per lane beyond the shared high term. All 166,560 arithmetic checks pass; this new controller and decoder have **not** been built, simulated or routed.

The combined eligibility screen increases the ideal issue-saving range on the same 18 numerical model profiles from 7.71-19.20% to 10.56-19.36%. In the two synthetic burst streams, ideal issue savings rise from 2.59-3.04% to 14.69-17.30%. The early synthetic bursts have identical lanes and therefore favor shared offsets. These numbers are numerical opportunities, not hardware speedups or evidence of natural-model burst acceleration.

This is a concrete next test for retaining packing when membrane values grow together. Its shared correction/monitor costs, equally streaming fixed baselines, and fixed three-full-range correction alternative must be included before claiming a gain. No novelty claim is established for shared-offset arithmetic.

FireFly is related work, not a reproduced baseline here. It uses DSP48E2 synaptic crossbars on different hardware; our unit uses DSP48E1 leakage multiplication. No claim of beating its accuracy, latency, TOPS, host costs or accelerator utilization follows from these results. [DSP-Packing](https://arxiv.org/html/2203.11028) already covers SNN addition packing and generic corrections, while [XtraMAC](https://arxiv.org/html/2605.06052) includes runtime datatype switching. The potential distinction remains an efficient actual-membrane-driven policy with demonstrated benefits, rather than packed arithmetic by itself.

## Evidence

The paired summary, source hashes, simulation stimuli/outputs, scalar checks, saved-model files, range certificates, route checkpoints/reports, initial tool-failure logs where retained, and boundary checks are packaged alongside this report. The original external research folder was not modified. No datasets, models or packages were downloaded.
