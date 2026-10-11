# Exact membrane-aware packing: continuous and four-output RTL follow-up

This note records completed local implementation trials. The arithmetic is leakage, not synaptic accumulation: L(U)=U-floor(25U/256)=ceil(231U/256), with signed eleven-bit inputs/outputs. No membrane is rescaled or rounded.

## Continuous three-output trial

The adaptive controller uses DSP three-lane arithmetic for eligible actual membranes; otherwise it uses DSP two-lane arithmetic plus the LUT third lane. Both it and the fixed hybrid retire three results per request. Saved-model service is 216,580 clocks for both. This trial increases hardware without reducing service cycles.

- top_continuous_adaptive_const: 181 LUT / 159 FF / 1 DSP; target 6 ns; setup/hold slack +1.063/+0.093 ns.
- top_continuous_adaptive_prog: 295 LUT / 163 FF / 1 DSP; target 8 ns; setup/hold slack +1.213/+0.155 ns.
- top_continuous_hybrid_const: 95 LUT / 155 FF / 1 DSP; target 6 ns; setup/hold slack +0.935/+0.151 ns.
- top_continuous_hybrid_prog: 154 LUT / 160 FF / 1 DSP; target 8 ns; setup/hold slack +1.752/+0.103 ns.

## Matched four-output trial

Every engine receives the same up-to-four ordered raw membranes. Adaptive and fixed three-lane engines equally copy a fourth value in [0,10], where leakage is exactly the identity. Otherwise adaptive packing chooses four lanes when every membrane fits its signed six- or seven-bit range and uses the full-range three-lane format for fallback. Fixed four-lane and LUT four-lane engines consume four whenever available.

All five cores use the same four-advancing-clock pipeline contract and 6 ns registered out-of-context timing fixture. Counts below exclude its 103 FF. The fixture supplies windows; a real memory reader/window builder is not implemented.

- Adaptive six-bit: 302 LUT / 201 FF / 1 DSP; 171,280 saved-model service clocks; setup/hold +0.230/+0.125 ns (passes target).
- Adaptive seven-bit: 304 LUT / 210 FF / 1 DSP; 166,624 saved-model service clocks; setup/hold -0.180/+0.123 ns (fails target).
- Fixed DSP three-lane with fourth copy: 141 LUT / 167 FF / 1 DSP; 184,421 saved-model service clocks; setup/hold +0.598/+0.152 ns (passes target).
- Fixed DSP four-lane: 213 LUT / 243 FF / 1 DSP; 161,284 saved-model service clocks; setup/hold +0.855/+0.142 ns (passes target).
- LUT four-lane: 129 LUT / 224 FF / 0 DSP; 161,284 saved-model service clocks; setup/hold +1.811/+0.104 ns (passes target).

Relative to matched fixed three-lane, adaptive six-bit reduces service clocks by 7.126%; seven-bit by 9.650%. Seven-bit still needs 3.311% more clocks than fixed four-lane. Request savings against three lanes alone do not establish superiority over the four-lane baselines.

## Hardware diagnosis and next screen

The four-output adaptive leakage implementation does not establish an overall hardware benefit. Six-bit uses 302 LUTs versus fixed three-lane 141 and LUT four-lane 129. Its 201 FF versus LUT four-lane 224 is a register saving, but it adds 173 LUTs and one DSP and takes more service clocks. Seven-bit uses 304 LUTs/210 FF/one DSP and fails the matched 6 ns setup target by 0.180 ns. Therefore its cycle-count reduction is not a closed-timing latency result at that target.

The seven-bit critical path runs from raw0_reg[16] to meta1_reg[19], outside the DSP. The routed report gives 6.188 ns data-path delay and nine logic levels, including four CARRY4 stages. This is the high-part constant multiplication/pre-subtraction and metadata selection stage. Sharing arithmetic reduced duplication but left a long serial fabric path. Constant leakage is also inexpensive in the LUT baseline; the DSP computes small residual products while full-membrane correction remains in fabric.

A separate arithmetic-only screen returns to accumulation U+I: six eight-bit guarded fields for signed seven-bit operands, otherwise four twelve-bit guarded fields for signed eleven-bit operands. The result is signed twelve-bit, so this is a different operation/domain from the leakage RTL. A guard prevents interlane carry; one sign-parity XOR per lane recovers the exact sum. It passes 4,210,688 scalar pairs and 100,490 structured/random packed additions, with zero mismatches. No RTL, timing or SNN result is claimed for this new screen. A fixed six-output DSP-four-plus-LUT-two hybrid can already match its maximum throughput; that baseline must be priced before treating this as a promising controller.

## Verification and limits

The four main/model RTL runs compare 9,530,290 neuron outputs across five engines, with zero mismatches. Coverage includes every eleven-bit scalar in structured contexts, all 65,536 signed four-bit quadruples, boundary/residue cases, random lengths, tails, source/output backpressure and reset cancellation. It is not exhaustive over all eleven-bit quadruples.

The saved-model replay checks 635,904 leakage outputs per engine/run. RTL outputs plus Python current addition, threshold and subtractive reset reproduce states, spikes, spike counts and classifications for 144 sampled images across three saved seeds. The reference leakage was changed to beta=231/256; this does not establish preservation of original trained-model accuracy. No retraining or download occurred.

Registered fixture timing is not board Fmax. Raw-port hold audits remain separate and do not establish a complete external interface. No memory bandwidth, closed-loop SNN RTL, host cost, full burst latency or power is measured. Arithmetic issue and mode counts do not measure useful DSP utilization or power. Constant and programmable cohorts have different clock targets and must not be mixed.

The local LUT implementations are reconstructed operation baselines, not FireFly RTL or reproduced FireFly hardware/accuracy results.
