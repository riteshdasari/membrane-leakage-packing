# Follow-up: trace-based screen of certified DSP packing

8 October 2026. The previous proposal was screened on all available saved models before committing to another adaptive RTL design. The stronger static baseline changes the recommendation: actual-U interval certificates provide no intrinsic field-width advantage over an optimally biased current interval under the same input bounds. On these models, a spike-count variant also provides no modeled benefit over the best fixed packing once tile size is optimized.

## Work completed

- Profiled three saved int4 64-128-10 digits models, 360 held-out images each, 32 timesteps, IF and two LIF leak settings, hard and subtractive reset: 18 configurations.
- Swept input tiles of 4, 8, 16, 32 and full fan-in; output groups of up to 24 neurons; field widths 6, 8, 12 and 16 bits, giving 8, 6, 4 and 3 lanes per 48-bit datapath.
- Compared dense input service and matched active-spike compaction. Candidate and baseline always use the same activity convention. Active-spike figures below still count zero-weight contributions; dual weight sparsity was not implemented.
- Compared actual-U certificates, current-only fixed packing, fixed interval-biased packing, and known-spike-count interval-biased packing. Included a fractional-lane oracle and a future-prefix oracle as optimistic diagnostics.
- Checked every analyzed tile's real prefixes against its certificate. Independent matrix products agree with the prefix traces, and reference classification agrees with previous inference results for every configuration.
- Audited physical 48-bit word addition on 8,000 random current tiles and 8,000 membrane tiles across the four formats: zero mismatches. This checks radix encoding and arithmetic; it is not a DSP primitive, RTL scheduler or routed-timing test.

No new training, model/dataset download, RTL synthesis or board run was performed. Only the local digits models were available in the inspected SNN experiment folders. These traces are not CIFAR or a FireFly reproduction.

## Why the stronger fixed baseline matters

Let a tile's current-prefix interval be [L,H], with L <= 0 <= H. The actual membrane interval is [U+L,U+H]. Its span is always H-L; adding U only translates it.

If a b-bit signed field can contain [U+L,U+H], then H-L <= 2^b-1. A fixed current representation Q=I-L also fits that b-bit field as an unsigned integer, because Q is in [0,H-L]. Recover I=Q+L exactly. The initial value Q=-L also lies inside the interval. Proper full-word signed weight encoding is required to prevent cross-field borrow mistakes.

Therefore, with identical tile bounds and grouping, the static biased-current field can always be at least as narrow as the certified actual-U field. This was also asserted throughout the profile. This is an arithmetic-width dominance result, not proof of total hardware dominance: current representation still needs a final wide-state combination and offset restoration, while carrying U directly may fuse that work.

The result applies to the examined timestep semantics: leakage before accumulation and threshold/reset after accumulation. It is not a theorem about every event-level neuron model, arbitrary reordering, approximate formats or all membrane-aware optimizations.

The earlier preimplementation screen omitted this stronger static baseline. Its proposed occupancy thresholds were valid for that hypothetical model, but insufficient to justify the adaptive mechanism. Generic offset priming and segmented packed arithmetic also overlap with [BSEG prior art](https://arxiv.org/html/2606.11065v1); this offset is not claimed as an invention.

## Cost model and comparison results

The unit is serialized pooled DSP service work, not elapsed FPGA cycles. Both sides process two contributions per cycle per lane. Each packed word gets one seed cycle. A 16-bit wide merge is modeled optimistically as three additions per DSP cycle; biased recovery is evaluated with one-pass, two-pass and fully overlapped merge alternatives. These merge architectures are not implemented here.

For the adaptive cases, the reported control scenario adds one check/lookup cycle per active 24-neuron block and two extra cycles per block format change. A serial per-neuron checker is also recorded. These are sensitivity assumptions, not measured controller costs. Common leakage and threshold work, memory ports, metadata bandwidth, LUT/FF cost and clock penalties are excluded. Bias restoration must not be treated as free in an implementation.

Tile size is selected independently per layer, separately for each method, using minimum modeled work on these traces. This is an optimistic screening choice, not a deployment setting validated on a separate workload. A speed ratio greater than 1 favors the named candidate.

- **Membrane adaptation versus fixed biased current, serialized one-pass merge:** 0.843–1.181x. Some apparent gains remain when wide-state merging occupies the same service resource.
- **Membrane adaptation versus fixed biased current, fully overlapped merge:** 0.641–0.884x. It loses in every configuration in this stronger baseline scenario. The overlap requires hardware/buffering and is not free area.
- **Spike-count adaptation, free control and overlapped merge:** 1.000–1.000x. It ties the best fixed design in all 18 configurations.
- **Spike-count adaptation with modeled control and overlapped merge:** 0.945–0.953x.
- **Spike-count adaptation with modeled control and serialized one-pass merge:** 0.979–0.989x. It also loses under this matched merge assumption.
- **Fixed biased packing versus the reconstructed fixed-twelve-bit current reference, both with serialized one-pass merge:** 1.441–1.448x. This is a modeled low-bit arithmetic improvement, not measured superiority over FireFly and not a membrane-adaptation benefit.

The original FireFly uses a pipelined unified membrane-update path; a reconstruction that forces all wide updates to serialize with synaptic computation can be unfair. Its precise overlap and memory limits must be reproduced before making a system claim. [FireFly architecture](https://arxiv.org/html/2301.01905v5)

## Spike-count variant and its additional cost

For a tile with r active inputs, safe prefix bounds can be tightened to the sum of up to r most-negative weights and up to r most-positive weights. The signs are clipped at zero so the empty prefix is included. Tables indexed by r can be prepared from the weights. The input bitmap/count must be available before dispatch; collecting it can itself require buffering.

This is activity-aware current packing. It can shrink the interval's span, whereas U alone translates an interval. It is a different mechanism from membrane awareness. Exact bounds were confirmed against all observed prefixes, but the favorable formats were already available to an optimized fixed tile layout in the tested models.

Straightforward bound tables also add memory. The summary JSON computes bit-packed tables for every neuron and every possible r, using separate minimal unsigned widths for the negative and positive bound magnitudes. Across the profiled table layouts, they occupy 0.94–3.43 times the int4 weight bits. Their size is additional to int4 weights and excludes headers, word rounding, ports and any replicated lookup bank. This is one storage implementation, not an information-theoretic lower bound: compressed formulas or shared conservative tables could cost less, potentially with looser bounds. No storage advantage is established here.

## What the result supports

Do not build another membrane-certificate controller on the strength of this proposal. The analytical packing advantage does not survive the stronger baseline as a robust result. A spike-count version also fails the free-control gate on the current models.

If continuing hardware work, the useful next reference is the simplest two-input fixed packed core with correct signed-word encoding and a pipelined wide-state update. That establishes the real cost of static range reduction and prevents attributing its gains to adaptation. A membrane-aware proposal should then target a separately demonstrated benefit, such as removing a measured state-movement bottleneck or fusing a costly neuron update, and must retain that benefit after memory, timing and control costs are included.

This conclusion rejects the examined certificate/packing mechanisms on the available workload and exposes a general limitation of U-only interval translation. It does not prove that every membrane-aware architecture is unhelpful. Larger workloads can test other opportunities, but cannot invalidate the interval-width argument under its assumptions. No claim of beating FireFly, FireFly v2 or FireFly-T is supported by this study.

## Reproduction

The source bundle contains the profiler, arithmetic audit, publisher, saved models, prior calibrated setup/reference accuracy JSON and raw/summary results. Python needs NumPy. Run `python certified_packing_profile.py`, then `python audit_certified_arithmetic.py`. The profiler checks free memory and completed in about 156 seconds on this host. To regenerate the publication files, keep the bundle under `work/adaptive_snn_probe` within a workspace and run `python publish_certified_study.py`; it writes into that workspace's `outputs` directory. SHA256SUMS.txt covers the bundled contents.
