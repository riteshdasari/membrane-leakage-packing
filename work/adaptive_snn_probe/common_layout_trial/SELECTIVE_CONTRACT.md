# Integrated selective-correction RTL trial

This implements the single policy chosen by the hardware and adaptation study.
The original common-layout contract and frozen fixed trial remain unchanged.

## Profiles

The interface remains six ordered signed11 U/I buses and exact signed12 output.
V0 fixed parallel and V1 adaptive shared accept the entire signed11 current domain.
V2 fixed parallel and V3 adaptive shared declare current signed8, sign-extended
on the11-bit input bus. Both current8 implementations receive only that domain.
The archived weight-derived bounds justify current8 for the saved beta231 model;
the specialized profile is never tested or claimed exact for arbitrary I11.

All profiles use the SAME fixed six eight-bit unsigned residue fields. High
correction changes; physical DSP lane count and field positions do not.
For each lane, s=rU+rI, carry=c=s[7], low=s[6:0], H=hU+hI+c.

## One adaptive policy

- Both U and I signed8: reconstruct H=c-sign8(U)-sign8(I).
- I signed8 and c=sign8(I): H=hU, including wide U.
- Otherwise: compute H with the one shared signed5 exact high corrector.
- In the current8 profile I8 is a declared invariant, not a runtime discovery.

One correction can occur in the usual output stage. A window needing k>1
corrections holds the existing DSP result and high metadata and consumes k-1
extra physical clocks. The controller does not add a reordering queue or a
membrane-state memory. It must clear a handshaken prior output even when the
arithmetic pipeline freezes; it must preserve an output stalled by the sink.
The last correction consumes v2 and advances the held pipeline exactly once.

The inherited four-advance latency is checked using the actual advance wire;
physical acceptance/retirement clocks and stalls are separately reported.
For continuously supplied saved inputs and ready output, the model predicts
110710 clocks (fixed6 110596):114 extra frozen clocks, not a measured result.
An adversarial all-six-correction window needs five extra clocks and remains
exact. The performance claim must include this worst case.

## Shared goal and evidence

Optimize within the arithmetic primitive and measure all LUT/FF/DSP resources,
registered timing, exact outputs, service clocks and internal corrections.
Compare V1 against V0, V3 against V2, and both against retimedhybrid/LUT6.
Do not claim power savings from suppressed logical correction calls alone.
Do not rename adaptive exact correction as variable DSP lane-count packing.
Do not widen saved data or alter neuron dynamics to handicap fixed baselines.
Root runs heavy jobs serially under the existing RAM gates.
