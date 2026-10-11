"""Pin primary evidence and record exactly which equivalence gaps remain."""
import hashlib
import json
import re
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]

def pin(path):
    return {"path": str(path), "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

sources = [
    {"id": "dsp_packing", "url": "https://arxiv.org/html/2203.11028",
     "status": "full_primary_method_checked", "sections": ["IV", "V", "VI-B", "VII"]},
    {"id": "arithmetic_packing", "url": "https://arxiv.org/html/2606.11065",
     "status": "full_primary_method_checked", "sections": ["III-B", "III-C", "III-D", "V"]},
    {"id": "xtramac", "url": "https://arxiv.org/html/2605.06052",
     "status": "full_primary_method_checked", "sections": ["III-C", "IV", "VI"]},
    {"id": "brooks2000", "url": "https://mrmgroup.cs.princeton.edu/papers/dbrooks-tocs2000.pdf",
     "status": "full_primary_method_checked", "sections": ["5.1", "5.2", "5.4", "6.2"]},
    {"id": "udp", "url": "https://doi.org/10.1145/3748173.3779194",
     "source_url": "https://github.com/wintermelon008/UDP",
     "revision": "f5a6b4f2522e54a815f5026b67cf7f78b7438160",
     "status": "complete_released_module_checked_full_paper_unavailable",
     "method_file": "src/main/scala/UDP.scala"},
    {"id": "six_signed", "url": "https://doi.org/10.1109/ICFPT64416.2024.11113473",
     "status": "primary_abstract_and_outline_only_full_method_unresolved"},
    {"id": "ou_dynamic_packing", "url": "https://doi.org/10.1109/TCSII.2024.3377356",
     "status": "primary_existence_verified_full_method_unresolved"},
    {"id": "mckeown_range", "url": "https://doi.org/10.1109/SIPS.2008.4671768",
     "status": "primary_existence_verified_full_method_unresolved"},
    {"id": "skipopu", "url": "https://arxiv.org/html/2603.14785",
     "status": "full_primary_packing_method_checked", "sections": ["3.2"]},
]
papers = []
for path in sorted(OUT.glob("*.pdf")):
    text_path = path.with_suffix(".txt")
    text = text_path.read_text(encoding="utf-8") if text_path.exists() else ""
    match = re.search(r"arXiv:[^\s]+", text)
    papers.append({**pin(path), "version_footer": match.group(0) if match else None})

benchmarks = [
    {"paper": "FireFly", "url": "https://arxiv.org/html/2301.01905v5",
     "section": "V-C Table III", "model_dataset": [
         ["SCNN5", "MNIST"], ["SCNN7", "CIFAR10"], ["SCNN11", "CIFAR100"],
         ["SCNN9", "DVS-CIFAR10"], ["SCNN9", "DVS-Gesture"]],
     "stated_lif_training": {"tau": 2.0, "threshold": 0.5, "time_steps": 4},
     "hardware": "IF/LIF with shift approximation to leakage"},
    {"paper": "FireFly v2", "url": "https://arxiv.org/html/2309.16158",
     "section": "VI Tables IV-VI", "model_dataset": [
         ["SNN5", "MNIST"], ["SNN7", "CIFAR10"], ["SNN11", "CIFAR100"],
         ["SNN9", "DVS-CIFAR10"], ["SNN9", "DVS-Gesture"],
         ["CIFAR-Net", "CIFAR10"], ["CIFAR-Net", "CIFAR100"],
         ["SEW-ResNet34", "ImageNet"]],
     "hardware": "IF/LIF/residual membrane potential support; equation per row not established"},
    {"paper": "FireFly-S", "url": "https://arxiv.org/html/2408.15578v1",
     "section": "VI-A Table II", "model_dataset": [
         ["SCNN5", "MNIST"], ["SCNN7", "DVS-Gesture"], ["SCNN9", "CIFAR10"]],
     "hardware": "IF/LIF; sparse 4-bit models differ from original FireFly topologies"},
    {"paper": "FireFly-T", "url": "https://arxiv.org/html/2505.12771",
     "section": "V-A", "model_dataset": [
         ["CIFAR-Net", "CIFAR10"], ["Spikingformer-4-256", "CIFAR10"],
         ["Spikingformer-8-512", "ImageNet"]],
     "hardware": "BrainCog models; 4-bit quantization"},
]

repo_files = [pin(p) for p in sorted((OUT / "udp_source" / "UDP-main").rglob("*")) if p.is_file()]
pinned_udp = pin(OUT / "udp_pinned.scala")
assert pinned_udp["sha256"] == pin(OUT / "udp_source" / "UDP-main" / "src" / "main" / "scala" / "UDP.scala")["sha256"]
record = {
    "audit_date": "2026-10-10",
    "target": "E5 exact signed9-pair / signed12 scalar ceil-leakage primitive",
    "blanket_method_equivalence_closed": False,
    "exact_same_policy_found_in_accessible_methods": False,
    "absence_proof": False,
    "established_prior_concepts": [
        "actual-operand narrowness-driven dynamic operation packing",
        "arbitrary-width multiplication packing",
        "exact signed-product correction",
        "modulo-reference spill reconstruction",
        "runtime datatype-dependent DSP packing",
    ],
    "potential_specific_contribution": "Exact rounded-leakage specialization and membrane admission with measured SNN implementation trade-offs",
    "sources": sources, "primary_pdfs": papers, "udp_source_files": repo_files,
    "udp_commit_raw_module": pinned_udp,
    "udp_module_matches_pinned_revision": True,
    "e5_source": pin(ROOT / "sequential_paper_trial" / "leak_core.sv"),
    "report": pin(OUT / "equivalence_audit.md"),
    "access_limits": "UDP full PDF challenge; six-signed, Ou2024, McKeown2008 primary methods inaccessible. No messages or restricted-access bypass.",
    "benchmarks": benchmarks,
}
(OUT / "equivalence_audit.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
(OUT / "firefly_benchmark_targets.json").write_text(json.dumps(benchmarks, indent=2), encoding="utf-8")
print(json.dumps({"papers_pinned": len(papers), "udp_files_pinned": len(repo_files),
                  "full_equivalence_closed": record["blanket_method_equivalence_closed"]}))
