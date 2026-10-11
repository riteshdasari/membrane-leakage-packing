# Persistent membrane-aware DSP packing: completed implementation check

## Decision

This implementation has not established the requested practical benefit over both strong fixed packing and a LUT implementation of the same operation. It preserves the tested integer neuron states and spikes and saves service cycles relative to a fixed persistent membrane width. A fixed narrow-current DSP design and a direct LUT design need fewer cycles on the burst workload. Adaptation introduces more logic and a longer feedback path; reduced fabric FF count is a resource tradeoff, not evidence of lower total area or power. This is insufficient evidence to commit this candidate as a strong ISCAS contribution.

The study implements a small arithmetic primitive, not an accelerator. No models, datasets or packages were downloaded. Existing saved weights and data were reused. No FireFly chip throughput, power or accuracy result is reproduced.

## What was built

Six neurons receive two signed int4 weights per ADD command. Binary input spikes determine which weights the source supplies; multiplication by a spike is event selection. BEGIN performs integer leakage, ADD accumulates current, and FINISH applies one timestep-boundary threshold and hard or subtractive reset. Reference semantics are U <- U - (U >>> shift), then all event additions, then one spike/reset decision. There is no intermediate firing, membrane clamp, multi-spike emission or exponent quantization.

The candidate keeps actual membrane values in the DSP's registered P output. Signed values use an offset-binary representation. Narrow mode packs six 8-bit fields in 48 bits. Wide formats 10/12/16 pack 4/4/3 fields per word and process six neurons in two passes. The source replays the same event stream for the second output group. Conversion uses fixed wiring and multiplexers. It contains no barrel shifter, full-width per-neuron recovery adder or refill crossbar.

For 10/12-bit formats the side register has 20/24 bits. After processing the first four neurons, two completed lanes stay in the upper part of P, while the other two move to the side register; the last two neurons occupy P's lower fields. Their additions preserve the completed upper fields because the lower fields are proven not to carry or borrow across their boundary. For 16 bits the side register is 48 bits. This retained-lane layout was independently tested, including wide-to-narrow and narrow-to-wide changes.

At BEGIN, the causal controller examines actual membrane U and a conservative bound [L,H] for every allowed current prefix. It chooses 8 bits only if the leaked membrane plus every prefix fits [-128,127]. Otherwise it uses the configured wide format, whose safety requires a separate proof. It does not detect arbitrary overflow after it happens. The prefix certificate, maximum fan-in and wide state bound are part of the interface contract; the module does not enforce them dynamically.

This is legitimately membrane-potential-aware adaptation: the actual U affects the format. Naming alone does not establish novelty or a performance advantage.

## Stronger references and range proof

All routed comparisons use the same six-neuron operation, threshold 35, subtractive reset, leak shift 3 and prefix bound [-64,56]. The stress stream has up to eight input events per timestep. An inductive invariant U in [-512,448] is sufficient: after leakage U is in [-448,392], and every current prefix stays in [-512,448]. Reset cannot move values outside that interval. Therefore a fixed 10-bit membrane is safe for every permitted input pattern, for arbitrarily many timesteps under these semantics. Comparing only against 16-bit membrane storage would overstate the benefit.

The fixed-current reference packs all six 8-bit current sums in one DSP and updates six 10-bit fabric membrane registers at FINISH. Current prefixes fit [-64,56], so it does not need promotions. The LUT reference performs the same paired addition and leak/reset on six 10-bit registers. Its strengthened version first adds the two signed int4 weights into a signed 5-bit sum, then adds that result to membrane. It uses no DSP.

For leak shift 1, an invariant [-128,126] is sufficient: leakage gives [-64,63], and every prefix gives [-128,119]; reset remains in the invariant. Fixed 8-bit persistent packing is therefore safe for that workload. The adaptive controller never chooses wide mode in its corresponding tests. The best case for narrow packing is consequently not evidence that adaptation is needed.

For non-leaky IF, a stream of inhibitory events can keep lowering membrane even with hard reset. Wide-format safety is horizon-specific there; the 320-step stress test fits 16 bits. The 10/12-bit variants and fixed 8-bit persistent reference are not tested as valid IF implementations.

## Exact monitor simplification

The original monitor waits for leakage before comparing six lanes and selecting the next layout. The improved monitor inverts leakage's monotone integer mapping. For shift 3, f(U)=U-(U>>>3)=ceil(7U/8). The default 8-bit safety requirement is -64 <= f(U) <= 71, exactly equivalent to -74 <= U <= 81. Constant inverse bounds are evaluated at elaboration, without a hardware divider. Monitoring and leakage then run in parallel; scheduling and output values are unchanged.

An independent exhaustive integer audit checks 524,288 combinations of membrane, two leak shifts and four prefix-bound settings, with zero failures. Original and simplified RTL both match the integer oracle in all 50 engine/configuration runs, each 320 timesteps. Tests include IF/LIF, hard/subtractive reset, empty timesteps, maximum positive/negative bursts and random lane weights. Each implementation checks 96,000 neuron state/spike pairs. This is simulation plus an arithmetic argument, not a formal RTL proof over all parameter settings.

## Service cycles and burst latency

The driver issues consecutive commands with no inserted per-step bubbles. Counts include six common startup/drain cycles. All engines receive the same events and timestep boundaries and independently run to completion. Wide mode includes the second event replay and both FINISH commands. It receives no free conversion cycles or uncounted serialized membrane merge.

- Shift-3 LIF, 320 stress timesteps: adaptive **1431 cycles**, fixed 10-bit persistent membrane **2086**, fixed-current DSP **1206**, and LUT **1206**. Adaptation saves 31.4% of cycles relative to fixed persistent membrane, but uses 18.7% more than fixed current or LUT.
- Adaptive shift-3 operation uses narrow mode for 239 timesteps and wide mode for 81, with four format changes. Moving to 12 or 16 wide bits does not change this six-neuron pass count. The simplified monitor has exactly the same cycle counts.
- A maximum four-pair burst needs six service cycles in narrow/current/LUT mode and eleven in wide persistent mode, excluding common startup/drain. These are command/service counts, not measured nanoseconds on a board.
- Shift-1 LIF: adaptive and proof-safe fixed 8-bit persistent packing both take 1,206 cycles; there are no adaptive format changes.
- Non-leaky IF: adaptive 8/16 takes 2,075 cycles versus fixed-wide 2,086 and fixed-current/LUT 1,206. It is wide for 316 of 320 timesteps. Hard and subtractive reset have identical schedule counts on this stress stream.

## Saved-model RTL replay

The first six hidden neurons of the existing seed0 64-128-10 digits model were replayed on 48 held-out images for 32 timesteps, with shift 3, threshold 17 and subtractive reset. Neuron indices were chosen as the first block, without searching for a favorable block. Weight-only bounds are [-32,43]; actual paired current prefixes are [-18,27]. All ten relevant engines/formats in both original and improved RTL exactly match all reference membrane states and spikes.

Adaptive takes 18,871 cycles, equal to fixed current and LUT, while fixed persistent wide packing takes 36,059. Adaptive stays narrow for all 1,536 timesteps: this block demonstrates safe narrow operation, not a gain from repeated adaptation. These are block replays; they do not measure whole-network RTL classification accuracy. Earlier full-network Python checks on all three saved models remain separate evidence. Hardware was routed with threshold 35, while this replay uses the saved threshold 17; no claim is made that the replay's exact hardware cost was measured.

## Routed hardware

Vivado 2025.2, Artix-7 xc7a100tcsg324-1, out-of-context, one thread, common 4 ns clock target. Each run completed placement and routing. These numbers count core logic, six parallel neuron updates and adaptive control, rather than the DSP adder alone.

- **Adaptive 8/10, original monitor:** 537 LUTs, 35 fabric FFs, 1 DSP; setup slack -7.564 ns; hold slack +0.230 ns; feedback period estimate 11.564 ns.
- **Fixed 8-bit current + 10-bit membrane:** 320 LUTs, 68 fabric FFs, 1 DSP; setup slack -1.284 ns; hold slack +0.498 ns; feedback period estimate 5.284 ns.
- **LUT 10-bit, direct addition:** 249 LUTs, 68 fabric FFs, 0 DSP; setup slack -0.460 ns; hold slack +0.314 ns; feedback period estimate 4.460 ns.
- **Fixed 10-bit persistent membrane:** 485 LUTs, 33 fabric FFs, 1 DSP; setup slack -4.082 ns; hold slack +0.288 ns; feedback period estimate 8.082 ns.
- **Adaptive 8/10, exact pre-leak monitor:** 566 LUTs, 37 fabric FFs, 1 DSP; setup slack -5.888 ns; hold slack +0.231 ns; feedback period estimate 9.888 ns.
- **LUT 10-bit, 5-bit pair pre-adder:** 261 LUTs, 68 fabric FFs, 0 DSP; setup slack -0.118 ns; hold slack +0.434 ns; feedback period estimate 4.118 ns.

The feedback period estimate is 4 ns minus reported setup slack. It describes the routed internal recurrence path at this placement, not an achieved maximum board clock; there is no clock-period sweep or timing closure claim. All six runs miss the common 4 ns setup target, while their internal hold checks pass. External input/output delays are unspecified, and the OOC ports have partial-route warnings. Operand-to-register timing and board I/O are not verified. Hold slack is reported separately. Synthesis-only area and simulated 4 ns cycles must not be described as achieved throughput.

The original adaptive critical path passes from DSP P through membrane decoding, leakage, range checks and layout selection back to DSP C. It has 12 logic levels, 9.779 ns data-path delay, including 7.064 ns routing. The pre-leak rewrite reduces the internal feedback period estimate by 14.5% but increases LUT count by 5.4%. Its critical path still has nine logic levels and 8.103 ns data-path delay, including 6.161 ns routing. This exact optimization helps timing, but does not meet the matched clock target or beat the fixed-current/LUT alternatives.

The fixed-membrane run initially hit Vivado's blank Synth 20-411 error in opt_design. It was retried once by opening the saved synthesis checkpoint, then successfully placed/routed. No RTL changes were made to fix that tool failure. The failed log and retry reports are retained.

## Storage, operand delivery and fair interpretation

Fabric FF counts exclude registers inside DSP primitives. Adaptive 8/10 still reserves P's 48 bits and a 20-bit side register in both modes; it does not free the side storage during narrow operation. Fixed 10-bit persistent packing uses the same reservation. The fixed-current design keeps a 60-bit membrane plus the DSP's current state, so persistent storage can save fabric registers, but that advantage is also available without adaptation. A LUT design has no DSP allocation. No DSP-to-LUT area conversion factor is assumed and no total-area or power improvement is claimed.

DSP operands are pre-encoded signed radix words: sum_i(w_i*2^(b*i)) modulo 2^48. Naively concatenating negative weights is incorrect. Pre-encoding is done by the simulation source; its logic/host work and memory are excluded from core area and service cycles. The LUT uses raw int4 weights. This is favorable to the DSP candidate. Fixed current needs one operand format; adaptive operation needs width-specific words or an encoder. The two 48-bit DSP operand ports transfer 96 bits per issued ADD, versus 48 useful raw-weight bits for a six-lane LUT ADD. A wide step issues two DSP ADDs per input pair, including padding and replay. BRAM packing, dual-format storage, host time, interface registers, power and a board are unmeasured.

Integrating DSP into the proposed logic does not remove the LUT comparison. The operation being accelerated is paired synaptic accumulation plus the same neuron update. A baseline can implement that operation with another FPGA resource. Likewise a benefit over fixed membrane packing does not establish a benefit over the stronger fixed-current design.

## Research implication

The checked candidate is simpler than the prior promotion/overpacking variants and avoids their wide recovery logic. It still does not establish a substantial adaptive benefit over the best matched alternatives tested here. There is a real cycle benefit over fixed persistent wide packing and a fabric-register tradeoff relative to fixed current, but those do not add up to a demonstrated implementation win across timing and resources.

Do not grow this into a complicated accelerator merely to conceal the primitive's costs. A further candidate needs a concrete reason for a measured saving that strong fixed current and LUT implementations cannot obtain as cheaply, plus a matched check of control, state storage, operand delivery and timing. This experiment narrows the question; it does not prove all possible adaptive packing designs are impossible. Ordinary packed SNN additions already appear in [DSP-Packing, Section VII](https://arxiv.org/html/2203.11028). A novelty claim for membrane-aware adaptation still requires a separate prior-art audit. These local DSP48E1 results are not comparisons with FireFly's complete accelerators or published DSP48E2 system throughput.

## Reproduction and evidence

The accompanying ZIP contains both RTL versions, testbenches, independent integer checks, monitor-bound audit, existing model input, stimuli, raw model replay outputs, implementation scripts and routed utilization/timing reports. Use the existing Python environment and installed Vivado; no installation is required. Run check_persistent_unit.py, make_fast_unit.py, check_fast_unit.py, check_persistent_model_trace.py and check_fast_model_trace.py from this directory. Build selected tops with run_persistent_route.py or run_fast_route.py. Paths to the existing local Vivado installation are explicit in the runners.

Source SHA256: original 071145f102f34589cf23ac2fe08dd89e383c1db1d23f0a5defc33d6eee56aa77; simplified fface042fc6d0e693c1bb5ca88df3cd5d08a04cd41c9543b4d0485e576d7d911. Hardware rows and model replays verify these hashes. The JSON summary preserves all raw engine rows and resource vectors.
