# Exact prefix-capacity generalization screen

This is a light software screen of the same mechanism as current E5: keep eight
radix32 residue fields, equip the first F lanes for full signed11 U, and admit
ordered additional lanes only while their actual U fits signed8. Current I is
statically signed8 throughout. No operand, group order or integer neuron update
changes. F ranges from one to eight; F8 is full-range fixed8. No RTL was changed
and the current six-engine implementation/energy validation remains intact.

The screen reproduces the measured F6 and F8 request and no-output-stall service
counts for both saved and stress streams. Service includes four drain clocks per
dependent group and the existing source gaps. Other F rows are software
predictions, not measured RTL clocks. Model rows retain the 635,904 scalar
updates, 9,216 groups, three seeds and both layers. Stress retains all 524,288
scalar domain pairs plus the same structured contexts, totaling 541,456 updates.

The smallest immediate follow-up is F5: five full-range lanes and three U8 tail
lanes. On these saved traces F5 and current F6 have exactly the same 83,006
requests and 119,870 service clocks, versus fixed8 at 82,944 and 119,808. That
equality also holds separately for every seed/layer cohort. The only extra
requests versus fixed8 are 12 in seed1 hidden-layer groups and 50 in seed2
hidden-layer groups. Output-layer groups incur none. This is an opportunity
within the existing workload, not evidence of broad SNN generality.

Replacing one more seven-bit high base with four bits saves three logical bits
per metadata stage. Across three stages and the final sign-extended output,
F5 exposes 36 fewer logical register bits than fixed8, versus 24 for F6. The
additional potential reduction is 12 bits. These are structural width counts,
not synthesized FF or energy predictions. F5 also requires one more actual-U
predicate and a longer prefix-count selection rule; extra monitor/control
logic and routing can consume the benefit. Its arithmetic still produces exact
nine-bit sums in admitted narrow tail lanes, sign-extended to twelve bits.

The adverse full-domain workload becomes substantially worse: F5 predicts
104,097 requests and 115,049 service clocks, versus current F6 at 87,964 and
98,916 and fixed8 at 67,906 and 78,858. F5 therefore costs 45.89% more service
than fixed8 on this stress stream, versus F6's measured 25.44% penalty. Reducing
F further raises this penalty sharply. F4 also raises saved-model service by
0.5083% and its stress service by 74.59% relative to fixed8. The screen does not
justify pursuing many variants or claiming a universally superior policy.

Six full-range lanes therefore do cap the structural register-saving
opportunity somewhat. One later F5 trial is scientifically justified if the
current routed/energy result establishes a useful tradeoff: compare the same
fixed8/hybrid/LUT baselines, retain the unfavorable stress, and test whether the
extra 12-bit opportunity survives its additional detector/control cost. It
must not replace or interrupt the scheduled six-engine validation. If that
validation lacks a useful measured tradeoff, this small width opportunity is
not enough by itself to justify more hardware optimization.

No throughput, energy, total-area, board, original trained-accuracy or strong
ISCAS claim follows from this screen. The residue identity is established
arithmetic. Novelty of the actual-membrane prefix admission rule and the
significance of an implementation benefit remain separate questions.

Reproduction: run `screen_prefix_generalization.py` with the existing Python
environment. It refuses to overwrite its result. All inputs and the script are
SHA256-pinned in `results/prefix_generalization_screen.json`; each F includes
take histograms and model seed/layer breakdowns. No downloads, packages, model
training, Vivado jobs or existing frozen-file changes were used.
