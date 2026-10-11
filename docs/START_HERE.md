# Mentor reading guide

1. Read the README for the operation, adaptation rule and measured trade-offs.
2. Open the slide deck in `slides/`. Its speaker notes include explanations and evidence pointers.
3. Run `python examples/run_examples.py` to see the integer arithmetic, including a negative borrow and exact wide fallback.
4. Read `docs/MECHANISM.md` for the decoder derivation and interface obligations.
5. Review `paper/membrane_leakage_paper_draft.tex`, `docs/RESULTS.md` and the explicit limitations.
6. Use `docs/REPRODUCIBILITY.md` for portable checks and the preserved research archive.
7. Read `chat/conversation.html` locally, or use the shared chat link. It records the exploration, including failed candidates, rather than only the final conclusion.

The contribution concerns membrane **leakage multiplication**. Synaptic accumulation, complete neuron scheduling and a complete accelerator are outside measured core scope.
