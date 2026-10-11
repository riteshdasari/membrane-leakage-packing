# Matched signed8-current fixed-baseline trial

This is an isolated comparison, not a change to any archived measured core.
The question is whether the fixed six-residue DSP implementation has a useful
resource/timing tradeoff against equally specialized hybrid and LUT additions.

All active operands use signed11 U and signed8 I, sign-extended on the existing
six 11-bit buses. Each lane returns the exact signed12 sum U+I. The mathematical
range is [-1152,1150], so the output must remain 12 bits. There is no rounding,
saturation, changing scale or changed membrane domain. I11 inputs outside I8
are outside this declared contract. Unavailable tail lanes may contain arbitrary
binary payloads; their retired output lanes are zero.

The interface, lane order and control match the archived four-advance cores:
available is 0..6, take=available, in_ready indicates pipeline advancement,
and a valid nonempty input is held until accepted. A valid output stalled by
the sink remains stable. Reset cancels in-flight work. Without output stalls,
acceptance to output handshake is four clocks; all six active lanes are served
per issue. There is no state-memory or arrival queue in this trial.

The four functional variants are:

- 0: new hybrid, four FOUR12 DSP sums plus two LUT sums captured at acceptance;
  its first-four current registers physically store eight bits per lane.
- 1: new LUT-only implementation, all six exact sums captured at acceptance;
  each addition sign-extends an eight-bit current.
- 2: unchanged common-layout selective V2, six seven-bit residue sums in
  eight-bit DSP fields and six exact fabric high recoveries.
- 3: unchanged full-current retimed hybrid E2, used as a functional reference
  on the same I8 input domain, not as the final specialized cost comparator.

The four full suites use the existing stress frames with the SAME signed8
modular current projection as the archived selective profile1, and the
unchanged saved-model operands. The stress projection changes the input domain;
it is not lossless requantization of arbitrary original I11 currents. Stimulus
and fixed retirement bytes, including physical clock columns, must match the
archived profile1 fixed results. Tests include poisoned unavailable tails,
input and output stalls, reset cancellation and arithmetic boundaries.

Saved SNN replay verifies the declared beta231 integer reference using RTL
addition and Python leakage, threshold and subtractive reset. It establishes
reference equivalence, not preservation of the originally trained model's
accuracy or an entire RTL neuron update. No new model/data downloads occur.

Both new routes use Vivado 2025.2, xc7a100tcsg324-1, one thread and a 6 ns target,
with the same 219 preserved fixture FFs: 138 launch and 81 capture. Core counts
exclude those fixture FFs. Slice sets overlap and must not be subtracted as if
they were additive counts. Registered setup and hold are evaluated separately
from raw-port boundary timing. OOC timing does not establish board Fmax.

The fixed residue V2 and shared V3 routed references remain immutable. Every
source, full verification artifact, route report and old publication used in
the comparison is pinned in the final evidence manifest. Heavy simulations and
routes run serially, with 1.2 GiB and 2.3 GiB free-memory gates respectively.

LUTs, FFs and DSPs are reported separately, together with timing and service
clocks. A lower LUT count is not automatically lower total area or energy.
This study supplies no first-ever novelty, power/energy, trained-accuracy,
arrival-burst or full-system claim. Adaptation's benefit remains a separate
question; fixed lane layout and static I8 specialization are not adaptation.
