# Candidate contribution and exact policy ablations

The candidate keeps a fixed signed16 membrane interface and unchanged voltage units. It packs two signed9 membrane leakage operations when both actual values fit and their coefficients match; otherwise it issues one full signed16 operation. Range-aware admission is membrane-potential-aware here because it examines the actual stored state.

The full mode is exact for U in [-32768,32767] and beta in [0,256]. The product is in [-8388608,8388352]; adding255 and dividing by256 with arithmetic shift implements ceil without widening the stored membrane. The resulting leakage fits signed16. The existing signed9 packed algebra remains unchanged.

The two-lane multiplicand fits the DSP48E1 signed25 input: nine upper lane bits start at bit16, while the lower biased membrane occupies nine bits. Full16 mode simply sign-extends into the same physical DSP port. The fixed split control instead uses two low8 products in the DSP and two signed high8 products in LUTs. The widening from the historical signed12 interface increases those high-part fabric products; their actual resource cost must be measured.

For GLIF ResNet18 CIFAR10 T2 channelwise, the complete64-image stream contains 79,246,135 arithmetic updates after the common zero bypass. 99.0189% fit signed9.

- Adaptive: 42,785,698 issues; 1.852164 results per DSP issue.
- Fixed split: 42,327,032 issues; adaptation adds 1.0836%.
- Independent fixed two-lane control: 39,623,132 issues; adaptation adds 7.9816%.
- Scalar DSP: 79,246,135 issues; adaptation removes 46.0091%.

Coefficient compatibility costs 2,703,900 issues relative to independent fixed two-lane operations. Membrane admission costs another 458,666 issues relative to fixed split. These differences include greedy matching phase; they are policy ablations, not independent event probabilities.

For OTTT VGG11 CIFAR10 T6 vanilla LIF tau2, the complete64-image stream contains 130,823,879 arithmetic updates after the common zero bypass. 53.3389% fit signed9.

- Adaptive: 101,715,765 issues; 1.286171 results per DSP issue.
- Fixed split: 65,412,092 issues; adaptation adds 55.4999%.
- Independent fixed two-lane control: 65,412,092 issues; adaptation adds 55.4999%.
- Scalar DSP: 130,823,879 issues; adaptation removes 22.2498%.

Coefficient compatibility costs 0 issues relative to independent fixed two-lane operations. Membrane admission costs another 36,303,673 issues relative to fixed split. These differences include greedy matching phase; they are policy ablations, not independent event probabilities.

The GLIF stream is favorable to pair admission, while the vanilla LIF stream has many wider states. The vanilla model also uses beta128, for which ceil(U/2) has an exact shift-only implementation. Its shift baseline is essential; the paper must retain the unfavorable result if adaptation loses to it.

The possible contribution is the exact membrane-driven admission policy and implementation trade-off under a general coefficient contract. Carry correction and generic DSP packing should not be claimed as inventions. Measured signed16 area/energy results and the final equivalence audit must support the claim before describing it as a hardware advantage.

Controller overhead has not been isolated. E5-versus-scalar resource differences include admission, operand layout, result decoding and registers. A dedicated always-pair signed9-only ablation could isolate admission cost, but it would have a narrower caller contract and could not replace the signed16 controls.

Evidence: `candidate_contribution.json`, SHA256 `eb9c1bd4a153509b4e27be35d196d93a155a730130763819ab86b08b135b3e22`.
