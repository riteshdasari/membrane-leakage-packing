# Further checks of membrane-aware adaptive packing

The work remains useful, but these checks do not yet establish a strong adaptive paper contribution. The exact arithmetic, safety proofs, verified RTL and strong fixed controls are reusable evidence; the measured tradeoff must determine the paper claim.

## New hardware control

A uniform safe interval covering all three original shift3 model certificates is U=[-686,245], with any signed8 current. All five designs use this same specialized caller contract. Full fabric sums shrink to11 bits and high-part metadata to6 bits, with exact signextension to the original12-bit interface. This contract is narrower than the earlier full-word U11 primitive.

All six native arithmetic/protocol cohorts passed: every238,592 legal scalar pair plus mixed lanes/prefix failures, and the unchanged shift1/shift3 model streams under both stall settings. Model hardware replay covers the first48 held-out inputs per seed; actual retired sums reproduce every saved membrane,spike,count and class in that replay. Full360-example accuracy remains a software-reference result.

Routed core resources follow, excluding the same290-FF fixture. Internal6ns setup/hold closure is reported separately from raw external ports:

- Adaptive DSP: 121 LUT,47 FF,1 DSP; 49 touched slices; WNS2.025ns,WHS0.084ns; pass.
- Fixed8 precomputed DSP: 130 LUT,53 FF,1 DSP; 52 touched slices; WNS2.187ns,WHS0.156ns; pass.
- Native FOUR12 DSP+four LUT lanes: 87 LUT,49 FF,1 DSP; 30 touched slices; WNS2.412ns,WHS0.129ns; pass.
- Fixed LUT8: 98 LUT,93 FF,0 DSP; 28 touched slices; WNS1.790ns,WHS0.056ns; pass.
- Same-policy adaptive LUT: 99 LUT,87 FF,0 DSP; 34 touched slices; WNS0.841ns,WHS0.041ns; pass.

These new rows do not inherit the earlier generic-domain energy estimates. Their timed replay and energy remain unmeasured.

## Closed energy gap for the earlier one-edge U11 cores

The original unstalled shift3 trace retires635,904 scalar additions per engine. Four complete SDF replays passed, including all known invalid output rows. Their physical activity and power annotations passed strict independent audits. The fixed8 precomputed engine retained a timed data failure and has no accepted energy number.

- Adaptive DSP: 11.375523pJ/update vendor-estimated dynamic energy.
- Native FOUR12 DSP+four LUT lanes: 10.403704pJ/update vendor-estimated dynamic energy.
- Fixed LUT8: 11.373290pJ/update vendor-estimated dynamic energy.
- Same-policy adaptive LUT: 12.075569pJ/update vendor-estimated dynamic energy.

Adaptive is 9.3411% higher than the strongest fixed native hybrid and 5.7972% lower than the same-policy adaptive LUT. The fixed-LUT difference is below the combined export serialization bound and does not establish energy separation. These are complete290-FF measurement-fixture estimates, not core-only/board/full-neuron energy.

The fixed8 mapped-functional diagnostic status is `mapped_functional_pass`. Its timing and energy gates remain excluded even if this diagnostic passes.

The first postprocessor had a helper-import error after four complete numerical replays. A stale subagent also changed a frozen runner log line; the source gate rejected acceptance. The exact original SHA256 was restored and all source/artifact pins independently rechecked. Original failures remain retained. Auditor version2 changes only two stale returned fixture labels(338→290), with identical strict gates/calculations.

## Range, shared-high and proof checks

All72 predeclared coefficient/horizon/seed variants are retained, including poor accuracy cases. Only beta224/T32 reproduces the original shift3 dynamics. The shared-high union remains software-only and gives a small scheduling improvement; fixed8 uses no more service clocks in any cohort. It has no mapped cost or energy advantage.

The largest aggregate union service reduction over the original admission policy is 0.1668% across the24 predeclared three-seed cohorts. This is an analytic service count, not a clock-frequency/area result.

An independent audit recomputed all72 interval rows and216 sum/high-width contracts, including reset-discontinuity enumeration and directed residue cases. Ten generic-versus-specialized rows change native lane count; using membrane width+1 blindly would manufacture a SIMD cliff. The actual sum certificate decides FOUR12 versus TWO24.

The original software screen shallow-copied its nested histograms. A separate full72-row rerun repaired144 earlier-horizon histograms, validated all216 distributions, and proved every other result field identical. The original erroneous files remain retained. Fixed8 zero histogram placeholders are not measured distributions.

## AdEx and broader benchmarks

The eight published AdEx single-neuron cases were independently screened with their original Euler dynamics. Only one passed the strict scalar/vector numerical gate; six had matching spike lists, while two diverged in spike timing. All failures remain. Seven vector cases show a narrow stored voltage with a wide intrinsic intermediate under the illustrative units. This is component scope evidence, not Brian2 validation, integer exactness,8-lane workload or classifier accuracy.

Trained SNN benchmarks are still needed. A small primitive paper can use traced neuron updates from trained static-image LIF CNNs and event-based LIF networks, with unchanged reference accuracy and exact state/spike replay. The published benchmark sources, local availability and numerical admission gate are documented in [benchmark_contract.md](../work/adaptive_snn_probe/benchmark_followup/benchmark_contract.md). No broader trained-model execution is being claimed.

A further48-case U/current-width screen proves that narrowing U alone saves no high-base metadata when the current is equally wide or wider. The original signed4 tail metadata is only legal for signed8 current. Native ONE48 must remain a control above24 sum bits; a separately retained version2 corrects that omission in the first analytic screen. No mapped result follows from these formulas.

Eight packed residue fields are not eight complete wide additions implemented solely in DSP fabric: high-part arithmetic and reconstruction remain in LUTs/registers. Count useful completed neuron operations and total hardware cost; lane count alone can exaggerate DSP efficiency. The native four-DSP-lane plus four-LUT-lane control also completes eight additions per request.

Fixed8 attains the minimum number of requests for the current eight-addition interface. A different workload cannot reverse that capacity bound. A strong adaptive claim must therefore demonstrate a meaningful resource/energy frontier or a different justified operation; it cannot rest on novel naming or deliberately weak controls.

Complete AdEx,broader trained SNN traces,new-specialization energy,board measurements and a genuine application-backed product candidate remain explicitly untested. Earlier constant/programmable leakage experiments must be retained before calling a product idea new.
