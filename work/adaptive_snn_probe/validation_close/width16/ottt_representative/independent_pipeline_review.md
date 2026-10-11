# Independent review of representative OTTT three-control path

Reviewed on 2026-10-10, source/host only. No model inference, vendor invocation, route mutation or accepted energy was produced by this review. Source hashes and host-check results are retained in `independent_source_review_checks.json`. At review there were no `closure_*.json` files.

No critical source correctness issue found in the active three-control path. This is permission to proceed to its declared validation gates, not acceptance of an unexecuted capture, timing replay or power result.

## Mapping and exact arithmetic

The active native testbench instantiates three engines in order E5/E1/E6. `run_native16_rep3.py` preserves that actual-engine order while saving trace/out indices 0/1/2. The energy runner selects the acceptance row by actual engine and derives its trace path from `native_index`. The independent auditor enforces the inverse mapping `{5:0,1:1,6:2}`. The wrapper checks all three rows before permitting energy stages.

All stream/NPZ operands and declared frame boundaries are checked at preparation. The independent replay auditor rechecks every available operand against the expected NPZ, each greedy admission, independent integer division result, accepted request, retirement, output mode and two-cycle latency. A separate maximal-narrow-run oracle reproduced issue counts on the historical 7,335 operands and 14 frame/endpoint cases. Those host operands remain stress data and are not reported as the new representative capture.

## Positive capture and source gates

The wrapper first requires the exact status `pass_exact_feedback_and_distribution_gates`; the retained failed-distribution status was independently rejected. It subsequently recomputes the six declared distribution gates, narrow fraction, fixed/adaptive request difference, per-frame strata/indices/weights, layer/time counts, complete text/NPZ binding and scalar leakage. Captured logits and full operation counts must equal the previously accepted original 64-image integer/packed evaluation. Hashes pin capture code, its original model assets and capture artifacts. A failure cannot produce a cohort receipt or accepted energy.

Forty distinct preparation/certificate source/artifact pins matched their current files. Seven RTL/fixture/Tcl copies were byte-identical to parent fixed16 files. The wrapper requires explicitly selected main route hardware receipts for E5/E1/E6, the same part, signed16 interface, 12 ns clock, positive setup/hold/boundary slack and 55 launch plus 39 capture fixture FFs. It checks that each selected route's recorded core/DSP/fixture source SHA equals both the parent and the representative golden copies. Export and annotation use that route's recorded `design.dcp`; DCP, export, golden, native and trace hashes are checked again by the auditor. No alternate old stress route is inferred silently.

## Activity interval and denominator

Routed replay has a 12 ns period, and the ROI opens one picosecond before the first source row is launched: `132000 + first*12000 - 1` ps. It lasts `(last-first+3)*12000` ps, including the common two-row fixture delay and final capture/drainage. The auditor independently derives first acceptance, last retirement, interval and every clock transition from the native trace. Golden and routed replay compare every known row through the same 94-FF fixture. Slow/max SDF annotation, transport internal delays and zero pulse settings are explicit; timing-check disabling options are rejected.

The power auditor verifies every physical net/alias and its SAIF static probability and transition rate. Defaults are accepted only when proved by primitive connectivity; actual clock source activity, DSP CEs and physical unknown time are checked. It checks the exact reused DCP, fixture counts, common electrical/thermal settings and full physical matching. Dynamic energy is power times measured duration, divided by retired nonzero scalar operations; its `W*ps/operation` numerical value is pJ/operation. This is vendor-estimated full OOC fixture arithmetic energy after common zero filtering. Sampling weights establish representativeness of the capture; they do not turn the measured bounded stream into board or full-network energy.

## Remaining execution gates and minor clarity points

The accepted representative capture, newly copied cohort, native pass, positive SDF/timing replay and complete physical activity/power audit must still exist and pass. Source inspection cannot establish these future results or guarantee distribution gates pass.

The functional native bench uses a 6 ns period; this is not a 12 ns timing result. Actual 12 ns timing/power evidence is provided only by the subsequent routed replay and selected main route. The stale native comment “All7 controls” should eventually read “All3 controls”; execution itself instantiates and checks exactly three. No implementation changes were made by this review.

Earlier seven-control scripts/manifests are retained as historical, unlaunched copies. Active variant scripts, expected cohort paths, workload `ottt_representative`, cohort `actual_ottt_representative` and outputs are explicitly distinct from parent `actual128` stress evidence. Only independently accepted power audits populate `closure_<attempt>.json` energy fields; rejected stages retain their failures.
