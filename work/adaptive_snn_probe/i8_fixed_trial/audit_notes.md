# Independent audit of the signed8-current fixed trial

This audit does not modify a datapath, fixture, testbench, checker or archived
result. Root runs all heavy tools. The static audit, independent full
functional evidence audit and both independent routed evidence audits are
complete. The publisher and final manifest remain owned by root.

## Declared operation and specialization

Valid lanes compute signed11 U plus a statically signed8 I, represented by a
sign-extended value on an 11-bit input lane. The exact result spans [-1152,1150],
so a signed12 output remains necessary. Arbitrary signed11 currents outside
[-128,127] are outside this contract. Taking input bits [7:0] is correct only
under that invariant, and is not lossless conversion of arbitrary I11 data.

The frozen new source `guard_add_i8_fixed.sv`, SHA256
`1dbc500f27eb02f963474698ce754d87c5ed23ff1c9c9885282cca5d9f733420`,
contains a physical specialization. Hybrid E2 stores four 8-bit currents in
32 registers and sign-extends their bit7 into each FOUR12 DSP field. The two
LUT lanes sign-extend each current from bit7. LUT E3 sign-extends bit7 for all
six additions. Every membrane operand retains all 11 bits and every sum all
12 bits. No timing constraint supplies or invents an I8 relation.

The static current-domain certificate is justified for its pinned integer
weights and binary spikes by summing the negative and positive weights of
each neuron independently. Its bounds [-100,70] fit I8. That proof does not
automatically apply to unrelated weights, nonbinary spikes or added currents.

## Arithmetic and pipeline invariants

FOUR12 isolates four modulo4096 sums. Signed extension and the declared
result range make each modulo result the exact signed12 sum. E2's last two
and E3's six LUT sums are captured at acceptance, then advance through two
further data registers before the common output register. The DSP branch has
acceptance data registers, DSP input registers, DSP P and the output register.
Both therefore retain the same four preceding advances to handshake as the
frozen retimed cores.

The common controller, count pipeline and output masking mechanically match
the frozen retimed E2/E3 source. `advance = !out_valid || out_ready`; every
pipeline stage and the DSP CE pause together when a valid output is stalled.
Reset has priority and clears valid/count/data and all internal data stages.
Each nonempty accepted request consumes all available lanes, in the existing
order. Unavailable binary tails are masked to zero at output and cannot
interfere with valid lanes. The declared available range remains 0..6.

The frozen residue reference V2 has exactly the same external arithmetic
domain and service contract. It sums six unsigned7 residues in eight-bit
ONE48 fields, then recovers each signed high part in fabric as
`H = hU + carry - sign(I8)`. The result is exact, but these are six residue
additions in the DSP plus fabric high recovery; they are not six full-width
membrane additions performed solely inside the DSP. This reference has a
fixed layout and no adaptive controller.

## Fair hardware fixture

The new fixture SHA256
`6300175f4058b534f401685eb6aaf17987fae2f61b8d94a32b95d5f3e396bcd0`
preserves the existing 138 launch and 81 capture FFs, including the unused
upper current input bits. These 219 FFs are measurement fixtures and must be
excluded from reported core counts. They are not a production ready/valid
adapter and do not change the functional kernel's latency contract.

The route Tcl SHA256
`a6b2ecaebdbbe2739a497245b5ae4c2a8055843638d39241c1e7951ad3312833`
retains xc7a100tcsg324-1, a 6ns target, one thread, the same OOC clock source
and core hierarchy boundary. It reports registered setup/hold before adding
raw-port boundary timing. Boundary hold and board timing must remain distinct
from registered OOC closure. Occupied slice sites overlap between core and
fixture and cannot be subtracted as additive counts.

## Evidence and interpretation requirements

The final functional cohort must pin all sources and stimuli, validate the
same full stress projection and unchanged saved model as the archived I8
profile, and compare complete fixed retirement rows including physical clocks.
It must include I8 extrema, full U11 values, poison tails, source/sink stalls,
reset cancellation and the actual four-advance invariant. The modular stress
current projection changes the stress domain; saved model operands must not
be projected or otherwise changed.

Saved SNN replay can establish equality to the saved beta231 integer reference
when RTL performs addition and Python performs leakage, threshold and reset.
It does not establish original trained-model accuracy or full RTL neuron
equivalence. Fixed LUT, fixed hybrid and residue implementations have the same
exact output contract; accuracy is not a differentiator here.

Report LUT, FF and DSP counts separately at matched six-lane service and
timing. A LUT improvement with more FFs is a resource tradeoff, not an automatic
total-area or energy win. Static I8 specialization is not adaptation. Exact
packed addition and external high recovery have prior literature; this audit
does not establish first-ever novelty. It supplies no switching, power, burst
arrival, state-memory or complete accelerator claim.

## Completed independent functional audit

`audit_i8_fixed_trial.py --functional` completed with exit0. It imports no
experiment checker or arithmetic oracle, launches no HDL tools, writes no
evidence files, and streams stimuli and retirement rows with bounded buffers.
All eight frozen functional source pins and the saved-model current-domain
certificate and its inputs were rehashed. The auditor independently verifies
the stress current projection against original I11 source text, preserves U,
frame headers and gaps, and verifies unchanged saved-model operands.

All four full cohorts pass for all four fixed implementations. The stream
audit checks 11,579,320 repeated scalar outputs, with zero arithmetic, ordering,
tail masking or physical clock mismatches. Every complete retirement file is
byte-identical to the archived fixed residue V2 result, including acceptance
and retirement clocks. These are repeated stress/model checks rather than an
exhaustive multi-neuron input-space proof. Each variant in each cohort also
reports the 12 passing exact extrema/tail prelude cases; these directed cases
are additional to the scalar-output count.

The measured service is identical across all four fixed variants:

- Full stress, no external backpressure: 811,511 scalar pairs in 136,591
  requests, 137,454 service clocks; every physical latency is four clocks.
- Full stress with backpressure: the same pairs and requests, 187,826 clocks,
  physical latencies four through seven; input/output stall checks are
  39,285/41,305 for each variant.
- Unchanged saved models, no external backpressure: 635,904 pairs in 110,592
  requests, 110,596 clocks; every physical latency is four clocks.
- Unchanged saved models with backpressure: the same pairs and requests,
  151,549 clocks, physical latencies four through seven; input/output stall
  checks are 31,977/33,471 for each variant.

The actual four-advance invariant, source stability while blocked, stalled
output retention, reset cancellation and zero-available behavior are asserted
by the frozen TB. Every full run contains its RTL PASS marker. No correction
steps or internal correction freezes are present in these fixed variants.

The eight saved SNN replay records pass their source/output/reference hash
audit. All report zero state and spike mismatches, matched spike counts and
classifications, 48 images per seed for three seeds, and the same 635,904
updates. The audit rehashes their functional suites and saved inputs/outputs;
it does not rerun NumPy reconstruction during routing. Their conclusion is
equivalence to the saved beta231 integer reference, with the earlier trained
accuracy and complete-neuron limitations retained above.

These findings close the functional-domain and service fairness gap. The
matched routed resource tradeoffs are recorded below; energy remains unmeasured.

## Completed independent route audit and matched tradeoffs

`audit_i8_fixed_trial.py --routes` completed with exit0. Both rows match all
14 current source/proof pins and the five completed functional/SNN evidence
pins. All synthesis and route artifact hashes, source-bound provenance,
Vivado/part/clock metadata, utilization reports, fixture accounting and
registered/raw-port slack values pass independent read-only checks. The
resumed LUT route also matches the exact resume-helper and synthesis-DCP
SHA256 fields. No HDL or Vivado tools were launched by this audit.

Both new cores pass registered OOC setup and hold at the declared 6ns target:

- Specialized I8 hybrid: 66 LUT, 236 FF, one DSP; WNS +1.840ns and
  WHS +0.103ns. Its core touches 44 slices; the full fixture touches 85.
- Specialized I8 LUT-only: 79 LUT, 304 FF, zero DSP; WNS +1.807ns and
  WHS +0.101ns. Its core touches 77 slices; the full fixture touches 124.

The unchanged fixed residue V2 reference has 43 LUT, 262 FF and one DSP,
registered WNS +2.141ns/WHS +0.130ns, 54 core slices touched and 99 slices
touched by its full fixture. It retains the equal six-lane, four-advance
service already verified independently against both new cores.

Relative to the matched hybrid, fixed residue saves 23 LUT (34.85%) but uses
26 more FF (11.02%) and the same DSP. It also touches ten more core slices
in these placements. Relative to the LUT-only core, fixed residue saves
36 LUT (45.57%) and 42 FF (13.82%) but requires one DSP instead of zero,
and touches 23 fewer core slices. Neither comparison establishes resource
vector dominance or a measured weighted-total-area/energy ordering.

Core slices touched count the set of slice sites containing any core
primitive; they include sites shared with fixture registers. They are not
the sum of independent LUT and FF areas, and exclude DSP-site area. Full
fixture and core slice counts cannot be separated by subtracting the fixture
slice count because those sets overlap. A slice-footprint comparison is
specific to these OOC placements and must not be called total weighted area.

The raw-port boundary hold audits remain negative: hybrid -1.092ns and LUT
-1.138ns. Thus passing timing refers only to the registered OOC fixture.
This is not board closure or a board-ready interface; no measured board Fmax
or frequency extrapolation follows from the positive registered WNS.

The archived adaptive I8 V3 remains 147 LUT, 268 FF and one DSP, with 114
extra saved-model service clocks relative to its own fixed residue V2.
The new matched comparisons do not provide an adaptive throughput, accuracy
or energy benefit. Static current specialization and this fixed residue
layout must continue to be described separately from runtime adaptation.

The read-only publisher review passes its domain, service, resource-vector,
fixture, saved-reference accuracy and novelty claim boundaries. It reports
both hardware tradeoffs and explicitly avoids first-ever or universally
best claims. Exact addition packing and external high-part recovery are
established arithmetic ideas; absence of an identical six-lane configuration
is not evidence that the arithmetic decomposition is new.
