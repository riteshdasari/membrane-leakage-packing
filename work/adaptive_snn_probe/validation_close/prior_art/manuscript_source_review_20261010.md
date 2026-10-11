# Independent source review of the working manuscript

Reviewed `outputs/membrane_leakage_paper_draft.tex`, SHA256 `9740f14f4a2fb39bc7c82173af1c9f3bd8d6cadb9acdd9bb3d9197295c96d06a`, on2026-10-10. Source-only review; no manuscript edits, LaTeX compilation, Torch import, inference or vendor launch. Root already confirmed compilation. Line references below concern this exact snapshot; subsequent root updates may resolve them.

## Outcome

No unsupported priority/absence claim, packing-derived accuracy gain, universal hardware superiority or arithmetic error was found. The paper correctly separates exact declared-integer packing from FP32 conversion, primitive issue counts from accelerator latency, historical signed12 results from current signed16 results, admitted signed9 pairs from full16 fallback, and pending delayed-replay/energy work from accepted resource routes.

The following bounded precision/replication fixes remain useful:

1. **Line114: qualify all-wide bursts by coefficient compatibility.** E1's issue-count advantage requires consecutive available coefficients to match. With unequal coefficients, E1 also consumes one operand per issue. Suggested wording: “Wide bursts with matching consecutive coefficients favor E1's two-lane issue count.” This is the only identified broad behavioral overstatement.
2. **Lines16/35: define adjacency after common filtering.** The executed policies pair the head two operands of the stable, order-preserving **nonzero arithmetic stream**, after bypassing U=0 or beta=0. Therefore two adjacent issued operands can belong to originally nonadjacent neurons. No reordering/search occurs, but the stream boundary should be explicit. Suggested wording: “Two consecutive operands in the order-preserving stream after common zero filtering…”
3. **Line116: refresh E2 status once the pipeline snapshot is finalized.** The source-identical checkpoint retry now has an accepted resource route in `width16/hardware/route12_e2_a1/hardware.json`:340 LUT,88 FF,0 DSP; WNS2.037ns, WHS0.137ns. Its delayed replay and energy remain separate acceptance gates. This is an evolving status correction, not a numerical error in the earlier frozen draft. Retain the original failed attempt and the unresolved historical signed12 diagnostic.
4. **Line71: distinguish sigmoid-transformed parameters from stored trainable logits.** `integer_glif.py` constructs alpha/gamma/tau from their sigmoid values before computing a0/a1. The current formula is correct under that interpretation; explicitly defining it improves replication. Defining effective current I, quantized bias B, reset R, threshold Theta and beta_p would also make the declared conversion independently reconstructable. This is a missing methods detail, not evidence of wrong inference.
5. **Line136: use a complete primary citation for the independent checkpoint.** The exact source is the Kim–Panda visual-explanations implementation, which documents training with BNTT. Avoid leaving it as an unnamed “Public BNTT/visual-explanations” bibliography entry. A replacement is supplied below.
6. **Line123: identify the four access gaps in related work.** UDP2026, Ou2024 dynamic packing, Cui2024 six-signed packing and McKeown2008 should be named/cited in a submission. The full McAllister2009 primary follow-on can also be cited for range-utilization ancestry. Their unnamed collective treatment in this working draft is cautious but insufficiently traceable for final peer review.

## Arithmetic and all-coefficient domain

Equation1's signed16 U and unsigned beta0–256 contract is consistent with the new cores. `floor((beta*U+255)/256)` equals the ceiling for either sign. Its output remains signed16, including beta0/256. The scalar intermediate product bounds are−8,388,608…8,388,352; adding255 fits signed24. Actual DSP intermediates are wider.

For a signed9 pair, A lies in signed25 and x lies in−65,281…65,535, so the stated strict bound−65,536<x<65,536 is valid. The lower spill is only0 or−1. The parity formula, low-byte signed restoration and upper quotient boundary increment are correct. E5 includes all257 legal coefficients; E0 restricts pair admission to beta≥64 but retains the same general scalar domain. The E0 corner thresholds match `beta*u0+255<0`.

The paper now correctly avoids the earlier25-versus27 packing-limit overclaim: conventional layouts need27 or, for the restricted beta range,26 A bits, but the same one-bit spill can reconstruct complete products at stride16. The contribution is the economical leakage decoder and evaluated admission trade-off, not unique feasibility or a generic new exact correction invention.

The E1 fixed split uses Euclidean `U=256h+r`, with nonnegative r, and the exact identity `ceil(beta*U/256)=beta*h+ceil(beta*r/256)`. It is properly presented as a strong constructive baseline. E6's beta128-only and E8's signed9-only caller limits are disclosed; E7 has the same general arithmetic contract. In the abstract, “all new general-core comparisons” would avoid any ambiguity about those restricted controls.

The beta253 constant identity is correct for negative and positive U. Signed18 is sufficient for `3U` over the full16 domain. The draft correctly treats this trained uniform-coefficient model as applicability/negative-control evidence rather than proof that a multiplier is intrinsically necessary.

## Checked numerical claims

- The area table exactly matches the accepted hardware JSONs for E0,E1,E3,E4,E5,E6 at12ns: `(LUT,FF,DSP)` respectively `(71,44,1)`, `(202,79,1)`, `(35,56,2)`, `(13,29,1)`, `(62,44,1)`, `(35,70,0)`. All setup/hold slacks are nonnegative. The E5 resource reductions69.31% LUT and44.30% FF versus E1 are correctly rounded. Fixture accounting is explicitly separate.
- GLIF full-test conversion values94.05% versus94.03%,371 changed predictions,160 becoming correct and158 becoming incorrect match stage2 results/acceptance. The remaining53 changed predictions are wrong in both variants, so “including” is accurate. The stated24,903,680,000 updates and old/new range bounds match that acceptance. This full-test scalar conversion is not presented as a full10,000-image packed hardware execution.
- GLIF64 arithmetic counts, signed9 rate99.0189%,1.0836% E5 penalty versus E1,1.852 useful results per issue and46.0091% fewer issues than E4 match stage3/candidate records. The stronger independent two-lane controls'39,623,132 issue count is retained.
- OTTT64's60/64 classifications per reference,157,286,400 updates, old range−10,220…10,562,53.3389% narrow fraction and55.4999% E5 issue penalty match the accepted result. Its observed stored-state range is also signed16; the old signed12 contract is insufficient. The full10,000-image job was still incomplete at review time, so withholding a final full-run accuracy is correct.
- GLIF representative capture uses262,528 operands and2,176 windows;3.52% weighted coefficient and0.90% coarse-membrane variation,1.0821% sample issue overhead and1.0836% complete-stream overhead match the acceptance. The draft discloses restarts, avoids confidence/full-stream-energy claims, and labels the old OTTT7,335-operand sample as stress activity.

## Verified citation improvement

Youngeun Kim and Priyadarshini Panda, “Visual explanations from spiking neural networks using inter-spike intervals,” *Scientific Reports*, vol.11, article19037,2021, DOI[10.1038/s41598-021-98448-0](https://doi.org/10.1038/s41598-021-98448-0). The [publisher record](https://www.nature.com/articles/s41598-021-98448-0) confirms the authors, title,24 September2021 publication and article number. Its evaluated model is VGG11/LIF on TinyImageNet. The pinned [official source README](https://github.com/Intelligent-Computing-Lab-Panda/Visual-Explanations-from-Spiking-Neural-Networks-using-Interspike-Intervals/blob/178789c74fef72b9c25bd31d65ac598c987e1de9/README.md) identifies the specific public checkpoint as TinyImageNet/VGG11 and links the author weights. The30-step/.99/default recurrence details are verified from that source, without conflating generic paper equations or another BNTT checkpoint.

Suggested LaTeX bibliography replacement:

```tex
\bibitem{bntt} Y. Kim and P. Panda, ``Visual explanations from spiking neural networks using inter-spike intervals,'' Scientific Reports, vol. 11, art. 19037, 2021. \url{https://doi.org/10.1038/s41598-021-98448-0}. Author implementation/checkpoint: \url{https://github.com/Intelligent-Computing-Lab-Panda/Visual-Explanations-from-Spiking-Neural-Networks-using-Interspike-Intervals}, revision 178789c74fef72b9c25bd31d65ac598c987e1de9.
```

DSP-Packing's existing FPL2022 venue is verified by its [primary arXiv record](https://arxiv.org/abs/2203.11028), which lists the32nd FPL2022 conference and DOI[10.1109/FPL57034.2022.00035](https://doi.org/10.1109/FPL57034.2022.00035). No bibliography correction is needed for that venue.

## Acceptance boundary

The working draft remains appropriately conditional. Resource routes and exact arithmetic are supported; complete new delayed replay, physical activity/energy, full OTTT evaluation, BNTT inference and E8 cost ablation still require their own final accepted records. A route pass must not be relabeled a resolved historical simulator diagnostic. First-use priority and complete prior-method equivalence remain unproven because the four access gaps remain.
