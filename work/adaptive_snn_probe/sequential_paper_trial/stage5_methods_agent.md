# Methods draft: exact membrane-aware leakage packing

## Arithmetic contract and adaptation

The primitive evaluates the integer leakage term

\[
L(U,\beta)=\left\lceil\frac{\beta U}{256}\right\rceil,
\quad U\in[-2048,2047],\quad \beta\in\{0,\ldots,256\}.
\]

Thus the coefficient is an unsigned nine-bit Q8 value and the full membrane input is signed twelve-bit. Ceiling is part of the declared integer neuron model. Packing must preserve this result exactly, including negative inputs; it introduces no further quantization or rounding change. The mechanism changes the DSP operand format and number of operations issued together. It retains the membrane's numerical unit and stored value.

For two consecutive available operands, the adaptive post-corrected implementation (E5) issues a pair only when both actual membranes fit signed nine-bit, \([-256,255]\), and their coefficients match. Otherwise it consumes the first operand in the full twelve-bit format. It preserves stream order and does not seek matching coefficients elsewhere in the stream. A wide membrane therefore reduces the admitted operation count rather than triggering precision loss. A coefficient mismatch also prevents pairing. All-zero leakage, from either \(U=0\) or \(\beta=0\), receives the same stable bypass in every software scheduling control; its bandwidth and integration costs are outside the measured leakage primitive.

## Exact pair construction and spill recovery

For an admitted pair \((u_0,u_1)\) with shared coefficient \(\beta\), the DSP computes

\[
\begin{aligned}
A&=(u_0+256)+2^{16}u_1,\\
C&=255-256\beta+255\,2^{16},\\
P&=A\beta+C.
\end{aligned}
\]

The multiplicand fits signed twenty-five-bit, the coefficient fits the DSP's positive signed eighteen-bit input, and the multiply-add fits the forty-eight-bit result. Expanding gives \(P=x+2^{16}y\), where \(x=\beta u_0+255\) and \(y=\beta u_1+255\). Since \(-65536<x<65536\), the low term can borrow at most one unit from the upper field. Denote that borrow by \(n=1\) when \(x<0\), and zero otherwise. A modulo-two reference recovers it from the DSP result:

\[
n=P_{16}\mathbin{\oplus}\big((\beta_0\land (u_1)_0)\mathbin{\oplus}1\big),
\]

where subscripts denote individual bits. The exact outputs are

\[
\begin{aligned}
L_0&=\operatorname{uint}(P_{15:8})-256n,\\
L_1&=\operatorname{int9}(P_{32:24})+
\mathbf{1}\{n=1\ \land\ P_{23:16}=255\}.
\end{aligned}
\]

The final increment restores a boundary crossing caused by the low-field borrow. Both outputs are sign-extended to the twelve-bit interface. The full-format fallback computes \(P=\beta U+255\) and returns its arithmetic right shift by eight. This equals the same ceiling rule throughout the legal input domain.

The precompensated variant (E0) is a control: for \(\beta\ge64\), a small membrane-and-coefficient predicate predicts the borrow before the multiply-add and incorporates it in \(C\). E5 instead recovers the borrow after the DSP and admits all legal coefficients. Exact correction and modulo references are established arithmetic techniques; the candidate contribution is their integration with this membrane-dependent admission policy and its measured implementation trade-off.

## Matched controls and hardware interface

The principal equal-DSP-budget control computes two full-width leakage operations through fixed residue/high-part splitting. For each membrane, write \(U=256h+r\), with \(r\in[0,255]\). Then

\[
L(U,\beta)=\beta h+\left\lceil\frac{\beta r}{256}\right\rceil.
\]

Two unsigned low residues share one DSP, while two fabric products retain the high terms exactly. Like the adaptive implementation, this control consumes one operand when adjacent coefficients differ. Its ability to process a full-width pair is retained. Additional controls use two independent LUT multipliers, two scalar DSPs, or one scalar DSP. Every control implements the same twelve-bit membrane and Q8 coefficient domain; a permanently narrow-only implementation is insufficient as the primary comparison.

Each RTL implementation uses the same two-stage elastic interface with valid/ready flow control and a returned consumed count. It preserves ordered results and held outputs under backpressure. The common timing fixture contains input-launch and output-capture registers. Core area is reported separately from that fixture, while activity-based dynamic energy includes it. This is a leakage primitive experiment, not a complete neuron engine or accelerator. Memory traffic, range-screen integration in a larger machine, synaptic accumulation, threshold/reset latency and board power are not inferred from its issue counts.

## Application-backed integer reference

The application is the official channelwise GLIF ResNet18 CIFAR-10 checkpoint with two time steps, pinned to repository commit `60638b28ff8b688b51867e7dd44f1e065d4892b0`. GLIF is a gated LIF-family model; this evaluation does not implement vanilla LIF or AdEx. Convolution, batch normalization and readout remain in the source FP32 implementation. Only the neuron arithmetic and stored membrane are quantized, without retraining or coefficient substitution.

One integer membrane unit represents \(1/256\) of the source voltage unit. Learned parameters define \(a_0=1-\alpha(1-\tau)\) and \(a_1=a_0(1-\gamma)\). The two previous-spike contexts are separately rounded to nearest-even Q8 coefficients \(\beta_0,\beta_1\). Bias \(B\), deferred reset \(R\) and threshold \(\Theta\) are rounded nearest-even into membrane units. The source effective input-current expression remains FP32 and is rounded into those units. With previous spike \(p\in\{0,1\}\), the integer update is

\[
\begin{aligned}
L&=\lceil\beta_p U/256\rceil,\\
U_{\mathrm{next}}&=L+I-B-Rp,\\
s&=\mathbf{1}\{U_{\mathrm{next}}>\Theta\}.
\end{aligned}
\]

No additional immediate reset is introduced: the source model applies its previous-spike reset on the following update. States start at zero for each inference. Software accepts signed twenty-four-bit state/current and uses int64 intermediate arithmetic without saturation. Observed full-test states fit the hardware's signed twelve-bit domain, but this observation is not a proof for every possible input image or retrained model.

The scalar integer reference is evaluated on all original 10,000 test images and compared with the floating reference. This establishes the effect of the declared neuron quantization separately from packing. A first-batch independent NumPy implementation checks states and spikes. Ordered packed leakage is then fed back into the neuron update on the first 64 original images, without retuning; post-corrected pair results are independently compared with the same scalar leakage values. This is not a claim that a full 10,000-image packed RTL inference was executed.

## Validation and measurement boundaries

The pair algebra is exhaustively checked for both signed nine-bit operands over every legal Q8 coefficient; scalar and fixed-split algebra cover the full signed twelve-bit domain. Native RTL checks include sign/range/coefficient boundaries, actual-model operands, and stalls. Routed timing and activity results require matched source/checkpoint/netlist hashes and exact delayed pin replay, rather than a timing-summary pass alone. Failed routes or replay attempts remain part of the evidence.

Activity capture uses the predeclared first 64 nonzero operands per recorded layer/time-step/batch frame in their original order. Consequently, energy is a vendor estimate for that captured sample and fixture, not an unbiased full-network energy estimate. Whole-stream scheduling counts are reported separately. All-wide bursts and coefficient mismatches reduce adaptive utilization; fixed full-width pairing can serve those cases more quickly. Accuracy improvement, universal burst-latency improvement and whole-accelerator speedup are excluded claims.

# Related work draft

[DSP-Packing](https://arxiv.org/html/2203.11028#S7) covers packed arithmetic, corrections and carry-isolated SNN additions. It establishes that packing and exact carry handling alone are insufficient novelty claims. [FireFly](https://arxiv.org/html/2301.01905v5) uses fixed twelve-bit DSP addition lanes with spike-controlled multiplexers. That differs in both arithmetic operation and selection criterion from membrane-range admission for coefficient multiplication. Its accelerator-level throughput and accuracy are not matched primitive baselines. [FireFly-S](https://arxiv.org/html/2408.15578v1) implements low-bit spike arithmetic in LUTs, supporting a fabric arithmetic comparison but not identifying a published LUT implementation of the present leakage operation.

[XtraMAC](https://arxiv.org/html/2605.06052) supports runtime datatype-dependent packing in LLM arithmetic. A broad claim of adaptive DSP packing is therefore inappropriate. [Arithmetic Packing on Wide Integer Datapaths](https://arxiv.org/html/2606.11065) describes signed packing and exact spill tracking using modulo references and external high accumulators. The present post-correction shares that arithmetic lineage; its distinguishing research question is whether the actual membrane range permits a useful variable operation count with less fabric correction hardware under a fixed one-DSP budget.

The accessible abstracts of [UDP](https://doi.org/10.1145/3748173.3779194) and [Efficient DSP Packing Method for Neural Network Accelerator](https://doi.org/10.1109/ICFPT64416.2024.11113473) indicate further overlap with low-bit packing and lossless signed multiplication. Their full methods were not available for detailed equivalence review. The bounded literature audit has not identified the exact membrane-driven nine-bit-pair/twelve-bit-fallback leakage policy; this is a potential narrow contribution, not proof of first use. A final submission should distinguish the policy, arithmetic contract and measured hardware frontier from established generic guard/correction constructions.

The application source is [Gated-LIF](https://github.com/CAS-CLab/Gated-LIF), accompanying [Gated Leaky Integrate-and-Fire Neurons](https://openreview.net/forum?id=UmFSx2c4ubT). The benchmark demonstrates use with learned LIF-family dynamics, while validation on ordinary LIF, AdEx, more checkpoints and additional hardware targets remains outside the current evidence.
