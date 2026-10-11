"""Independent, read-only verification of the delivered study and LIF comparisons."""
from pathlib import Path
import hashlib
import json
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs"
STEM = "membrane_adaptive_packing_verdict"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


manifest_path = OUT / (STEM + ".manifest.json")
manifest = read(manifest_path)
assert manifest["status"] == "pass_hash_closure"
for name, record in manifest["files"].items():
    path = Path(name)
    assert path.stat().st_size == record["bytes"], ("Size changed", name)
    assert digest(path) == record["sha256"], ("Bytes changed", name)

summary_path = OUT / (STEM + ".summary.json")
summary = read(summary_path)
hardware = summary["natural_U11_hardware"]
assert hardware["status"] == "pass" and len(hardware["rows"]) == 5
by_id = {row["engine"]: row for row in hardware["rows"]}
assert set(by_id) == set(range(5))
for engine, row in by_id.items():
    actual = read(row["hardware_file"])
    assert actual["core"] == row["core"]
    assert actual["status"] == row["status"] == "pass"
    assert actual["clock_period_ns"] == 6
    assert min(actual["WNS_ns"], actual["WHS_ns"]) >= 0
    assert actual["full_fixture"]["FF"] - actual["core"]["FF"] == 290
    assert actual["core"]["DSP"] == (1 if engine < 3 else 0)

native = summary["natural_U11_native"]
assert native["status"] == "pass" and len(native["cohorts"]) == 6
assert {(c["kind"], c["backpressure"]) for c in native["cohorts"]} == {
    (kind, stalled) for kind in ("main", "shift1", "shift3") for stalled in (False, True)
}
for cohort in native["cohorts"]:
    actual = read(cohort["check_file"])
    assert actual["rows"] == cohort["rows"] and actual["status"] == "pass"
    rows = {row["engine"]: row for row in actual["rows"]}
    assert set(rows) == set(range(5))
    assert all(row["status"] == "pass" for row in rows.values())
    assert len({row["numeric_retirement_sha256"] for row in rows.values()}) == 1
    assert len({rows[e]["service_clocks"] for e in (1, 2, 3)}) == 1
    for key in ("requests", "service_clocks", "neurons", "take_histogram"):
        assert rows[0][key] == rows[4][key]
    if cohort["kind"] != "main":
        assert all(row["original_LIF_numeric_retirements_match"] for row in rows.values())
        assert all(item["state_spike_count_class_disagreements"] == 0
                   for row in rows.values() for item in row["actual_retired_feedback"])

assert {row["engine"] for row in summary["u13_accepted_energy"]} == set(range(6))
assert not summary["mapped_functional_diagnostic"]["accepted_energy"]
assert not summary["mapped_functional_diagnostic"]["accepted_timing_result"]
print(json.dumps({
    "status": "pass_independent_delivery_verification",
    "manifest_files_verified": len(manifest["files"]),
    "manifest_sha256": digest(manifest_path),
    "summary_sha256": digest(summary_path),
    "U11_adaptive_core": by_id[0]["core"],
    "U11_native_hybrid_core": by_id[2]["core"],
    "scope": "Preserved bytes, reported internal timing/resources and exact native LIF comparisons; no external-I/O, new timed replay, board or natural-latency energy certification."
}, indent=2), flush=True)
