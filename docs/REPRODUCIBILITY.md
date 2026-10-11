# Reproduction levels

## Portable arithmetic example

Python 3.10 or later, with no external packages:

```
python examples/run_examples.py
python examples/check_arithmetic.py
python scripts/verify_release.py
```

These commands are portable and leave the preserved evidence unchanged. They demonstrate the algebra and audit the release. They do not rerun full model inference or certify a new routed FPGA implementation.

## Portable RTL smoke simulation

With Icarus Verilog on PATH:

```
python scripts/run_rtl_smoke.py
```

The portable smoke test substitutes an explicitly labeled behavioral multiply-add for the vendor DSP primitive. It exercises the unmodified E5 control/decoder and stalls. Accepted Vivado RTL evidence uses the real AMD DSP48E1 library and remains indexed in the research archive. The behavioral test is not new FPGA timing or energy evidence.

## Paper and slides

The paper is a standalone IEEEtran conference `.tex` file. Compile it with an IEEEtran-capable LaTeX installation. Its source enforces at most four technical pages and five total pages. The main workspace copy was checked with the Codex built-in compiler. Exported submission PDF font embedding, file size and final visual inspection still need the authors' upload check.

`slides/mentor_briefing.pptx` contains editable diagrams/charts/tables and detailed notes. `slides/slide-notes.md` provides a text reading route.

## Preserved full research workflow

`work/adaptive_snn_probe/` preserves all research-authored Python, SystemVerilog and Tcl sources, including discarded trials. Their original directory relationships remain intact. Historical manifests contain original absolute paths and source hashes. They are provenance receipts, not portable launch instructions. Some historical scripts write accepted filenames or require missing raw assets. Read their source and use a separate working copy with fresh attempt labels before running them.

`release_manifest.json` binds shipped file bytes by relative path. It provides portability without rewriting historical evidence hashes. `scripts/verify_release.py` checks every published file. Generated DCPs, complete SAIFs, large logs, raw inference tensors, trained weights and datasets are excluded from Git. They are not required for the portable examples but are required for independently rerunning some complete research stages.

The repository's `.gitattributes` preserves original file bytes across operating systems, including line endings. GitHub Actions runs the portable arithmetic checks, release manifest check and behavioral RTL smoke test; it does not reproduce licensed Vivado routes or complete model inference.

The detailed existing guide is `research_reports/membrane_leakage_reproduce_20261011.md`. Read its absolute links as historical local locations. Relevant selected route/power/model receipts reside under `work/adaptive_snn_probe/validation_close/`. Reports preserve failed attempts and distinguish accepted data from unmeasured controls.

## Original model assets

GLIF: https://github.com/CAS-CLab/Gated-LIF at commit `60638b28ff8b688b51867e7dd44f1e065d4892b0`, ResNet18/CIFAR10/T2 checkpoint `trained models/resCifar18stand-CIFAR10-step2-CW.pth.tar`.

OTTT: https://github.com/pkuxmq/OTTT-SNN at commit `c15d5da05eea0c48e1fa837a4f8073297006d93f`, official VGG11/CIFAR10/T6 checkpoint. `ottt_source_manifest.json` records the official Drive folder and selected asset hash.

TinyImageNet: https://github.com/Intelligent-Computing-Lab-Panda/Visual-Explanations-from-Spiking-Neural-Networks-using-Interspike-Intervals at commit `178789c74fef72b9c25bd31d65ac598c987e1de9`, `pretrained_tiny_t30.pth.tar`. This is the evaluated BNTT-style model released with the Scientific Reports paper, not an evaluated checkpoint from the separate BNTT training repository.

Download source/weights/data from their original owners, retain licenses and verify the recorded hashes. Evaluation adapters preserve reset ordering, thresholds and Poisson inputs. They require NumPy, PyTorch and the model-specific dependencies described by the original repositories. Exact package metadata remains in the historical environment/source records. The local validation used `rn_dps/.venv`; that machine path is not a portable environment specification.

## Hardware and estimated energy

Accepted runs use Vivado 2025.2, Artix7 `xc7a100tcsg324-1`, 12 ns, the same 94 FF fixture, complete slow/max known-pin SDF replay and complete physical-net SAIF annotation. Timing checks remain enabled. Energy means estimated fixture dynamic pJ per scalar operand at 25 C, not board/static/memory/full-neuron energy. Do not suppress timing errors or substitute a different activity interval to obtain a passing energy result.
