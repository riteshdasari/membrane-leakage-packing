# Mechanism screen before the next implementation

> Updated after the trace study: the recommendation below has been superseded by the [completed follow-up](certified_packing_followup.md). A stronger fixed, interval-biased current baseline removes the intrinsic field-width advantage of the actual-membrane certificate under identical bounds. Across the 18 saved configurations, spike-count adaptation also only ties optimized fixed packing with free control and loses with modeled control costs. Another adaptive RTL controller is not justified by these results. The original conditional analysis is retained below for context.

8 October 2026. This is a paper, arithmetic and cost-model study using the existing local results. No new RTL implementation, synthesis, training, dataset/model download or board benchmark was run for this study. The speed ratios below are conditional calculations, not measured accelerator improvements.

## Decision

There is a plausible route to higher arithmetic throughput than the original FireFly: retain its two-input DSP computation, pack more output accumulations, and select a provably safe field width at a tile boundary. The best candidate for further study is **two-input, tile-bound-certified packing**, with the actual membrane included in the range certificate when the DSP carries actual membrane state.

This does not yet establish superiority over FireFly, FireFly v2, FireFly-T, or an optimized fixed packed core. The critical competing explanation is that low-bit weights and a better static datapath produce the gain, while membrane awareness adds overhead. The next study must distinguish those possibilities.

## Correct reference point

[Original FireFly, section IV-B](https://arxiv.org/html/2301.01905v5) maps two presynaptic inputs by four output lanes onto each DSP48E2 and cascades eight DSPs for sixteen inputs. It uses int8 weights, registered inputs, native FOUR12 arithmetic, stationary weights and dedicated cascade wiring. Its partial currents are combined with membrane state through a unified Psum/Vmem buffer. A twelve-bit DSP field therefore does not imply that the entire persistent membrane is restricted to twelve bits. Our six-lane, one-input Artix-7 core has a lower peak contribution count per DSP cycle: six versus eight. Its current-only FOUR12 comparator is not a full FireFly implementation.

[FireFly v2](https://arxiv.org/pdf/2309.16158) uses a DSP domain at twice the fabric frequency, with 500–600 MHz DSP operation, and a temporal/spatial dataflow that avoids the large full-feature-map membrane buffer. Local residual membrane state remains. A compression proposal cannot claim to remove a large buffer that this comparator already avoids. A comparison at half the DSP clock must account for that disadvantage explicitly.

[FireFly-T, section IV-A](https://arxiv.org/html/2505.12771v1) already decodes multiple active spikes per cycle and balances sparse work using a wide-bank memory organization. It evaluates int4 models. Generic zero skipping and queues are therefore insufficient distinguishing contributions. A packing extension should be evaluated on a matched sparse backend and precision, as well as against the original dense design.

All arithmetic comparisons here count one spike-weight contribution as one synaptic contribution, avoiding differences in papers' GOPS conventions. The packing ratios assume matched input activity and useful lane utilization.

## Changes screened

### 1. Parallelize the present wide fallback

This removes the current six-update-clock serialization and should reduce its cycle count, but needs extra wide adders, write ports and routing. It does not increase the narrow core's one-input/six-output capacity. The current LUT core already consumes one complete event vector per clock at lower resource counts. This is a repair of a known bottleneck, with no established route to beating FireFly by itself. Do not select it as the main research contribution.

### 2. Add independent queues and remove the global ready barrier

This can help when only a few groups stall. It costs queue storage, dispatch/control and neuron-state ordering logic. All-wide bursts still exhaust the available service capacity; buffering cannot create arithmetic throughput. It is useful supporting engineering only after there is an arithmetic or memory advantage to preserve. Sparse dispatch and balancing already overlap with FireFly-T.

### 3. Retain two inputs and pre-encode signed packed weight words

For b-bit fields with radix R=2^b, encode state and a weight vector as:

    P(U) = sum_i (U_i + R/2) R^i
    W(w) = sum_i w_i R^i mod 2^48

Then the intended update is:

    P_next = P(U) + s_a W(w_a) + s_b W(w_b) mod 2^48

If every resulting field remains within its signed range, the result is exactly the encoded independent-lane sum. This follows from integer linearity. A simple concatenation of each weight's two's-complement field is not generally W(w): for two byte fields, weights (-1,2) encode as 511, not 767. Borrow correction must be included when preparing the full word.

For stationary weights, investigate doing that preparation offline or once during weight loading. This could remove the per-update bias-correction operand used by our current prototype and preserve two weight inputs plus a partial sum/feedback path. It does not prove a fast DSP implementation. Spike gating, register alignment, seed delivery and legal source selections still need primitive-level verification. Pre-expanded weight words can also inflate memory traffic; count preparation, storage and format changes.

The [AMD DSP48E2 documentation](https://docs.amd.com/r/2024.2-English/ug974-vivado-ultrascale-libraries/DSP48E2) distinguishes static USE_SIMD attributes from runtime OPMODE control. We cannot switch the hardware attribute between ONE48 and FOUR12 per event. A dynamic field-width design would normally keep ONE48 and alter the packed representation, or dispatch work to separately configured engines. The legal operand-source options are described in the [AMD Opmode documentation](https://docs.amd.com/r/2022.2-English/ug1483-model-composer-sys-gen-user-guide/Opmode).

Actual membrane seeding is a further cost: P feedback belongs to the preceding accumulation context, while PCIN is a dedicated cascade path. A streaming FireFly-like chain cannot assume that an arbitrary new membrane vector is freely available as another independent input. Any seed stage, load cycle, context interleaving or reduction in input parallelism must be counted.

### 4. Choose width using a safe tile certificate

For each neuron's upcoming input tile, precompute bounds from its weights:

    L = sum_j min(w_j, 0)
    H = sum_j max(w_j, 0)

With at most one binary spike from each listed input in that timestep/tile, these bound every current prefix in any order. After applying the reference leakage, a b-bit actual-membrane field is safe for the complete tile if:

    -2^(b-1) <= U + L  and  U + H <= 2^(b-1)-1

This is a sufficient certificate. It can be conservative; use the complete tile's weight bounds, not a forecast of future spikes. For example, L=-32 and H=32 with U=40 gives [8,72], which fits signed eight-bit state. The same tile with U=-110 gives [-142,-78], requiring a wider field.

Select the format at a tile boundary, carry the format/context through the pipeline, and finish that tile without per-add overflow recovery. This removes warning-driven mid-tile promotion from the common path. Carry/borrow isolation remains essential; the certificate must cover every prefix and any extra accepted pipeline work. Reset and threshold timing must match the reference exactly. Do not leak once per tile when the reference leaks once per timestep.

The group certificate uses the worst lane. An outlier can widen a whole group. Regrouping, padded lanes, weights following new neuron assignments, metadata fetches and draining contexts are real costs. Checking at larger boundaries amortizes control but gives looser ranges; smaller tiles tighten bounds but add migrations and partial reductions. A tile-width sweep is necessary.

This is membrane-aware only when the actual U participates in the decision and representation. Certifying a current chunk that starts at zero is current-range-aware, even if its output is later added to a membrane.

### 5. Consider six-bit fields only with their reduction cost included

For int4 weights and a zero-based current chunk, four contributions lie in [-32,28], so eight six-bit fields can fit in 48 bits. Two inputs across eight output fields offer sixteen contribution slots per DSP cycle. Sixteen int4 contributions lie in [-128,112], allowing six eight-bit fields instead. These are analytically safe bounds for the stated chunks, not implemented hardware measurements.

Shorter chunks require more partial-sum reductions, state accesses and scheduling. Actual membrane U shifts the entire range and can disqualify a narrow format. Six-bit packing is an optional extension to screen, not a demonstrated 2x system gain.

## The strongest static competitor

Sixteen int4 contributions already fit signed eight-bit current fields, independently of membrane or input sparsity. A fixed two-input/six-lane implementation using those chunks could capture the 12/8 packing gain without adaptive control. The previously trained digits models have still tighter proven current bounds. That improved static architecture must be included.

The int8 bound for sixteen unrestricted contributions is [-2048,2032]. It needs twelve bits; six eight-bit fields cannot support it with the same unrestricted range. Comparing our int4 packing with original FireFly int8 combines a precision change and an architecture change. Evaluate an equally quantized FireFly reconstruction and report quantization accuracy separately. Exact packed arithmetic preserves its chosen integer reference; it does not make int4 weights equivalent to int8 weights.

Membrane-aware selection needs to beat fixed per-layer/group widths and current-only segmented packing, not merely a uniformly wide baseline. A high observed narrow-state percentage alone is insufficient evidence.

## Quantitative break-even screen

For a proposed two-input engine, eight-, twelve- and sixteen-bit fields provide 12, 8 and 6 contribution slots per DSP cycle respectively. Let q8 and q16 be the fractions of serviced work at those widths; the remaining fraction uses twelve-bit fields. These are work fractions after grouping/padding, not just percentages of neurons.

Let r be candidate/reference DSP clock ratio, p the fraction of the equal DSP budget unavailable for the modeled work because of extra support/reservation, and h additional non-overlapped service time normalized to the ideal reference compute time. Do not count the same wide work again in p or h. With matched useful lane/input utilization and ideal pooling, the normalized compute speed ratio is:

    S_compute = r(1-p) / [1 - q8/3 + q16/3 + h]

This is a screening model, not a cycle-accurate FireFly reproduction. It excludes memory/bandwidth limitations and differences in neuron-update cost, which must subsequently be modeled. Inadequate weight bandwidth, fragmentation or bubbles make the result worse. Better sparsity utilization must be justified separately rather than silently assumed.

- All work eight-bit, equal clock, no overhead: 1.50x packing-only ceiling for this 8/12/16-bit family.
- 80% eight-bit work, 20% twelve-bit, no overhead: 1.364x.
- Same width mix, 5% clock loss, 5% DSP reservation, h=0.03: 1.182x.
- Same width mix, 10% clock loss, 10% DSP reservation, h=0.05: 1.034x.
- Only 50% eight-bit work with those larger costs: 0.917x, a regression.
- 80% eight-bit, 10% twelve-bit and 10% sixteen-bit with those larger costs: 0.992x.
- All work eight-bit at half the reference DSP clock, otherwise ideal: 0.75x.

Every percentage above is a hypothetical sensitivity assumption, not a measured workload statistic. For a provisional 20% compute-speed target, r=0.95, p=0.05, h=0.03 and no sixteen-bit work require more than 83.375% of work to execute in eight-bit groups. This is a proposed engineering decision threshold, not a publication requirement.

There is a concrete certificate-cost trap. A six-output tile with sixteen inputs contains 96 contribution slots. The ideal four-output/two-input reference needs 12 amortized DSP-cycles, while six-output/two-input packing needs 8. Only four cycles of savings are available. If a shared checker takes six unhidden cycles per tile, the candidate needs 14 cycles and the ratio becomes 12/14=0.857x, before seeding or migration. This uses amortized full-lane service across multiple groups; a standalone six-output fixed-four job can incur additional padding. The comparison must not count padding only against the baseline.

The safe U interval can be precomputed as [-2^(b-1)-L, 2^(b-1)-1-H], replacing runtime addition by comparisons. Checks could be parallel or overlap work on other contexts, with their area/buffering charged. Larger tiles amortize checks but widen current bounds and reduce narrow eligibility. A low h cannot simply be assumed for short tiles.

If six-bit fields are included, define q6 similarly and subtract q6/2 in the denominator. A hypothetical mix of 30% six-bit, 50% eight-bit and 20% twelve-bit work under the modest overhead assumptions gives 1.265x. The extra format/reduction overhead must be added; this example does not establish that the extension pays.

These are compute ratios. In a simple non-overlapped example where improved arithmetic accounts for 60% of baseline latency, even a 1.5x compute gain yields only 1/(0.4+0.6/1.5)=1.25x end-to-end. For overlapped memory/compute pipelines, use the actual bottleneck/roofline model instead. Peak packing does not establish lower energy or better burst-tail latency.

## Exactness, novelty and decision gates

Bound-certified width changes need no mantissa truncation and can preserve IF/LIF states with hard or subtractive reset, provided integer leakage, threshold, reset, update order and wide range match the reference. Threshold crossing by itself does not permit saturation or dropping later inhibitory inputs. Even a guaranteed future spike does not generally allow discarding contributions under subtractive reset, because the residual membrane matters.

[DSP-Packing](https://arxiv.org/html/2203.11028v1) already covers packed addition for SNNs and discusses dynamic packing. [SDV/BSEG](https://arxiv.org/html/2606.11065v1) covers exact arithmetic packing with spill/segmentation techniques. Neither generic packing nor generic segmentation should be presented as new. The possible contribution is a cheap, SNN-specific certificate/scheduler with a measured advantage over the best static implementation. This search is not a novelty clearance.

Before another substantial RTL run, the necessary evidence is:

1. A legal two-input packed DSP mapping, including signed encoding, actual-U seeding, fixed ONE48 operation and pipeline tags; no hidden extra arithmetic operand or free format conversion.
2. Work-weighted format occupancy and change rates for realistic models, using safe certificates and fixed group layouts as well as an ideal regrouping upper bound. Current toy models cannot support a general win claim.
3. A cost model that includes short-chunk reduction, seeds, weight/state bandwidth, metadata, format changes and worst-case all-wide service. Compare fixed per-layer/group and segmented-current alternatives at the same precision and resource budget.
4. A projected advantage that survives conservative costs. Only then implement the simplest winning variant and measure exact states/spikes, routed clock, throughput, burst tail latency, LUT/FF/DSP/BRAM and power scope.

Recommendation: advance **two-input signed packing plus tile-bound certificates** to that mapping/workload screen. Treat local queues as supporting machinery. Keep membrane awareness only if it adds an incremental benefit over the upgraded static core. A claim that the modified mechanism beats FireFly is currently unsupported.
