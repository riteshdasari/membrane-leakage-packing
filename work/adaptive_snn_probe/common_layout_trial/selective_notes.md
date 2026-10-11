# Selective exact high correction

guard_add_selective.sv uses the same six immutable eight-bit unsigned-residue
DSP fields and exact signed12 output as guard_add_common. The adaptation
selects which high results require a full corrector. It does not change DSP
lane count, field positions, or persistent membrane representation.

## Matched profiles

- V0: full signed11 U/I, six parallel signed5 high correctors.
- V1: the same full signed11 U/I domain, one shared high corrector.
- V2: signed11 U and statically signed8 I, six parallel high correctors.
- V3: the same statically signed8 I domain, one shared high corrector.

All retain the original 66-bit U/I input buses. V2/V3 require every valid I
to be sign-extended signed8; bits[10:8] must equal I[7]. Binary unavailable
tail slots need not obey that restriction. The static current8 specialization
is a declared domain reduction shared equally by its fixed/adaptive pair.
It must not be evaluated as a full signed11 fallback design.

Nominal external FF counts, before synthesis: V0 316, V1 323, V2 262,
V3 269. The shared versions add busy plus six pending-mask bits. All use
84 residue-capture bits, 72 output bits, 12 count bits, and four valid bits;
high metadata consumes 144 bits (full current) or 90 (static current8).
DSP-internal registers are excluded. Synthesis may remove constants or
alter counts; these estimates are not measured hardware results.

## Exact fast union

For each lane let hU/hI be signed4 upper fields, c the residue sum bit7,
and low the residue sum bits[6:0]. The exact result is
{signed5(hU+hI+c),low}. Signed8 membership is equivalent to h being 0 or -1.

When U and I both fit signed8, hU=-sign(U8) and hI=-sign(I8), so
H=c-sign(U8)-sign(I8). This lies in [-2,1] and is computed as signed2 then
sign-extended to five bits. Otherwise, when I fits signed8 and c=sign(I8),
hI+c=0 and H=hU. The union of those two cases needs no full high addition.
Every valid lane outside that union uses the shared exact signed5 corrector.
The full-current profiles retain all four bits of hI. Static-current8 profiles
retain only its sign and reconstruct hI as four identical sign bits.

In shared static-current8 V3, every selected bad lane has failed the fast-copy
condition, so c!=sign(I8). Its fallback is therefore exactly hU+1 for a
nonnegative current, or hU-1 for a negative current. V3 uses that equivalent
signed5 increment/decrement, removing the selected DSP-carry mux from its
fallback path. Fixed V2 still computes hU+hI+c for every lane, and full-domain
shared V1 retains the generic full high sum. This specialization changes no
domain, fast certificate, correction mask, latency, or output value.

This condition depends on actual U, I, and the DSP carry. It broadens the
earlier signed7 certificate and preserves every output bit. No rounding,
overflow loss, rescaling, or stored exponent is introduced.

## Controller and observable interface

The input is ordered, take=available, and narrow_mode=0 for every profile.
Input acceptance uses in_valid && advance && available!=0. At acceptance
the residue and high stage0 capture; subsequent global advancing edges
capture DSP A:B/C with high1, then DSP P with high2. The pending output is
identified by v2 and cnt2. All inputs, intermediate stages, and DSP registers
freeze together when advance=0.

For k bad lanes in that output, the first correction is fused into its normal
output stage. If k>1, the DSP P/high2/count2 stages remain frozen while one
additional high is written per physical clock. The controller holds the
remaining lane mask and selects the lowest pending lane. It writes low bits
and all fast highs once, then only the remaining corrected high fields. On
the last correction it advances once, consumes v2, and can accept the next
input; there is no retention FIFO or output reordering. The output becomes
valid only when all corrections are complete. This adds max(k-1,0) physical
clocks per request under continuous input and ready output.

Output writes occur only when !out_valid || out_ready, preserving every
stalled valid result. If a prior completed output is ready on the first
correction-freeze edge for the next pending result, that prior output retires
once and out_valid is cleared while the next partial result is assembled.
Thus a valid output can retire on an edge with global advance=0. The original
testbench stores its global-step counter immediately before acceptance;
acceptance, DSP operand capture, DSP sum capture, and completed output capture
then contribute four advancing events before retirement. This convention
still counts four when retirement coincides with a later correction-freeze
edge. Verification should preserve that convention and check it in RTL; the
handshake edge itself need not advance the internal pipeline.

Debug signals visible hierarchically: advance, accept, correction_step,
busy, pending_mask, bad_mask, work_mask, selected_lane, selected_mask, and
next_mask. correction_step is always zero in fixed profiles. In shared
profiles correction_step && !advance counts extra correction-freeze clocks.
Reset clears every stage, output and controller bit, including a partial
assembly. Unused output lanes remain zero.

## Measurement limits

Sharing removes five full high correctors but adds priority selection,
metadata/carry multiplexing, fast-case recovery, output write selection, and
controller state. Whether the whole kernel saves LUTs or meets timing must
be measured. The fixed current8 comparator is mandatory when using the
certified current8 model domain. The strong retimed hybrid and LUT-only
references remain relevant. More DSP-covered additions and plausible
novelty alone do not establish an efficiency advantage.

Only this new core and this note were created by the hardware agent. The
frozen common-layout core and previous evidence were not modified. No HDL
tools, heavy jobs, downloads, or user applications were launched or altered.
