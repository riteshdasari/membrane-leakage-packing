# Mechanism contribution and technical readiness

11 October 2026. This independent review reads the current draft, the exact signed16 RTL, saved mathematical validation, the current accepted scope audit, UDP's full-reader inspection receipt, and the three unresolved original-method access records. It does not repeat broad searching, run vendor tools or inference, or change the paper. Input hashes are in the paired JSON.

**The user is right: a research contribution does not require inventing every building block.** A new and useful mechanism can combine known components, provided the combination has a concrete technical distinction, is implemented, and has evidence of a meaningful trade-off. “First ever” is a stronger priority claim than is necessary to present such a contribution. Unavailable originals create a priority risk; they do not automatically erase the implemented result.

**Strongest precise contribution:** an exact rounded-leakage primitive on DSP48E1 that combines a compact stride16 borrow/quotient decoder with actual signed9 shared-coefficient pair admission and exact signed16 singleton execution. Stored state, voltage units, coefficient interpretation and update order stay fixed. This is one integrated contribution, with algebra, implementation and workload evidence supporting it. Fixed E1 splitting is a constructive control, not a separately demonstrated discovery.

## What makes it an actual mechanism

The current `leak_core16.sv` tests both raw operands for sign-extension from nine bits, tests coefficient equality and two-operand availability, and selects packed versus scalar DSP operands internally. It produces a one/two consume count and maintains a common elastic ordered interface. Those are implementable decisions, rather than a software-preassigned packing label. Source re-presentation, zero filtering and memory integration remain outside the counted primitive.

The operating domain is signed16 U and unsigned Q8 beta0..256, with `L(U,beta)=ceil(beta*U/256)`. For an admitted pair, `A=(u0+256)+(u1<<16)` lies between -16777216 and16712191 and fits the DSP48E1 signed25 input. With `x=beta*u0+255`, `y=beta*u1+255`, `P=x+(y<<16)`, the lower field is bounded by -65281..65535. Hence only a zero spill or a negative borrow of one occurs. The parity reference recovers that borrow; the lower quotient uses one sign/borrow bit plus eight extracted bits, and the upper quotient needs an increment only at the indicated all-ones-byte boundary. Its signed9 quotient range remains legal, including beta0/256 and both operand endpoints.

**No fatal algebra problem was found.** The retained unchanged narrow-pair proof covers67,371,008 cases, and the signed16 scalar/split checks cover16,842,752 cases. These accepted checks are reused, not presented as newly run. The compact decoder can be the technical specialization, but exact full products are also recoverable from P and the same borrow. Therefore the straightforward26/27-bit nonoverlapping layouts are comparisons, not a universal input-width impossibility result.

## Novelty boundary

Brooks--Martonosi already provides actual-value admission, packing and ordinary full-width execution. DSP-Packing and Arithmetic Packing provide signed contamination and modulo spill recovery; XtraMAC provides runtime datatype packing. UDP's complete inspected methods select packing from configured widths and generate parameterized hardware, while retaining runtime sign and most-negative corrections. Those methods did not describe this signed16/signed9 rounded-leakage admission conjunction. Ou, Cui and McKeown remain unread originals, so this review cannot exclude equivalent equations or policies in them.

Calling a generic operand detector “membrane aware” does not itself add novelty. The defensible difference is the **complete exact leakage contract and inexpensive implementation**, rather than just the name of U. Conversely, old arithmetic ingredients do not make the entire mechanism invalid. A useful circuit specialization can contribute without a new general mathematical packing principle.

A reviewer may still regard the combination as a straightforward specialization. The response must show the exact quotient-decoding difference and measured cost, rather than rely on keyword absence. A generic spill decoder reconstructing both full products before taking their quotients, with the same admission/fallback, has not been measured as a decoder-only control. E0/E5 and E8 currently support implementation/combined-overhead comparisons, not isolation of every inventive element.

## What the evidence establishes

The core is62LUT/44FF/oneDSP. On GLIF, complete64-image issue counts fall46.0091% against a one-DSP scalar implementation. Accepted representative fixture dynamic energy falls12.3695% against that scalar and60.9472% against the fixed full-domain split control. The two-DSP scalar pair has1.0689% lower estimated energy, so halving DSP count is a resource trade-off. The E5-minus-E8 cost is15LUT/eightFF for admission and full-width support together. Rare wide values still matter: exact fallback allows the cheap narrow path to cover most updates without restricting the unchanged state domain.

These results support the mechanism as a focused paper contribution. They do not establish an accuracy improvement: packing preserves the declared integer outputs, while FP32-to-integer conversion is a different experiment. They also do not establish universal burst-latency or model superiority. OTTT half-leakage shifting beats E5 by94.6139% estimated energy. BNTT beta253 admits a cheap exact constant expression. GLIF selects two constants per channel; its optimized constant/CSD bank is still unmeasured. Those controls matter because the strongest practical alternative may not use a general multiplier.

## Readiness interpretation and recommended wording

**Ready to develop the focused primitive manuscript; no algebraic reason to discard the direction.** The remaining strong-submission risks are comparative sufficiency for the actual model, the modest novelty margin over established value packing/correction, and integration scope. First-ever proof is not a prerequisite for writing, but access-limited papers must not be described as inspected or definitively different.

Recommended contribution sentence:

> We present an exact adaptive membrane-leakage primitive that retains a fixed signed16 state contract, admits same-coefficient signed9 pairs to a compact one-DSP rounded decoder, and executes other values exactly as singletons. We derive its correction bounds and evaluate its resource, issue-rate and estimated dynamic-energy trade-offs against matched fixed-DSP and fabric controls on public SNN workloads.

Use the measured GLIF benefit and the negative vanilla-LIF result together to define applicability. Do not claim that generic adaptation, exact spill correction, the fixed-split identity, or the use of the membrane variable is independently new. A guaranteed strong ISCAS outcome cannot be inferred from either a novel-sounding phrase or the accepted numbers alone.
