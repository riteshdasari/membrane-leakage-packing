# Adaptive membrane-addition layout optimization trial

This trial reduces signed reconstruction and operand-layout overhead while retaining the exact signed 11-bit U plus signed 11-bit I operation, signed 12-bit output, original packing decisions, identity-copy priority, and four advancing clocks from acceptance to retirement.

Both variants replace sign-parity correction with offset-binary fields. For payload width K, flipping each operand sign bit encodes x + 2^(K-1). The guarded DSP field computes U + I + 2^K, so flipping result bit K recovers the exact signed sum. The guard prevents interlane carry. This is an exact representation of the same integer arithmetic, with no shifts or rounding.

The narrow physical order remains logical lanes 0,1,2,3,4,5 at 8-bit spacing. The wider order becomes 0,1,3,2 at 12-bit spacing; output wires restore logical order. Logical lanes 0 and 3 therefore share field starts between modes. Two aligned starts are the maximum for these contiguous 8-bit and 12-bit formats, since their common starts in a 48-bit word are 0 and 24.

- V0 retains raw input registers, removes parity metadata, and uses the aligned, biased fields.
- V1 additionally registers already encoded DSP operands and the exact two possible copies at acceptance. This moves format selection onto the input path while keeping the four-stage interface.
- V2 is the original adaptive core instantiated directly in the functional testbench. Its previously completed route remains the hardware reference.

Offset-binary encoding and static lane permutation are measured together in V0; their individual LUT savings are not isolated. The V1 versus V0 comparison tests stage placement.

Matched Vivado 2025.2 routes target xc7a100tcsg324-1 at 6 ns, use one thread, and retain the same core boundary and identical 219 fixture FFs (138 launch + 81 capture). Reported core resources exclude those FFs. The fixture is for timing measurement and is not a production handshake adapter.

Measured new variants:

- V0: 130 LUT / 257 FF / 1 DSP; change versus original -27 LUT / -10 FF / +0 DSP. LUT reduction 17.20%, FF reduction 3.75%. WNS +1.119 ns / WHS +0.117 ns; passes registered setup and hold. Core touches 70 slices; full fixture occupies 102 slices. Separate raw-port audit WNS +1.119 ns / WHS -1.136 ns.
- V1: 130 LUT / 247 FF / 1 DSP; change versus original -27 LUT / -20 FF / +0 DSP. LUT reduction 17.20%, FF reduction 7.49%. WNS +0.670 ns / WHS +0.020 ns; passes registered setup and hold. Core touches 72 slices; full fixture occupies 107 slices. Separate raw-port audit WNS +0.670 ns / WHS -1.139 ns.

Original matched reference kernels:

- Original adaptive: 157 LUT / 267 FF / 1 DSP, WNS +1.036 ns / WHS +0.013 ns; 115,758 supplied-window service clocks on the saved trace.
- Native four-lane DSP plus identity copies: 25 LUT / 240 FF / 1 DSP, WNS +2.074 ns / WHS +0.108 ns; 159,540 supplied-window service clocks on the saved trace.
- Native four-lane DSP plus two LUT additions: 66 LUT / 268 FF / 1 DSP, WNS +2.320 ns / WHS +0.103 ns; 110,596 supplied-window service clocks on the saved trace.
- Six LUT additions: 79 LUT / 364 FF / 0 DSP, WNS +2.007 ns / WHS +0.080 ns; 110,596 supplied-window service clocks on the saved trace.

Every layout variant has the original adaptive schedule: 115,758 supplied-window service clocks versus 159,540 native-four clocks (27.44% fewer), and 110,596 fixed hybrid/LUT clocks (4.67% more). The saved trace therefore supplies no new schedule gain from these layout changes; their value is any measured hardware reduction at the retained schedule.

V1 is preferred by the declared LUT-then-FF selection rule among variants passing registered timing. Compared with hybrid6 it uses +64 LUT / -21 FF / +0 DSP and still takes 4.67% more service clocks. Compared with LUT6 it uses +51 LUT / -117 FF / +1 DSP and the same longer schedule. These are separate resource tradeoffs; no weighted area, energy, or universal implementation advantage is established.

Functional evidence checks 8,684,490 scalar outputs across two input sets, three variants, and both backpressure settings. All twelve retired files are byte-identical within each cohort and also match the original adaptive output hash; exact sums, request policy, latency, ordering, poisoned tails, stalled output stability and reset cancellation pass. These are repeated comparisons, not exhaustive combinations of six neuron updates.

The mathematical screen separately covers all 16,384 signed7 and 4,194,304 signed11 scalar pairs, plus 101,014 packed cases, with zero mismatches. It establishes the encoding algebra; timing and RTL behavior are checked separately.

Saved SNN reconstruction matches every state, spike, spike count and sampled classification across 144 images from three seeds. Leakage with beta=231/256 and threshold/subtractive reset execute in Python, while addition executes in RTL. This modified reference does not establish preservation of original trained-model accuracy or a complete SNN RTL implementation.

All registered timing results are OOC fixture results. Raw ports have a separate declared 1 ns setup / 0.1 ns minimum budget; negative raw-port hold slack is not production interface closure. No board Fmax follows from target minus WNS. Slice sets overlap and cannot be treated as additive core/fixture areas.

Memory supply, gather/scatter, neuron-state memory, host performance, threshold/reset hardware, burst arrival latency, power and energy remain unmeasured. These are local kernels; FireFly hardware is not reproduced. The exact runtime policy has no established first-ever claim. A full-range fixed six-lane residue/high-part reconstruction remains an unmeasured alternative, so superiority over fixed packing generally is not established.

Evidence: [new routes](<C:/Users/Ritesh/Documents/Codex/2026-10-08/oka/work/adaptive_snn_probe/layout_trial/results/layout_hardware.json>), [saved replay](<C:/Users/Ritesh/Documents/Codex/2026-10-08/oka/work/adaptive_snn_probe/layout_trial/results/layout_snn_checks.json>), [layout core](<C:/Users/Ritesh/Documents/Codex/2026-10-08/oka/work/adaptive_snn_probe/layout_trial/guard_add_layout.sv>), [source/output/checkpoint manifest](<C:/Users/Ritesh/Documents/Codex/2026-10-08/oka/outputs/guarded_membrane_layout_trial.manifest.json>).
