# Exact adaptation screen for the shared common layout

The hardware and policy studies use the same operation: six ordered signed11
membranes plus signed11 currents produce signed12 sums. The DSP always adds six
isolated eight-bit residue fields. The only candidate adaptation here changes
the exact high-part correction; this is not variable DSP lane-count packing.

Reproduce this lightweight screen with `screen_common_adaptation.py`. It launches
no HDL tools and pins its script, contract, original oracle, model inputs and
saved weight files in `common_adaptation_policy_results.json`. Original trial
evidence is unchanged.

The screening records below predate the completed selective implementation.
The root has since measured the no-backpressure full-current saved-model RTL
suite: 110,710 shared clocks, 1,008 correction steps, 114 freezes, exact sums,
and four-to-seven-clock physical latencies. Remaining suites, reconstruction
and routes are gated separately. The integrated
`outputs/membrane_selective_correction_trial.md`, once published, is the current
measured conclusion; earlier unfused estimates here remain labeled diagnostics.

## Exact certificates

For each lane, define `rU = U & 127`, `rI = I & 127`, `hU = U >> 7`, and
`hI = I >> 7`. The packed DSP returns `s = rU + rI`, `c = s >> 7` and
`low = s & 127`. The full exact correction is `H = hU + hI + c`, and
the signed12 answer is `128*H + low`.

The first policy is a sign-certified fast path with shared exact fallback.
When both operands fit signed8, `hU = -signU` and `hI = -signI`, hence
`H = c - signU - signI`. Its range is `[-2,1]`, so two signed bits suffice.
This is broader than the original signed7 fast path. Signed7 instead permits
restoring the signed8 sum using the operand-sign parity and sign extension.

The second policy safely copies or reuses high-part work. For signed8 current,
`H = hU + c - signI`. When `c == signI`, **H is exactly hU**, including
membranes wider than signed8. Otherwise H is exactly `hU+1` or `hU-1`.
General signed11 currents still need the full fallback. The strongest simple
candidate is the union of the first policy's signed8 predicate and this direct
high-copy predicate. It consumes actual membrane/current values and the exact
DSP residue carry without moving any DSP field.

The screen exhausted every signed11 operand pair: 4,194,304 pairs, zero
mismatches. It separately checked 16,384 signed7 pairs, 65,536 signed8 pairs,
and 524,288 signed11-U/signed8-I pairs. Another 18,432 packed cases enumerate
all high-part pairs, both low-carry values, each lane and each output-tail count.
These are Python arithmetic checks; the adaptive controller has not passed RTL
simulation, synthesis or routing.

## Saved workload observations

All counts below refer to the existing beta231 addition reference: 635,904
scalar pairs in 110,592 six-value windows across 9,216 records. The saved
sample covers 144 images and three seeds. This is not preservation of the
original trained model's accuracy, nor an arrival-burst latency measurement.

The prior signed7 predicate handles 611,513 pairs, leaving 24,391 corrections.
The signed8 predicate handles 627,273 pairs, leaving 8,631 corrections.
Direct high copy alone handles 604,686 pairs. The union handles **634,896
pairs (99.84%)**, leaving **1,008 exact corrections in 894 windows**.
There are 789 one-correction windows, 96 two-correction windows and nine
three-correction windows; 109,698 windows need no general correction.

The full-domain worst case still has six exceptions in every window. The
controller must support it exactly with backpressure, even though it does not
occur in this saved model stream. A shared unit saves instantiated arithmetic
only if the selection, retained operands, valid masks and output assembly do
not cost more than the removed units.

Under the explicit arithmetic assumption of one six-lane base slot plus one
added correction slot per exception, the union yields 111,604 service clocks
including four startup/drain clocks. This is 0.91% more clocks than fixed
hybrid6/LUT6 (110,596), and 30.04% fewer than native4 (159,540). Two shared
correctors give 111,499 modeled clocks, only 105 fewer; this does not justify
the second unit from the trace alone. These figures omit actual pipeline and
controller timing and therefore are neither RTL results nor physical latency.

An ideal admission queue with one correction unit and capacity for six jobs
accepts all offered saved windows without an admission stall; the maximum
modeled backlog is three jobs. This demonstrates low correction demand, but
does not prove a one-window-per-cycle implementation. DSP availability, job
tags, ordered output retention, dependency barriers and queue-ready timing
are excluded. A scheduler cannot deliver more than the fixed6 kernel's six
ordered results per supplied window at the same clock.

## Strong static alternative from the same weights

This screen independently sums the negative and positive weights for every
neuron in all six saved weight matrices. For arbitrary incoming binary spikes,
the current lies between those two sums. The aggregate extrema are `[-100,70]`:
every current is safely signed8, independently of the sampled trace and of the
leakage coefficient. Every saved record also satisfies its individual neuron's
bound. The weight files and bounds are pinned in the JSON.
The standalone certificate is archived as `common_i8_current_bounds.json`,
with SHA256 in the policy results. It also records the SHA256 of the existing
bound script and bound artifact. The earlier unfused service screen remains
archived as `common_adaptation_policy_results_pre_fused.json`.

Therefore a separately declared signed11-U/signed8-I implementation can use
`H = hU + c - signI` statically without an I8 detector or a general-current
fallback. It is an essential model-specific comparator for any runtime adaptive
correction claim. The generic signed11-U/signed11-I API still needs fallback;
these two contracts must not be silently mixed. A fixed hybrid and LUT6 must
receive the same known-current specialization if used in that comparison.

The fixed common-layout reference likewise remains essential. Its precomputed
five-bit `hU+hI` metadata may need fewer registers than an adaptive shared
corrector that must retain both four-bit high operands. Rare exceptions alone
are not a resource or power result. LUTs, flip-flops and DSP count must be
reported together, and switching-power claims need actual activity evidence.

## Temporal cache check

Among 616,032 consecutive-timestep pairs for the same neuron, hU repeats
592,962 times, hI repeats 519,038 times, and both explicit keys repeat 505,929
times. The high sum repeats 515,880 times, but determining equal sums without
the keys would itself require arithmetic or another certificate. The first
timestep additionally needs initialization for 19,872 neuron identities.

A plain cache stores two four-bit keys plus a five-bit high sum: 13 payload bits
per live neuron, before valid/ownership bits, addressing and memory ports. A
single live image has 138 neurons, so 1,794 payload bits suffice if the cache is
reused or invalidated across images. Forty-eight concurrent images need 86,112
payload bits. Summing all 19,872 offline dataset identities gives 258,336 bits
only if all 144 images coexist; that is not a measured hardware footprint.
The cumulative 19,872 cold starts across replays remain valid. Reusing existing
state storage could change the incremental cost, but it would also broaden
this simple kernel into a state/memory design. The cache misses far more often
than the union certificate, needs memory ports and update rules, and is not the
recommended next RTL candidate.

## Conditional width scope

A real signed13–15 domain permits a regular alternative: six eight-bit narrow
fields versus three sixteen-bit full fields, with common starts 0, 16 and 32
using narrow logical order `[0,3,1,4,2,5]`. Its fair full-range comparison is
three DSP additions plus three LUT additions and LUT6 at the same declared
width. The current beta231 traces and bounds do not require that wider domain;
padding them is not a demonstrated SNN advantage.

An independently declared leakage family can require wider membranes. For
maximum negative current N and leakage `ceil(beta*U/256)`, the lower invariant
`-ceil(256*N/(256-beta))` gives a legitimate range certificate. With N=100,
beta248 gives -3200 (signed13), beta252 gives -6400 (signed14), and beta254
gives -12800 (signed15), whereas beta231 gives -1024 (signed11). A leakage
sweep would require fresh exact neuron traces and references, its own upper
bounds, and explicit accuracy qualification. No width or leakage scope was
changed by this screen.

## Coordinated recommendation

Finish measuring the fixed common-layout V0/V1 reference first. If its cost
leaves a plausible niche, the one next adaptive candidate is signed8 fast
recovery plus carry-certified high copy with **one shared exact fallback**.
Keep whole-window backpressure and ordered output assembly simple rather than
assuming an unmeasured overlap queue. Root must agree an explicit variable
latency/stall contract before adaptive RTL is written. Compare its total cost
with the generic fixed common reference and the strong fixed hybrid/LUT
kernels, and separately compare any known-current specialization fairly.

This candidate offers a strong numerical/adaptation observation, not a proven
hardware win. It also broadens the original title toward membrane-aware exact
correction for packed DSP addition; retaining a claim of adaptive lane packing
would require an actual change in DSP operation count or lane arrangement.

## Approved fused-output controller model

The root and hardware task subsequently agreed on four matched variants:
V0 fixed full-current correction, V1 shared full-current correction, V2 fixed
signed8-current correction, and V3 shared signed8-current correction. The
shared variants use the union certificate above. Static-current V2/V3 require
their signed8 input contract rather than silently accepting arbitrary I11.

The first bad lane is corrected in the ordinary output stage. A window with
`k` bad lanes therefore freezes the whole pipeline for only
`max(k-1,0)` additional clocks. Remaining bad lanes are corrected in lane order,
with outputs retained until the window is complete. This is the agreed
controller model; RTL simulation must verify its exactness, stalls and latency.
An independent Python control model checks ordered acceptance/retirement through
three internal stages and an output register. It consumes an old valid output
independently of a new window's correction freeze, avoiding duplicate retirement.

For continuous input, `out_ready=1`, and six-wide supplied windows, the exact
saved exception histogram gives **114 extra frozen clocks**:
`96*(2-1) + 9*(3-1)`. V0/V2 predict 110,596 service clocks; V1/V3 predict
**110,710**. That is **0.103% more clocks than fixed6** and 30.61% fewer
than native4. The predicted clock count is `requests + 4 + sum(max(k-1,0))`,
not a measurement. Input gaps, output backpressure, source-memory service and
dependent neuron scheduling require their own accounting.
The control model gives saved shared-variant latency counts of 110,288 requests
at four clocks, 270 at five, 30 at six and four at seven. A request can wait for
earlier windows' correction stalls, so its latency is not determined by its own
bad mask alone. These remain control-model observations rather than RTL results.

This fused model supersedes the earlier non-overlapped extra-slot estimate
for the agreed RTL candidate. The earlier estimate is retained and labeled
in the JSON and notes so the two assumptions cannot be confused.

Adversarial windows retain exact outputs even when all six lanes are bad.
Examples include `(U,I)=(1023,1023)` for the full-current contract,
`(1023,127)` for signed8 current, and `(-1024,-128)` for signed8 current.
Each sustained window then requires five extra frozen clocks: one six-neuron
window per six physical service cycles, approaching one result per clock.
A 64-window fully bad burst predicts `64 + 4 + 64*5 = 388` clocks. Wide
membranes with zero current instead use exact high copy and need no extra
correction clocks. These are independent arithmetic/controller-model tests,
not arrival-burst latency evidence.

“Avoiding general correction” refers to which runtime path is selected. It
does not prove lower power or fewer total LUTs/flip-flops. The shared unit's
operand mux, bad masks, retained metadata, global stall control and output
assembly must be included in the routed implementation. Fixed6 still sets
the minimum supplied-window issue count at the same clock.
