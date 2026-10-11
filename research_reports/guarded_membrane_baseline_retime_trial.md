# Guarded membrane-addition fixed-baseline retiming trial

This trial gives the fixed hybrid and LUT implementations the input-stage computation already used by the lean adaptive layout. All kernels still compute exact signed 11-bit membrane U plus signed 11-bit current I into a signed 12-bit sum, retain lane order, backpressure and reset behavior, and retire after four advancing clocks.

## Measured facts

The retimed hybrid registers the first four U/I operands and the two exact signed 12-bit LUT sums at acceptance. The DSP operands, DSP result, and output retain the original stage positions; the extra sums advance through matching registers. The retimed LUT kernel registers all six exact signed 12-bit sums at acceptance. These are registration-boundary changes, with unchanged always-six request policies and full integer domain. The original comparisons were valid for their implementations; this trial strengthens the baselines by applying a legal optimization equally.

All routes use Vivado 2025.2, xc7a100tcsg324-1, a 6 ns target, the same clock-source constraint, retained core hierarchy, and the identical registered OOC fixture. Core counts exclude 219 fixture FFs (138 launch + 81 capture). Core slice sets and fixture slice sets overlap; occupied slices are not additive.

- Retimed native DSP4 plus two LUT additions: 66 LUT / 248 FF / 1 DSP; change from its original fixed baseline +0 LUT / -20 FF / +0 DSP. Registered WNS +2.599 ns / WHS +0.122 ns; passes registered setup and hold. Core touches 43 slices, full fixture occupies 80 slices. Separate raw-port WNS +1.826 ns / WHS -1.076 ns.
- Retimed six LUT additions: 79 LUT / 304 FF / 0 DSP; change from its original fixed baseline +0 LUT / -60 FF / +0 DSP. Registered WNS +1.607 ns / WHS +0.147 ns; passes registered setup and hold. Core touches 81 slices, full fixture occupies 131 slices. Separate raw-port WNS +1.607 ns / WHS -1.064 ns.

The immutable adaptive V1 layout remains 130 LUT / 247 FF / 1 DSP, with registered WNS +0.670 ns / WHS +0.020 ns and 115,758 saved-trace service clocks. It uses offset-binary fields, the measured wide-lane permutation, and encoded operands captured at acceptance. Its six-versus-four policy still tests actual U and I for signed7 fit, with the same ordered zero-current identity-copy priority. Membrane storage and the externally declared integer operation remain full signed11; only the temporary DSP layout narrows.

Original matched resource references, revalidated from their saved publications:

- Adaptive guarded DSP: 157 LUT / 267 FF / 1 DSP, 115,758 supplied-window service clocks; registered WNS +1.036 ns / WHS +0.013 ns.
- Native DSP four-lane + identity copies: 25 LUT / 240 FF / 1 DSP, 159,540 supplied-window service clocks; registered WNS +2.074 ns / WHS +0.108 ns.
- Native DSP four-lane + two LUT lanes: 66 LUT / 268 FF / 1 DSP, 110,596 supplied-window service clocks; registered WNS +2.320 ns / WHS +0.103 ns.
- Six LUT lanes: 79 LUT / 364 FF / 0 DSP, 110,596 supplied-window service clocks; registered WNS +2.007 ns / WHS +0.080 ns.

The two retimed kernels each retain 110,592 requests and 110,596 service clocks on the 635,904-neuron saved trace. Their retired output hashes, request counts, arithmetic-issue counts, stalls and latency checks match the directly instantiated original E2/E3 references. No schedule improvement is attributed to retiming.

Four full suites check 11,579,320 scalar outputs across stress and model inputs, four variants, and two backpressure settings. This is repeated checking of 811,511 stress additions and 635,904 model additions, not an exhaustive six-neuron input space. Within each suite all four output files are byte-identical and match the original corresponding fixed-engine hash, with zero mismatches. Tests cover exact signed sums, ordering, four-advance latency, unavailable poisoned tails, stalled-output stability, and reset cancellation.

Saved reconstruction matches states, spikes, output spike counts and sampled classifications for 144 images across three seeds. Leakage at beta=231/256 and threshold/subtractive reset execute in Python; addition executes in RTL. The reference uses a changed leakage coefficient, so this establishes replay equivalence to that saved reference, not preservation of original trained-model accuracy or a complete SNN RTL implementation.

## Research interpretation

Adaptive format selection is a real functional capability: it obtains six DSP additions from eligible actual values and retains a full-range four-lane fallback. Against native fixed4 with the same ordered identity-copy opportunity, the adaptive schedule uses 27.44% fewer saved-trace service clocks for +105 LUT / +7 FF / +0 DSP. This is a bounded resource/service tradeoff against that baseline, rather than an overall winner claim.

Both members pass registered timing at 6 ns; the ideal supplied-window service rate is 37.82% higher than native fixed4 on this trace.

Against retimed native dsp4 plus two lut additions, adaptive V1 uses +64 LUT / -1 FF / +0 DSP and 4.67% more service clocks.
At the common passing 6 ns target, its ideal supplied-window service rate changes by -4.46%, and its service per core FF changes by -4.07%. The latter divides the equal-work service rate by core FF count; it excludes the fixture and assumes no shared memory or routing limit. It is not a measurement of replicated kernels or application throughput.
Under this FF-only normalization, adaptive V1 improves on the fixed hybrid only when the hybrid uses more than 258.53 core FFs (at least 259 integer FFs), before common integration overhead. This condition alone is not an area or application-throughput advantage; LUT and DSP costs still apply.
The hybrid uses fewer LUTs and the same DSP count, with a shorter schedule, at the cost of one extra FF. The adaptive one-FF saving does not establish a practical benefit over this hybrid.

Against retimed six lut additions, adaptive V1 uses +51 LUT / -57 FF / +1 DSP and 4.67% more service clocks.
At the common passing 6 ns target, its ideal supplied-window service rate changes by -4.46%, and its service per core FF changes by +17.59%. The latter divides the equal-work service rate by core FF count; it excludes the fixture and assumes no shared memory or routing limit. It is not a measurement of replicated kernels or application throughput.
The resource vectors remain a tradeoff; this experiment supplies no universal area or throughput advantage.

LUT and FF costs remain relevant even when adaptation is the proposed contribution: classification, format selection, exact reconstruction and pipeline storage implement that functionality. The fixed hybrid and LUT kernels provide the same full-range ordered result without a fit-based scheduler and can be better practical baselines. More work inside the DSP alone is not an application benefit. A useful adaptive claim needs a concrete workload or resource constraint where the complete measured kernel improves service or fits a budget better than strong fixed alternatives.

This result does not invalidate the membrane-aware adaptive-packing research question. It distinguishes a demonstrable native-four tradeoff from an unestablished advantage over strong always-six implementations. A fixed six-lane residue/high-part DSP reconstruction remains unmeasured; no best-fixed-packing or first-ever mechanism claim follows.

Registered setup/hold and raw-port timing are separate. Raw ports use a declared 1 ns setup / 0.1 ns minimum budget; negative raw-port hold slack is not production interface closure. The OOC target and slack do not establish board Fmax. The fixture is a timing fixture rather than a production handshake adapter, and retained hierarchy limits inference about a fully integrated implementation.

Memory supply, gather/scatter, state memory, host time, threshold/reset hardware, power, energy and true burst-arrival latency remain unmeasured. No FireFly accelerator was reproduced; these are matched local arithmetic kernels.

Evidence: [current fixed routes](<C:/Users/Ritesh/Documents/Codex/2026-10-08/oka/work/adaptive_snn_probe/baseline_retime_trial/results/retime_hardware.json>), [saved replay](<C:/Users/Ritesh/Documents/Codex/2026-10-08/oka/work/adaptive_snn_probe/baseline_retime_trial/results/retime_snn_checks.json>), [retimed core](<C:/Users/Ritesh/Documents/Codex/2026-10-08/oka/work/adaptive_snn_probe/baseline_retime_trial/guard_add_retime.sv>), [immutable adaptive layout](<C:/Users/Ritesh/Documents/Codex/2026-10-08/oka/outputs/guarded_membrane_layout_trial.summary.json>), [source/output/checkpoint manifest](<C:/Users/Ritesh/Documents/Codex/2026-10-08/oka/outputs/guarded_membrane_baseline_retime_trial.manifest.json>).
