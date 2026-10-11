# Matched signed8-current fixed membrane-addition comparison

Against the equally specialized hybrid, the fixed residue implementation changes resources by -23 LUT (-34.8%) and +26 FF (+11.0%), with the same one DSP and saved service clocks. LUTs and registers remain separate tradeoff axes; this does not establish a total-area or energy saving.

This isolated trial closes the operand-domain gap: every cost comparator supports signed11 membrane U plus statically signed8 current I, producing exact signed12 U+I. It retains six ordered lanes, four advancing clocks, stalls, reset cancellation and zero output tails. The fixed residue and adaptive routes are unchanged archived references; only two specialized fixed baselines are newly routed.

The hybrid physically stores four eight-bit currents before its FOUR12 DSP additions; the other two sums are computed in fabric at acceptance. The LUT-only implementation uses eight-bit signed currents in all six fabric additions. The membrane input remains eleven bits and each output remains twelve bits. Ignored tail payloads can be arbitrary.

The archived fixed residue design splits U=128hU+rU and I=128hI+rI. One DSP adds six pairs of unsigned seven-bit residues in eight-bit fields. Each residue sum is at most 254, so no carry crosses into another field. Fabric reconstructs the exact high part hU+hI+carry; in the I8 domain this is hU+carry-sign(I). Thus the DSP computes six low-part additions, while fabric completes the full-width sums.

## Routed core results

Vivado 2025.2, xc7a100tcsg324-1, one thread, 6 ns, identical registered OOC fixture. Core counts exclude 219 fixture FFs. Slice sets overlap. Registered setup/hold and raw-port timing are separate.

- I8 hybrid: FOUR12 DSP plus two LUT sums: 66 LUT / 236 FF / 1 DSP; WNS +1.840 ns, WHS +0.103 ns; registered timing passes; 110,596 saved service clocks.
- I8 LUT-only: six fabric sums: 79 LUT / 304 FF / 0 DSP; WNS +1.807 ns, WHS +0.101 ns; registered timing passes; 110,596 saved service clocks.
- Fixed residue: six DSP low sums plus fabric high recovery: 43 LUT / 262 FF / 1 DSP; WNS +2.141 ns, WHS +0.130 ns; registered timing passes; 110,596 saved service clocks.
- Shared adaptive exact correction (archived I8 V3): 147 LUT / 268 FF / 1 DSP; WNS +0.108 ns, WHS +0.132 ns; registered timing passes; 110,710 saved service clocks.

Under the separately declared raw-port budgets, boundary hold slack is -1.092 ns for the hybrid and -1.138 ns for LUT-only. These boundary checks do not pass; the passing timing statements above apply to the registered OOC fixture. A board interface and clock network have not been validated.

For the fixed residue core relative to each newly specialized baseline:

- Versus I8 hybrid: FOUR12 DSP plus two LUT sums: -23 LUT / +26 FF / +0 DSP. This is a resource tradeoff; no total-area or energy ordering is measured.
- Versus I8 LUT-only: six fabric sums: -36 LUT / -42 FF / +1 DSP. This is a resource tradeoff; no total-area or energy ordering is measured.

All fixed implementations accept six available updates per issue and use the same saved service clocks. The current shared adaptive implementation still costs +104 LUT and +6 FF versus its own fixed residue reference, with the same DSP count and 114 extra saved clocks. This comparator study does not create an adaptive throughput or accuracy benefit. Energy per completed update remains unmeasured.

## Exactness and workload contract

Four full RTL suites check 11,579,320 repeated scalar outputs across four implementations, with and without output backpressure. All retirement files must be byte-identical to the archived profile1 fixed result, including physical clock columns. Eight SNN replays match the saved states, spikes, spike counts and sampled classes. This is repeated checking, not exhaustive six-neuron combinations.

Stress inputs use the same modular signed8-current projection as the archived profile1 trial. This changes the stress domain and is not lossless requantization of arbitrary I11 inputs. Saved model operands remain unchanged: 635,904 scalar pairs in 110,592 windows, 144 images across three seeds. The weight certificate bounds all permitted binary-spike currents in [-100,70], which fits signed8. Other weights, extra currents or nonbinary spike encodings require their own certificate.

SNN leakage at beta231, threshold and subtractive reset execute in Python; U+I executes in RTL. The leakage differs from original training, so equivalence is to the declared saved integer reference, not preservation of original trained-model accuracy.

## Contribution boundary

Exact guarded SNN addition packing is already described in [DSP-Packing, Section VII](https://arxiv.org/html/2203.11028#S7). Packed low-part DSP arithmetic with exact external high-part handling also appears in [Arithmetic Packing, Sections III-C/III-D](https://arxiv.org/html/2606.11065). Our fixed candidate is a particular six-lane unsigned-residue mapping with direct high reconstruction and a certified current-width specialization. Its arithmetic decomposition is not established here as new, and absence of an identical configuration does not prove novelty.

This local primitive comparison measures resources, OOC timing and RTL service. It does not measure total weighted area, energy, board Fmax, memory supply, arrival-burst latency or complete SNN-update latency. No FireFly accelerator RTL is reproduced. Static I8 specialization and fixed six-lane mapping are not runtime adaptation.

Evidence: [specialized RTL](<C:/Users/Ritesh/Documents/Codex/2026-10-08/oka/work/adaptive_snn_probe/i8_fixed_trial/guard_add_i8_fixed.sv>), [two new routes](<C:/Users/Ritesh/Documents/Codex/2026-10-08/oka/work/adaptive_snn_probe/i8_fixed_trial/results/i8_fixed_hardware.json>), [independent audit](<C:/Users/Ritesh/Documents/Codex/2026-10-08/oka/work/adaptive_snn_probe/i8_fixed_trial/audit_notes.md>), [complete manifest](<C:/Users/Ritesh/Documents/Codex/2026-10-08/oka/outputs/membrane_i8_fixed_comparison_trial.manifest.json>).
