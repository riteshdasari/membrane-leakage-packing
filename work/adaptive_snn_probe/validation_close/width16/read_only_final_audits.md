# Read-only final audit invocation

These scripts never launch vendor tools or model inference. Their help/AST checks pass; actual acceptance requires the completed experiment files. Every audit label creates new JSON/Markdown evidence and refuses to overwrite an earlier audit.

`static9_e8/audit_closure_static9.py` requires:

```text
python -B static9_e8/audit_closure_static9.py
  --pair-s0 <absolute E8 pair/stall0 acceptance.json>
  --pair-s1 <absolute E8 pair/stall1 acceptance.json>
  --scalar-s0 <absolute E8 scalar/stall0 acceptance.json>
  --scalar-s1 <absolute E8 scalar/stall1 acceptance.json>
  --e8-hardware <absolute selected E8 hardware.json>
  --e5-hardware <absolute selected E5 hardware.json>
  --label <new label>
```

It independently reconstructs every saved native output/count, verifies all source/artifact pins, checks signed9 input legality and16-bit signextension, and requires matched12ns/94FF/1DSP routes with passing setup/hold/boundary slacks. The E8 route must bind the explicit pair/stall0 acceptance. It reports E5−E8 combined membrane admission/full16 support cost. E8 does not support wide inputs and cannot replace a full16 baseline. No E8 energy claim is made.

`verify_selected_evidence.py` requires:

```text
python -B verify_selected_evidence.py
  --route-acceptance <absolute resolved main route acceptance.json>
  --e7-hardware <absolute selected E7 hardware.json>
  --sequence <absolute completed energy_closure_sequence_<attempt>.json>
  --label <new label>
  --strict-primary
```

Alternatively supply `--power-map` instead of `--sequence`. The JSON form is:

```json
{
  "power_paths": {
    "glif": {"5": "absolute path to power_audit.json", "1": "absolute path to power_audit.json"},
    "ottt": {"5": "absolute path to power_audit.json", "6": "absolute path to power_audit.json"}
  },
  "retained_failures": []
}
```

Map every completed control explicitly. No directory scan or modification-time selection occurs. Sequence mode accepts only power receipts from stages whose post-stage gate passed; it verifies receipt hashes and retains failed/skipped stages. The strict installed source/artifact audit is rerun for every power value. The selected audit must reference the explicit selected route path andSHA256, and its area must equal that same route. Rejected evidence has no accepted energy value.

The report saves power, exact integer ROI duration, scalar-update denominator, issue/retirement counts, and an exact rational energy derived from serialized XML voltage/current fields. This fraction is exact for the exported numbers; it is not a physical-accuracy guarantee.

Primary comparison closure requires GLIF E0/E1/E3/E4/E5/E7 and OTTT E0/E1/E3/E4/E5/E6. E2 is still checked when supplied and included in a separate all-attempted-control gate. A missing or rejected E2 cannot become complete all-control closure. Accepting exact alternate LUT topology E7 does not resolve the original annotated CARRY4 discrepancy. Original diagnostic, full public-model completion and access-limited method equivalence statuses remain separate. The report never declares publication readiness.

`final_source_review_acceptance_v1.json` pins the final root runner review snapshot and verifies27 route-template mappings. `energy_sequence_source_review_v1.json/md` retain the earlier review proposals. `final_evidence_outline.md` maps every hardware/model/activity/diagnostic/prior-work gate to its evidence files.
