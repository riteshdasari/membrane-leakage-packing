# Accepted GLIF E3/E5 scalar trade-off

E3's certified power audit reproduced independently and identically. All existing E5 comparison source/artifact pins were revalidated; E3 route, scalar NPZ, cohort and source bindings passed. Both use the same262,528 accepted GLIF scalar operands and outputs, signed16 domain,12ns clock and94-FF common fixture at25 C junction/typical process. NPZ SHA256:`07f68efe215e9e0dd8c70a009f97cca8c6a7cf8d3c7bc5de33062a4302b2d3eb`. E3 route SHA256:`926efc7a9c829c900ae50b8052e908d92dbf718cedfc1bd350201f2045730567`. Detailed receipts are in `glif_scalar_tradeoff_v1.json`.

E3 uses35 LUTs,56 FFs and **two DSPs** and estimates21.3710653340pJ/scalar. E5 uses62 LUTs,44 FFs and **one DSP**, estimating21.5994968308pJ/scalar. Thus E5 halves the DSP count, adds27 LUTs, removes12 FFs, and has **1.06888212% higher estimated dynamic energy** (0.228431497pJ/scalar). Neither dominates the complete resource/issue/energy vector.

E3 retires131,328 issues in1.575984ms. E5 retires141,985 in1.703868ms:8.11479654% more issues and8.11454939% longer ROI. E5's average dynamic power is lower,3.328 versus3.560mW (6.516854% lower), but its longer interval yields slightly higher energy. E3 supports independent coefficients in its two scalar lanes; E5 pairs require matching coefficients and signed9 actual values. These are primitive request counts, not full-neuron burst-latency measurements.

The reported energy separation exceeds the combined XML serialization bounds:0.228431497pJ versus0.035002854pJ. The serialization-only difference interval is[0.193428642,0.263434351]pJ. This supports the numerical direction within report rounding; it does not bound vendor-model/physical uncertainty or establish a statistically significant measured-board difference. The sensible characterization is near energy parity with a DSP/fabric/rate trade-off, not an E5 energy win over E3.

Suggested claim paragraph:

> Compared with a two-scalar-DSP implementation on the same GLIF capture, the adaptive primitive halves DSP count with near estimated dynamic-energy parity:21.60 versus21.37pJ per scalar result, a1.07% increase. It uses27 additional LUTs and12 fewer FFs and requires8.11% more issues. This is a resource-budget trade-off rather than universal dominance.

Energy includes the complete common fixture and excludes chip static power, memory and complete neuron updates. No complete accelerator replication or bandwidth consequence is inferred. E4 is still running/pending and is not extrapolated; this receipt does not declare all-control completion. No vendor or model job was launched for this read-only audit.
