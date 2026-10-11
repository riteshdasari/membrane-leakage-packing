# Exact shared-offset streaming leakage trial

Completed 2026-10-09. **Streaming improves the packing opportunity, but neither tested adaptive implementation establishes a net hardware benefit over the strong fixed references.** The original shared-offset unit reduces sampled leakage-unit clocks by 19.10% versus an equally streaming fixed DSP pair. The fixed three-lane LUT implementation uses fewer clocks and dominates the original adaptive unit in the reported resource and setup-timing metrics, for both constant and programmable coefficients. The centered-bin repair does not produce a convincing win either; all its measurements are retained below.

## Scope and interface

The unit accepts a raw ordered window of one to three signed 11-bit membrane values, an availability count, and a shared delta in[0,31]. It returns a consume count immediately and later emits the corresponding one to three exact leakage results with a count. While reset is deasserted, the caller advances only on input valid/ready. Reset cancels queued work and the caller must stop presenting valid inputs during reset. No membrane sorting or packing is performed by the caller. The decoder, high corrections, format choice, count metadata, output registers and backpressure control are inside the measured unit.

Every implementation may accept one window each clock. A request produces valid results two clocks after its accept edge; with ready always high, the output handshake occurs three clocks after acceptance. For K uninterrupted windows, the measured span from the first acceptance through the last retirement is K+3 clocks. Output stalls freeze all data, format/coefficient metadata and DSP pipeline registers. Input bubbles do not change the ordering. Reset cancels unfinished requests. Input availability excludes padded neurons; unavailable payload bits are deliberately poisoned in the testbench and must have no effect.

The caller supplies three raw values as an ordered lookahead window. State storage, reading/bank rotation, pointer advancement, caching an unconsumed third value, and writing variable-size results are outside this primitive and have not been implemented or costed. Consequently this is not a complete SNN accelerator or a measured memory-to-memory update engine. Three-read/write bandwidth is required to sustain three real neuron updates per clock. A two-read/write state interface caps every design at two updates per clock, regardless of the DSP packing count.

## Integer update and original shared-offset policy

The contract is leak(U)=ceil((256-delta)*U/256)=U-floor(delta*U/256). Constant delta = 25 corresponds to beta = 231 in Q8 notation. This is leakage, rather than synaptic accumulation. No exponent representation or approximate mantissa shift is introduced.

The original adaptive engine consumes three neurons when the available triple either fits[-16,15] or has equal upper parts U//32. For the first case choose b=-16; otherwise choose b=32*(U0//32). Write U_i=b+r_i with unsigned five-bit residuals 0<=r_i<32. A single DSP packs three products p_i=delta*r_i in ten-bit fields. Centering the top multiplicand and adding its constant bias keeps the signed 25-bit DSP input legal. The product fields do not overlap and their maximum is 961.

For exact reconstruction, let z=delta*(b/16), q=floor(z/16), and s=z mod 16. Then floor(delta*U_i/256)=q+(p_i>>8)+carry_i, where carry_i=(((p_i>>4)&15)+s)>>4. The returned value is (b-q)+(r_i-(p_i>>8)-carry_i). The low residual result remains in[0,31]. The floor operations are part of the declared integer neuron update; they do not discard information from an approximate membrane representation.

When the triple is ineligible, the engine consumes two full-range neurons. Split U=256*h+r with signed eight-bit r. A DSP packs two delta*r products in sixteen-bit fields, while two small fabric high corrections reconstruct U-delta*h-floor(delta*r/256). This does not promote state into a separate wide accumulator. Stored and returned membranes remain signed 11-bit values.

All engines consume three copies for a delta = 0 identity request or an all-zero window. The fixed pairs also consume three when the third available neuron is zero: the first two use arithmetic and the third is returned as zero. This avoids giving adaptation an advantage solely from zero tail lanes.

## Strong fixed references and a controller repair

The fixed DSP pair uses the same wide residual split, scheduling contract and backpressure support. The fixed DSP triple is fully implemented in this trial: U_i=32*h_i+r_i with signed five-bit r_i, three packed residue products, and three independent exact high corrections. It always consumes three available neurons, including values outside the adaptive eligibility interval. Thus two lanes is not a full-range capacity limit.

The LUT pair and LUT triple implement the same integer update with DSP use disabled. For constant delta = 25 they explicitly factor multiplication as16*U+8*U+U. Programmable LUT references support the same allowed five-bit delta range as the adaptive engine. They use the same output latency and stall protocol. This is a comparison of the same leakage operation, not an inflated general multiplier baseline.

The isolated repair replaces the absolute-range OR uncentered-bin monitor with one equality test on h_i=floor((U_i+16)/32). Equal high parts permit a shared correction for signed five-bit residuals. With z=delta*h, the common high result is32*h-floor(z/8); each residual needs its signed product floor and a three-bit fraction carry. The first high-correction multiplier is also reused for the wide pair. This changes the eligibility set: it is not a strict superset of the original policy. The centered arithmetic screen passes 165,536 checks, and the complete RTL tests/replays below pass.

## Verification and reconstructed SNN outputs

Across both implementations, 48 engine/configuration runs check **20,743,272 individual neuron outputs** in 9,777,785 retired windows. These counts include repeated inputs across reference engines and implementations; they are not unique arithmetic tuples. There are zero detected mismatches against an independent scalar oracle. The range tests exercise every signed 11-bit scalar at every allowed delta, complementary wide inputs, equal-prefix triples near the range boundaries, every signed-int5 triple at delta = 25, random longer frames, coefficient transitions, one/two/three-neuron tails, zero/identity bypass, input gaps, output backpressure, and reset cancellation while the output is blocked. The acceptance count and three advancing-clock pipeline latency are also checked. An initial simulation startup error was traced to Xilinx glbl holding DSP primitives in reset during the first 100 ns; the final testbench begins after that reset and then explicitly exercises its own reset protocol. Oracle expectations were not changed to accommodate the failure.

Each model replay covers 635,904 real-neuron leakage updates in 9,216 frames: first 48 held-out images from each of three saved seeds, 32 timesteps, 128 hidden and 10 output neurons. Padded lanes from the previous six-neuron experiment are removed. Python adds the saved current, performs threshold/subtractive reset, and reconstructs membrane states, spikes, output spike counts and classification. All engines match exactly. Sampled reference and reconstructed classification is 93.75%,95.83%, and 97.92% for seeds 0, 1, 2 respectively.

Beta = 231 changes the saved models' original leakage. There was no retraining, and the equality claim is against the scalar beta = 231 reference, not unchanged accuracy versus the originally trained beta. Synaptic integration and threshold/reset are not executed in RTL here. The previous beta = 231 range certificate for these saved weights/thresholds is included; no range claim is made for arbitrary SNNs or other neuron models. This primitive tests linear integer leakage suitable for the declared LIF update, not complete Izhikevich or Hodgkin-Huxley neurons.

## Complete-unit clocks and useful arithmetic

- **offset, adaptive:** 245,975 accepted windows, 245,978 continuous clocks, 238,622 arithmetic requests; zero numerical/state/spike mismatches.
- **offset, fixed DSP pair:** 304,045 accepted windows, 304,048 continuous clocks, 297,185 arithmetic requests; zero numerical/state/spike mismatches.
- **offset, LUT pair:** 304,045 accepted windows, 304,048 continuous clocks, 297,185 arithmetic requests; zero numerical/state/spike mismatches.
- **offset, LUT triple:** 216,576 accepted windows, 216,579 continuous clocks, 209,481 arithmetic requests; zero numerical/state/spike mismatches.
- **offset, fixed DSP triple:** 216,576 accepted windows, 216,579 continuous clocks, 209,481 arithmetic requests; zero numerical/state/spike mismatches.
- **offset, absolute-only adaptive:** 255,558 accepted windows, 255,561 continuous clocks, 248,244 arithmetic requests; zero numerical/state/spike mismatches.
- **centered, adaptive:** 255,320 accepted windows, 255,323 continuous clocks, 248,015 arithmetic requests; zero numerical/state/spike mismatches.
- **centered, fixed DSP pair:** 304,045 accepted windows, 304,048 continuous clocks, 297,185 arithmetic requests; zero numerical/state/spike mismatches.
- **centered, LUT pair:** 304,045 accepted windows, 304,048 continuous clocks, 297,185 arithmetic requests; zero numerical/state/spike mismatches.
- **centered, LUT triple:** 216,576 accepted windows, 216,579 continuous clocks, 209,481 arithmetic requests; zero numerical/state/spike mismatches.
- **centered, fixed DSP triple:** 216,576 accepted windows, 216,579 continuous clocks, 209,481 arithmetic requests; zero numerical/state/spike mismatches.
- **centered, absolute-only adaptive:** 255,558 accepted windows, 255,561 continuous clocks, 248,244 arithmetic requests; zero numerical/state/spike mismatches.

The original adaptive unit takes **245,978 clocks versus 304,048** for fixed DSP pairs, a 19.10% saving. Fixed DSP/LUT triples take **216,579 clocks**, so the adaptive schedule takes 13.57% more clocks than them. The centered policy takes 255,323 clocks, saving 16.03% versus the fixed pair; it gives up some eligibility in exchange for a simpler intended controller.

These are measured cycles of a continuously supplied leakage unit. They are not whole-network latency. If each neuron-array frame instead waits for the pipeline to drain, adding three clocks per frame gives analytic proxies of 273,623 adaptive, 331,693 fixed pair and 282,968 centered clocks. Synaptic work, threshold/reset, memory transfers and host costs are still excluded.

The sampled membranes contain 568,948 nonzero multiplier terms and 299,884 updates whose leaked value actually changes. Original adaptive packing performs 2.384 nonzero products per active DSP issue versus 1.914 for the fixed pair and 2.716 for the fixed triple. Counting only changes instead gives 1.257, 1.009 and 1.432. These are declared work-per-issue measures, not DSP power or energy measurements. The fixed triple remains the most productive of these DSP schedules.

For delta = 25, U in[0,10] is an exact integer leakage fixed point. A stronger pair schedule that copies three such values without arithmetic would take 289,627 clocks in an optimistic schedule screen. The original adaptive saving versus that estimate falls to 15.07%. Its extra monitor has not been built or routed. This prevents treating all small nonzero membrane products as necessary computation, or calling the measured pair the strongest conceivable baseline.

## Bursts

- **Subtractive reset:** adaptive 791 requests, fixed pair 958, fixed triple 640. Adding a drain after each six-neuron timestep gives proxies of 1751, 1918, and 1600 clocks respectively.
- **Hard reset:** adaptive 791 requests, fixed pair 910, fixed triple 640. Adding a drain after each six-neuron timestep gives proxies of 1751, 1870, and 1600 clocks respectively.

On the concatenated synthetic sparse/burst stream, original adaptive clocks fall from 1871 to 1585, saving 15.29% under continuous supply. A drain per timestep reduces that opportunity, as shown above. The early synthetic bursts have identical lanes and favor shared offsets. This is not evidence of natural-model burst acceleration or a worst-case latency guarantee. Divergent membrane high parts force pair mode; fixed three-lane arithmetic still needs fewer issue windows.

## Routed hardware and timing limitations

Vivado 2025.2, xc7a100tcsg324-1, one tool thread, common 4 ns out-of-context clock. All twelve designs use the same core interface. Counts include the per-request correction/format/count registers, ready/valid handling and output registers; internal DSP registers are excluded from fabric FF counts. All routed checkpoints and reports are retained.

- **top_stream_offset_const:** 195 LUTs, 127 fabric FFs, 1 DSP, 0 RAMB18, 0 RAMB36; internal setup/hold slack -0.727/+0.189 ns, internal period estimate 4.727 ns; boundary setup/hold slack -6.159/-0.258 ns.
- **top_stream_fixed2_const:** 97 LUTs, 77 fabric FFs, 1 DSP, 0 RAMB18, 0 RAMB36; internal setup/hold slack +0.573/+0.168 ns, internal period estimate 3.427 ns; boundary setup/hold slack -2.179/-0.402 ns.
- **top_stream_fixed3_const:** 215 LUTs, 158 fabric FFs, 1 DSP, 0 RAMB18, 0 RAMB36; internal setup/hold slack -0.371/+0.175 ns, internal period estimate 4.371 ns; boundary setup/hold slack -4.727/-0.402 ns.
- **top_stream_lut3_const:** 137 LUTs, 108 fabric FFs, 0 DSP, 0 RAMB18, 0 RAMB36; internal setup/hold slack +1.156/+0.145 ns, internal period estimate 2.844 ns; boundary setup/hold slack -2.804/-0.234 ns.
- **top_stream_absolute_const:** 184 LUTs, 127 fabric FFs, 1 DSP, 0 RAMB18, 0 RAMB36; internal setup/hold slack -0.897/+0.162 ns, internal period estimate 4.897 ns; boundary setup/hold slack -6.152/-0.258 ns.
- **top_stream_lut2_const:** 81 LUTs, 75 fabric FFs, 0 DSP, 0 RAMB18, 0 RAMB36; internal setup/hold slack +0.781/+0.159 ns, internal period estimate 3.219 ns; boundary setup/hold slack -2.964/-0.233 ns.
- **top_stream_offset_prog:** 297 LUTs, 133 fabric FFs, 1 DSP, 0 RAMB18, 0 RAMB36; internal setup/hold slack -0.756/+0.168 ns, internal period estimate 4.756 ns; boundary setup/hold slack -9.613/-0.258 ns.
- **top_stream_fixed2_prog:** 177 LUTs, 110 fabric FFs, 1 DSP, 0 RAMB18, 0 RAMB36; internal setup/hold slack +0.800/+0.159 ns, internal period estimate 3.200 ns; boundary setup/hold slack -4.916/-0.258 ns.
- **top_stream_fixed3_prog:** 302 LUTs, 173 fabric FFs, 1 DSP, 0 RAMB18, 0 RAMB36; internal setup/hold slack -0.224/+0.170 ns, internal period estimate 4.224 ns; boundary setup/hold slack -6.343/-0.258 ns.
- **top_stream_lut3_prog:** 272 LUTs, 108 fabric FFs, 0 DSP, 0 RAMB18, 0 RAMB36; internal setup/hold slack +0.776/+0.159 ns, internal period estimate 3.224 ns; boundary setup/hold slack -5.931/-0.215 ns.
- **top_stream_centered_offset_const:** 241 LUTs, 131 fabric FFs, 1 DSP, 0 RAMB18, 0 RAMB36; internal setup/hold slack -0.402/+0.154 ns, internal period estimate 4.402 ns; boundary setup/hold slack -7.882/-0.258 ns.
- **top_stream_centered_offset_prog:** 306 LUTs, 131 fabric FFs, 1 DSP, 0 RAMB18, 0 RAMB36; internal setup/hold slack -0.516/+0.184 ns, internal period estimate 4.516 ns; boundary setup/hold slack -9.291/-0.258 ns.

The first adaptive constant version uses 195 LUTs and 127 fabric FFs versus97/77 for a fixed DSP pair,215/158 for a fixed DSP triple, and137/108 for a LUT triple. The programmable adaptive version uses 297/133 plus one DSP, versus272/108 with zero DSPs for programmable LUT triples. The isolated repair measurements appear above: simpler arithmetic block sharing in the source is not sufficient evidence of a smaller mapped design.

- **offset, const, versus fixed2:** cycle saving +19.10%; LUT/FF/DSP differences +98/+50/+0; internal timing-times-cycle ratio 1.116, boundary diagnostic ratio 1.330. Ratios above 1 mean the adaptive diagnostic is worse.
- **offset, const, versus fixed3:** cycle saving -13.57%; LUT/FF/DSP differences -20/-31/+0; internal timing-times-cycle ratio 1.228, boundary diagnostic ratio 1.322. Ratios above 1 mean the adaptive diagnostic is worse.
- **offset, const, versus lut3:** cycle saving -13.57%; LUT/FF/DSP differences +58/+19/+1; internal timing-times-cycle ratio 1.888, boundary diagnostic ratio 1.696. Ratios above 1 mean the adaptive diagnostic is worse.
- **offset, prog, versus fixed2:** cycle saving +19.10%; LUT/FF/DSP differences +120/+23/+0; internal timing-times-cycle ratio 1.202, boundary diagnostic ratio 1.235. Ratios above 1 mean the adaptive diagnostic is worse.
- **offset, prog, versus fixed3:** cycle saving -13.57%; LUT/FF/DSP differences -5/-40/+0; internal timing-times-cycle ratio 1.279, boundary diagnostic ratio 1.495. Ratios above 1 mean the adaptive diagnostic is worse.
- **offset, prog, versus lut3:** cycle saving -13.57%; LUT/FF/DSP differences +25/+25/+1; internal timing-times-cycle ratio 1.675, boundary diagnostic ratio 1.557. Ratios above 1 mean the adaptive diagnostic is worse.
- **centered, const, versus fixed2:** cycle saving +16.03%; LUT/FF/DSP differences +144/+54/+0; internal timing-times-cycle ratio 1.079, boundary diagnostic ratio 1.615. Ratios above 1 mean the adaptive diagnostic is worse.
- **centered, const, versus fixed3:** cycle saving -17.89%; LUT/FF/DSP differences +26/-27/+0; internal timing-times-cycle ratio 1.187, boundary diagnostic ratio 1.605. Ratios above 1 mean the adaptive diagnostic is worse.
- **centered, const, versus lut3:** cycle saving -17.89%; LUT/FF/DSP differences +104/+23/+1; internal timing-times-cycle ratio 1.825, boundary diagnostic ratio 2.059. Ratios above 1 mean the adaptive diagnostic is worse.
- **centered, prog, versus fixed2:** cycle saving +16.03%; LUT/FF/DSP differences +129/+21/+0; internal timing-times-cycle ratio 1.185, boundary diagnostic ratio 1.252. Ratios above 1 mean the adaptive diagnostic is worse.
- **centered, prog, versus fixed3:** cycle saving -17.89%; LUT/FF/DSP differences +4/-42/+0; internal timing-times-cycle ratio 1.260, boundary diagnostic ratio 1.515. Ratios above 1 mean the adaptive diagnostic is worse.
- **centered, prog, versus lut3:** cycle saving -17.89%; LUT/FF/DSP differences +34/+23/+1; internal timing-times-cycle ratio 1.651, boundary diagnostic ratio 1.578. Ratios above 1 mean the adaptive diagnostic is worse.

An internal period estimate is 4 ns minus internal setup slack. It is a diagnostic, not a certified operating period. Multiplying it by the measured cycles likewise gives a comparison diagnostic, not observed FPGA latency. The separate boundary audit applies 1 ns max and 0.1 ns min input/output delays after routing and includes raw membrane, availability, coefficient, consume-count and backpressure paths. Primary-port segments and the OOC clock source are not fully implemented. All boundary audits have negative hold slack; increasing the clock period alone does not repair that. No complete interface timing closure or board measurement is claimed.

The raw-input correction paths are material: the original constant adaptive audit reports 12 logic levels and a 10.079 ns estimated data path from availability to correction metadata, while its register-to-register period estimate is 4.727 ns. Ignoring this input path would make the claimed speed too optimistic. A registered-input refinement could expose and pipeline those paths, at additional latency/register cost, but it was not implemented in this trial. The centered repair moves selection ahead of the reused high multiplier and has its own boundary path reports. No timing-times-cycle ratio here should be presented as an achieved accelerator speedup.

## What this establishes

Actual membrane values can safely select a three- or two-operation DSP layout, and shared offsets can preserve triple packing at larger membrane magnitudes. The RTL and model tests support the declared integer output preservation. Streaming removes much of the old six-neuron bank startup/drain overhead, which explains the larger average cycle opportunity.

The measurements still do not establish a publication-strength hardware win. For small five-bit leakage complements, constant and programmable LUT arithmetic is inexpensive. The adaptive datapath adds monitoring, multiple field layouts, high-correction selection and metadata; the full-range fixed triple avoids the adaptive issue fallback. The targeted centered repair does not eliminate those costs. This conclusion is about the two implemented datapaths, not a proof that all membrane-aware hardware is ineffective.

FireFly is related work, not a matched implementation baseline: its synaptic DSP crossbars and accelerator measurements are different from this leakage primitive. No accuracy, TOPS, latency, power or host comparison with FireFly is justified. No first-ever novelty claim is established by this hardware trial. Generic packing/correction is covered by [DSP-Packing](https://arxiv.org/html/2203.11028); runtime datatype switching is also established in work such as [XtraMAC](https://arxiv.org/html/2605.06052). The research claim would still need a useful, efficient actual-membrane-driven policy rather than packed arithmetic alone.

## Reproduction and evidence

The evidence archive includes both RTL versions and testbenches, independent checking scripts, exact stimuli and outputs, model inputs/ledger, prior range certificates, all twelve routed checkpoints/reports, tool logs, this report, the summary and a SHA256 manifest. Use the installed Python environment and Vivado 2025.2. The verification scripts require the local Xilinx unisim libraries; no tool binaries are distributed. The finish scripts serialize heavy routes and check available RAM. No models, datasets or packages were downloaded, and the original external research folder was not changed.
