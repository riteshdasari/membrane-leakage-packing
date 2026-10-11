# Contribution boundary for the residue frontier

Primary texts were inspected in the preceding contribution audit. This note
does not claim a complete systematic patent/paper search or first-ever status.

[DSP-Packing (Sommer et al., FPL2022), Section VII](https://arxiv.org/html/2203.11028#S7)
explicitly targets SNN additions in a wide DSP adder. Zero guard bits prevent
cross-lane carries and permit exact independent results. General exact packed
SNN addition therefore is not the novelty of this trial.

[Arithmetic Packing (Borntraeger et al., arXiv2606.11065v1,9June2026),
Sections III-C/III-D](https://arxiv.org/html/2606.11065) describes modulo-reference
spill monitoring with external high accumulators and low/high-part handling.
Its conclusion lists real-time workload adaptation as future work; its use of
the word dynamic for signed-input packing is not evidence that it implements
our actual-membrane admission rule. General exact high/low decomposition remains
established. Its MAC/multiplier datapath is not identical to this U+I primitive.

[US10671388B1 (2020)](https://patents.google.com/patent/US10671388B1/en) describes
side-band numeric overflow monitoring and extends arithmetic operations beyond
MACs. This supplies technical prior art, not a legal assessment or freedom-to-
operate opinion. Exact spill recovery is not new merely because a2026paper
describes it.

This trial tests concrete implementation differences: full-range radix128/six
fields versus radix32/eight fields; late versus precomputed high recovery; and
six full-range plus two statically narrow tail lanes with runtime prefix
admission using actual U. It does not alter the integer neuron reference,
introduce rounding or claim a new residue identity. A unique configuration
alone does not establish a strong contribution.

The adaptive candidate genuinely changes consumed lane count6/7/8. Its first
six lanes remain full-range, and its two extra lanes require U8/I8. A prefix
rule preserves order and never truncates a consumed wide membrane. It uses one
fixed residue layout, avoiding a layout-switch mux and shared correction
scheduler. This particular rule requires its own further prior-art comparison;
we have not proven its novelty through absence of an identical keyword match.

Strong claim gates are separate: arithmetic exactness; causal input supply and
work equivalence; timing/resource tradeoff versus both fixed8 recovery versions,
fixed6, hybrid8 and LUT8; full-interval physical activity/energy; representative
model dependence; then contribution distinction from closest prior art. A
negative result at any gate must remain visible. No FireFly hardware, trained
accuracy, board performance or full-neuron-update energy is reproduced here.
