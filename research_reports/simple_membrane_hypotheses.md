# Two small membrane-aware packing hypotheses: completed screen

Both hypotheses were tested as arithmetic-unit mechanisms using all three saved int4 digits models: 360 held-out examples each, 32 timesteps, IF and LIF shifts 1/3, hard and subtractive reset (18 configurations). No new training, downloads, RTL, synthesis or board runs were performed. These are trace/arithmetic service estimates, not measured hardware throughput or a FireFly reproduction.

The result supports keeping the research scope small, but neither tested variant yet supports another adaptive RTL implementation. Persistent packing has an opportunity relative to conservative membrane widths; its causal controller gives inconsistent, small gains against a strong narrow-current baseline with overlapping wide updates. Guaranteed-firing retirement is exact for hard reset, but releases too little work in fixed groups.

## 1. Keep the membrane packed

Candidate: retain actual membrane in packed fields between timesteps; choose one field width per contiguous block of up to 24 neurons. Widths 6/8/12/16 correspond to 8/6/4/3 lanes in 48 bits. This is a representation and arithmetic study; lifetime storage inside a DSP, state swapping, address mapping and leak/reset implementation are not built.

Three references prevent conflating adaptation with ordinary quantization:

- Fixed membrane width proven for every input spike pattern over the 32-step horizon, derived from weights, leak and reset. This proof is horizon-specific, not an infinite-time bound.
- Fixed width fitted to the maximum range observed on all evaluation traces. This is an optimistic diagnostic that uses evaluation data, not a deployable calibration claim.
- Fixed eight-bit current plus wide membrane update. Previous local weight-only checks prove full-layer current fits signed eight bits on these three saved models. Each method receives the same input activity and grouping.

The future-aware oracle chooses a width covering the old state, all real current prefixes, and final reset state. Its service advantage against trace-fitted fixed membrane packing is 1.175–1.417x. This oracle knows the future and is not a controller.

The causal candidate chooses width from actual U and weight-only prefix bounds [L,H], including initial state and zero. It requires no future spikes but must reserve room for every permitted input pattern. Against the fixed finite-horizon membrane proof it gives 1.066–1.389x with free control, or 1.038–1.352x after one unhidden check per 24-neuron block per timestep and two cycles per format change.

Against fixed narrow current with a fully overlapping wide update, the causal candidate gives 0.832–1.088x even with free control, or 0.816–1.061x with those control costs. A ratio above one favors the candidate. If wide updates instead serialize as ideal three-lane 16-bit additions, the free-control ratio is 0.961–1.264x. Consequently, deleting a serialized merge is insufficient evidence unless that serialization is unavoidable in the matched baseline.

The candidate exceeds that overlapping-current baseline in 9 of 18 configurations under the assumed control costs; its best advantage is only about 6%. These are optimistic service estimates. A monitor, per-lane bound storage, remapping logic or clock penalty can readily consume that budget.

This screen counts serialized pooled arithmetic service, not wall-clock FPGA cycles. It excludes common leak/threshold costs and area. Fixed-current initialization costs are included. Retaining the membrane assumes no reseeding charge when format is unchanged; actual DSP scheduling could require it. No positive hardware claim follows from these assumptions.

### Storage and adaptation cost

The oracle's compact timestep-end representation uses 6.25–9.72 bits/neuron on average; the causal processing-format representation uses 8.11–10.38, including an ideal two-bit format tag per block. Compact endpoint formats can differ from formats needed during accumulation, adding another conversion that is not modeled. The fixed proof uses 8.29–12.29 bits/neuron before metadata. This comparison excludes row rounding, ports, maps and replicas.

Logical state-bit reduction does not automatically remove physical registers or BRAM. Reserving the maximum width for every block retains the maximum storage allocation. Reclaiming narrow-block space requires a concrete allocation and addressing scheme, whose cost is outside this small-unit screen.

Changing b moves neuron i from bit offset i*b to a new offset. A single ordinary shift cannot convert the packed word: lanes require extraction/sign extension and placement. Supporting all widths also changes which neurons belong to each DSP word. Thus a cheap monitor does not imply cheap migration. Exact leakage and threshold/reset must also operate on each lane without cross-lane borrow. Our earlier routed fixed cores show those costs matter.

The representation could still become useful if it removes a measured wide-state storage/update cost with simpler migration than the existing designs. The present oracle/control gap and lack of a robust win over overlapping current accumulation do not establish that mechanism. Ordinary packed addition is already in [DSP-Packing, Section VII](https://arxiv.org/html/2203.11028); narrower state alone is not claimed as new.

## 2. Retire a lane when hard-reset firing is guaranteed

At a prefix boundary j, let current membrane plus accumulated current be A. Let L_remaining be the sum of all negative remaining weights, treating positive weights as zero. Every permitted future spike pattern gives a final value at least A+L_remaining. If A+L_remaining >= threshold, the final boundary-time spike is one and hard-reset state is zero. The remaining additions may be omitted exactly; the spike is still emitted at the normal timestep boundary.

For example, A=50, threshold=35 and L_remaining=-10 guarantee firing. A=36 with L_remaining=-10 does not. Simply crossing threshold is unsafe with inhibitory weights: 12 followed by -5 ends below threshold 10. With subtractive reset, skipping a remaining +5 after a partial 12 changes residual from 7 to 2, even though both fire. This study therefore does not apply retirement to subtractive reset. It assumes ordinary timestep-boundary firing, no intermediate plasticity/observables and mathematically unbounded intermediates or a proven absence of machine overflow.

Checking every two input positions, weight-only certificates save 3.016–5.087% of spike-weight addition slots with perfect free lane refill. Keeping fixed six-lane packets reduces pair service by only 0.000–0.069%: the last unfinished lane keeps the packet alive. This is an upper opportunity screen, with checking/refill/weight gather excluded. Addition slots include active inputs with zero weights; they are not exclusively nonzero arithmetic.

An oracle that already knows the sum of future active negative contributions raises ideal addition savings to 5.027–8.823%. Even then fixed six-lane packet service savings are 0.000–0.093%. Computing that exact future-negative sum would itself do work, so this is an opportunity diagnostic only.

Checking every 8 or 16 input positions further reduces free-refill savings. One extra serial check cycle at each visited prefix boundary produces a modeled speed ratio of 0.229–0.246x for the two-position schedule. Those checks use input-position boundaries, not an optimized active-event schedule; fully parallel checks might avoid these cycles but still cost logic, tables and routing. Even zero-cost checking has almost no fixed-packet throughput gain here.

The independent audit checked 204,000 random prefix/neuron certificate cases with zero failures. Every retired state and spike in the full hard-reset trace screen exactly matches the independent matrix-product reference, and all 18 reference classification accuracies match previous saved inference results. This is mathematical/Python validation, not RTL verification of a retirement controller.

Membrane-based stopping overlaps [dynamic predictive early stopping](https://globals.ieice.org/en_publications/elex/10.1587/elex.21.20240206/_f), and membrane-directed masking overlaps [SpQuant-SNN](https://pmc.ncbi.nlm.nih.gov/articles/PMC11408473/). Our exact certificate has a distinct correctness condition from prediction/masking, but novelty of a complete packing mechanism is not established.

## Decision for a compact packing paper

No full accelerator is needed to evaluate a packing primitive. A suitable paper could contain one datapath, one inexpensive adaptive rule, a correctness argument, routed resource/timing results and workload traces. However, it still needs a measured benefit over strong fixed packing and a LUT implementation of the same operation. An isolated unit does not eliminate the cost of delivering operands or converting its representation.

Do not add a crossbar/refill scheduler merely to realize the 3–5% retirement opportunity on these models. It conflicts with the requested simple mechanism and has a small budget even before control costs. Do not treat the oracle's narrower widths as a demonstrated persistent-packing controller.

The completed tests identify the conditions another simple mechanism must satisfy: preserve a fixed lane map; avoid maintaining a duplicate full-width datapath; amortize rare recovery; and show a substantial causal benefit on actual traces. The current experiments provide no FireFly superiority claim and no publication-strength result for these two hypotheses.

## Reproduction

The bundle includes the script, publisher, raw/summary JSON, saved model files and previous setup/reference results, with SHA256 hashes. Run `simple_membrane_hypotheses.py` with Python and NumPy. It checks available RAM and requires no new data. This screen does not retrain or evaluate a new dataset. The only available local models in this experiment remain the small 8x8 digits networks; broader workload conclusions are unsupported.
