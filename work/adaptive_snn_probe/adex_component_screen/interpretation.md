# Retained numerical and applicability results

This experiment independently reimplements the simultaneous Euler equations
for the eight published [Brian2 parameter cases](https://brian2.readthedocs.io/en/stable/examples/frompapers.Naud_et_al_2008_adex_firing_patterns.html).
It does not run Brian2, which is absent locally, and it does not quantize the
trajectory. All original parameters,0.1ms timestep,0.6s duration,threshold
V>0 and voltage/adaptation reset are retained. Clipping in the example's plot
was not applied to the dynamics.

The predeclared cross-implementation gate requires identical spike-step lists
and less than1e-6 absolute difference in candidate voltage and adaptation
current. Only the transient-spiking case passes all parts. Six cases have
identical spike-step lists, but five of those exceed the strict voltage
difference gate. Delayed regular bursting and irregular spiking also differ in
spike steps. All failures remain in results.json; no tolerance was relaxed.

The implementations use math.exp versus NumPy exp and different but
mathematically equivalent addition grouping. The exponential greatly amplifies
small floating-point differences near spike initiation; some candidate
voltages before immediate reset exceed1e9mV. This observation explains why
absolute candidate differences can be large without a different spike in some
cases. It does not establish agreement with the official simulator or license
a new fixed-point/AdEx accuracy claim. A fixed-point AdEx study needs an explicit
evaluation-order and exponential/rounding contract.

The vector traces provide a limited counterexample screen: under the two
declared illustrative physical units(1mV and0.25mV), seven cases contain stored
V values inside the signed8 interval while the intrinsic candidate X is
outside it. X includes leakage,adaptation feedback and the exponential; the
final current contribution is added afterward. Therefore the saved membrane
alone is not an adequate eligibility input for that candidate operation.
These sample-based observations are not certified legal range bounds. They
also are not hardware savings,8-lane groups or trained-model accuracy.

The useful outcome is a concrete scope boundary: LIF arithmetic exactness
does not automatically transfer to full AdEx. Preserve the current exact
primitive while obtaining a real AdEx numerical specification, and verify
the intrinsic intermediate rather than assuming the stored voltage bounds it.
