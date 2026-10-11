"""Normal publisher/institution/proceedings links for McKeown's original."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

HERE = Path(__file__).resolve().parent
ITEMS = [
    ("mckeown_ieee_pdf_response.bin", "https://ieeexplore.ieee.org/ielx5/4667697/4671720/04671768.pdf?arnumber=4671768"),
    ("mckeown_crossref_pdf_response.bin", "http://xplorestaging.ieee.org/ielx5/4667697/4671720/04671768.pdf?arnumber=4671768"),
    ("mckeown_qub_current.html", "https://pure.qub.ac.uk/en/publications/power-efficient-dynamic-range-utilisation-for-dsp-on-fpga/"),
    ("mckeown_qub_uuid.html", "https://pure.qub.ac.uk/en/publications/061f6949-b501-4002-879f-c1533e3cd224"),
    ("mckeown_qub_legacy.html", "https://pure.qub.ac.uk/portal/en/publications/power-efficient-dynamic-range-utilisation-for-dsp-on-fpga(061f6949-b501-4002-879f-c1533e3cd224).html"),
    ("mckeown_proceedings_listing.html", "https://www.proceedings.com/04087.html"),
    ("mckeown_dblp_original.html", "https://dblp.org/rec/conf/sips/McKeownWM08.html"),
    ("mckeown_orcid.json", "https://pub.orcid.org/v3.0/0000-0001-5832-4022/works"),
]
def fetch(item):
    name, url = item
    row = {"url": url, "artifact": name, "started_utc": datetime.now(timezone.utc).isoformat()}
    try:
        request = urllib.request.Request(url)
        if name.endswith(".json"):
            request.add_header("Accept", "application/json")
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read()
            row.update(status=response.status, final_url=response.url, content_type=response.headers.get("Content-Type"))
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
receipt = {"written_utc": datetime.now(timezone.utc).isoformat(), "resources": rows,
           "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           "authentication_or_access_bypass_attempted": False}
(HERE / "udp_mckeown_fetch_secondary_v1.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
