"""Update the existing editor source; preserve the historical signed12 draft."""
from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parents[3];DEST=P/'outputs/membrane_leakage_paper_draft.tex'
history=P/'outputs/history';history.mkdir(exist_ok=True)
old=history/'membrane_leakage_paper_draft_signed12_20261010.tex'
assert not old.exists();old.write_bytes(DEST.read_bytes())
text=r'''\documentclass[10pt,twocolumn]{article}
\usepackage[a4paper,margin=0.68in,columnsep=0.23in]{geometry}
\usepackage{amsmath,amssymb,booktabs}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage[hidelinks]{hyperref}
\setlength{\parindent}{1em}
\setlength{\parskip}{0pt}
\sloppy
\title{Exact Membrane-Range-Selected DSP Packing\newline for Variable-Coefficient SNN Leakage}
\author{Working research draft: authors and affiliations to be supplied}
\date{Validation snapshot: 10 October 2026}
\begin{document}
\maketitle
\begin{abstract}
We evaluate an exact FPGA leakage primitive that selects two narrow membrane operations or one wide operation from actual membrane values. All new comparisons retain signed sixteen-bit storage and interfaces, unsigned Q8 coefficients $\beta\in[0,256]$, and the declared result $\lceil\beta U/256\rceil$. Two consecutive signed nine-bit values sharing a coefficient occupy one DSP issue; other values use an exact sixteen-bit scalar fallback. On Artix-7, the selected implementation uses 62 LUTs, 44 FFs and one DSP, compared with 202 LUTs, 79 FFs and one DSP for a fixed full-domain split control. A public GLIF stream incurs a 1.08\% issue penalty; a vanilla LIF stream incurs 55.50\%, and its original half-leakage admits a cheaper exact shift control. Exhaustive arithmetic proofs and fed-back integer-neuron checks support exactness relative to the declared integer update. Representative activity is captured, but the new delayed-replay and energy comparisons are still running. Generic value-dependent packing and spill reconstruction are established prior art. This is a primitive research draft, not a complete accelerator or submission-ready result.
\end{abstract}

\section{Question and contribution boundary}
The question is whether actual membrane range can reduce the cost of exact leakage arithmetic while preserving a fixed wider legal domain. This targets membrane leakage multiplication within a neuron update. Synaptic accumulation, state memory, threshold/reset hardware and full accelerator integration are outside the measured primitive.

Stored membrane precision and voltage units are fixed. Adaptation changes the number of operations sharing a DSP issue. It does not halve membrane values, change an exponent, round away overflow bits, predict spikes or retune a trained coefficient. Numerical exactness is relative to the declared integer neuron; quantization relative to an original FP32 model is evaluated separately.

Actual-value narrowness detection and operation packing already appear in Brooks and Martonosi~\cite{brooks}. DSP multiplication packing and signed correction~\cite{dsppack}, modulo spill recovery~\cite{wide}, and runtime datatype packing~\cite{xtramac} are also established. The candidate contribution is the specific leakage decoder, membrane admission/fallback contract, and measured implementation/workload trade-off. We make no first-use claim.

\section{Fixed arithmetic contract}
Every new general core accepts the same operation:
\begin{equation}
 L(U,\beta)=\left\lceil\frac{\beta U}{256}\right\rceil,
 \quad -32768\le U\le32767,\quad0\le\beta\le256.
 \label{eq:leak}
\end{equation}
The membrane interface is signed sixteen-bit; the coefficient is unsigned nine-bit Q8. The intermediate product is sufficiently wide, and an arithmetic shift of $\beta U+255$ by eight implements ceiling for both signs. The result fits signed sixteen-bit. No saturation or wrapping is permitted by the reference.

Two consecutive available operands are paired when both actual membranes fit $[-256,255]$ and their coefficients match. Otherwise the first is issued alone. No matching search or reordering is used. A common two-stage elastic valid/ready interface retains result order under stalls. Common zero filtering is granted to all scheduling controls; its integration and bandwidth cost are outside the kernel energy comparison.

\section{Exact packed leakage}
For an admitted pair $(u_0,u_1)$ and common coefficient, the DSP computes
\begin{align}
 A&=(u_0+256)+2^{16}u_1,\\
 C&=255-256\beta+255\,2^{16},\\
 P&=A\beta+C=x+2^{16}y,\label{eq:packed}
\end{align}
where $x=\beta u_0+255$ and $y=\beta u_1+255$. The multiplicand fits the signed twenty-five-bit DSP48E1 input; the coefficient fits its eighteen-bit input. Since $-65536<x<65536$, the lower field contributes no spill or one negative borrow. Let $n=\mathbf1\{x<0\}$. The upper field is $T=\lfloor P/2^{16}\rfloor=y-n$.

The parity reference $r=(\beta_0\land (u_1)_0)\oplus1$ yields $n=P_{16}\oplus r$, where subscripts denote bits. The exact leakage results are
\begin{align}
 L_0&=\operatorname{uint}(P_{15:8})-256n,\\
 L_1&=\operatorname{int9}(P_{32:24})+
       \mathbf1\{n\land P_{23:16}=255\}.
\end{align}
The first expression restores the signed quotient from its low byte. In the second, adding the borrow changes the quotient only at the indicated byte boundary. Both include $\beta=0,256$ and the signed endpoints. Results are sign-extended to the common sixteen-bit interface. The same DSP computes a full-width singleton when admission fails.

A conventional nonoverlapping full-product layout at stride eighteen needs twenty-seven multiplicand bits; exploiting this restricted coefficient range reduces that straightforward requirement to twenty-six bits at stride seventeen. These are layout comparisons, not universal lower bounds. The same spill reference in~(\ref{eq:packed}) also reconstructs complete products via $x=(P\bmod2^{16})-2^{16}n$ and $y=\lfloor P/2^{16}\rfloor+n$. The useful specialization here is compact rounded-result decoding, not unique feasibility of exact packing.

E0 predicts the lower borrow before the DSP for $\beta\ge64$, using $u_0\le-4$ or the corner conditions $(-3,\beta\ge86)$, $(-2,\beta\ge128)$ and $(-1,256)$. E5 uses post-correction and admits all coefficients. These are implementation controls, not distinct generic arithmetic inventions.

\section{Matched fixed and fabric controls}
The primary one-DSP fixed control E1 decomposes $U=256h+r$, $0\le r\le255$:
\begin{equation}
 L(U,\beta)=\beta h+\left\lceil\beta r/256\right\rceil.
\end{equation}
Two unsigned residue products share the DSP; two fabric products recover the high contributions. E1 admits full sixteen-bit pairs when coefficients match. The identity is a strong constructive baseline, not an independently established novelty claim.

E2 uses two general LUT multipliers; E3 uses two scalar DSPs; E4 uses one scalar DSP. E7 is an independently exact general LUT control using the floor quotient plus a nonzero-remainder increment, with a $\beta=256$ bypass. E6 is an exact two-lane shift control restricted to $\beta=128$. These retain their actual DSP costs rather than using an invented aggregate area score.

E8 is a signed-nine-bit-only packing ablation on the same sixteen-bit ports, with range admission and the full-width fallback removed. Its caller must sign-extend from nine bits. E5--E8 measures the combined admission/wide-support cost after synthesis; it is not literal isolated controller area and E8 cannot replace a full-domain baseline. E7 and E8 hardware validation is pending.

\section{Public model contracts and exactness}
\subsection{GLIF ResNet18, CIFAR-10}
The official channelwise GLIF checkpoint~\cite{glif} uses two time steps. Synapses, batch normalization and readout retain FP32. One integer membrane unit is $1/256$ of the source voltage unit. Learned $a_0=1-\alpha(1-\tau)$ and $a_1=a_0(1-\gamma)$ are separately rounded nearest-even to Q8. Current, bias, reset and threshold use the same voltage unit. With previous spike $p$,
\begin{align}
 U'&=L(U,\beta_p)+I-B-Rp,\\
 s&=\mathbf1\{U'>\Theta\}.
\end{align}
Previous-spike reset remains deferred. Software uses wider exact diagnostic intermediates, with no clipping; every observed old and next state is checked against the fixed hardware domain.

The full 10,000-image scalar integer reference obtains 94.05\%, versus 94.03\% for its saved floating reference. There are 371 changed predictions, including 160 becoming correct and 158 becoming incorrect; this is not a packing accuracy gain. Across 24,903,680,000 updates, old membranes range from $-1378$ to $1529$ and next membranes from $-2038$ to $1752$. In 64-image fed-back execution, packed and scalar integer logits match bit for bit across 159,383,552 raw updates.

After common zero filtering, 79,246,135 updates require arithmetic; 99.0189\% fit signed nine-bit. E5 issues 42,785,698 operations, E1 42,327,032, E2/E3 39,623,132, and E4 79,246,135. Thus E5 has 1.852 useful results per DSP issue, a 1.0836\% issue penalty versus E1, and 46.0091\% fewer issues than E4. These are kernel issues, not full neuron-update cycles or burst-latency measurements.

\subsection{OTTT VGG11, CIFAR-10}
The authors' public vanilla LIF checkpoint~\cite{ottt} uses six time steps, $\tau=2$, threshold $\ge1$, and immediate subtractive reset. Its original leakage gives $\beta=128$, unchanged by packing. The integer contract is $U'=\lceil U/2\rceil+I$, followed by threshold $\ge256$ and subtraction of 256 on a spike. FP32 synapses and readout remain intact; effective currents are rounded nearest-even into units of $1/256$.

On the accepted 64-image run, floating, integer and packed references each classify 60 images correctly. Every integer state and spike and all final logits agree between scalar and packed feedback over 157,286,400 updates. Old membranes range from $-10220$ to $10562$, so the historical twelve-bit interface is insufficient; the fixed sixteen-bit interface covers the observed run. Only 53.3389\% of arithmetic operands fit signed nine-bit. E5 requires 101,715,765 issues against E1's 65,412,092: a 55.4999\% penalty. Exact shift leakage is mandatory as the model-specific baseline. The full 10,000-image run remains in progress; no final full-run accuracy is reported yet.

\subsection{Independent longer-recurrence validation}
A public BNTT/visual-explanations VGG11 TinyImageNet checkpoint~\cite{bntt} with thirty time steps is acquired and source-audited, but inference is pending. Its original old-membrane strict threshold, deferred subtractive reset, timestep batch normalization and Poisson input are preserved. The declared conversion uses $\beta=\operatorname{RNE}(0.99\cdot256)=253$. A predeclared random 64-image held-out subset is used without selection for packing. Its strong constant-specific control is $\lceil253U/256\rceil=U-\lfloor3U/256\rfloor$, implementable exactly without a DSP. Non-power-of-two leakage alone therefore does not justify a general multiplier. AdEx is not validated by these LIF tests.

\section{Implementation and activity protocol}
All new cores target Artix-7 \texttt{xc7a100tcsg324-1} in Vivado 2025.2, using a common 12 ns clock and falling-edge input phase. The fixture has 55 launch and 39 capture FFs: its 94 FFs are excluded from core area but included in energy. Native checks cover 360,487 general operations per main engine with and without stalls, plus shift-only and actual-model cohorts. Unstalled latency is two advancing edges; stalled tests retain held outputs and order. Mathematical checks include 67,371,008 signed-nine-bit pair cases and 16,842,752 full-domain scalar/split cases with no mismatch.

The new GLIF activity capture uses predeclared seed 417839 and 2,176 ordered contiguous windows stratified across the complete 64-image stream, totaling 262,528 nonzero operands. Saved logits and complete stream counts are recaptured exactly. Predeclared distribution gates pass: coefficient total variation 3.52\%, coarse membrane variation 0.90\%, and sample issue overhead 1.0821\% versus complete-stream 1.0836\%. This is a bounded representative capture, not a full-stream energy measurement or a confidence interval. Window restart/boundary effects are recorded. The current OTTT 7,335-operand sample is deliberately wide-value coverage and must be labeled stress activity, not representative activity.

Accepted energy requires exact known-pin replay under slow/max SDF, enabled timing checks, and complete physical-net SAIF annotation. Unknown physical activity and unsupported defaults are rejected. Vendor estimates include the complete common fixture at 25 degrees C; chip static power, memory, complete neuron updates and board measurements are outside scope. These new energy audits are still pending.

\section{Measured results and retained gaps}
\begin{table}[t]
\centering\small
\caption{Verified new fixed-sixteen-bit core routes at 12 ns. Fixture FFs excluded. E6 is restricted to $\beta=128$.}
\begin{tabular}{@{}lrrr@{}}
\toprule
Implementation&LUT&FF&DSP\\\midrule
E0 adaptive pre&71&44&1\\
E1 fixed split&202&79&1\\
E3 scalar DSP pair&35&56&2\\
E4 scalar DSP&13&29&1\\
E5 adaptive post&62&44&1\\
E6 shift pair&35&70&0\\
\bottomrule
\end{tabular}
\label{tab:area}
\end{table}
E5 uses 69.31\% fewer LUTs and 44.30\% fewer FFs than E1 at equal one-DSP budget and the same full input domain. Admission and correction are included. This does not imply universal FPGA area superiority: E4 is smaller but produces one result per issue, and E3 uses fewer LUTs and provides two independent results with two DSPs. All-wide bursts favor E1; we do not claim universal burst-latency improvement.

The original E2 fixed-sixteen-bit route hit a Vivado \texttt{Synth 20-411} error after completed synthesis; a source-identical checkpoint retry is underway. This tool failure supplies no accepted route or energy number. Historical signed-twelve-bit E2 passed functional replay and static timing but failed delayed replay at rows 914 and 2836. Internal inspection localizes a stable wrong value inside a CARRY4 delayed model; a correctly annotated isolated cell passes. The exact event-scheduling cause remains unproven. E7 is an independent stronger LUT implementation; its success cannot retroactively resolve E2's diagnostic.

Earlier twelve-bit values of 53 versus 122 LUTs and 34.4\% lower energy were from a separate 17,408-operand prefix sample. Its coefficient distribution did not pass the later representative audit. Those results remain historical implementation/sample evidence and are not substituted for the new fixed-sixteen-bit measurements.

\section{Related work and applicability limits}
FireFly~\cite{firefly} uses fixed twelve-bit SIMD additions and spike-controlled multiplexers; its original $\tau=2$ leakage is shift-based. Our fixed split and LUT controls are built for the same leakage primitive, not reproduced FireFly accelerators. Its whole-accelerator throughput or accuracy cannot be compared directly with kernel issues or fixture energy. Testing public LIF and GLIF checkpoints supports applicability but is not reproduction of FireFly's trained SCNN models.

The inspected DSP-Packing, Arithmetic Packing, XtraMAC, Brooks--Martonosi and released UDP multiplier code provide substantial ancestry. Full methods for four relevant papers remain access-limited, including dynamic DSP packing and six-signed multiplication work. The bounded review has not identified this exact implemented leakage/admission conjunction, but it does not establish absence or priority. The same stored-state policy must remain compared with strong fixed and fabric alternatives.

\section{Conclusion}
The exact membrane-range-selected kernel has a verified fabric saving at equal one-DSP budget, fixed sixteen-bit precision and a small GLIF issue penalty. Vanilla LIF demonstrates an unfavorable range profile and an essential cheap shift alternative. Representative delayed replay, energy, full vanilla-LIF evaluation, longer-recurrence validation and the narrow-only cost ablation remain running or pending. A focused primitive paper may be defensible if those results support the scoped trade-off; strong-publication readiness is not yet established.

\begin{thebibliography}{9}\small
\bibitem{brooks} D. Brooks and M. Martonosi, ``Value-Based Clock Gating and Operation Packing: Dynamic Strategies for Improving Processor Power and Performance,'' ACM TOCS, vol. 18, no. 2, pp. 89--126, 2000. \url{https://doi.org/10.1145/350853.350856}.
\bibitem{dsppack} J. Sommer et al., ``DSP-Packing: Squeezing Low-precision Arithmetic into FPGA DSP Blocks,'' FPL 2022. \url{https://arxiv.org/abs/2203.11028}.
\bibitem{wide} ``Arithmetic Packing on Wide Integer Datapaths in DSP Primitives of Modern FPGA Devices,'' 2026. \url{https://arxiv.org/abs/2606.11065}.
\bibitem{xtramac} F. Yu et al., ``XtraMAC: An Efficient MAC Architecture for Mixed-Precision LLM Inference on FPGA,'' 2026. \url{https://arxiv.org/abs/2605.06052}.
\bibitem{firefly} ``FireFly: A High-Throughput Hardware Accelerator for Spiking Neural Networks with Efficient DSP and Memory Optimization.'' \url{https://arxiv.org/abs/2301.01905}.
\bibitem{glif} ``GLIF: A Unified Gated Leaky Integrate-and-Fire Neuron for Spiking Neural Networks,'' NeurIPS 2022. \url{https://github.com/CAS-CLab/Gated-LIF}.
\bibitem{ottt} ``Online Training Through Time for Spiking Neural Networks,'' NeurIPS 2022. \url{https://github.com/pkuxmq/OTTT-SNN}.
\bibitem{bntt} Public BNTT/visual-explanations TinyImageNet VGG11 implementation and checkpoint; Scientific Reports 2021. Exact source and assets pinned in the benchmark evidence bundle.
\end{thebibliography}
\end{document}
'''
DEST.write_text(text,encoding='utf-8')
print(json.dumps(dict(updated=str(DEST),historical_copy=str(old),historical_sha256=hashlib.sha256(old.read_bytes()).hexdigest(),new_sha256=hashlib.sha256(DEST.read_bytes()).hexdigest())))
