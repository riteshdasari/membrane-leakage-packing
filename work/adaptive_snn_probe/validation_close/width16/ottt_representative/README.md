# Representative OTTT fixed16 energy path

This folder is prepared source-only. No representative model capture or hardware energy has been accepted by this preparation. Original OTTT stress controls in the parent folder remain separately labeled.

After the original64-image capture finishes, prepare the actual operand cohort with:

```text
python -B prepare_and_run.py
  --capture-results <absolute activity/ottt_random_stratified_a0/results.json>
  --route-acceptance <absolute selected main route_resolved_acceptance JSON>
  --attempt a0
  --prepare-only
```

The wrapper requires `pass_exact_feedback_and_distribution_gates`, verifies all capture and preparation hashes, and independently checks exact scalar leakage, accepted64 logits, signed16/beta128 legality, both text streams, NPZ/frame boundaries, source-neuron indices, weighted distributions, layer/time counts and greedy requests. It rejects a failed distribution gate before creating a cohort. It does not retune thresholds, leakage, voltage units, source order or sample windows.

The same command with `--launch` explicitly launches the serial vendor sequence after those gates:

- One actual-sample native test with three mapped controls: native0→E5 exact adaptive, native1→E1 fixedsplit, native2→E6 exact tau2 shift.
- For each E5/E1/E6: golden fixture replay, export of its explicitly selected main routed checkpoint, original-strength slow/max SDF replay and SAIF capture, physical activity/power audit, then independent audit reproduction.

The RTL, timing fixture, replay fixture and export/power Tcl are byte-identical copies of the parent fixed16 sources. Core precision, clock12ns and94fixtureFFs are fixed. New source and expectation paths are isolated here. No route is rerun. Each reused route must prove that its core/DSP/fixture sources equal the golden copies. Source and retirement checks bind every available operand to the accepted NPZ and every result to an independent ceil oracle; mapped trace paths are explicit.

The dynamic data receipt is `cohort_acceptance.json`, with `domain_acceptance_ottt_representative.json` plus the copied stimulus/expected NPZ. Launch outputs use distinct workload `ottt_representative` and cohort `actual_ottt_representative`. Final serial status is in `closure_<attempt>.json`; only independently accepted power audits populate its energy fields. Missing activity, mismatches or rejected stages remain failures and supply no accepted energy.

Preparation checks in `source_acceptance.json` pass AST inspection, seven byte-identical copy checks, three-control mapping checks, independent request counts on the existing7,335 stress operands, four boundary-count cases and rejection of a synthetic failed-distribution status. Those are host/source checks, not new hardware or model evidence. `source_test_failed_capture.json` is explicitly synthetic.

`preparation_rep3.json` and `energy16_preparation_rep3.json` pin the active three-control variant. Earlier seven-control copies/manifests are retained and unlaunched. The current wrapper selects the three-control variant exclusively.

RAM gates remain the inherited ones:1.2GiB vendor simulation working gate and2.3GiB export/power working gate, with0.15GiB headroom. Root owns vendor scheduling and invokes `--launch` only when the current serial job window is free. All results concern bounded representative64-image arithmetic after common zero filtering and vendor-estimated full fixture dynamic energy; they are not board, memory/filter or complete-neuron energy.
