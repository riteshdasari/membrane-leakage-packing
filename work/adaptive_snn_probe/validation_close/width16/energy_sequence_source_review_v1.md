# Fixed16 serial closure source review

Source-only review. No vendor tools, model inference, source mutations or acceptance waivers were performed.

Engine mappings are consistent: E7 is native index6; E8 native indices0/1 correspond to E5/E8. E8 retains the identical exact post-correction body, and independently recomputed signed9 outputs/counts match both prepared cohorts.

Required changes to the root-owned sequence:

- [required] run_energy_closure_sequence.py:12: Hardcoded original a0 aggregate cannot represent accepted mixed original/retry routes. Add --resolved-route-acceptance. Verify the immutable manifest, its original acceptance pin, and exactly one accepted hardware.json per engine0..6. Allow a0 successes plus source-identical a1 retry directories; never overwrite original a0 evidence.
- [required] run_energy_closure_sequence.py:15: One a0 route template forces all engines to use the same route attempt. For each selected route, dispatch one-engine energy invocation with a route template whose engine token is retained and whose suffix matches that selected directory. Use unique child attempt per workload/engine or distinct attempt per grouping, because the child progress filename omits engine.
- [required] run_energy_closure_sequence.py:44: Child energy runners catch failures and return zero; process status alone does not establish closure. After each step require its exact expected acceptance/progress status, verify pins and required rows, and save the acceptance path+SHA in the sequence. For energy require progress status pass, zero failures and all four stage records plus each power_audit.json. Skip dependent stages when prerequisites fail; continue independent branches.
- [required] run_energy_closure_sequence.py:29: Final aggregation is invoked without its strict-complete option. Invoke --strict-complete and independently inspect output JSON. Keep primary comparison closure and original-E2 discrepancy resolution as distinct statuses: E7 acceptance cannot close the original E2 diagnostic.
- [required_if_reporting_E8] aggregate_hardwareclosure.py:34: Aggregator scans main/E7 only and excludes E8 native and route evidence. Add explicit separate E8 closure gate or a versioned ablation aggregator requiring pair/scalar stalled+unstalled native plus matched12ns route. Check legal_state_signed_bits9, mapping5/8→0/1, and94FF/1DSP. Do not add E8 to the full16 baseline set.
- [report_binding] aggregate_hardwareclosure.py:90: Latest route and latest power are selected independently, although every power audit binds a specific routed hardware file. For final selected comparison use the explicit resolved route manifest and require power.routed_hardware_file+SHA equal the chosen route. Snapshot all unselected attempts separately. Do not combine area from one route attempt with power from another without identifying both.
- [low_standalone_provenance] run_native_static9.py:18: Standalone E8 native pins arithmetic sources through preparation but does not directly pin common job runner or installed glbl.v; parent sequence currently pins both. For standalone provenance completeness add these to a versioned E8 native runner, or record parent sequence provenance as required context. This does not invalidate the signed9 arithmetic source gate.
- [cosmetic] run_route_static9.py:1: Docstring calls E8 an optimized LUT route although it is a one-DSP signed9 cost ablation. Correct the label in a future version; current accepted record fields correctly identify1DSP/signed9-only.

Resolved route manifest proposal:

Keep a new immutable JSON with status pass, B16, clock12, fixture94, part, an engine-keyed selected_routes mapping to absolute hardware.json path and SHA256, original_route_acceptance_file+SHA, retained_attempts, source_sha256 and artifact_sha256. Each selected hardware file must pass setup/hold and boundary checks, match top and expected DSP count, and prove source-identical arithmetic/constraints. A retry must retain checkpoint_origin.json and its original DCP pin.

Record sequence post-stage acceptance hashes, not just child return codes. Original E2 delayed-replay failure, E2 route opt_design error and E7 exact alternate topology are different evidence categories. An E7 pass cannot retrospectively accept original E2.

Exact snapshot: energy_sequence_source_review_v1.json.
