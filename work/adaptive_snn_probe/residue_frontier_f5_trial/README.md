# F5 preparation and root-only execution

This folder contains one isolated adaptive follow-up. It changes only E5 to
five full-range lanes plus three actual-U8-admitted tail lanes. Original E0..E4
datapaths are source-checked against the frozen parent and are regression-tested
against its exact retirement bytes. Only E5 may be routed/exported/replayed/
powered here. No physical jobs were executed during agent preparation.

The preparation audit passed524288 full scalar pairs,65536 narrow pairs and72
availability/membership cases. It also reconstructs the frozen original RTL by
reversing exactly the declared E5 changes and module identifiers. The fixture
is byte-identical after identifier normalization. This algebra/source check
does not replace the required four native cohorts or routed slow-SDF replay.

Ownership: the agent prepared only this new sibling folder and the preceding
new `prefix_generalization_screen` files in the parent. Root owns all subsequent
jobs, evidence audits and contribution decisions. `parent_copy_manifest.json`
pins both parent and final child copies; the runner verifies it before jobs.
Existing parent sources, reports, checkpoints, traces and SAIF were untouched.

From this directory, use the existing Python executable:
`C:/Users/Ritesh/rn_dps/.venv/Scripts/python.exe`. Run serially after the original
six-engine validation queue completes. Each command refuses an existing attempt.

```powershell
& 'C:/Users/Ritesh/rn_dps/.venv/Scripts/python.exe' -B run_frontier_f5.py --run --stage native --kind models --stall 0 --attempt 0
& 'C:/Users/Ritesh/rn_dps/.venv/Scripts/python.exe' -B run_frontier_f5.py --run --stage native --kind models --stall 1 --attempt 0
& 'C:/Users/Ritesh/rn_dps/.venv/Scripts/python.exe' -B run_frontier_f5.py --run --stage native --kind main --stall 0 --attempt 0
& 'C:/Users/Ritesh/rn_dps/.venv/Scripts/python.exe' -B run_frontier_f5.py --run --stage native --kind main --stall 1 --attempt 0
& 'C:/Users/Ritesh/rn_dps/.venv/Scripts/python.exe' -B run_frontier_f5.py --run --stage route --engine 5 --attempt 0
```

Only if E5 registered setup/hold timing passes, continue:

```powershell
& 'C:/Users/Ritesh/rn_dps/.venv/Scripts/python.exe' -B run_frontier_f5.py --run --stage export --engine 5 --attempt 0
& 'C:/Users/Ritesh/rn_dps/.venv/Scripts/python.exe' -B run_frontier_f5.py --run --stage replay --engine 5 --attempt 0
& 'C:/Users/Ritesh/rn_dps/.venv/Scripts/python.exe' -B audit_frontier_power.py --replay-dir results/replay_e5_a0 --output results/replay_e5_a0/interval_audit.json
& 'C:/Users/Ritesh/rn_dps/.venv/Scripts/python.exe' -B run_frontier_f5.py --run --stage power --engine 5 --attempt 0
& 'C:/Users/Ritesh/rn_dps/.venv/Scripts/python.exe' -B audit_frontier_power.py --power-dir results/power_e5_a0 --output results/power_e5_a0/power_audit.json
```

The copied measurement auditor includes native-row attribution and export
netlist/SDF/DCP provenance checks. Gate replay uses a phase-preserving initial
6ns clock delay: first rise9ns, unchanged useful falling/rising phase and ROI.
No timing waiver is permitted. Root compares complete audited settings and
equal-work energy against immutable parent fixed8/hybrid/LUT/F6 evidence.

Optional bandwidth control, only if root requires another measured supply2
confirmation: run `run_supply2.py`. It uses the same F5 RTL and at most two valid
supplied values per useful request. Its checker matches E0..E4 retirement bytes
to the already passed parent's supply2 cohort. The analytic prediction is the
same354816 saved clocks; this is not a implemented memory or window buffer.

Expected F5 screen counts are83006 requests/119870 saved clocks and104097
requests/115049 no-stall stress clocks. These are predictions until RTL checks
pass. The stress penalty is greater than F6 and must remain in the publication.
Only the actual routed resource/timing and fully audited power outputs may be
used for implementation or contribution claims.
