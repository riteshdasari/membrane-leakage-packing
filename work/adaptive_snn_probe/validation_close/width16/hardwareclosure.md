# Fixed16 hardware closure handoff

The main interface now uses signed16 membranes for every workload, with the original membrane unit256 and trained coefficients unchanged. Signed9 is the internal two-lane admission range. It does not alter stored precision or voltage scale. Every route uses the same 12ns clock and 94-FF timing fixture (55 launch,39 capture). The original signed12 resources and captured energy remain historical evidence, separate from the new fixed16 comparisons.

Root owns all vendor launches. This agent prepared and independently reviewed sources only; no vendor tool was launched here.

Prepared native mathematics passed16,842,752signed16 scalar cases and the same number of fixed-split cases for beta0..256, plus65,536beta128 shift cases. The signed9 pair correction is unchanged from the frozen exhaustive proof. This establishes arithmetic preparation, and does not stand in for compiled RTL, STA or timed replay.

Use `run_native16_v2.py` for `general`, `shift128`, `actual128` and `actual_glif` cohorts. The GLIF source is the262,528operand random-stratified capture, with predeclared distribution gates and exact64image feedback. The OTTT7335operand source is a stress/coverage capture deliberately retaining wide membranes; label its energy as stress evidence until a representative capture is available.

`run_routes16.py` is the root's matched engine0..6 route runner. `run_routes16_checkpoint_retry.py` creates a new attempt from a failed attempt's completed source-pinned synthesis checkpoint, retaining the original. It verifies both the source and the original vendor job's selected top and12ns period. No checkpoint retry changes arithmetic or timing constraints.

The strengthened exact LUT control is isolated in `lutceil_e7`. E7 computes the signed quotient of the low8 coefficient product plus an indicator of a nonzero remainder, and handles beta256 by identity. Its16,842,752exhaustive scalar cases passed. Original E2 arithmetic is byte-identical and remains in the source. E7 is a stronger LUT baseline; a future pass by E7 would not establish the cause of E2's retained SDF failure.

Use `lutceil_e7/run_native16_lutceil_v2.py` for E7 cohorts. Native index6 maps to engine7, alongside engines0..5. `lutceil_e7/run_route16_lutceil.py` provides the matched12ns route and optional pinned synthesis retry. Its `--native-acceptance` must point to the accepted E7 general unstalled cohort.

`run_energy16_12.py` performs golden fixture replay, slow/max SDF replay, physical SAIF annotation and strict independent audit for main engines. It binds every accepted U/beta to the original expected-operand NPZ, checks frame-end admission, retirement counts and exact results/modes, and requires natural two-edge latency. Physical activity aliases, clocks, constants, zero unknown physical activity and100% annotation are audited. `lutceil_e7/run_energy16_lutceil_12.py` applies the same audit with explicit engine7/native-index6 mapping.

`aggregate_hardwareclosure.py --label NAME` writes a new immutable JSON/Markdown snapshot, retaining all failed attempts and all missing gates. It verifies source/artifact hashes, checks matched widths/fixtures/clock/resources and independently reproduces each saved strict power audit. `--strict-complete` exits with failure until every required native cohort, route and workload energy audit exists and passes. It chooses the latest accepted retry transparently, never by its area or energy value.

Current read-only snapshot `hardwareclosure_preparation_snapshot.md` is explicitly incomplete: one native cohort is accepted; routes and energy are unmeasured. No signed16 hardware advantage or publication-readiness claim has been made in this handoff.
