# Exact adaptive DSP packing for SNN membrane leakage

This public research handoff explains and implements a compact FPGA leakage primitive. Actual membrane values select **two narrow operations or one exact full-width operation** per DSP issue. The stored membrane remains signed16 throughout.

**The contribution is the integrated exact leakage decoder and membrane admission mechanism, with measured trade-offs.** It is a focused circuit study for a potential ISCAS submission. It is not an accepted paper or a complete SNN accelerator.

## Start here

- [Mentor reading guide](docs/START_HERE.md)
- [Editable explanatory slides](slides/mentor_briefing.pptx) and [slide notes](slides/slide-notes.md)
- [IEEE paper source](paper/membrane_leakage_paper_draft.tex)
- [Current verified results](docs/RESULTS.md)
- [Submission recommendation and remaining author checks](docs/READINESS.md)
- [Complete user-facing conversation export](chat/conversation.md), [offline HTML](chat/conversation.html), and [shared chat snapshot](https://chatgpt.com/s/cx_6acb1c46e7688191b3cd0aa437cddd1c)

## What operation does it pack?

```
L(U, beta) = ceil(beta * U / 256)
U: signed16, -32768 through 32767
beta: unsigned Q8 coefficient code, 0 through 256
```

This is the membrane **leakage multiplication** within a neuron update. Synaptic accumulation is a different operation. Converting a floating neuron into this integer contract can change predictions. Packing then preserves the declared integer results exactly.

## What makes it adaptive?

The core examines two consecutive available operands at runtime. When both membranes lie in `[-256,255]` and their beta values match, it consumes two. Otherwise it consumes one and computes the full signed16 result. The output count tells the external source how many operands to advance. No voltage rescaling or exponent changes occur.

```
(-3, 5), beta=128: narrow pair gives (-1, 3) in one DSP issue
381, beta=78: wide singleton gives 117 exactly
```

An overlapping product layout saves DSP input bits. A parity bit recovers the lower field's signed borrow, and a compact correction recovers the exact rounded upper result. [Derivation, boundary example and architecture](docs/MECHANISM.md).

## Quick examples

```
python examples/run_examples.py
python examples/check_arithmetic.py
python scripts/verify_release.py
```

These use Python's standard library. The optional `python scripts/run_rtl_smoke.py` requires Icarus Verilog and exercises the unmodified core with a labeled behavioral DSP model. [Reproduction scope and original model assets](docs/REPRODUCIBILITY.md).

## Verified evidence

The adaptive E5 core uses **62 LUTs, 44 FFs and one DSP** at the selected matched 12 ns route. The fixed full-domain split E1 uses 202 LUTs,79 FFs and one DSP. Both implement the same declared general coefficient arithmetic.

On the evaluated GLIF 64-image stream, E5 needs **46.01% fewer leakage issues than a one-DSP scalar**, and 1.0836% more than fixed split packing. Representative fixture dynamic energy is 21.599 pJ/scalar, compared with 24.648 for the one-DSP scalar and 55.308 for fixed split. The two-DSP scalar pair uses 21.371 pJ/scalar, so this is approximately energy parity with half the DSP count, not universal superiority.

Public-model validation covers GLIF ResNet18/CIFAR10/T2, OTTT VGG11/CIFAR10/T6 and an independent BNTT-style VGG11/TinyImageNet/T30 model. Every tested packed integer state/spike/logit matches its scalar integer reference. Full-test and 64-image scopes differ and are stated in [results](docs/RESULTS.md).

The added checkpoint-specific GLIF control supports all 33 trained coefficient codes using a shared exact add/sub pair: **375 LUTs, 82 FFs, zero DSPs and 96.758 pJ/scalar** on the same representative capture. Its full timed replay and independent physical audit pass. This is one measured construction, not an optimality bound for every constant implementation.

## Operating limits

Exact half-leakage shifting outperforms E5 for OTTT's beta 128. Wider membrane streams reduce pairing opportunities. E5's issues exceed fixed split on OTTT and TinyImageNet. Operand memory and variable-consumption source integration remain outside reported core area/energy. There is no demonstrated end-to-end burst-latency improvement or packing accuracy gain.

Original LUT E2 failed delayed replay and contributes no accepted energy. The independent exact E7 LUT control passes the stricter replay/activity audit. Failed evidence is retained. Three relevant original full methods remain unavailable, so this repository does not claim proven first-ever status. [Prior-work distinctions](docs/PRIOR_WORK.md).

## Repository organization

`rtl/` provides convenient exact copies of the current core and controls. `examples/` explains the arithmetic with executable integers. `scripts/` contains portable release and RTL-smoke commands. `paper/`, `slides/`, `docs/` and `chat/` provide the mentor handoff. `work/adaptive_snn_probe/` preserves the complete research-authored source archive and lightweight result receipts, including earlier discarded approaches. `research_reports/` preserves experiment summaries.

The release manifest checks shipped bytes. Historical receipts retain their original paths and hashes rather than pretending a Git clone contains every large raw artifact. Vendor libraries, datasets, weights, routed checkpoints and complete SAIF files remain external. See [source/release notice](NOTICE.md).
