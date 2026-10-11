The natural-latency trial preserves the frozen U13/I8 integer operation and changes only the legal pipeline organization. Its RTL and checker sources are pinned in each trial's preparation record. This note does not replace the frozen four-edge proof.

For each signed membrane U and current I, write U=32hU+rU and I=32hI+rI, with residues in0..31. A six-bit DSP field stores rU+rI, in0..62, so eight adjacent fields in one48-bit addition cannot carry into one another. Its bit5 is the field carry c; bits4..0 give r. The exact result is32(hU+hI+c)+r.

Signed13 U gives hU in[-128,127]; signed8 I gives hI in[-4,3]. Their base is[-132,130], and base+c is[-132,131], fitting signed9. A tail admitted only when actualU fits signed8 gives both high parts in[-4,3], base in[-8,6], and base+c in[-8,7], fitting signed4. The resulting signed9 tail sum can therefore sign-extend to the declared signed14 result exactly. Unadmitted tails are masked to zero and never retire as useful operations.

The DSP uses combinational A/B/C inputs and one enabled P register. The corresponding high-part metadata, count, and valid flag update at that same accepting edge. Reconstruction after the register reads aligned operands. When an output is blocked, the shared advance rule inhibits both DSP CEP and fabric metadata updates. An advancing invalid bubble clears valid while holding data; reset clears DSP P and fabric state and cancels outstanding work. These rules are exercised by the independent native protocol checker.

For k full positions and8-k U8 tail positions, ordered admission consumes at leastmin(k,N) and at mostmin(8,N) of a remaining N-value group. Tail admission stops at the first wide value. It does not reorder values or change the physical DSP field geometry. The next request can move a deferred value into an existing full position, giving progress for k>=1.

Explicit precomputed-metadata fabric storage is5+k*(b-4)+(8-k)*4: one valid bit, four count bits, k signed(b-4) high bases, and8-k signed4 high bases. Atb13,k8 this is77bits; atb13,k5 it is62bits. The predicted reduction is15bits. This formula excludes DSP internal P registers, fixture registers, LUTs, occupied slices, memory, routing, and energy. The route reports, rather than this expression, determine mapped resources.

Direct LUT arithmetic with the same policy registers k signed14 sums and8-k signed9 sums plus the same five control bits:77+5k fabric bits. Atk5 this is102bits; fixed eight full sums require117bits. DSP internal P48 storage belongs to the separately reported DSP resource. FabricFF savings cannot be converted directly into total silicon-area savings.

At the same clock, fixed eight full-range lanes can consume every prefix accepted by the adaptive policy and possibly more. The adaptive capacity rule cannot claim better burst latency or useful operations per DSP than that fixed full-eight implementation. The candidate trades tail high-part arithmetic and metadata against state-dependent service. The same-policy adaptive LUT trial tests the packing substrate separately from the admission policy.

Exactness here means the declared signed integer addition and checked neuron feedback agree. It does not certify an unspecified biological model, full leakage datapath, threshold/reset implementation, memory system, complete AdEx update, physical-board behavior, or energy of the one-edge cores.
