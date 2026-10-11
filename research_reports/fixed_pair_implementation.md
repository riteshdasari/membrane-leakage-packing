# Fixed two-input packed baseline: verified RTL and routed comparison

All four matched 24-neuron kernels are implemented, pass independent integer-reference tests, and have completed out-of-context place-and-route. Fixed packing saves DSPs versus the native core but does not establish an overall win over the LUT-only core. None meets the 4 ns target. No end-to-end speedup or FireFly superiority is claimed.

## Implemented comparison

- Six-bit interval-biased current: eight lanes per DSP, three DSP instances. A supplied seed represents minus the tile's lower bound; exact current recovery subtracts that seed.
- Eight-bit midpoint current: six lanes per DSP, four DSP instances. Constant initialization and midpoint recovery avoid runtime bound metadata.
- Native FOUR12: four lanes per DSP, six DSP instances. Raw int4 weights are sign-extended by wiring; no bias recovery is needed.
- LUT-only: 24 parallel eight-bit current accumulators and 16-bit membrane state. Routed utilization confirms zero DSPs.

All accept two input-weight vectors per add command. All share a pipelined wide-state merge, leakage on the first tile of a timestep, and threshold/reset only on the last tile. Subsequent accumulation overlaps the merge. A commit interlock preserves state ordering when tiles are short. The source must retain a stalled command; the output has no backpressure.

Packing is fixed per instantiated core. This is a baseline, not an adaptive or novel membrane-aware mechanism. Bounds are supplied by an offline compiler; there is no runtime overflow fallback. Supported configurations are the four provided top modules, rather than arbitrary combinations of the module parameters.

## Verification

The final RTL was simulated using Vivado UNISIM DSP48E1 models against an independent Python integer oracle. Four kernels times six neuron settings gives 24 passing comparisons: IF, LIF with shifts 1 and 3, each with hard and subtractive reset. Each comparison contains 240 timesteps and 600 committed tiles. Every committed membrane state and spike vector matched: zero mismatches across 14,400 kernel/tile observations.

Inputs include empty tiles, odd input counts, positive/negative weights, activity bursts, sparse activity, consecutive commands and source bubbles. Tile lengths range from zero to seven, with certificates checked to fit all four designs. The testbench waits past UNISIM global reset. This is directed/random functional testing, not formal proof, network inference accuracy evaluation, or a board test.

Each configuration used 2,120 accepted commands, 223 stalled source cycles and 3,587 total simulation cycles including source bubbles and drain. The four designs were driven in lockstep and have a common controller, so these counts do not establish an independent performance ranking. The counted 44,160 contribution slots include inactive and padded inputs; they are not useful nonzero operations.

## What still determines whether this helps

### Routed results

Vivado 2025.2, Artix-7 xc7a100tcsg324-1, one implementation run per final design, 4 ns constraint, LIF shift 1 and subtractive reset:

- Six-bit: **3 DSP, 1,269 LUT, 1,552 FF; setup slack -0.522 ns**.
- Eight-bit: **4 DSP, 1,129 LUT, 1,260 FF; setup slack -0.396 ns**.
- Native twelve-bit: **6 DSP, 1,021 LUT, 1,288 FF; setup slack -0.577 ns**.
- LUT-only: **0 DSP, 1,170 LUT, 1,384 FF; setup slack -0.381 ns**.

All four have positive reported internal hold slack and zero hold-failing endpoints; all four fail setup at 4 ns. The summary JSON's `critical_period_estimate_ns` is 4 minus setup slack, not a verified closed clock period or measured FPGA frequency. External I/O paths are unconstrained and lack out-of-context physical port locations.

Eight-bit packing saves 33.3% of the native kernel's DSPs, with 10.6% more LUTs and 2.2% fewer FFs. Against LUT-only, it saves just 41 LUTs (3.5%) and 124 FFs (9.0%), consumes four DSPs, and has nearly identical setup slack. Six-bit packing saves 50% of native DSPs but uses 24.3% more LUTs and 20.5% more FFs. In this run the LUT-only core has fewer LUTs and FFs, zero DSPs, and better slack than the six-bit core. These are resource tradeoffs, not a scalar area or energy comparison.

The worst paths for both packed variants are the threshold/subtractive-reset stage. The native variant's worst path is command control to the DSP C input. Small timing differences from a single implementation run should not be treated as robust frequency advantages. The common neuron update and protocol are deliberately simple baseline implementations, not fully tuned accelerators.

The initial memory check stopped a launch; later RAM recovered. Restricted Vivado initialization failed with a file-writing error, while execution outside that restriction succeeded. One optimization attempt failed with an uninformative Synth 20-411; the diagnostic retry completed, with synthesis checkpoints saved. All four final routed reports now exist; no job remains running from this experiment.

The shared short tiles establish functional equivalence, not optimal system scheduling. Native twelve-bit and eight-bit baselines can support longer tiles when their bounds permit, amortizing seed/commit overhead differently. They must be allowed that advantage in a network comparison. The six-bit result is therefore not a demonstrated twofold system improvement despite halving DSP count versus the native kernel.

The packed variants accept pre-encoded full-word signed radix weights. Their two payloads require 288 bits (six-bit) or 384 bits (eight-bit) per add command, versus 192 raw int4 weight bits for native/LUT. This is 1.5x or 2x payload expansion if directly stored and delivered. A practical compressed encoding/decoder could change that tradeoff, but is not implemented. Six-bit tiles additionally need seed data. A claim based only on saved DSPs would ignore these costs.

The routing script targets Artix-7 xc7a100tcsg324-1 at 4 ns with one Vivado worker. It is an out-of-context core experiment, with external I/O delays unspecified. Even successful internal timing would not establish host-interface or board timing. No SRAM, DMA, host software, power measurement, FireFly reproduction, or end-to-end accelerator benchmark is included.

The fixed two-input baseline is now concrete. The next research gate is a workload-specific system benefit after weight delivery, longer baseline tiles, state traffic and neuron-update costs are included. The present evidence does not justify adding a membrane-width controller. A follow-up optimization of threshold/reset must be applied to all relevant baselines; it would be a common implementation improvement, not evidence for membrane-aware packing. There is currently no evidence that this baseline beats FireFly or supports the adaptive contribution.

## Reproduction

Extract the source bundle and run `check_fixed_pair.py` with Python. It uses the installed Vivado 2025.2 path recorded in the script and requires no downloaded packages. Run `run_fixed_pair_route.py` after sufficient RAM is available. It checks memory before each serial build and writes raw reports and `fixed_pair_hardware.json`. The simulation runner writes `fixed_pair_checks.json` and the stimuli, expected values and per-kernel outputs.
