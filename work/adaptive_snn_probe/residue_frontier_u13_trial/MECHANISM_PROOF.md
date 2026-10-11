# Exact membrane-driven admission over an invariant residue layout

This is an arithmetic and scheduling argument for the declared integer
primitive. Native RTL tests check its implementation. It does not waive a
failed routed timing replay or establish correctness on a physical board.

For each lane write U = 32 hU + rU and I = 32 hI + rI, using arithmetic
right shift for h and the low five bits for r. This is Euclidean division:
rU and rI are integers in [0,31], including for negative operands. Pack
eight residues in eight six-bit fields of one 48-bit DSP addition. Each
field sum s = rU+rI is in [0,62], so there is no carry into another field.
Let c=s[5] and r=s[4:0]. The independently reconstructed result is
32*(hU+hI+c)+r = U+I. A carry from the low five bits is part of this
identity, not an approximation or exceptional recovery.

For full signed13 U and signed8 I, hU lies in [-128,127] and hI in
[-4,3]. The precomputed base hU+hI lies in [-132,130]; after the residue
carry, high lies in [-132,131]. Both fit signed9, and concatenating
that signed9 high part with the five-bit residue yields the exact
signed14 output. For U restricted to signed8, both high operands lie
in [-4,3], base lies in [-8,6], and base+c lies in [-8,7]. Signed4
metadata and a signed9 reconstructed result suffice. Its sign extension
to the common fourteen-bit result preserves U+I exactly, even when
the result itself no longer fits signed8.

The first five physical lane positions use the full signed9 high path.
Each following position uses the signed4 high path and is consumed only
when its actual U is a sign extension of its low eight bits. Admission
stops at the first wide candidate in the tail. Its value is retained at
the source; subsequent requests shift that same neuron into one of the
five full positions. The DSP field geometry and arithmetic are unchanged.
There is no mantissa/exponent, scaling, clipping, data reordering or
dedicated overflow accumulator. The actual membrane controls which
ordered prefix is legal in this trimmed datapath.

With N remaining values, a successful request consumes between min(5,N)
and min(8,N). Thus it makes progress whenever the output is allowed to
advance and the source offers values; it cannot livelock on a wide
neuron. The number of requests for a group lies between ceil(N/8) and
ceil(N/5). Pipeline backpressure freezes residue, metadata, validity,
count and result together. Reset cancels all validity; masked output
positions are zero. These protocol properties are separately checked
under stalls, reset, unused-lane poison and four-advancing-edge latency.

The same-clock full-width fixed8 implementation has at least the same
capacity for every available window. Under the same supply and group
drain assumptions, this candidate cannot claim a service-latency gain
over that baseline. Its proposed benefit is less full-range recovery
hardware while retaining nearly eight-lane service on favorable ranges.
Wide tails increase requests. A two-value source cap prevents any
packing-capacity gain, even if the arithmetic hardware remains different.

For this four-edge pipeline, before mapping, the explicit core storage
for a k-full-lane, (8-k)-U8-tail design of full input width b>=8 is
268 + 4*k*(b-8) flip-flop bits. The constant 268 comprises 80 residue
input bits, 96 narrow high-metadata bits, 72 independent result bits,
and 20 validity/count bits. Each extra full-range bit costs three
metadata pipeline bits and one output bit per full lane. Narrow result
sign-extension bits are wires. Therefore the expected reduction from
full8 is 4*(8-k)*(b-8) FF bits: 36 at b=11,k=5 and 60 at b=13,k=5.
This is a storage model, not a LUT, slice, energy, Fmax or total-area
prediction. The routed records determine whether these counts survive
mapping. DSP-internal registers and the common measurement fixture are
outside this explicit core-FF formula and must not be subtracted from
silicon area or power.

The original IF application has a finite-horizon width justification.
For a neuron with binary incoming spikes and fixed signed weights,
let L be the sum of negative weights and H the sum of positive weights.
Every current lies in [L,H]. Starting at zero, positive-threshold
subtractive reset gives state after t updates in [tL,tH]. Before any
of the first 32 IF updates, U therefore lies in [31L,31H]. Across the
saved weights, the certified global lower bound needs signed13.
This supports the tested 32-step domain; it is not an unbounded IF
certificate. Stronger static weight/timestep intervals can justify
some narrow values, and are an optimistic service-policy control.

The exact residue/high identity and guarded packed addition are established
ideas. The candidate distinction being investigated is the low-cost
actual-membrane ordered admission rule and its reuse of existing full
lanes to handle wide candidates. No absence-of-prior-art or generic
adaptive-packing-first claim follows from this proof.
