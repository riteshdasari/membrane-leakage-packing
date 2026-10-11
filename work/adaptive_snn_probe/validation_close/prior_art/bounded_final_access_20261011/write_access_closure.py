"""Additive, bounded four-paper access record; no publisher or hardware launches."""
from pathlib import Path
import hashlib
import json
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
PRIOR = HERE.parent

def pin(p):
    return {"path": str(p.resolve()), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}

QUESTIONS = [
    "Does the complete method select packed lane count from each actual operand value at issue, rather than only configured precision?",
    "Does it retain exact full-width execution for operands outside the admitted narrow range with the same stored integer representation?",
    "Does its decoder implement an equivalent shared-coefficient signed rounded quotient ceil(beta*U/256), including the overlapping-lane borrow and quotient correction?",
]

papers = [
    {
        "id": "Ou_TCASII_2024", "doi": "10.1109/TCSII.2024.3377356",
        "title": "A 119.64 GOPs/W FPGA-Based ResNet50 Mixed-Precision Accelerator Using the Dynamic DSP Packing",
        "full_method_retrieved": False,
        "primary_attempts": [
            {"url": "https://doi.org/10.1109/TCSII.2024.3377356", "outcome": "Reader retrieval error; no complete paper returned."},
            {"url": "https://epapers2.org/iscas2024/ESR/paper_details.php?paper_id=1893", "outcome": "Official conference abstract and metadata retrieved; no method equations or manuscript download link on the returned page."},
            {"url": "https://ime.um.edu.mo/wp-content/uploads/2025/03/NewsletterPDF_Final250211_Editable_smallWebSite.pdf", "outcome": "Institutional publication list identifies the journal item; not the full method."},
            {"url": "https://ime.um.edu.mo/zh-hans/people-zh-hans/weihan-yu/", "outcome": "Direct reader retrieval error; indexed author discovery did not yield a complete manuscript."},
            {"url": "https://ime.um.edu.mo/people/weihan-yu/", "outcome": "Direct reader retrieval error; no paper returned."},
        ],
        "allowed_observation": "Official abstract names mixed-precision quantization, dynamic DSP packing and pre-calibrated unpacking. It does not establish the actual-value selector or detailed rounded decoder.",
        "method_question_status": ["unresolved_full_method_access"] * 3,
    },
    {
        "id": "Cui_ICFPT_2024", "doi": "10.1109/ICFPT64416.2024.11113473",
        "title": "Efficient DSP Packing Method for Neural Network Accelerator",
        "full_method_retrieved": False,
        "primary_attempts": [
            {"url": "https://doi.org/10.1109/ICFPT64416.2024.11113473", "outcome": "Publisher access did not return complete method text."},
            {"url": "https://ieeexplore.ieee.org/document/11113473", "outcome": "JavaScript robot-verification page returned, not paper content."},
        ],
        "allowed_observation": "No new method-level observation. Targeted exact-title/author/institution/repository searches produced no inspectable primary full copy in this bounded attempt.",
        "method_question_status": ["unresolved_full_method_access"] * 3,
    },
    {
        "id": "McKeown_SiPS_2008", "doi": "10.1109/SIPS.2008.4671768",
        "title": "Power efficient dynamic-range utilisation for DSP on FPGA",
        "full_method_retrieved": False,
        "primary_attempts": [
            {"url": "https://doi.org/10.1109/SIPS.2008.4671768", "outcome": "Reader retrieval error; no complete original six-page paper returned."},
            {"url": "https://pure.qub.ac.uk/en/publications/power-efficient-dynamic-range-utilisation-for-dsp-on-fpga/", "outcome": "Institutional record and abstract retrieved. Access to Document links only to the DOI, with no manuscript attachment on the returned page."},
            {"url": "https://eurasip.org/Proceedings/Eusipco/Eusipco2009/contents/papers/1569193849.pdf", "outcome": "Already-retained full primary coauthor follow-on: Section 3.3/Table 3 support range-utilization stream packing; they do not expose all original runtime admission/exception details."},
        ],
        "allowed_observation": "Range-utilization stream packing is established conceptual overlap. The full original admission/fallback/exactness policy remains unresolved. First-author full-name inconsistency between metadata records is not corrected categorically.",
        "method_question_status": ["unresolved_full_method_access"] * 3,
    },
    {
        "id": "UDP_FPGA_2026", "doi": "10.1145/3748173.3779194",
        "title": "UDP: A Universal DSP Packing Framework for Low-bitwidth MAC Acceleration on FPGAs",
        "full_method_retrieved": False,
        "primary_attempts": [
            {"url": "https://doi.org/10.1145/3748173.3779194", "outcome": "Indexed publisher abstract/references readable; direct fetch reported 403. No full methods returned."},
            {"url": "https://dl.acm.org/doi/pdf/10.1145/3748173.3779194", "outcome": "Reader retrieval error; no paper returned."},
            {"url": "https://dl.acm.org/doi/full/10.1145/3748173.3779194", "outcome": "Reader retrieval error; no complete method returned."},
            {"url": "https://dl.acm.org/doi/epdf/10.1145/3748173.3779194", "outcome": "Reader retrieval error; no paper returned."},
            {"url": "https://cs.ustc.edu.cn/2020/1203/c23239a462623/page.htm", "outcome": "Official author publication page retrieved; UDP entry has no manuscript link."},
            {"url": "https://raw.githubusercontent.com/wintermelon008/UDP/main/README.md", "outcome": "Author repository README retrieved. Usage is a placeholder and citation supplies no manuscript URL. Mutable main README is discovery evidence, not a pinned source-version replacement."},
            {"url": "https://api.github.com/repos/wintermelon008/UDP/contents/", "outcome": "Reader access error; no new repository-tree completeness claim."},
        ],
        "allowed_observation": "Independently reread retained complete UDP_MUL module: widths and parallelism are Scala constructor parameters; data-dependent branches correct operand signs; its IO has fixed operand/product vectors plus valid bits and no actual-U pair/full admission interface. This observation applies to the pinned module only, not every policy in the unavailable full paper.",
        "released_source_revision": "f5a6b4f2522e54a815f5026b67cf7f78b7438160",
        "method_question_status": ["unresolved_full_paper; pinned_module_has_no_actual_U_admission_interface", "unresolved_full_paper", "unresolved_full_paper; pinned_module_is_full_product_multiplier_not_declared_leakage_kernel"],
    },
]

record = {
    "status": "bounded_access_attempt_complete_equivalence_still_unresolved",
    "started_utc": "2026-10-10T23:19:55Z",
    "record_written_utc": datetime.now(timezone.utc).isoformat(),
    "maximum_search_minutes": 10,
    "scope": "Only the four full-method access gaps named by parent; primary-source scientific conclusions only.",
    "new_full_methods_retrieved": 0,
    "unresolved_full_methods": 4,
    "old_records_modified": False,
    "vendor_or_model_jobs_launched": False,
    "authentication_or_access_bypass_attempted": False,
    "source_content_retention": "Retrieval observations recorded; no new complete publisher PDF obtained. Existing pinned UDP source reread and hashed.",
    "questions": QUESTIONS,
    "papers": papers,
    "prior_record_and_source_pins": [pin(PRIOR / "final_contribution_boundary.md"), pin(PRIOR / "targeted_followup/targeted_equivalence_followup.md"), pin(PRIOR / "udp_pinned.scala"), pin(PRIOR / "udp_source.zip"), pin(Path(__file__))],
    "claim_boundary": "The bounded attempt does not establish absence, first-ever priority, or full equivalence closure. Retain exact rounded leakage specialization and measured comparisons as the candidate contribution; broad actual-value packing and exact correction have established ancestry.",
}

HERE.mkdir(parents=True, exist_ok=True)
(HERE / "access_closure.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

md = """# Bounded final four-paper access check

Prepared 11 October 2026. This additive check revisited only the four full-method gaps in the frozen contribution-boundary record. No vendor or model runs were launched and old records were not edited. The record includes their hashes.

**Result: no new complete method was retrieved; all four paper-level equivalence gaps remain unresolved.** This is an access outcome, not evidence that an equivalent method does not exist.

For each full method, the remaining questions are whether current operand values select lane count at issue, whether exact full-width fallback preserves the same stored integer contract, and whether a decoder is equivalent to the shared-coefficient signed rounded leakage operation `ceil(beta*U/256)` with its overlapping-lane borrow and quotient correction.

Ou's [official ISCAS abstract](https://epapers2.org/iscas2024/ESR/paper_details.php?paper_id=1893) identifies mixed-precision quantization and dynamic packing/unpacking. It does not reveal the selector or unpacking equations. Publisher and Macau author/repository routes did not produce the full method. Do not label its adaptation as static per-layer, actual-value, or approximate from the abstract alone. [Journal DOI](https://doi.org/10.1109/TCSII.2024.3377356).

Cui's [publisher page](https://ieeexplore.ieee.org/document/11113473) returned a robot-verification page in this attempt. Exact-title/author/institution/repository searches found no inspectable primary author copy. No new method-level non-equivalence claim follows. [Paper DOI](https://doi.org/10.1109/ICFPT64416.2024.11113473).

McKeown's [Queen's institutional record](https://pure.qub.ac.uk/en/publications/power-efficient-dynamic-range-utilisation-for-dsp-on-fpga/) supplies an abstract and DOI but no attached manuscript in its returned access section. The already-read [full primary coauthor follow-on](https://eurasip.org/Proceedings/Eusipco/Eusipco2009/contents/papers/1569193849.pdf), Section 3.3/Table 3, supports range-utilization stream packing. It does not close the original runtime admission, exceptional full-range handling or integer-exactness questions. [Original DOI](https://doi.org/10.1109/SIPS.2008.4671768).

UDP's [official author page](https://cs.ustc.edu.cn/2020/1203/c23239a462623/page.htm) and [author repository README](https://raw.githubusercontent.com/wintermelon008/UDP/main/README.md) give no manuscript download. Publisher PDF/HTML/ePDF routes remained inaccessible. The complete retained `UDP_MUL` module at revision `f5a6b4f2522e54a815f5026b67cf7f78b7438160` was independently reread: width/parallelism are constructor parameters and runtime value branches implement sign correction. Its fixed operand/product-vector interface has no actual-U pair/full admission port or controller. This is a statement about the pinned module, not all policies in the unavailable [full paper](https://doi.org/10.1145/3748173.3779194).

The candidate remains an exact rounded membrane-leakage specialization with actual signed9 pair admission and signed16 scalar fallback, compact quotient decoding, and measured hardware/workload trade-offs. Generic actual-value operation packing and exact spill correction are established ideas. These four unresolved methods prevent first-ever or fully-closed-equivalence wording. A claimed contribution still needs the accepted measured benefit, not access failures as novelty evidence.

`access_closure.json` records exact primary URLs, retrieval outcomes, unresolved questions and pinned local inputs. No authentication or restricted-access bypass was attempted.
"""
(HERE / "access_closure.md").write_text(md, encoding="utf-8")
print(json.dumps({"status": record["status"], "new_full_methods_retrieved": 0, "unresolved_full_methods": 4, "record": str(HERE / "access_closure.json")}))
