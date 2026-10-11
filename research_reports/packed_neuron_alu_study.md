# Packed neuron ALU: next hypothesis tested

## What this result means for the paper

Keep the research question open, but do not make this datapath the main contribution yet. This experiment tested the concrete next hypothesis: remove the separate fabric leakage/reset arithmetic by executing it inside the packed DSP. It works exactly on the tested integer neuron contract and substantially improves the previous fixed-current DSP implementation. A stronger, matched LUT core still needs fewer LUTs, no DSP, and a shorter internal feedback period. All three engines have equal service-cycle counts. A controller would have to add a new measured benefit; making this fixed circuit adaptive does not itself solve the baseline gap.

The deliverable is a small neuron arithmetic primitive, not a complete accelerator. It is a fixed-format feasibility check. No adaptive controller was added and no novelty claim is established for this implementation.

## Arithmetic and compact encoding

The neuron uses binary input spikes with signed int4 weights, integer leak U <- U - (U >>> SH), then paired weight accumulation, then one boundary threshold/reset decision. The DSP implementation stores q = U + 2^(B-1). For B greater than SH:

    q_next = q - (q >> SH) + (2^(B-1) >> SH)

Each shift is fixed wiring. The DSP subtracts the concatenated shifted fields and adds the concatenated constants. In each field q >= q>>SH and the final q_next fits the field. Therefore the complete packed operation has no cross-field borrow or carry. Soft reset subtracts TH only from fields with U >= TH; hard reset subtracts their positive U. These nonnegative subtractions also stay within their fields. The DSP uses its 48-bit ALU, without its multiplier.

The ALU performs paired synaptic additions, leakage and reset. Fabric still supplies threshold comparisons, operation/input selection and output/control registers. Signed radix operands must be pre-encoded as sum_i(weight_i * 2^(B*i)) modulo 2^48. Concatenating two's-complement negative weights directly is incorrect. Correctness requires all current prefixes and persistent membrane values to fit the selected signed B-bit field; this fixed module does not detect or recover an out-of-contract overflow.

The LUT baseline explicitly forms a signed five-bit sum of each pair of weights, then updates its signed membrane register. It performs the identical leak and reset operation. It is stronger than the earlier more general LUT wrapper: its control and arithmetic are stated directly, allowing Vivado to simplify them together.

## Correctness and cycles

- Independent packed arithmetic audit: 180,000 random leakage/reset cases, zero failures. This supplements the lane arithmetic argument; it is not a formal RTL proof.
- RTL: 24 engine/configuration runs, each 320 timesteps, zero membrane/spike mismatches. Configurations cover 8/10/12/16 bits, LIF and non-leaky IF, hard and subtractive reset, empty timesteps, positive/negative bursts and random paired weights. The 16-bit IF test is finite-horizon only.
- Every engine takes 1,206 cycles in the corresponding stress tests, including common startup/drain. A maximum four-pair burst needs six command cycles: BEGIN, four ADDs and FINISH. Moving neuron arithmetic into the DSP does not reduce these counts.
- Saved-model replay: seed0, 48 held-out images, 32 steps each. The first six hidden neurons use 8 bits, SH=1, TH=9; the first four use 10 bits, SH=3, TH=17. Each of the DSP, LUT and fixed-current engines matches every reference state/spike in both configurations, with 18,871 cycles each. Blocks were selected by index, without a favorable-block search. This is block-level replay, not whole-network RTL accuracy. The SH=1 replay is a changed leak configuration of the saved weights, not a claim that the originally trained model's full accuracy is preserved under that change.

## Routed matched cores

Vivado 2025.2, Artix-7 xc7a100tcsg324-1, out-of-context, one thread, 4 ns clock constraint, TH=35, subtractive reset. Each result completed placement and routing. Compare implementations within a bit-width group: the 8-bit group has six neurons; the 10-bit group has four. The fixed-current 10-bit wrapper exposes four neurons and has no input/output dependency on the other two lanes.

### 8-bit membrane, 6 neurons, leak shift 1
- **Packed DSP performs accumulation, leakage and reset:** 133 LUTs, 8 fabric FFs, 1 DSP; setup slack -1.033 ns; hold slack +0.279 ns; internal feedback period estimate 5.033 ns.
- **Matched LUT neuron core:** 95 LUTs, 56 fabric FFs, 0 DSP; setup slack +0.654 ns; hold slack +0.204 ns; internal feedback period estimate 3.346 ns.
- **Fixed-current DSP with fabric membrane update:** 266 LUTs, 56 fabric FFs, 1 DSP; setup slack -1.320 ns; hold slack +0.532 ns; internal feedback period estimate 5.320 ns.

### 10-bit membrane, 4 neurons, leak shift 3
- **Packed DSP performs accumulation, leakage and reset:** 130 LUTs, 6 fabric FFs, 1 DSP; setup slack -1.022 ns; hold slack +0.490 ns; internal feedback period estimate 5.022 ns.
- **Matched LUT neuron core:** 80 LUTs, 46 fabric FFs, 0 DSP; setup slack +0.575 ns; hold slack +0.134 ns; internal feedback period estimate 3.425 ns.
- **Fixed-current DSP with fabric membrane update:** 216 LUTs, 46 fabric FFs, 1 DSP; setup slack -1.260 ns; hold slack +0.447 ns; internal feedback period estimate 5.260 ns.

The packed ALU reduces LUTs by 50.0% versus the six-neuron fixed-current DSP core, and 39.8% in the four-neuron group. Against the LUT core, it uses 40.0% and 62.5% more LUTs respectively, plus one DSP.

Both LUT cores meet the internal 4 ns setup target. Both packed ALU cores miss it. The six-neuron DSP path has only two LUT logic levels, but its P-to-fabric-to-DSP-A feedback path also pays routing and the unregistered DSP input setup time. This explains why fewer fabric arithmetic operators alone did not win timing. It is evidence about this implementation on this part, not a theorem that every DSP implementation must lose.

Fabric FF savings are real, but exclude the 48-bit P register inside the DSP. They are a resource tradeoff, not proof of smaller total area, lower energy or fewer state bits. The period estimate is 4 ns minus setup slack; it is not measured board frequency. Input/output delays are unconstrained, and the OOC ports have partial-route warnings. Thus the passing internal paths do not certify full-interface timing. Registering/pipelining DSP feedback may change cycles and storage and must be compared under a matched schedule.

The fixed-current 10-bit route initially hit a blank Vivado Synth 20-411 during opt_design. One retry reopened the unchanged synthesis checkpoint and completed. Both failure and retry logs are retained. No RTL repair was made for that tool failure.

DSP inputs are externally pre-encoded 48-bit words. The encoder, alternative-format storage, operand memory, host work and interface registers are excluded. The LUT uses raw int4 weights. This omission favors the DSP core. No board, power, model download, dataset download or package installation was used. These local cores do not reproduce FireFly's full dataflow, memories, FPGA family or throughput.

## Constructive next experiment

The binary-spike operation has no general synaptic multiplication: a spike selects a weight. The tested leakage is also a shift/subtract. LUT carry chains implement these operations cheaply, so adding format selection to an already losing fixed core is a weak next investment.

If broadening the neuron-update arithmetic is acceptable, the recommended feasibility target is **shared quantized leakage multiplication plus binary synaptic accumulation**, while keeping a small unit. General membrane time constants have a real model motivation: [Fang et al., ICCV 2021](https://arxiv.org/abs/2007.05785) train membrane time constants as well as weights. This paper is model motivation, not evidence that the proposed hardware is novel or that arbitrary per-neuron coefficients can share one packed multiplication. Packable lanes need a shared coefficient or explicit grouping costs.

For example, define the integer reference explicitly as U_leak = ceil(beta*U/256), beta in [0,256]. For an 8-bit membrane q=U+128, the algebraic candidate is:

    R = beta*q + 128*(256-beta) + 255
    q_leak = R >> 8

R lies in [0,65535]. Two q values placed at bit positions 0 and 16 fit in the DSP48E1's signed-positive multiplier input; a shared coefficient and two packed constants can produce two separate 16-bit results. A 16-bit membrane instead requires a 24-bit result per product and cannot pack two such operands into that same 25-bit multiplier input. This provides a possible narrow/wide throughput difference to investigate. It is a proposed arithmetic layout, **not implemented, simulated or routed in this study**. State storage, extraction, format conversion and command scheduling could still erase its benefit.

Beta=128 and beta=224 reproduce the existing SH=1 and SH=3 ceil-rounded leak respectively. General coefficients define a broader quantized neuron contract; preserving that reference exactly does not prove equivalence to a floating-point trained model. A next experiment must preserve its declared rounding/reset semantics and separately check classification accuracy.

Use three gates before calling it the paper mechanism:

1. **Fixed primitive gate:** compare packed DSP leakage/accumulation against shared fixed packing and optimized LUT cores at the same coefficients, outputs and accepted work. Check both fixed per-layer coefficients (allow LUT constant optimization) and genuinely required programmable coefficients. Include extraction/state/operand costs, and account for every cycle. A programmable multiplier comparison alone cannot justify a model whose coefficient is fixed.
2. **Adaptive gate:** only if a fixed DSP primitive has a useful resource/throughput tradeoff, add the smallest causal U-based narrow/wide choice. Compare with the strongest bound-proved fixed widths and count mode/conversion cycles. Measure a real extra benefit from adaptation across sparse activity and bursts, rather than the benefit of packing itself.
3. **Paper gate:** verify exact integer outputs, full model accuracy where applicable, and overlap with existing packing and neuron-update work. Avoid claiming first-ever adaptation from an unsuccessful keyword search. [DSP-Packing](https://arxiv.org/html/2203.11028) already covers packed SNN additions, and [FireFly](https://arxiv.org/html/2301.01905v5) already includes neuron leakage/threshold/reset computation.

If the scope must remain binary-spike accumulation with the same shift leak, keep the present negative results and investigate a specific measured cost that the LUT and fixed-current cores cannot obtain as cheaply. Renaming the monitor or declaring DSP intrinsic cannot remove those baselines. The unresolved scope choice is whether a general leakage multiplication is allowed; it has not been assumed accepted here. No publication-strength positive result is claimed yet.

## Reproduction

Use the existing Python/Vivado installations named in the scripts. Run check_neuron_alu.py and check_neuron_model.py. Route each of top_neuron_dsp8/lut8/current8 and top_neuron_dsp10/lut10/current10 with run_neuron_route.py; --resume opens an existing synthesis checkpoint after a tool failure. Run publish_neuron_alu.py to validate and package the result. Simulation/build scripts check available RAM before launching work. The evidence ZIP includes RTL, testbenches, checks, existing model input, raw stimuli/outputs, JSON rows, implementation scripts and routed reports/logs. Checkpoints and generated simulator binaries are excluded to keep it compact.

New RTL SHA256: d86970e669f68a605fc30c712f5edf9bbfd8f72fd2b55c50a5780bbbec355ebb. Baseline source SHA256: 071145f102f34589cf23ac2fe08dd89e383c1db1d23f0a5defc33d6eee56aa77.
