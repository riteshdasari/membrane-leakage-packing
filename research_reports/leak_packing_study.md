# Exact leakage packing: fixed building block and next adaptive hypothesis

## Decision

The general leakage multiplication is a more useful DSP target than the previously tested binary-spike addition and shift leak. With a shared programmable coefficient, two 8-bit operations use **12 LUTs and one DSP**, versus **163 LUTs and no DSP** for the tested matched LUT multiplier. The complete 10-bit fixed high/low version uses **73 LUTs and one DSP**, versus **218 LUTs** for its matched pipelined LUT multiplier. Both comparisons have equal accepted work and pipeline latency within their group. These are resource/timing tradeoffs for fixed primitives, not an adaptive novelty result.

Constant coefficients demand stronger comparisons. The initial constant LUT multiplication is reduced from 99 to 43 LUTs by factoring it, and the factored core has better internal timing than the packed DSP core. A table implementation maps to one RAMB18 and six LUTs, with faster internal timing. A forced distributed table uses **57 LUTs, zero DSP and zero BRAM**, with an internal period estimate of **2.524 ns**. The DSP implementation cannot be presented as uniformly superior to these fixed-coefficient alternatives.

The next adaptive mechanism worth a bounded RTL test is packing **three narrow membrane leakage operations versus two full-range operations**, using a small decay coefficient. The arithmetic is checked, and coefficient-231 trace scenarios offer an ideal **7.3–19.7% reduction in leakage issue slots** after removing zero groups. No adaptive RTL, controller area, burst latency, total neuron-update speedup or publication-strength gain has been established. The fixed two-lane full-range baseline must be retained; comparing only with one un-packed wide multiplication would overstate adaptation.

This is explicitly a change from packing synaptic accumulation alone. The implemented cores compute **membrane leakage**, while input spikes can remain binary in a surrounding neuron. Accumulation, threshold/reset, the complete neuron state bank and an accelerator are not implemented in these new cores.

## Fixed two-lane arithmetic

Declare the reference as U_next=ceil(beta*U/256), with shared beta in [0,256]. For signed int8 membrane U, store q=U+128. Let K=128*(256-beta)+255. A=(q0+q1*2^16) fits the positive input range of the DSP48E1's 25-bit multiplier; B=beta and C=K*(1+2^16). P=A*B+C contains two independent 16-bit results. Each field R=beta*q+K lies in [0,65535]. Extract each field's upper eight bits and subtract the bias by toggling its sign bit. There is no cross-field carry and no exponent quantization.

The RTL uses registered raw inputs and the DSP P register. The LUT version has the same accepted-input/result schedule, one pair per clock, with DSP inference disabled. The coefficient is either constant 231/256 or programmable for each request. The fixed coefficient was a representative general coefficient; this is not a survey of all constant-coefficient synthesis outcomes. Packable lanes require equal coefficients. Per-neuron coefficient grouping and its storage/routing costs are unmeasured.

## Strong full-range packing baseline

A 10-bit membrane does not force one complete operation per DSP. Write U=256*h+r, with r the signed low int8 value. Then

    ceil(beta*U/256) = beta*h + ceil(beta*r/256)

The small high term h ranges from -2 to +2 for signed int10. The fixed baseline always packs both low residues in one DSP and computes the small high correction in LUTs. It therefore handles **two complete int10 neurons per DSP**, without an adaptive monitor or overflow fallback. It adds a second registered compute stage for the correction. The matched LUT reference registers its full product, then rounding/extraction in a second stage. Both accept one pair per clock and have the same valid latency, including bubbles.

This baseline prevents an artificial twofold adaptive gain from treating every wider membrane as necessarily an un-packed DSP operation. The implemented split is int10 only. Wider states need a larger high correction and separate validation/costs; software int64 correction is not evidence that those wider hardware implementations have been tested.

## Strong constant-coefficient alternatives

For beta=231, leakage is also U-floor(25*U/256). The factored LUT version forms 25U=16U+8U+U, then performs the correction. It matches the exact integer oracle on every int8 input pair, and the same accepted-input/result schedule. An explicit constant truth table was also tested. Vivado automatically mapped the first table to a dual-port RAMB18; it is a BRAM alternative, not a LUT-only implementation. A separate source forces distributed ROM and consumes zero BRAM. Both table outputs are checked against the independent reference. ROM width, depth and bandwidth become material costs for wider states or many coefficients.

For programmable beta, the tested LUT baselines use general multiplication. A layer-programmable table with reloading/caching is not implemented here. If beta changes only between layers, that alternative must be assessed with its table, setup and coefficient-storage costs before claiming a deployment advantage. A per-request programmable multiplier comparison does not justify a workload whose coefficients can be hardwired cheaply.

## Routed cores

Vivado 2025.2, Artix-7 xc7a100tcsg324-1, out-of-context, one thread, common 4 ns constraint. Every listed design completed placement and routing. All rows contain two neuron outputs. The int8 group has one registered compute stage after the input registers; the full int10 group has two. Compare within a width/latency group.

- **Packed DSP, 8-bit, constant beta231:** 5 LUTs, 18 fabric FFs, 1 DSP, 0 RAMB18, 0 RAMB36; setup slack -1.143 ns; hold slack +0.320 ns; internal period estimate 5.143 ns.
- **Initial LUT multiply, 8-bit, beta231:** 99 LUTs, 34 fabric FFs, 0 DSP, 0 RAMB18, 0 RAMB36; setup slack -2.142 ns; hold slack +0.407 ns; internal period estimate 6.142 ns.
- **Packed DSP, 8-bit, programmable beta:** 12 LUTs, 27 fabric FFs, 1 DSP, 0 RAMB18, 0 RAMB36; setup slack -1.097 ns; hold slack +0.381 ns; internal period estimate 5.097 ns.
- **LUT multiply, 8-bit, programmable beta:** 163 LUTs, 43 fabric FFs, 0 DSP, 0 RAMB18, 0 RAMB36; setup slack -3.475 ns; hold slack +0.417 ns; internal period estimate 7.475 ns.
- **Factored LUT arithmetic, 8-bit, beta231:** 43 LUTs, 34 fabric FFs, 0 DSP, 0 RAMB18, 0 RAMB36; setup slack -0.517 ns; hold slack +0.313 ns; internal period estimate 4.517 ns.
- **Automatic ROM mapping, 8-bit, beta231:** 6 LUTs, 10 fabric FFs, 0 DSP, 1 RAMB18, 0 RAMB36; setup slack +1.289 ns; hold slack +0.166 ns; internal period estimate 2.711 ns.
- **Distributed ROM, 8-bit, beta231:** 57 LUTs, 34 fabric FFs, 0 DSP, 0 RAMB18, 0 RAMB36; setup slack +1.476 ns; hold slack +0.233 ns; internal period estimate 2.524 ns.
- **Fixed high/low split, 10-bit, beta231:** 44 LUTs, 63 fabric FFs, 1 DSP, 0 RAMB18, 0 RAMB36; setup slack -1.107 ns; hold slack +0.238 ns; internal period estimate 5.107 ns.
- **Pipelined LUT multiply, 10-bit, beta231:** 118 LUTs, 79 fabric FFs, 0 DSP, 0 RAMB18, 0 RAMB36; setup slack -0.579 ns; hold slack +0.207 ns; internal period estimate 4.579 ns.
- **Fixed high/low split, 10-bit, programmable beta:** 73 LUTs, 72 fabric FFs, 1 DSP, 0 RAMB18, 0 RAMB36; setup slack -1.229 ns; hold slack +0.185 ns; internal period estimate 5.229 ns.
- **Pipelined LUT multiply, 10-bit, programmable beta:** 218 LUTs, 88 fabric FFs, 0 DSP, 0 RAMB18, 0 RAMB36; setup slack -3.584 ns; hold slack +0.247 ns; internal period estimate 7.584 ns.

Internal period estimates equal 4 ns minus setup slack. They are not achieved board frequencies or measured throughput. External input/output delays are unspecified and OOC ports have partial-route warnings. BRAM/DSP internal registers are excluded from fabric FF counts. The initial 4 ns constraint is missed by several cores; positive internal slack does not certify interface timing. No power, energy, host time, memory subsystem, board or FireFly system result is reproduced.

The programmable packed and split DSP builds each initially hit Vivado's blank Synth 20-411 at opt_design. Each was retried once by opening its unchanged synthesis checkpoint and completed. Failed and retry logs are retained. The simulator also needed unsandboxed access for its generated-code compiler. Neither issue was repaired by changing the arithmetic. Early declaration errors were corrected before the passing source hashes and hardware builds.

## Correctness evidence

- Int8 algebra: 65,792 scalar input/coefficient combinations and 100,000 packed pairs, zero failures.
- Full int10 decomposition: 263,168 exhaustive scalar/coefficient combinations, zero failures.
- RTL: 20 engine/configuration runs and 1,297,509 checked pair requests in total across engines, zero differences. The int8 constant test includes every input pair. The programmable int8 test covers every individual int8 value/coefficient combination and additional random/boundary pairs. Full int10 programmable tests cover every individual value/coefficient combination, plus random pairs and bubbles. Both fixed LUT alternatives and their distributed source are independently compared against the integer oracle.
- The possible three-lane format described below adds 1,048,576 exhaustive arithmetic combinations, zero failures. It has no RTL implementation in this study. Total arithmetic audit cases: 1,477,536.
- Saved-model numerical screen: all three existing seed weight sets, nine saved IF/LIF/threshold reference configurations, hard and subtractive reset, original beta and beta231 scenarios, 360 held-out digits images, 32 timesteps. All 36 runs have zero integer leakage differences under the checked low-residue plus int64 high-correction transformation. This is Python inference, not FPGA inference or full-network RTL validation. Beta231 scenarios change the dynamics of the existing weights; no retraining was performed and their classification accuracy is not proof that a floating-point trained model is preserved. Raw accuracy and range values are in the JSON.

Several beta231 scenarios reach membrane values outside signed int10. They need a wider exact path before whole-model hardware deployment. The three saved reference beta values 128,224,256 are especially cheap shift/identity cases; the programmable multiplication benefit does not apply automatically to those models' original leakage. Beta256 needs no leakage multiplication, and strong baselines should bypass it.

## The next adaptive arithmetic layout

Use delta=256-beta. For delta<=31 and actual U in [-16,15], the exact update is

    U_next = U - floor(delta*U/256)

Three signed five-bit inputs fit in one DSP multiply with ten-bit product spacing. Bias the lower two inputs by 16 and leave the upper input signed:

    A = (U0+16) + (U1+16)*2^10 + U2*2^20
    C = (512-16*delta)*(1+2^10)
    P = A*delta + C

A lies within the DSP48E1's signed 25-bit range. The lower two product fields are delta*U+512, nonnegative and below 1024. The upper field is a signed ten-bit product. Each floor quotient uses two extracted bits; the lower two have a bias of two to remove. Subtract the quotient from the original U. The original U must remain available/aligned for that correction, which has a hardware and scheduling cost. Exhaustively checking every delta and every input triple gives the count above. Beta256 and all-zero groups should be handled directly by both baselines.

A causal controller could examine actual membrane values, choose this three-lane format only when their range fits, and otherwise use the fixed two-lane full-range split. That is genuinely membrane-potential-aware representation selection. It is currently an arithmetic hypothesis, not a tested controller. Native signed packing, multiplication correction and mixed-width packing already have extensive prior art; the small packing formula alone is not claimed as novel.

## Numerical opportunity and its limits

The screen examines naturally ordered groups of six stored membranes before leakage. Full groups only are counted: the final two hidden neurons and final four output neurons are omitted from this grouping profile. A three-lane format needs two issues per group, versus three for a fixed two-lane format. Both candidates may skip groups whose six membranes are all zero. Among the coefficient-231 scenarios, the resulting ideal issue saving ranges from 7.28% to 19.75%. The upper end comes from a changed-dynamics scenario with hard reset, not a cherry-picked claim about the original model's exact dynamics.

These fractions omit range-check cycles, packet preparation, retained operands, mode tags, conversion, memory bandwidth/ports, stalls, pipeline drain, accumulation, firing and reset. They are a screen for whether to build a controller, not measured latency. Three reads/results per narrow issue may require more instantaneous state bandwidth than the fixed two-lane unit. A gain in leakage issue slots can be much smaller when expressed over a complete timestep with many synaptic events.

The older direct-beta three-bit packing opportunity is generally much smaller once zero groups are removed. Factoring into the small decay coefficient widens the eligible input range from signed int3 to signed int5 for beta231, explaining why this new numerical screen is more promising. That observation still requires a matched hardware test.

## What to test next, while keeping the paper small

Build one small arithmetic unit with an actual-U monitor, the three-lane narrow format and a validated wider fixed split. Compare against the same wider fixed split, optimized LUT arithmetic, and constant/programmed-table alternatives appropriate to the model. Include state storage, operand delivery and every control/convert/drain cycle. Try sparse steps and bursts using the same event stream and integer neuron contract. Report the incremental effect of adaptation separately from ordinary DSP packing. If controller cost consumes the numerical opportunity, retain the fixed primitive result and reject that adaptive implementation.

The scope remains a packing unit plus its minimal controller; no full accelerator is required to test that claim. The unresolved scientific requirement is demonstrating an adaptive benefit at a useful resource/clock tradeoff on a real model needing general leakage. This experiment supplies a more plausible arithmetic target and an exact next layout; it does not establish an ISCAS contribution yet.

## Prior-art position

[Fang et al., ICCV 2021](https://arxiv.org/abs/2007.05785) motivate learnable membrane time constants. That does not imply shared coefficients across arbitrary neurons or validate our integer rounding contract against their trained models. [DSP-Packing](https://arxiv.org/html/2203.11028) already generalizes packed low-precision multiplication and discusses packed SNN additions. The [official UDP FPGA 2026 repository](https://github.com/wintermelon008/UDP) supplies configurable packed multiplication templates; the publisher paper's full text was inaccessible in this audit, so no detailed superiority or novelty claim against UDP is made. [HAPQ, Sensors 2026](https://doi.org/10.3390/s26092910) overlaps in membrane quantization, SIMD alignment and shift-friendly FPGA recurrence; only the publisher abstract/search-visible material was available here, so its hardware is not reproduced. FireFly's neuron updates and existing mixed-precision packing must remain part of a broader novelty audit. No keyword-search absence is used as evidence that no one has done the adaptive idea.

## Reproduction and evidence

The ZIP contains the four RTL sources, testbenches, independent checks, generated stimuli/outputs, numerical screen, all three existing model files, saved reference configurations, build scripts, raw route reports and failure/retry logs. Checkpoints and generated simulator binaries are omitted. Source hashes and a verified ZIP manifest accompany the files. Use the already installed Python environment with NumPy and local Vivado named in the scripts; no model, dataset or package was downloaded.

Run check_packed_leak.py, check_split_leak.py, check_fixed_lut_leak.py, check_distributed_leak.py, check_delta_packing.py and screen_leak_adaptation.py. Build the listed tops with their corresponding run_*_route.py scripts; --resume opens an existing synthesis checkpoint after a tool failure. The route scripts require more than 2.3 GiB free RAM and launch serial builds; small two-lane simulations check a lower 1.0 GiB gate. The RAM shortage early in this run cleared before the hardware queue began.
