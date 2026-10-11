**Operand isolation did not produce a timing-valid improvement in this bounded trial.** Both implementations preserved every tested result and service cycle, but neither met the original 6 ns registered timing target. No isolated energy estimate was accepted.

The smaller candidate zeros the selected membrane-high and signed adjustment operands when no valid exception requires the shared corrector. The folded candidate incorporates a zero default into one-hot lane selection. Both keep signed11 membrane, statically certified signed8 current and exact signed12 sums; the DSP still has six fixed eight-bit residue fields. This adapts correction work, not lane count or packing width.

- Frozen fixed V2: 43 LUTs, 262 FFs, one DSP; setup slack +2.141 ns, hold +0.130 ns.
- Frozen adaptive V3: 147 LUTs, 268 FFs, one DSP; setup +0.108 ns, hold +0.132 ns.
- Post-selection isolation: 152 LUTs, 268 FFs, one DSP; setup −0.230 ns, hold +0.026 ns.
- Folded isolation: 167 LUTs, 268 FFs, one DSP; setup −0.114 ns, hold +0.105 ns.
- One post-route physical optimization pass on the smaller candidate: 152 LUTs, 268 FFs, one DSP; setup −0.227 ns, hold +0.026 ns. All 538 routable nets are fully routed; routing errors are zero.

These core counts exclude the identical 219-FF registered fixture (138 launch and 81 capture FFs). Physical optimization preserved its register counts, 6 ns clock and OOC clock-source location. It was an extra candidate-only implementation pass, so it is not evidence of a comparison under equally optimized implementation flows. The original references remain immutable.

Each RTL variant passed stress and saved-model workloads, both with and without output backpressure. Across eight suites there were 5,789,660 repeated scalar checks, covering 1,447,415 unique source updates across the two workload files. All result lanes, zero tails, retirement clocks and settled output/control/service pins matched frozen V3. Both no-backpressure model traces were byte-identical to its 110,756-row, 18-column archived trace. Reset, busy cancellation and stalls were checked. Independent algebra/source review covered all 524,288 signed11/signed8 scalar pairs per variant and the relevant correction/controller cases; this is not a whole-design sequential formal proof.

The smaller candidate's original critical path runs through membrane classification, exception detection and the pipeline register-enable network. Routing contributes about 76% of its data delay. The folded candidate has a different critical path through DSP residue carry, exception selection, isolated membrane-high bits and output arithmetic, with about 82% routing contribution. Therefore reducing toggles in the small corrector does not remove the actual timing bottlenecks. The physical pass improved worst setup by only 0.003 ns.

For the saved model stream, isolation leaves the original 635,904 scalar updates, 110,592 requests, 1,008 correction steps and 114 extra service clocks unchanged. No DSP operation is skipped and no additional useful operation is packed. The previously measured whole-fixture estimates remain 18.053 pJ/update for fixed V2 and 20.997 pJ/update for adaptive V3; these are vendor estimates of the frozen designs, not measurements of either new isolated circuit. No switching-saving claim follows from a zero-default RTL expression alone.

Vivado completed the physical pass successfully. The first recording helper expected a route-completion sentence absent from this tool's report format. A separate read-only collector verified the preserved source/checkpoint hashes and job record, then proved route completeness from its numeric net counts. The physical optimization was not repeated and timing failure was not waived.

The result limits this optimization, not the broader research direction. Keep the exactness certificate and correction policy as reusable evidence. A stronger subsequent experiment must reduce classifier/scheduler cost or increase useful operations per DSP; suppressing a five-bit corrector alone has not established that benefit. Accuracy is already exact to the declared integer reference in fixed V2, so it cannot be claimed as an advantage over that comparator. These baselines are constructed primitives, not FireFly reproductions; novelty still needs a scoped prior-art review.

Routed SDF replay, SAIF collection and power estimation were intentionally not run after the 6 ns setup failures. The separate raw-port audit also has negative hold slack (about −1.075 ns for the smaller candidate); this registered OOC experiment is not a board-ready interface or board power measurement. Original trained-model accuracy and total neuron-update energy remain outside this trial.

Machine-readable checks, source hashes, job/RAM logs, checkpoints and all failed results are retained in the accompanying summary and manifest.
