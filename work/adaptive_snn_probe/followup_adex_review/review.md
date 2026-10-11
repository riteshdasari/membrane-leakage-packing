# AdEx applicability and the remaining contribution gap

The present core is an exact integer addition component. It does not implement
an AdEx neuron, and an AdEx name alone cannot strengthen the measured adaptive
packing result. Broadening the neuron family can test applicability, but it
cannot create a service advantage for the current eight-lane addition interface.

The canonical AdEx model evolves membrane voltage V and adaptation current w,
with an exponential voltage term, linear leakage, injected current and feedback
from w. A spike resets V to Vr and increments w by b. The neuronal adaptation
and our packing admission policy are different mechanisms. These properties
are established by the [original model](https://journals.physiology.org/doi/abs/10.1152/jn.00686.2005)
and the [authors' textbook](https://neuronaldynamics.epfl.ch/online/Ch6.S1.html).

For a specified forward-Euler reference, the candidate voltage before firing is

    Vstar = V + (dt/C)*[-gL*(V-EL) + gL*DeltaT*exp((V-VT)/DeltaT) - w + I]
    wstar = w + (dt/tauw)*[a*(V-EL) - w]

The reference must define whether the w update uses the old or new V, when a
crossing is observed, how reset/jump is applied, and the refractory behavior.
The [Naud et al. paper](https://lcnwww.epfl.ch/gerstner/PUBLICATIONS/Naud08.pdf)
uses a fixed voltage reset and an accumulating adaptation jump; it also shows
distinct parameter regions for firing behaviors. One cannot replace that
behavior with our LIF subtractive reset and retain an AdEx claim.

An existing official [Brian2 example](https://brian2.readthedocs.io/en/stable/examples/frompapers.Naud_et_al_2008_adex_firing_patterns.html)
provides eight complete parameter dictionaries, a0.1ms Euler step,0.6s duration,
initial V=EL,w=0, threshold V>0mV and reset V=Vr,w+=b. It labels its dictionaries
as adapted to match the cited figures. These are a reproducible published
benchmark option, not the mentor's parameters or a trained classification model.
Its plotting clip is visualization only and must not be inserted into dynamics.

## What our U+I core could do

Our own architectural inference is that a declared integer AdEx update may
contain a last addition X+J. Here X is the already evaluated intrinsic update
from V,w and nonlinear terms; J is the current contribution in the same units.
If X fits the caller's signed-U word, J fits signed8, and the result fits the
declared signed-sum word, our verified arithmetic can implement that addition.
The present signed11/signed8 core returns signed12, and U8 tail admission remains
exact for X in [-128,127].

However, X need not be the stored membrane V. Testing only actual V cannot
certify X when X also depends on w and an exponential term. One must either
monitor the actual integer X, or prove a bound on X from all relevant states
and parameters. Calling that monitor membrane-only without this qualification
would overstate its information. Overflow of the upstream multiplier or
exponential cannot be repaired by an exact downstream addition.

Rounding placement is part of the reference. In general Q(A+B) is different
from Q(A)+Q(B). Splitting a physical update into an integer intrinsic value and
an independently rounded current is only valid if the reference specifies that
split, or exact fractional remainders are carried through. Integer bit identity
to such a reference is distinct from agreement with the continuous ODE.

There is no inherited signed8 current certificate for AdEx. Our old certificate
bounds binary spikes times int4 weights. Physical current units, dt/C scaling,
synaptic filters and a potentially different fan-in change this contract. The
[NEST current-based model](https://nest-simulator.readthedocs.io/en/stable/models/aeif_psc_exp.html)
keeps excitatory/inhibitory current states and uses an adaptive Runge-Kutta
solver; its default zero refractory period can permit multiple spikes within
a step. It is therefore not an interchangeable reference for our one-spike,
fixed-step integer LIF stream.

The [NEST conductance-based model](https://nest-simulator.readthedocs.io/en/stable/models/aeif_cond_exp.html)
adds excitatory/inhibitory conductance states and voltage-dependent synaptic
products. Its current is not merely a stored int8 sum. That variant needs a
different product/range contract and is outside a first component-only check.

The minimum new contracts are:

- Fixed dt, method and evaluation order; reset, crossing and refractory rules.
- V,w, synaptic-state and parameter representations, offsets and fractional bits.
- The exact exponential implementation and its legal argument/output interval.
- Rounding/overflow rules for every multiply, divide, sum and state update.
- Certified bounds for X, J, X+J, wstar and the w+b jump, including bursts.
- Coefficient sharing across operands, which packed multiplication requires.

Absolute voltage units or a constant rest-potential offset affect word widths.
A common fixed coordinate offset can be shared by every baseline. It is not
an adaptive halving/doubling scheme and must not be chosen solely to manufacture
a narrow-packed advantage. Observed voltage maxima are not a legal range proof.

## Existing hardware and novelty limits

AdEx hardware is established. [NeuroFlow](https://www.frontiersin.org/journals/neuroscience/articles/10.3389/fnins.2015.00516/full)
supports AdEx along with other neuron models, uses floating-point ODE state
updates, and separates those updates from synaptic integration. Its paired
AdEx experiment and whole simulator numbers do not reproduce the cost or
throughput of our integer primitive. This rules out an argument that supporting
AdEx itself is new; it does not settle the particular membrane admission policy.

Packing itself and exact correction also have relevant prior art.
[DSP-Packing](https://arxiv.org/html/2203.11028) covers low-precision arithmetic
and packed SNN additions. The2026 [Arithmetic Packing paper](https://arxiv.org/html/2606.11065v1)
uses the DSP pre-adder for signed input packing and external exact spill
tracking for packed MACs. Its illustrated targets are matrix-vector products
and convolution, not a demonstrated actual-membrane-based admission schedule.
This limited search did not identify our exact policy in an AdEx datapath,
but does not establish absence of prior work or a first-ever claim.

## A bounded AdEx check without inventing mentor parameters

The next AdEx-specific task should be a software contract and trace screen,
not another architecture implementation. Use all eight official Brian2
published cases once each, with their original parameters/inputs, timestep,
duration and reset. Do not select only a bursting case or duplicate one neuron
to fill an eight-lane packet. No classifier accuracy follows from single-neuron
traces. Record V,w, spikes, each intrinsic intermediate and current contribution,
including pre-reset excursions; compare the independent solver to the published
example and retain every case that fails.

That first stage estimates where a component might fit; it cannot claim integer
exactness or DSP savings. Only after an application numeric contract or an
explicitly separate published fixed-point reference is available should a
second stage quantize it, generate an ordered integer ledger and replay its
actual retired sums back into both V and w. Any exponential approximation must
be identical in adaptive/fixed references and separately assessed against the
unquantized reference. Do not choose a coefficient or precision to rescue DSPs.

A matched component trial is worthwhile only if the observed streams fit the
proved X/J domain, have a meaningful eligible/exception mixture, and expose an
operation where adaptation could change a priced bottleneck. Otherwise the
result is applicability evidence and a reason not to spend RTL effort. Preserve
native signed-SIMD, full fixed packing, same-policy adaptive LUT, full LUT,
constant-factor arithmetic and appropriate table alternatives.

## A genuinely untested path, and its gate

For N ordered additions in one dependent group, any interface accepting at most
eight useful operands needs at least ceil(N/8) requests. The fixed full8 core
achieves this for every input in its declared domain. Our adaptive take is
at most8, so it cannot use fewer requests. With matched latency and no extra
fixed8 stalls, the same applies to intrinsic group service. This proof survives
changing coefficients, horizon, neuron family or the range detector. Common
input-supply limits can erase the request differences; they cannot reverse this
capacity bound. Local range/horizon and sum-width screens should therefore be
read as resource/eligibility evidence, not prospective speedup over fixed8.

A remaining conditional path is a membrane-driven packed **intrinsic
coefficient product** rather than this final addition. For a genuinely required
non-shift coefficient, the wide correction contains coefficient times the high
part, not just a small high-part addition. An invariant product layout with
some full-range positions and conditionally admitted narrow positions could
trade reduced correction fabric for occasional extra requests. A fixed full
product might then require more priced correction units, so fixed full8 addition
no longer provides a pointwise service argument for that different operation.

This is a hypothesis, not a predicted win. Earlier constant-beta leakage trials
already lost to optimized fixed/LUT alternatives, and programmable continuous
trials also did not establish an advantage. Repeating beta231 or adding
programmability without an application need is unjustified. The untested part
is an invariant-layout intrinsic product tied to an actual declared application
coefficient/range and evaluated at its best natural latency; that application
has not been supplied. Full products with exact high correction, factorized
constant multipliers, LUT/ROM tables and the2026 spill method must be costed.

Under an explicitly equal resource envelope, fewer required correction units
might permit more parallel useful products than the strongest legal fixed unit.
That would be a measured resource/throughput frontier, not permission to omit
the unrestricted full fixed design. Run an algebra and analytic range/cost
screen first; if no plausible frontier remains, stop before new RTL. AdEx can
motivate the products only once its numerical specification needs them. Its
intrinsic adaptation does not itself demonstrate a benefit for our controller.

An exact variable-length state-storage experiment could also alter bandwidth,
but it changes the question to memory compression and is outside the requested
small DSP packing paper. It should not be introduced to hide the current
primitive's capacity limitation.

This review ran no vendor jobs and did not implement or validate AdEx. It makes
no new accuracy, resource, timing, energy, publication-readiness or novelty claim.
