# Operand-isolation audit

Scope: read-only checks of functional comparison evidence, the archived V3
pin trace, exact routed replay interval, SDF diagnostics, every physical activity
alias and estimated dynamic energy. This agent owns only the audit helper and
this note. Root owns RTL and all tool jobs. No new hardware or energy result is
claimed before the corresponding audit passes.

The prior audit helper is SHA-pinned and imported without editing it. Its replay
math recounts 635,904 updates, 110,592 requests, 1,008 correction steps, 114
freezes and the actual 664,272,000 ps activity interval including two equal
fixture settling cycles. Four new functional comparison records must pass and
remain hash pinned before isolated routed replay is accepted.

The new physical audit requires a primitive REF_NAME listing and pin/net
connectivity. It identifies DSP48E1 clock enables, clocks and constant drivers
from their primitive types and pin ports rather than synthesized net names.
Every physical SAIF-sourced alias must have zero TX/TZ/TB and the recorded
probability/transition rate; unmeasured dynamic/default activity fails. Raw
simulator-internal unknown records remain preserved and explicitly excluded
only after complete physical coverage is checked.

Corrector/isolation source-name matches are descriptive examples, not proof
that isolation survived synthesis. A separate mapped-connectivity review must
establish retention. Dynamic energy compares equal saved work with actual
durations and the same 6 ns clock, device, nominal rails, typical process and
25 C user junction temperature. Static power is separate. Vivado-derived
ambient may differ as estimated power changes; that is recorded rather than
treated as a changed primary model input.

The helper self-check passed on 2026-10-10. It re-audited both complete frozen
references, reproducing 18.05315330615942 pJ/update for fixed packing and
20.996671195652173 pJ/update for the original adaptive implementation. Its Tcl
list parser checks also passed. These are reference validation results;
isolated-version energy remains unmeasured.

The first route failed the 6 ns setup gate: 152 LUTs, 268 FFs, one DSP,
WNS -0.230 ns and WHS +0.026 ns. The worst path runs from membrane metadata
through fast_small, work_mask, remaining_any, multiple_bad and in_ready to a
pipeline clock enable. Its 5.851 ns data delay is 1.399 ns logic and 4.452 ns
routing (76.091%). The timing report does not identify the new corrector adder
as the worst path. This invalidates the earlier hypothesis that a late adder
gate necessarily caused the observed failure.

No timing replay or 6 ns energy is accepted for this failed route. Isolation
retention and switching savings remain unmeasured. Root is preparing one
separate folded-selection candidate; the first attempt remains preserved.
This report does not assert a board-power result, core-only energy result,
broad adaptive packing advantage or arithmetic novelty.
