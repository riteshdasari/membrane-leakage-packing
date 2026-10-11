# Mentor briefing slide notes

## 1. Exact adaptive DSP packing for SNN membrane leakage

This briefing begins with the neuron operation, then explains runtime packing and its exact decoder. The retained contribution concerns membrane leakage multiplication. Earlier accumulation and overflow candidates appear in the archived conversation, but they are not the measured contribution in this paper.

Source: current manuscript and release evidence index.

## 2. Leakage inside a neuron update

A leaky integrate-and-fire neuron stores membrane potential U. Leakage decays the previous membrane. Input current charges it, and threshold/reset rules produce the next state and spike. Different source models order these steps differently. The evaluation adapters preserve each original ordering. Only the highlighted leakage primitive has measured FPGA costs.

Sources: paper Sections II and IV, original GLIF/OTTT/TinyImageNet source manifests.

## 3. The exact integer contract

Beta is an integer Q8 coefficient code. Its effective leakage factor is beta/256. Ceiling rounds toward positive infinity, so ceil(-1.5) is -1. The circuit preserves this declared integer operation. Converting an original floating neuron to integer units is separate and can change predictions.

Sources: domain_acceptance_glif_v2.json, paper Equation 1 and model summaries.

## 4. Runtime admission uses actual membranes

Admission checks actual values, not only configured operand types. Two small membranes with the same coefficient share a DSP issue. A wide membrane or coefficient mismatch causes an exact singleton. The membrane remains stored at 16 bits. The returned count determines source advancement.

Source: rtl/leak_core16.sv, E5 generate branch and take expression.

## 5. Worked stream and source advancement

This example uses five ordered operands. The source advances by 2, then 1, then 2, preserving the unconsumed next operand. Results are -1,3,117,-1,4. Three DSP issues replace five scalar issues in this toy. Fixed full-domain packing also uses three here, so this example illustrates mechanics rather than a universal fixed-packing win.

Source: examples/run_examples.py, independently computed integer ceilings.

## 6. A compact multiplicand layout

The lower membrane receives a 256 bias and occupies nine low multiplicand bits. The upper signed membrane begins at bit 16, leaving seven zeros between them. This fits the 25-bit DSP input. The offset C removes the bias after multiplication and supplies both ceiling offsets. A signed borrow can cross the product boundary.

Source: paper Equations 2–4 and leak_core16.sv packed9.

## 7. The low product can borrow one bit

The lower term x can be negative, but its bounded range permits at most one negative borrow. The upper field then equals y minus that borrow. The known odd/even bit of y recovers the borrow with an XOR. This enables a small rounded-result correction instead of general spill reconstruction.

Sources: exhaustive stage3_algebra.json and manuscript decoder proof.

## 8. Negative-borrow example

For membranes -3 and 5 with beta 128, x=-129 and y=895. The lower quotient byte 255 becomes -1 when the borrow correction subtracts 256. The upper field 894 still has quotient 3. The independent integer ceilings agree with both results.

Source: examples/run_examples.py.

## 9. A byte-boundary correction and wide fallback

The pair (-256,1) with beta 1 exercises the upper correction boundary. A borrow changes upper field 256 to 255, so restoring it increases the upper quotient from 0 to 1. Separately,381 with beta 78 lies outside signed9. E5 computes 117 in a wide singleton. Unsafe narrowing would produce -39.

Sources: portable examples and GLIF capture unsafe-wrap check.

## 10. Counted core and external source

The measured core includes range tests, coefficient equality, operand selection, the DSP, quotient correction and the elastic interface. Its source queue, operand memory and common zero filter remain external. Core latency is two advancing edges without stalls. Neither source integration nor complete-neuron latency has been measured.

Sources: hardware/route12_e5_a0/hardware.json, rtl/timing16.sv, manuscript Figure 1.

## 11. Strong controls execute the same operation

All general controls compute the same signed16 leakage contract. E1 retains full-domain pairs using DSP residue products and fabric high parts. E3 uses two scalar DSPs, E4 one, and E7 uses general LUT arithmetic. E6 is legal only for half leakage. E9 supports the 33 trained GLIF coefficient codes using shared add/sub logic. These are matched constructed primitives rather than reproduced FireFly accelerators.

Sources: route and energy manifests.

## 12. Exactness and protocol validation

Exhaustive arithmetic checks cover every stated narrow pair and full-domain scalar/split case. Native RTL checks also verify consumption, ordering and held outputs under stalls. The added GLIF constant control passes all 65536 signed16 values for each of its 33 coefficients and the entire representative workload, both stalled and unstalled.

Source: stage3_algebra.json, domain_acceptance_glif_v2.json, native receipts, E9 independent_readiness_native_only_a0.json.

## 13. Public neuron model benchmarks

GLIF uses a full 10000-image conversion reference but 64-image packed feedback. OTTT uses full 10000-image packed feedback. The independent TinyImageNet model uses a predeclared 64-image subset. Exact agreement refers to packed versus scalar integer states/spikes/logits. Floating-to-integer conversion changes some network predictions, and those changes are reported separately.

Sources: stage2_acceptance, stage3_results, benchmark_acceptance, bntt_acceptance.

## 14. Selected core resource trade-offs

Bars show core LUT counts at selected matched 12 ns routes. The common 94 fixture FFs are excluded from these core resources. E5 and E1 both use one DSP. E3 uses two DSPs. E7 and E9 use zero DSPs. E9 is one shared implementation covering all trained GLIF coefficient codes, not a lower bound for every possible constant design.

Sources: selected hardware.json receipts and E9 hardware/route12_a0/hardware.json.

## 15. Representative GLIF dynamic energy

Bars show representative GLIF fixture dynamic energy per scalar operand. Every compared engine receives the same declared operands. E5 uses 21.599 pJ, E1 fixed split 55.308 pJ, one-DSP scalar 24.648 pJ, two-DSP scalar 21.371 pJ and general LUT 124.198 pJ. The independently audited GLIF constant control uses 96.758 pJ. Energy excludes chip static power, operand memory and whole-neuron integration.

Sources: explicit selected power map, physical audits, E9 independent_readiness_full_a0.json.

## 16. Pairing opportunity depends on the workload

These values show E5 extra leakage issues relative to fixed E1. GLIF small membranes allow nearly full pair occupancy, whereas the wider OTTT and TinyImageNet streams cause many singletons. Leakage issue counts do not establish complete-network runtime or burst latency.

Sources: stream profiles and Table 2.

## 17. Constant leakage defines an important negative case

Half leakage has a cheap exact shift control. It beats E5 on OTTT energy. The TinyImageNet coefficient 253 also has an exact shift/add identity, although its hardware and energy remain unmeasured. This bounds the useful conditions for a general DSP primitive.

Sources: OTTT representative accepted closure and BNTT exact constant check.

## 18. Specific novelty and established ingredients

Operation packing, actual-value narrowness detection and signed correction have established ancestry. The specific contribution is the compact exact rounded-leakage decoder integrated with actual-membrane admission and a wide singleton contract. The available review has not identified an equivalent implementation, but three original full methods remain unavailable. A worldwide first-ever claim is not established.

Source: paper related work and readiness review.

## 19. Paper recommendation and remaining limits

The evidence supports preparation of a focused circuit submission. The paper should report exactness, measured resources, conditional energy benefits and negative cases. It should avoid claims about a complete accelerator, board energy, improved accuracy or universal burst latency. Reviewers determine the significance of the contribution and acceptance.

Source: current paper and readiness report.

## 20. Mentor handoff and reproduction

The public repository packages the paper, slides, executable examples, research-authored source archive, lightweight evidence receipts and user-facing conversation export. Large weights, datasets and vendor artifacts remain external. The reading guide helps the mentor assess the final mechanism without following every discarded experiment.

Source: README and docs/REPRODUCIBILITY.md. AI disclosure: OpenAI Codex assisted RTL, software, evidence review, drafting and slides. X is the author placeholder.

## 21. Appendix: exact decoder equations

The lower quotient takes product bits 15:8 as an unsigned byte and subtracts 256 times the recovered borrow. The upper quotient interprets bits 32:24 as a signed9 value and adds 1 only if the borrow exists and product bits 23:16 are 255. Bits denote positions in the two-complement product. The parity reference needs only coefficient bit 0 and upper membrane bit 0. Source: manuscript Equations 5–6 and examples/leakage_reference.py.

## 22. Appendix: the exact fixed split reference

Fixed E1 writes U = 256h + q, where q lies between 0 and 255 and h = floor(U/256). It computes beta times h in fabric and packed beta times q in the DSP. Since beta times h is an integer, ceil(beta U/256) = beta h + ceil(beta q/256). For U = 381 and beta = 78, h = 1 and q = 125, giving 78 + 39 = 117. For U = -3 and beta = 128, h = -1 and q = 253, giving -128 + 127 = -1. It preserves full-domain pair occupancy but pays for the high-part arithmetic. Source: manuscript fixed control equation and leak_core16.sv E1 split branch.
