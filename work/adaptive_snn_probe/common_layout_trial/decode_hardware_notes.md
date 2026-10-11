# Isolated provisional-high decode trial

guard_add_selective_decode.sv renames the module and makes one expression
change from the frozen selective parent:

    fast_small ? small_ext : (fast_copy ? hu5 : 0)
    fast_small ? small_ext : hu5

No layout, predicate, correction selection, arithmetic fallback, register,
controller, valid/count behavior, or operand domain changes. fast_copy still
participates in bad_mask. All four V/profile mappings remain identical.

## Exactness argument

For a valid fast_small lane, the expression is unchanged. For a valid lane
that satisfies fast_copy but not fast_small, both expressions select hu5.
The only differing provisional highs belong to valid bad lanes. If there is
one bad lane, its exact corrected high overwrites the provisional high at
the same output edge. With multiple bad lanes, out_valid remains zero while
the controller patches every bad high; it becomes one only after the last
pending bit is removed. Unavailable tails are still explicitly zeroed and
cannot enter the pending mask. Reset cancels a partial assembly; output
backpressure holds every already-valid output exactly as before.

Consequently completed output values, output order, clock columns, input
acceptances and retirement latencies must remain byte-identical to the
parent. Invalid partial out_data may differ. The fixed profiles do not use
fast_answer, so this expression changes no reachable fixed output behavior.

## Measured motivation and limits

The parent V3 route used 147 LUTs / 268 external FFs / one DSP, with
WNS +0.108 ns and WHS +0.132 ns at the matched 6 ns target. Its worst
paths_max.rpt path runs from high_u2_reg[12] through fast_small, work_mask,
selected_lane, the selected-high operand mux, shared correction, and output
patch selection to out_data_reg[34]. It contains seven logic levels and
5.898 ns data-path delay, with 4.107 ns (69.6%) attributed to routing.

Removing the redundant provisional zero selection may save output decode
logic and routing pressure. It does not remove the classifier, priority
selector, selected-operand mux, or shared correction from that critical
path. Area and timing improvement are hypotheses until this isolated core
passes the same eight suites, byte comparison, sixteen SNN replays and
matched shared-profile routes. No winner is claimed.

The parent remains SHA256
b5c7d724d642b2310c4e447eabccaf965a3aa520aaf2e04c5f93accd5dbb9e48.
The isolated core is SHA256
c955bb5c8b2fad4ee374fc1dfe71b166305a75e3f1aa8bf3944f02d64fdf4593.
This agent created only the new core and this note and launched no HDL jobs.
