# Read-only audit: provisional high-part selection

Audited source: `guard_add_selective.sv`, SHA256
`b5c7d724d642b2310c4e447eabccaf965a3aa520aaf2e04c5f93accd5dbb9e48`.
The source and existing evidence were not modified. This is an invariant proof
for one proposed optimization, not an RTL simulation or routed result for it.

## Proposed change

The current provisional high value is
`fast_small ? small_extension : (fast_copy ? hu5 : 5'd0)`.
It can be replaced by `fast_small ? small_extension : hu5`.
Retain `fast_copy` in the bad-lane predicate. Retain the original controller,
correction arithmetic, masks, metadata, DSP layout, and interfaces.

For a valid lane, there are three exhaustive cases:

- `fast_small` is true. Both forms return the same exact small high part.
- `fast_small` is false and `fast_copy` is true. Both return the same exact
  sign-extended membrane high part `hu5`.
- Both are false. The lane is bad. Its provisional high part is hidden until
  the shared corrector patches it; either initial value is unobservable at a
  valid output handshake.

Fixed V0/V2 use `parallel_answer`, so provisional high selection does not
affect their outputs. The proposed change affects no policy decision and
therefore changes no request count, correction job, freeze, or output timing.

## Output assembly invariant

When a pending v2 request begins output assembly, its DSP result, high metadata
and count describe the same accepted window. Let B be its valid bad-lane mask.
The first assembly edge writes exact low bits for every valid lane and zero
for every unused tail. It writes exact fast-path high bits for every lane
outside B. If B is nonempty, the selected first bad lane receives its exact
corrected high part on that same edge; this later nonblocking part-select write
overrides the provisional high bits in the same sequential block.

For zero or one bad lane, all valid highs are then correct and output valid
may assert immediately. For two or more bad lanes, output valid is explicitly
cleared and the remaining bad mask is retained. The pipeline, DSP P, count2
and high metadata are frozen while additional lanes are corrected.

During busy assembly, pending_mask is exactly the set of uncorrected bad
lanes. Each correction edge patches one selected high part and removes its
bit. Already correct highs and all low bits remain intact. Output valid remains
zero while any pending bit remains. On the last correction edge, the final
patch and assertion of output valid occur together. Although pipeline metadata
may advance on that edge, the correction expression uses the old request's
registered values under nonblocking assignment semantics.

Thus every bad high is patched before the complete window becomes visible.
Replacing an unobservable provisional zero with hu5 preserves this invariant.

## Stalls, reset and tails

Output writes occur only when `output_space = !out_valid || out_ready`. A valid
stalled output therefore retains its data, count and valid bit. Starting a
new partial assembly can consume a previous ready output once, then clears
valid; no partial window or repeated previous window is presented as valid.

Reset has priority over output_space and clears output valid/data/count,
busy and pending_mask, while other blocks clear all pipeline and DSP state.
An abandoned partial window cannot later become valid without a new request.

The bad mask explicitly requires `cnt2 > lane`. An unavailable binary tail
cannot become a correction job. Initial output masking writes its entire
12-bit lane to zero, and subsequent correction writes select only valid bad
lanes. Arbitrary tail operand bits therefore remain hidden and cannot affect
other DSP fields because the eight-bit residue fields cannot intercarry.

## Measurement and verification requirements

The optimization removes one condition from the provisional-data path. A
LUT or timing benefit is possible but unmeasured; synthesis may already absorb
parts of this condition into other logic. There is no switching or energy
claim. Hidden provisional values can change activity even though outputs do not.

If root approves an implementation, preserve the current source and evidence
and use an isolated source cohort. Require the same full11 and signed8-current
profiles, integer oracle, order, stalls, reset-during-busy, poisoned tails and
physical-clock checks. Because control is unchanged, corresponding complete
retirement text, including clock columns, should also match the frozen source.
Only route the new cohort after functional source/evidence pins are frozen.
