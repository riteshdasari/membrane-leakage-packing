# Sequential five-task execution

Preserve all earlier evidence. Each numbered stage saves a separate result before the next dependent stage begins.

1. Final fixed/adaptive novelty audit: stage1_novelty.md.
2. Application-backed integer neuron contract and accuracy: use the pinned official GLIF ResNet18 CIFAR10 checkpoint and original 10,000-image test set. Quantize neuron arithmetic explicitly, retain original floating synaptic layers, report that mixed implementation honestly. Quantization is distinct from exact packing.
3. One final adaptive leakage candidate and strong fixed controls: original-order traces, true coefficients, common zero bypass, exact reconstruction; count complete scalar leak results. No favorable coefficient substitution or test-set retuning.
4. Hardware decision: build only if stage 3 passes its opportunity gate; retain the existing addition hardware as evidence. If rejected before RTL, save an explicit not-executed gate with the reason, rather than imply hardware measured. Accepted hardware requires exact native retirement, routed resources, setup/hold closure, timed replay, and stated energy scope.
5. Evidence-based manuscript/report: write only claims supported by stages 1–4, retain negative findings and limitations. A research report is the deliverable if no positive publication claim survives; do not fabricate a strong-paper conclusion.

Bound this round to one adaptive candidate. A failed gate closes that candidate, while subsequent evidence review and writing still proceed. Full accelerator design, retraining, AdEx implementation and board measurements are outside this focused round.
