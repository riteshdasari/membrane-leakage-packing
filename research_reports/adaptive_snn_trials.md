# Exact adaptive SNN accumulation: trial results

8 October 2026. New Python experiments, UNISIM DSP48E1 simulations and Vivado synthesis/place/route on Artix-7 xc7a100tcsg324-1. The original Desktop project was left unchanged. No packages, models or datasets were downloaded.

## Decision

There is a substantially cheaper exact alternative to the old overpacking recovery circuit. Six 8-bit current fields share one 48-bit DSP adder; a group warning checkpoints these currents into wider membrane state before a carry can corrupt an adjacent field. It saves DSPs with modest fabric cost. It has not demonstrated superior end-to-end latency, nor a benefit specifically from membrane-aware adaptation. Keep it as a prototype rather than declare the ISCAS contribution established.

## What the old design packed and why it cost so much

The old seven-lane circuit packed persistent neuron membrane accumulation, including signed synaptic increments. It used guard-free 6-bit fields with residue references and side counters to recover cross-field carries/borrows. The multiplier was disabled. This was addition packing, not multiplication packing.

Computationally, a single DSP update advanced seven independent sums. Correct recovery preserved the reference states and spikes within counter limits. That is a valid arithmetic advantage.

Hardware still had to predict/detect carries in every lane, update counters, reconstruct wide values, and perform leakage, comparison and reset. The zero-stall recovery RTL paid for this bookkeeping continuously. The packed DSP-to-recovery feedback also created long paths. Saving a small adder is of little value if its recovery circuit is larger than the adder.

Saved routed full-neuron results were 3,063 LUTs / 711 FFs / 4 DSPs for 28 packed neurons, versus 592 / 182 / 7 for FOUR12, and 547 / 479 / 0 for LUT-only. Those old results diagnose that implementation; they are not a matched comparison to our new 24-neuron prototypes. See the accompanying original review for provenance and wrapper limitations.

## Mechanisms tried

1. **Early checkpoint instead of overflow recovery.** Offset-binary fields allow signed increments without cross-field contamination while each field remains in range. A high-bit headroom test warns before the next additions can exceed that range. Copy the exact chunk into a wide shadow membrane and restore the narrow field to zero. This removes per-lane residue references and wrap counters.
2. **Shared wide neuron update.** Serialize leakage and the final threshold/reset through one wide unit per group. Do not fire or reset at an intermediate checkpoint: signed future increments may cancel earlier positive ones. This preserves the discrete timestep reference semantics.
3. **Pipeline and bank-write repair.** Register the group warning, reserve two-event headroom, and pipeline addition before threshold/reset. A shared bank write address/data bus avoided accidentally inferring two expensive variable-index write paths. The first pipeline synthesis used 933 LUTs; the corrected guarded design used 582. Pipeline placement and memory inference mattered as much as arithmetic packing.
4. **Reuse the DSP for wide membrane operations.** Snapshot narrow fields and reuse the same DSP for wide add, leak subtraction and reset subtraction. This passed functional checks but needed extra cycles and registers and had worse timing. It is not the preferred version.
5. **Seed fields with the actual membrane and promote a group when it grows.** An exact numerical prototype tried this direct membrane-aware interpretation. It checked state equality but did not implement migration/reconfiguration RTL. Even its optimistic work model generally lost to zero-based current chunks. One large membrane caused the entire group to fall back to wider processing.
6. **Static and periodic fixed baselines.** Compare native FOUR12, LUT-only, periodic worst-case drains, and offline signed weight bounds. This prevents attributing ordinary low-bit packing gains to adaptation.

## Routed hardware result

All new resource figures below are routed Slice LUT/FF/DSP counts. The target was 4 ns; a negative WNS means the design did not meet that target. These are local out-of-context cores with register banks, not complete accelerators or board measurements.

- Guarded shared pipeline, 24 neurons: **582 LUTs, 566 FFs, 4 DSPs; WNS -1.190 ns.**
- Native FOUR12 shared pipeline, 24 neurons: **618 LUTs, 602 FFs, 6 DSPs; WNS -0.662 ns.**
- DSP-reused guarded core, 24 neurons: **580 LUTs, 706 FFs, 4 DSPs; WNS -2.298 ns.**
- Direct LUT-only, 24 neurons: **672 LUTs, 465 FFs, zero DSPs; WNS +0.013 ns.** It meets the local 4 ns target and updates neurons in parallel, making it a serious baseline.
- Guarded accumulation-only, 84 lanes: **477 LUTs, 474 FFs, 14 DSPs; WNS -1.963 ns.** This wrapper uses the earlier combinational warning, not the final registered-warning neuron pipeline. It illustrates why a cheap area result alone does not establish good timing.

The preferred guarded prototype saves 33.3% of DSPs, 5.8% of LUTs and 6.0% of FFs against the shared FOUR12 prototype. Its timing is worse. A rough target-minus-slack estimate gives about 193 MHz versus 215 MHz, but this is not a closed maximum-frequency result. Local core wrappers register interfaces; external weight delivery and global event scheduling are not integrated or timed here.

Continuous-event UNISIM tests accepted 5,938 events over 120 timesteps with positive, negative and random weights. Both leak shifts, 1 and 3, produced zero state/spike mismatches. The six-lane guarded cluster took 9,002 clocks versus 7,379 for the four-lane native cluster: about 22% more clocks on that stress. They process different neurons per cluster; this is a scheduling measurement, not matched full-24-neuron inference latency. Reusing the DSP took about 11,224–11,244 clocks for six lanes.

## Numerical and scheduling evidence

Three independently trained 64-128-10 digits models were quantized to int4 and converted to integer IF/LIF inference over 32 timesteps. Reference classification used 360 held-out images. Packing characterization used the first 48; candidates were checked against exact reference currents and firing decisions. All tested candidate trace comparisons had zero mismatches. Physical packed arithmetic was separately fuzzed for 60,000 updates across six field widths. These are tests, not a formal proof.

The decisive finding: every neuron's full-timestep current in all three digits models has an offline signed weight bound fitting 8 bits. Across the models, hidden currents are bounded between approximately -49 and +51 and output currents between -100 and +70. For any binary input subset, sum negative weights bounds the minimum and sum positive weights bounds the maximum. Thus **static six-lane packing already suffices on these models**, independent of observed sparsity. Adaptive drains are unnecessary here.

The six-lane scheduling model uses about 0.731–0.739 times native FOUR12 aggregate DSP work, but adds about 4–6% abstract core latency for the longer final readout. This is principally a fixed-packing advantage. Its optimistic model omits full RTL leak/control cycles, SRAM ports and clock differences; do not interpret it as a measured accelerator speedup. The registered-warning model conservatively checkpoints immediately at the two-event margin; actual RTL permits one further update before that warning reaches the controller. UNISIM, rather than this abstraction, verifies that physical control timing.

Direct membrane-seeded packing had an ideal DSP-work ratio around 0.734 at leak beta=0.5, 0.763–0.833 at beta=0.875, and 0.861–0.948 for IF. These lower-bound estimates exclude migration overhead. Stronger retention makes persistent membranes less suitable for narrow packing. Int8 trials generally needed fields wide enough that useful density fell to four lanes or fewer, removing the main DSP-count advantage.

Untrained large-fan-in stress was added specifically to make adaptation necessary: 2,304 inputs, 96 neurons, eight steps with spike rates 1%,1%,60%,80%,1%,1%,60%,80%, signed int4 weights. It is a numerical stress test, not a task-accuracy benchmark. Observed native currents were checked to fit signed12.

- Balanced weights: registered-guard adaptive DSP-work ratio **0.671** versus **0.975** for periodic fixed drains. With a shared input stream paused whenever any group checkpoints, modeled latency ratios relative to FOUR12 were **1.075 adaptive** and **1.462 periodic fixed**. Here adaptation helps against the periodic baseline, while native FOUR12 remains faster.
- Positive-biased weights: adaptive DSP-work ratio **0.694** versus **0.975** fixed, but shared-stream latency ratios were **1.591 adaptive** and **1.462 fixed**. Frequent group-specific drain requests make adaptation worse for latency.

Three scheduling assumptions are retained in the data: independent-group work, resetting all groups together, and selective group draining with a global input pause. They are different architectures. Aggregate DSP work can improve while shared-stream latency worsens. Group queues, weight bandwidth and overlapping drain service must be implemented before claiming a throughput benefit.

## Can the mentor's motivation be incorporated?

Yes, through the exact decomposition `U = wide_base + narrow_delta`. At the start of a timestep leak the full membrane base; pack signed synaptic deltas; checkpoint when delta headroom is exhausted; evaluate threshold/reset only at the prescribed timestep boundary. Changing the base is an exact representation change. It is a cheaper way to accommodate a growing numerical range than continuously reconstructing overflowing membrane fields.

However, our implemented warning observes **current-delta range**, not membrane potential or distance to firing threshold. Calling the existing winner “membrane-potential-aware adaptive DSP packing” would overstate what the controller does. A precise present description is **lossless range-aware packed current accumulation with checkpointed membrane state**.

To earn the membrane-aware description, actual membrane state must influence a consequential decision: admission into narrow fields, promotion, regrouping, or service priority. The membrane-seeded promotion trial is one such policy, but it was not a winner. A possible next hypothesis is to choose narrow groups using predicted membrane range and upcoming signed current bounds, retaining a fixed/static safe mode for bounded layers. Whether that saves more than its predictors and migration cost remains unverified.

Simply right-shifting an overflowing membrane is not lossless. For example, 3 shifted right then restored becomes 2. Exact shifting requires retaining discarded residues and scaling thresholds, weights and leak/reset consistently; that may recreate the old bookkeeping cost. Saturation is also not generally exact with signed cancellation: signed6 saturation of +40 then -40 gives -9 instead of zero, which can change a later spike.

## What this supports, and what remains open

It supports a feasible DSP-saving core and explains why the earlier design failed. It does not establish a new membrane-aware method, an ISCAS-ready result, power savings, or improved complete-accelerator latency. Tested neuron semantics are integer IF/LIF with one soft-reset subtraction per timestep; RTL exercises LIF shifts 1 and 3. We did not test adaptive-exponential, Izhikevich, conductance-based, hard-reset or multi-spike neuron semantics.

Before committing the paper topic, demonstrate on a trained workload where offline bounds require wider fields: compare static heterogeneous packing, native SIMD, LUT-only and the adaptive policy under the same bandwidth/resource budget. Integrate bank ports and the shared event controller; report burst-tail latency, DSP work, LUT/FF/BRAM, routed timing and energy. The positive-biased stress failure is an explicit design target for overlapping checkpoint service. Novelty must be checked separately; checkpointing, width adaptation and time-sharing alone are not evidence of novelty.

## Reproduction

The companion ZIP contains the local dataset, Python scripts, model arrays, RTL, testbench, JSON results, routed/synthesized utilization and timing reports, and a SHA256 manifest. `README_REPRODUCE.md` distinguishes final designs from intermediate trials. Python paths and the Vivado installation path are environment-specific; edit them for another machine. No full FPGA bitstream, SRAM accelerator or physical power measurement is included.
