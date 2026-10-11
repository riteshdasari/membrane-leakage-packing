# Natural U11 comparison

Five new one-advancing-edge implementations accept signed11 U and sign-extended
signed8 I, returning exact signed12 U+I. No rounding, clipping, rescaling,
coefficient change, reordering or hidden wide fallback is allowed.

Engine IDs: 0 adaptive DSP (the earlier E5 policy), 1 fixed8 precomputed-high DSP
(earlier E2), 2 native DSP FOUR12 plus four full-width LUT lanes (earlier E3),
3 full-width LUT8 (earlier E4), 4 the identical adaptive policy using LUT sums.
Adaptive engines guarantee five full-width lanes and admit a contiguous prefix
of up to three U8 tail operands from actual membrane values. A wide tail is
not dropped: the supplier advances only by take and reoffers it next issue.
I always fits signed8. All fixed engines admit available, at most eight.

DSP residue fields use unsigned radix32 residues in eight six-bit fields of
ONE48. The guard sum is at most62, hence no interfield carry. Full high base
is U//32+I//32 in [-36,34], and high after residue carry is [-36,35]; seven bits
are sufficient. Narrow high base [-8,6], with carry [-8,7], fits four bits.
The final concatenations are exact signed12 or signed9, then sign extended.
Native FOUR12 uses four independent signed12 sums, followed by four LUT sums.

Global freeze is !out_valid || out_ready. Every valid output is produced after
one advancing acceptance edge; all count/data/valid registers freeze while
blocked. Synchronous reset cancels pending outputs. Unused output lanes are zero.
take and narrow_mode are descriptive combinational input-side values; mode is
true exactly when an adaptive engine admits more than five. available<=8.

The matched route fixture has183 unconditional launch FFs and107 capture FFs
(290 total), preserved identically for all five engines. Routes use Artix7
xc7a100tcsg324-1, Vivado2025.2, a6ns clock and HD.CLK_SRC BUFGCTRL_X0Y0.
Core LUT/FF/DSP exclude that fixture; occupied slices are sets with overlap.
Routes measure resources and STA only. No new routed SDF replay, energy, board
Fmax, memory bandwidth, host runtime or complete neuron-update result is claimed.

Native jobs must wait for natural_lif_feedback_trial/acceptance.json and
natural_supply2_trial/acceptance.json to pass, then run serially above1.2GiB free.
Routes additionally require residue_frontier_u13_trial/results/ram_retry_progress.json
status all_checks_passed or completed_with_retained_failures, and2.3GiB free.
All executed sources are pinned, never edited; failed attempts are retained.

The native exhaustive suite covers all524288 scalar U11/I8 pairs, structured
packed boundaries, all prefix-failure positions, poisoned unused tails, reset
cancellation and stalled source/output. Four original saved LIF cohorts use
unchanged shift1/shift3 coefficients, thresholds, weights, all360 RNG draws and
first48 images per seed. Actual retired sums feed back into states/spikes/counts
and classes. These are three64-128-10 ANN-to-SNN conversions, not directly trained
SNNs or independent model architectures. Shift1 admits static U8; shift3 has an
all-binary-history U11 bound. No accuracy gain is expected from exact packing.
