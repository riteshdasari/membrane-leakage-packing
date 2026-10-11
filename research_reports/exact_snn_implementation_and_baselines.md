# Exact adaptive SNN packing: implementations and matched baselines

Checked 8 October 2026. Both selected versions are implemented and pass numerical and real-DSP RTL checks. The current-checkpoint version saves DSPs relative to native FOUR12 but costs stalls. The membrane-promotion version is exact and genuinely membrane-aware, but its present shared wide fallback is substantially slower. Neither has yet demonstrated an end-to-end advantage over the strongest applicable fixed/fabric baseline.

## New matched FPGA measurements

Every core handles 24 neurons with int4 event weights and a 16-bit state. These are newly synthesized and routed cores with matching global-ready input semantics; the older 13-bit experiments are not mixed into these numbers. The default hardware configuration is LIF shift 1, subtractive reset and threshold 35. These configurations are arithmetic microbenchmarks, not the model-specific calibrated thresholds used in numerical inference.

- **Version 1: current checkpoint:** 663 LUTs, 648 FFs, 4 DSPs, 0 BRAMs; routed setup WNS -2.204 ns at a 4 ns target.
- **Version 3: membrane promotion:** 1253 LUTs, 660 FFs, 4 DSPs, 0 BRAMs; routed setup WNS -2.611 ns at a 4 ns target.
- **Native FOUR12:** 728 LUTs, 688 FFs, 6 DSPs, 0 BRAMs; routed setup WNS -2.006 ns at a 4 ns target.
- **Fixed six-lane current:** 616 LUTs, 641 FFs, 4 DSPs, 0 BRAMs; routed setup WNS -1.680 ns at a 4 ns target.
- **Parallel LUT-only:** 610 LUTs, 536 FFs, 0 DSPs, 0 BRAMs; routed setup WNS -0.464 ns at a 4 ns target.

Negative slack means the target is not met. These are out-of-context setup reports without board I/O constraints; they are not signoff timing, a clock sweep, measured Fmax or board operation at 250 MHz. Internal register banks, supplied weights and timing-shell registers are included; a full network's weights/SRAM/distributor/host are not.

The current-checkpoint critical path runs from a group's controller state through readiness gating to another group's DSP OPMODE control. The warning register avoids a direct combinational alarm loop, but the common input barrier still creates a cross-group control path. Promotion additionally needs membrane seeding/range checks and wide-path selection; its extra LUT cost and serialized wide updates explain why packing density alone is an insufficient hardware metric.

## Actual RTL cycle comparison

Cycles include accepted leakage, event and finish commands plus controller waits, over 120 timesteps. An event vector updates all 24 neurons. The following comparison uses identical stimulus and independent valid/ready drivers for each engine; it is not the earlier idealized sum of independent group schedules. Clock-period differences and end-to-end host latency are not folded into these cycle counts.

Burst-stress stream: 6031 accepted event vectors; maximum absolute current prefix 800.

- Version 1: current checkpoint: **9,412 clocks**, 3,141 input-busy clocks.
- Version 3: membrane promotion: **36,404 clocks**, 30,133 input-busy clocks.
- Native FOUR12: **7,472 clocks**, 1,201 input-busy clocks.
- Parallel LUT-only: **6,271 clocks**, 0 input-busy clocks.

Bounded-current stream: 794 accepted event vectors; maximum absolute current prefix 96.

- Version 1: current checkpoint: **2,715 clocks**, 1,681 input-busy clocks.
- Version 3: membrane promotion: **3,314 clocks**, 2,280 input-busy clocks.
- Native FOUR12: **2,235 clocks**, 1,201 input-busy clocks.
- Fixed six-lane current: **2,715 clocks**, 1,681 input-busy clocks.
- Parallel LUT-only: **1,034 clocks**, 0 input-busy clocks.

On this burst stream, version 1 takes 1.26 times the native core's clocks; version 3 takes 4.87 times. Version 1 uses 4 rather than 6 DSPs, a one-third saving, but this is not a latency win. The LUT baseline is fastest at 6,271 clocks.

Across the six leak/reset settings, membrane-promotion burst cost spans 36,404–43,927 clocks. Hard reset can alter membrane residency but does not make the present shared wide path fast. Fixed six-lane packing is excluded from the unbounded-current correctness/latency comparison because its range contract is violated. It does pass all bounded-current checks.

For these particular microcores, LUT-only has the lowest LUT, FF and DSP counts and the fewest clocks in both streams. Both adaptive designs therefore lose to it on these measured dimensions. None of the five cores meets the 4 ns setup target in this run; timing closure remains future implementation work. This result supports using LUT-only as the main local performance/resource baseline, not merely listing it as an optional alternative.

## What was implemented

Version 1 is exact current checkpointing: `U = wide base + packed current chunk`. Six signed eight-bit current fields share one 48-bit DSP adder. A registered headroom warning stops input, transfers the current chunk into a retained 16-bit register bank, and clears the packed chunk. Leakage operates on the wide state; threshold comparison and reset occur once at timestep completion. This controller observes current range, rather than actual membrane range.

Version 3 is exact actual-membrane promotion. After leakage, a group whose six membrane values lie within [-112,111] is seeded into the packed DSP. The controller observes those actual values during accumulation. A headroom warning transfers the exact state into the retained 16-bit register bank; the group then uses wide accumulation until the timestep ends. A group that cannot fit initially starts wide. This is legitimately membrane-potential-aware. The present wide path has one fabric adder per six-neuron group and serializes a vector across six update clocks, with an additional command-acceptance clock. It is not a fast parallel wide engine.

Neither version shifts away low bits or uses a mantissa/exponent approximation. Both retain a wide register bank throughout; wide storage is not allocated only when overflow occurs. Version 3 adapts whether a group participates in narrow DSP packing or wide processing; it does not yet remap six eight-bit DSP fields into four twelve-bit fields or consolidate freed DSP capacity. Both are exact only while the configured wide numerical range is sufficient. The implementation has no wide-overflow recovery. The Python verification checks that the tested workloads stay within that range.

The shared interface is `exact_tile`: 24 neurons, signed four-bit weights, 16-bit wide states, valid/ready input, and commands for an event vector, leakage/start, and timestep finish. One accepted event supplies one weight to each neuron. Global readiness gates delivery so every group consumes each vector exactly once. Different groups can checkpoint or promote independently, but a busy group stalls the shared input stream. Protocol: reset, accepted start/leak command, zero or more accepted events, accepted finish command, then wait for readiness before reading all output spikes and states. State-debug outputs are coherent after finish; they do not expose every in-flight narrow contribution.

`top_exact_*` wrappers are registered **out-of-context timing shells**, not a verified host-facing elastic valid/ready interface. They register ready and inputs without a skid buffer. Integrate the verified `exact_tile` handshake directly, or add and verify an elastic boundary before connecting a host. The reported wrappers have the same input/output register treatment.

## Verification and meaning of accuracy

The RTL tests use the real Vivado UNISIM DSP48E1 primitive, not independent-lane behavioral additions. Each engine receives the same stream through its own valid/ready driver. The suite covers IF and LIF with integer leakage shifts 1 and 3, each with hard and subtractive reset; positive, negative, canceling, random and empty-timestep workloads; and narrow-range boundary crossings. All 54 valid engine/configuration/workload cases passed, comparing every final membrane and spike across 120 timesteps. Static eight-bit current packing is included only in the bounded workload. The unbounded workload reaches an absolute current prefix of 800; native signed twelve-bit currents remain sufficient. The bounded workload reaches 96.

Full numerical inference separately tests both packed representations on all 360 held-out images of each of three saved models. All 36 combinations of model, leak, reset and engine preserve every checked membrane value, spike and prediction relative to the same independent integer reference. Physical packed 48-bit additions are simulated, including possible cross-field carries; this is not merely an independent per-neuron calculation. The numerical inference uses immediate conservative headroom checks, while the RTL tests independently verify the registered controller and its stalls. These are complementary checks, not full-network RTL inference.

The workload is the local 8x8 digits dataset, with a 64-128-10 network, signed int4 weights, 32 rate-coded timesteps and 1077/360/360 train/calibration/test samples per seed. Soft-reset accuracy spans 94.72â€“97.50%; hard-reset accuracy spans 93.06â€“97.22%. Thresholds were calibrated for the earlier soft-reset models and reused for hard reset, so these are not separately optimized hard-reset models. Exactness means no accuracy change against the corresponding reference, not a universal accuracy guarantee.

No MNIST/CIFAR model or dataset was downloaded. There is no complete SRAM/input-distribution accelerator, board inference, host transfer measurement, or measured power result. Vivado 2025.2 targets Artix-7 `xc7a100tcsg324-1`; the development host is Windows/Python/NumPy. An available FPGA board has not been confirmed.

## Strongest local baselines

There is no single strongest baseline across all workloads and resource objectives. Use the best feasible result from these matched cores:

- **Fixed six-lane current packing:** same exact wide-base/current representation and final neuron update, with warning/checkpoint control removed. It needs a proven bound on every current prefix, not merely the final sum. It is mandatory here: all three trained digits models require zero current checkpoints in the full inference run. An offline sum of each neuron's negative/positive weights proves all prefixes fit signed eight-bit fields when each input supplies at most one binary spike per timestep. Layer bounds across neurons are seed 0: [-49,51] / [-100,70]; seed 1: [-39,43] / [-100,64]; seed 2: [-47,48] / [-97,67]. This is a proof for these model weights and event semantics, rather than a conclusion from observed traces alone. On those models, adaptation has no demonstrated benefit over static packing.
- **LUT-only accumulation:** 24 parallel 16-bit state updates, same leak, threshold and reset semantics, zero DSPs. This is the strongest measured latency baseline in both supplied synthetic streams. Whether its LUT cost is worthwhile depends on the complete design's resource budget.
- **Native FOUR12 current packing:** six DSPs for 24 neurons, same wide state and final-update controller. It supplies an exact wider-current baseline for bursts that cannot use static signed-eight-bit packing.

The native baseline is an arithmetic reconstruction, **not an implementation of FireFly**. Original FireFly can process two presynaptic contributions across four output lanes per DSP per clock and uses DSP chains. Comparing our six single-input lanes with four lanes alone does not establish higher useful operations per DSP than FireFly. Any whole-accelerator claim needs the paper's full dataflow or an equivalently optimized matched backend.

## Published comparisons: accuracy, hardware, host and power

The following are representative reported configurations, not measurements of our cores. Accuracy is tied to the named dataset/network, precision and timesteps. LUT/DSP counts refer to whole published designs and cannot be equated with our 24-neuron arithmetic core. NR means not established from the cited main source; it does not mean zero.

- **[FireFly](https://arxiv.org/html/2301.01905v5):** static DSP SIMD/mux accumulation, IF/LIF support; simple firing/reset semantics. Ultra96 v2 implementation: about 15k LUTs, 288 DSPs, 300 MHz. CIFAR-10 SCNN7: 91.36%, 966 FPS, T=4, eight-bit weights, 2.55 W. The reported latency excludes the direct-coding layer; power scope excludes the PS CPU. Embedded Zynq PS controls the PL accelerator and AXI memory movement. This is a useful historical dense DSP reference, but native FOUR12 alone does not reproduce it.

- **[FireFly v2](https://arxiv.org/pdf/2309.16158):** static DSP packing with bit-serial support and double-frequency DSP operation. KV260: 26k LUTs, 512 DSPs, 87 BRAMs, eight URAMs; fabric 250 MHz, DSPs 500 MHz. CIFAR-Net/CIFAR-10: 93.6%, T=4, 2997 microseconds/image, about 334 FPS. Do not combine that accuracy/network with the smaller SCNN7's 2342 FPS. Reported 4.9 W is estimated whole-SoC power, a different scope from original FireFly. Embedded SoC control; a comparable PC-to-FPGA transfer benchmark is not established.

- **[FireFly-S](https://arxiv.org/html/2408.15578v1):** four-bit, dual-sparse, DSP-free accumulation; IF/LIF. KV260 at 333 MHz. CIFAR-10 SCNN9: 87.00%, 2327 FPS, 84,641 LUTs, 139,780 FFs, 76.5 BRAMs, zero DSPs, 3.799 W. MNIST SCNN5: 98.03%, 10,047 FPS, 30,911 LUTs, zero DSPs, 1.301 W. Power is Vivado estimation. Uses the Zynq/BrainCog framework; external host-transfer time is NR. It is an essential low-bit fabric baseline even though its CIFAR accuracy is lower than the other named configurations.

- **[FireFly-T](https://arxiv.org/html/2505.12771v1):** sparse DSP-based accelerator with load balancing and int4 quantization; KV260 at 300 MHz, embedded PS orchestration. CIFAR-Net/CIFAR-10: 93.60%, 354 FPS, 24k LUTs, 128 DSPs, 74 BRAMs. Spikingformer4-256/CIFAR-10: 94.45%, 907 FPS, 46k LUTs, 117k FFs, 304 DSPs, 100 BRAMs. Uses SpinalHDL/Vivado; power is estimated. Its DSP-efficiency gains include sparse scheduling, so they cannot be attributed solely to packing. This is a strong recent published DSP-based baseline for a complete accelerator.

- **[Spiker+](https://arxiv.org/html/2401.01141v1):** open fully connected LIF design with subtractive reset. MNIST 784-128-10, T=100, four-bit weights/six-bit membrane: hardware-quantized accuracy 93.85%, 0.78 ms/image; XC7Z020 at 100 MHz, 4314 LUTs, 3298 FFs, 18 BRAMs, zero DSPs, estimated 0.18 W. The higher float accuracy is not the hardware accuracy. Ready/start interfaces are described, but external PC transfer cost is NR. Useful for a full FC-system comparison; its six-bit quantized state differs from our exact 16-bit reference.

- **[HardF-SNN](https://ojs.aaai.org/index.php/AAAI/article/view/37174/41136):** hardware-friendly quantization with a FireFly-derived DSP systolic unit, FPGA `xc7z035`, ARM PS and DDR/AXI control. Hardware table: int4 CIFAR-10 VGG7, 91.83%, 2.22 ms/image, 511.75 GOPS and 129.23 GOPS/W. LUT/DSP counts and clock were not established from the main paper. The software ResNet19's 95.53% is not the same hardware-tested network. Relevant for int4 workload and quantization baselines, not a matched packing-policy experiment.

- **[ExSpike](https://arxiv.org/pdf/2606.20414):** fully event-driven DSP-free LIF accelerator, eight-bit weights/16-bit membrane; Virtex-7 `xc7v2000t`, 200 MHz. CIFAR-10 VGG11: 93.89%, 148 FPS, 41k LUTs, 40k FFs, 312 BRAMs, zero DSPs. Spikingformer4-256: 94.45%, 197 FPS, about 40k LUTs. Approximately 1.700 W is SAIF-based estimated dynamic power, not measured whole-SoC power. CPU/GPU comparison machines in the paper are not an identified FPGA host. This recent preprint is a strong event-driven fabric comparator, with different weight precision from ours.

- **[L-SPINE](https://arxiv.org/html/2604.03626v1):** multiplierless fabric SIMD with 2/4/8-bit modes, VC707/Virtex-7 and PicoRV32 control. A headline comparison reports 46.37k LUTs, 30.4k FFs, 2.38 ms and 0.54 W. The matched workload/precision and numerical accuracy for that configuration were not sufficiently established here, so it is a secondary source, not the primary baseline. Its neuron-path delay must not be interpreted as full-system clock frequency.

These sources support choosing **FireFly-T plus a DSP-free comparator such as FireFly-S/ExSpike**, with FireFly v2 for dense DSP throughput and Spiker+ for an FC network. They do not justify selecting a universal winner or comparing our digits accuracy directly with CIFAR accuracy. For a publishable comparison, match dataset/network, quantization, neuron equation, reset timing, T, FPGA family, memory budget and data movement; report accuracy, LUT/FF/DSP/BRAM, achieved clock, end-to-end latency, sustained throughput, energy, and host contribution separately.

## Prior art and the research claim

[Sommer et al., DSP-Packing](https://arxiv.org/html/2203.11028v1) explicitly discusses packed addition for SNNs, exact guard separation versus unguarded errors, and future dynamic packing. It is mandatory arithmetic prior art, not a matched end-to-end SNN accuracy baseline.

[SDV/BSEG](https://arxiv.org/html/2606.11065v1) studies exact packed arithmetic with spill tracking and block-segmented accumulation/rebiasing. Its high/low segment treatment overlaps with the generic wide-base/current-chunk idea. It is not an SNN membrane-aware evaluation, but means checkpointing/rebiasing itself cannot be assumed novel. This is an overlap check, not an exhaustive proof that no other related work exists.

The candidate research contribution is therefore the **SNN-specific policy and its verified system benefit**: which actual membrane states are kept narrow; when a group moves; how spill resources are shared; how exact threshold/leak/reset semantics are preserved; and whether the controller wins after stalls, migrations, LUT cost and host/memory overhead. The present implementation establishes exactness and exposes the costs. It does not establish that advantage.

Version 1 is the better starting point of these two implementations because it bounds per-timestep current independently of long-lived membrane growth. Version 3 is the more faithful realization of the mentor's membrane-aware description, but its shared wide path is currently slow. That result rejects the present fallback design, not all membrane-aware policies. A focused next revision would retain exact state while using a shared spill DSP/parallel wide path and evaluating workloads whose current-prefix bounds actually require adaptation. Do not add a large mechanism until its latency/resource tradeoff beats the matched baselines.
