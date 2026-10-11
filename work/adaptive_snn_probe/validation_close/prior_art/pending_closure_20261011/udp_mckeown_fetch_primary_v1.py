"""Additive public-access probes for two pending originals; no authentication."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor

HERE = Path(__file__).resolve().parent
HERE.mkdir(exist_ok=True)
ITEMS = [
    ("udp_crossref.json", "https://api.crossref.org/works/10.1145%2F3748173.3779194"),
    ("mckeown_crossref.json", "https://api.crossref.org/works/10.1109%2FSIPS.2008.4671768"),
    ("udp_openalex.json", "https://api.openalex.org/works/https://doi.org/10.1145/3748173.3779194"),
    ("mckeown_openalex.json", "https://api.openalex.org/works/https://doi.org/10.1109/SIPS.2008.4671768"),
    ("udp_current_tree.json", "https://api.github.com/repos/wintermelon008/UDP/git/trees/main?recursive=1"),
    ("udp_current_releases.json", "https://api.github.com/repos/wintermelon008/UDP/releases"),
    ("udp_current_readme.md", "https://raw.githubusercontent.com/wintermelon008/UDP/main/README.md"),
    ("udp_acm_pdf_response.bin", "https://dl.acm.org/doi/pdf/10.1145/3748173.3779194"),
    ("mckeown_ieee_stamp_response.bin", "https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber=4671768"),
    ("mckeown_proceedings_toc.pdf", "https://www.proceedings.com/content/004/004087webtoc.pdf"),
    ("udp_ultradsp_readme.md", "https://raw.githubusercontent.com/zcy-001-001/Ultra-DSP-MICRO26-AE/main/README.md"),
    ("udp_ultradsp_tree.json", "https://api.github.com/repos/zcy-001-001/Ultra-DSP-MICRO26-AE/git/trees/main?recursive=1"),
]

def fetch(item):
    name, url = item
    row = {"url": url, "artifact": name, "started_utc": datetime.now(timezone.utc).isoformat()}
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            body = response.read()
            row.update(status=response.status, final_url=response.url,
                       content_type=response.headers.get("Content-Type"))
    except urllib.error.HTTPError as exc:
        body = exc.read()
        row.update(status=exc.code, error=str(exc), content_type=exc.headers.get("Content-Type"))
    except Exception as exc:
        row.update(error=type(exc).__name__ + ": " + str(exc))
        return row
    (HERE / name).write_bytes(body)
    row.update(bytes=len(body), sha256=hashlib.sha256(body).hexdigest(), pdf_magic=body.startswith(b"%PDF-"))
    return row

with ThreadPoolExecutor(max_workers=4) as pool:
    rows = list(pool.map(fetch, ITEMS))
for row in rows:
    print(row["artifact"], row.get("status"), row.get("bytes"), row.get("error", ""), flush=True)
receipt = {"record_written_utc": datetime.now(timezone.utc).isoformat(), "resources": rows,
           "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           "authentication_or_access_bypass_attempted": False,
           "scope": "Read-only legal public primary/discovery routes, two pending original papers only."}
(HERE / "udp_mckeown_fetch_primary_v1.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
