# Planned next-stage candidate; not executed or accepted

Stage 2 has checked 7,808 trained Q8 coefficient contexts: beta0=153..170, beta1=74..88. All are at least64. Complete accuracy and old-state bounds are still being measured. Do not start the following trial until stage2_acceptance.json passes.

Proposed one final candidate: two signed9 membrane leakage operations when both values fit [-256,255], coefficients match, and beta>=64; otherwise one full-width exact operation. Choose the full input width from the completed old-state trace bound and apply the identical declared width to every control. Report the observed-model contract separately from any all-input range certificate.

An input carry rule may permit a cheaper common packed format than general output decoding. For narrow u0,u1 and beta64..256, define n=1 iff beta*u0+255<0. This can be predicted without a multiplier:

    u0<=-4 OR (u0==-3 AND beta>=86)
    OR (u0==-2 AND beta>=128) OR (u0==-1 AND beta==256).

Tentative DSP input and correction:

    A = (u0+256) + (u1<<16), signed25
    C = 255 - 256*beta + ((255+n)<<16)
    P = A*beta + C

The carry/borrow from beta*u0+255 is -n. The additional n in C's upper field should cancel it before output extraction. Candidate results:

    L0 = (P[15:8]) - 256*n
    L1 = signed9(P[32:24]).

For beta>=1, C's low16 bits are {(-beta modulo256),255}; upper16 bits are254+n. Thus most correction wiring may be constant rather than a general wide adder. This has not yet passed its exhaustive proof or RTL gate. Do not claim that it is new or hardware-efficient before those tests.

Required next-stage controls: one full-width scalar DSP; two scalar DSPs; two independent LUT multipliers; one-DSP fixed two-lane low-residue packing with full high products in fabric; and a fixed narrow signed9 instance for the narrow-domain subcomparison. Preserve coefficient changes and neuron order, grant common zero bypass, include range/coefficient detection and format/output control costs. Predeclare the stream screen before running it.

The existing 2026 packing/spill-tracking paper is related work. Generic exact carry correction is not a novelty claim; the possible contribution is this application-qualified implementation and membrane-driven format selection, provided it produces a measured benefit.
