# Fixed16 leakage hardware closure

Status: **incomplete_snapshot**. All new comparisons use signed16 full membrane inputs, signed9 internal pair packing, 12 ns clock and a common 94-FF fixture.

The full stored membrane precision is fixed. Adaptation changes how many operations share one DSP issue, without changing voltage units or losing integer bits.

Accepted native cohorts: 1. Accepted route records: 0. Independently reproduced power audits: 0.

Required gates still missing:

- native/main/general/stall1
- native/main/shift128/stall0
- native/main/shift128/stall1
- native/main/actual128/stall0/capture
- native/main/actual_glif/stall0/capture
- native/E7/general/stall0
- native/E7/general/stall1
- native/E7/actual_glif/stall0/capture
- route/engine0/12ns
- route/engine1/12ns
- route/engine2/12ns
- route/engine3/12ns
- route/engine4/12ns
- route/engine5/12ns
- route/engine6/12ns
- route/engine7/12ns
- energy/glif/engine0/12ns
- energy/glif/engine1/12ns
- energy/glif/engine2/12ns
- energy/glif/engine3/12ns
- energy/glif/engine4/12ns
- energy/glif/engine5/12ns
- energy/glif/engine7/12ns
- energy/ottt/engine0/12ns
- energy/ottt/engine1/12ns
- energy/ottt/engine2/12ns
- energy/ottt/engine3/12ns
- energy/ottt/engine4/12ns
- energy/ottt/engine5/12ns
- energy/ottt/engine6/12ns

All failed attempts are retained in the JSON evidence snapshot. Failed or absent audits never supply accepted power values.

GLIF energy is a bounded representative capture of the complete 64-image arithmetic stream after common zero filtering. OTTT energy from the current wide-value coverage sample is a stress result. Neither constitutes board or full-neuron energy.

Earlier signed12 resource/energy results remain separate. Publication readiness also depends on broader model results and prior-work equivalence checks managed by the parent task.

JSON evidence: `hardwareclosure_preparation_snapshot.json`. Snapshot SHA256: `42b400583a48e3aa09179dfe599cd13fa88b9370b2e7377452bdf971e36906c4`.
