"""Freeze additive McKeown original access/equivalence report; parent owns UDP reader audit."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json

HERE = Path(__file__).resolve().parent
PRIOR = HERE.parent
def pin(path):
    path = Path(path)
    return {"path": str(path.resolve()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

primary = json.loads((HERE / "udp_mckeown_fetch_primary_v1.json").read_text(encoding="utf-8"))
secondary = json.loads((HERE / "udp_mckeown_fetch_secondary_v1.json").read_text(encoding="utf-8"))
crossref = json.loads((HERE / "mckeown_crossref.json").read_text(encoding="utf-8"))["message"]
oa = json.loads((HERE / "mckeown_openalex.json").read_text(encoding="utf-8"))
orcid = json.loads((HERE / "mckeown_orcid.json").read_text(encoding="utf-8"))
target_work = [g["work-summary"][0] for g in orcid["group"]
               if any(e.get("external-id-value") == "10.1109/SIPS.2008.4671768"
                      for e in g["work-summary"][0]["external-ids"]["external-id"])]
assert len(target_work) == 1
assert crossref["page"] == "233-238"
resources = []
for row in primary["resources"] + secondary["resources"]:
    if not row["artifact"].startswith("mckeown_"):
        continue
    row = dict(row)
    if row["artifact"] == "mckeown_dblp_original.html":
        row["content_observation"] = "HTTP 200 contains bot-verification HTML, not bibliographic/full method content."
    if row["artifact"].endswith("pdf_response.bin") or row["artifact"].endswith("stamp_response.bin"):
        row["content_observation"] = "HTTP 418 HTML response, PDF magic absent; no methods."
    if row["artifact"] == "mckeown_proceedings_toc.pdf":
        row["content_observation"] = "Six-page table of contents only, not original six-page paper. Item L-DM.1 starts at proceedings p.233; next paper starts at p.239."
    if row["artifact"].startswith("mckeown_qub_"):
        row["content_observation"] = "Shell response is 403. Normal web reader separately returned the institutional metadata/abstract record, with DOI only in Access to Document."
    if row["artifact"] == "mckeown_orcid.json":
        row["content_observation"] = "Public works list has target DOI and Scopus URL, no manuscript URL."
    resources.append(row)

record = {
    "status": "bounded_new_primary_routes_complete_original_full_method_still_unresolved",
    "written_utc": datetime.now(timezone.utc).isoformat(),
    "scope": "McKeown SiPS 2008 original only; UDP full-paper reader audit is owned by parent after its normal-browser access succeeded.",
    "doi": "10.1109/SIPS.2008.4671768", "title": crossref["title"][0],
    "original_pages": "233-238", "original_full_method_retrieved": False,
    "new_full_methods_retrieved_by_this_agent": 0,
    "original_equations_or_sections_inspected": None,
    "bibliographic_identity": {
        "crossref_author_initials": [a["given"] + " " + a["family"] for a in crossref["author"]],
        "proceedings_toc_first_author": "Stephen McKeown",
        "qub_record_first_author": "Michael McKeown",
        "handling": "Retain DOI and S. McKeown from publisher-supplied Crossref; do not silently resolve QUB full-name inconsistency."
    },
    "resources": resources,
    "metadata_findings": {
        "crossref_original_pdf_link": crossref["link"],
        "openalex_location_count": len(oa["locations"]),
        "openalex_pdf_urls": [loc.get("pdf_url") for loc in oa["locations"]],
        "openalex_open_access": oa["open_access"],
        "orcid_target_url": target_work[0].get("url"),
        "caveat": "No PDF URL in these metadata records is not proof that no author manuscript exists."
    },
    "web_reader_observations": [
        {"url": "https://pure.qub.ac.uk/en/publications/power-efficient-dynamic-range-utilisation-for-dsp-on-fpga/", "observation": "Institutional abstract and metadata readable; no attached manuscript link in returned access section."},
        {"url": "https://pure.qub.ac.uk/en/persons/roger-woods/", "observation": "Author institutional profile and public CV route inspected; no newly identified original-paper PDF link."},
        {"url": "https://pure.qub.ac.uk/en/persons/john-mcallister/", "observation": "Coauthor institutional profile inspected; no newly identified original-paper PDF link."},
        {"url": "https://www.proceedings.com/04087.html", "observation": "Official distribution record lists a 298-page printed volume with ISBN 9781424429233 and a public TOC; does not supply original full text."}
    ],
    "bounded_search_scope": [
        "Exact DOI/title, hyphenless title, initials/full author names with PDF/PhD/thesis filters.",
        "QUB original/current/legacy identifiers and coauthor profiles; author ORCID public works.",
        "Publisher normal stamp and standard PDF routes; exact Crossref PDF URL.",
        "Proceedings catalog/TOC and public repository/preprint discovery; no new original primary manuscript found."
    ],
    "original_method_questions": [
        {"question": "Does actual operand magnitude select packed lane count at runtime, or are widths/stream modes configured?", "status": "unresolved_original_full_method"},
        {"question": "How are values outside the packed range handled, and is a full-width path exact for the same declared integer computation?", "status": "unresolved_original_full_method"},
        {"question": "Is there an algebraically equivalent shared-beta signed ceil(beta*U/256) quotient/borrow decoder?", "status": "unresolved_original_full_method"}
    ],
    "retained_follow_on_evidence": {
        "title": "Evolutionary Requirements for Next-Generation Dataflow-Based FPGA System Design",
        "url": "https://eurasip.org/Proceedings/Eusipco/Eusipco2009/contents/papers/1569193849.pdf",
        "author": "John McAllister", "sections": "3.3, Figures 8-9, Table 3; reference 13 cites the original.",
        "observation": "Primary coauthor follow-on describes packing multiple fixed-point FFT input streams using their underused dynamic range, and resource/power results. It does not expose the original runtime lane admission, exceptional full-range handling or exact rounded leakage decoder.",
        "equivalence_status": "Conceptual prior art; not original full-method closure.",
        "pins": [pin(PRIOR / "targeted_followup/mcallister_eusipco2009.pdf"), pin(PRIOR / "targeted_followup/mcallister_eusipco2009.txt")]
    },
    "access_needed_to_close": "An authorized IEEE/library copy of original proceedings pp.233-238 (DOI 10.1109/SIPS.2008.4671768), or a legitimate author-accepted manuscript of those methods. Need complete arithmetic representation, range selection, exceptional-value handling, and decoding sections/equations, not abstract or 2009 follow-on alone.",
    "claim_boundary": "Do not assert no equivalent prior work, first-ever range-aware packing, or fully closed equivalence from this access outcome. Keep the exact rounded membrane leakage specialization and measured implementation comparisons; describe original McKeown method comparison as pending access.",
    "no_authentication_or_access_bypass": True, "no_author_messages": True,
    "no_vendor_model_or_editor_operations": True,
    "prior_and_script_pins": [pin(PRIOR / "final_contribution_boundary.md"), pin(PRIOR / "bounded_final_access_20261011/access_closure.json"), pin(HERE / "udp_mckeown_fetch_primary_v1.json"), pin(HERE / "udp_mckeown_fetch_secondary_v1.json"), pin(HERE / "mckeown_proceedings_toc.txt"), pin(Path(__file__))]
}
(HERE / "udp_mckeown_closure_v1.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
md = """# McKeown 2008 original: fresh access and method boundary

11 October 2026. This additive record covers the original [SiPS 2008 paper](https://doi.org/10.1109/SIPS.2008.4671768), pp.233-238. Parent separately inspected the complete UDP paper through the normally accessible ACM eReader; this record does not repeat or supersede that inspection.

**The original McKeown full method was not retrieved. Its runtime admission, full-range handling and rounded decoder remain unresolved.** No new original section or equation can honestly be cited.

Fresh publisher stamp, standard ielx5 PDF and the exact publisher-supplied Crossref PDF route returned IEEE verification HTML (HTTP 418), with no PDF bytes. QUB current, UUID and legacy routes returned 403 to ordinary shell retrieval. The normal web reader could inspect [QUB's institutional record](https://pure.qub.ac.uk/en/publications/power-efficient-dynamic-range-utilisation-for-dsp-on-fpga/), whose access section contains only the DOI. Coauthor institutional profiles did not identify a manuscript attachment.

The author's public ORCID works list has DOI/Scopus links only. Fresh OpenAlex metadata lists publisher and QUB records, neither with a PDF URL. Exact-title/DOI, full-name/initials, repository, author and thesis searches found no new inspectable primary manuscript in this bounded attempt. These are access observations, not absence evidence.

The [proceedings distributor's catalog](https://www.proceedings.com/04087.html) supplies a printed-volume purchase record and public table of contents, not the paper. The retained six-page TOC is **not** the six-page original. Its L-DM.1 entry names Stephen McKeown and starts at p.233; the next paper starts at p.239. Publisher-supplied Crossref uses S. McKeown, while QUB uses Michael: retain initials/DOI rather than silently fixing conflicting metadata.

The already-retained [primary coauthor EUSIPCO 2009 follow-on](https://eurasip.org/Proceedings/Eusipco/Eusipco2009/contents/papers/1569193849.pdf), Section 3.3, Figures 8-9 and Table 3, establishes conceptual overlap: underused dynamic range lets fixed-point FFT streams share arithmetic. Its reference 13 cites this original. It does not establish the original's per-value selector, exact exceptional full-range policy or shared-coefficient signed rounded quotient decoder. A different application alone does not prove non-equivalence.

To close the original comparison, obtain an authorized IEEE/library copy of pp.233-238 or a legitimate accepted manuscript. Inspect its complete representation, lane selection, exceptional-value and decoding equations. Do not infer first-ever priority or no-equivalent-prior-work from these failed routes.

`udp_mckeown_closure_v1.json` binds URLs, public response hashes, retained follow-on hashes and previous boundary records. Responses and scripts are additive. No authentication, CAPTCHA solving, access bypass, author messaging, vendor/inference launch or manuscript edit was performed.
"""
(HERE / "udp_mckeown_closure_v1.md").write_text(md, encoding="utf-8")
print(json.dumps({"status": record["status"], "original_full_method_retrieved": False,
                  "record": str((HERE / "udp_mckeown_closure_v1.json").resolve())}))
