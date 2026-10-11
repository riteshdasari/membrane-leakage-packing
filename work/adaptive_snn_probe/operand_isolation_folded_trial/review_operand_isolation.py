"""Independent folded-selection scalar/source review; launches no HDL tools.

Exact source comparison, exhaustive scalar algebra, one-hot masked selection,
and combinational write implication do not replace sequential RTL equivalence,
reset/backpressure simulation, timing, or measured activity/power validation.
"""
from pathlib import Path
import argparse
import difflib
import hashlib
import itertools
import json
import re

P = Path(__file__).resolve().parent
FROZEN = P.parent / "common_layout_trial" / "guard_add_selective.sv"
ISOLATED = P / "guard_add_selective_isolated.sv"
FROZEN_SHA = "b5c7d724d642b2310c4e447eabccaf965a3aa520aaf2e04c5f93accd5dbb9e48"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_review():
    assert sha(FROZEN) == FROZEN_SHA, "Frozen baseline changed"
    original = FROZEN.read_text(encoding="utf-8")
    actual = ISOLATED.read_text(encoding="utf-8")
    old_header = "module guard_add_selective #(parameter integer V=0)("
    new_header = "module guard_add_selective_isolated #(parameter integer V=3, parameter integer ISOLATE=1)("
    old_arithmetic = """  wire signed[4:0]adjustment=selected_hi[0]?5'b11111:5'b00001;
  assign corrected_high=selected_hu5+adjustment;"""
    new_arithmetic = """  // Fold zero isolation into the existing one-hot lane selection.
  // selected_mask has one bit set for work, and is zero when no lane is bad.
  // This keeps a separate v2/any-work enable out of the selected HU adder.
  reg[3:0]masked_hu;
  reg masked_negative;
  always @* begin
   masked_hu=0;masked_negative=0;
   for(integer r=0;r<6;r=r+1)begin
    masked_hu=masked_hu|(hu[r]&{4{selected_mask[r]}});
    masked_negative=masked_negative|(hi[r][0]&selected_mask[r]);
   end
  end
  wire selected_any=|selected_mask;
  wire signed[4:0]adjustment=selected_hi[0]?5'b11111:5'b00001;
  wire signed[4:0]isolated_hu=ISOLATE?{masked_hu[3],masked_hu}:selected_hu5;
  wire signed[4:0]isolated_adjustment=ISOLATE?
   (selected_any?(masked_negative?5'b11111:5'b00001):5'd0):adjustment;
  assign corrected_high=isolated_hu+isolated_adjustment;"""
    assert original.count(old_header) == original.count(old_arithmetic) == 1
    expected = original.replace(old_header, new_header, 1).replace(old_arithmetic, new_arithmetic, 1)
    assert actual == expected, "Prepared RTL differs beyond the two reviewed substitutions"
    assert not re.search(r"\b(?:KEEP|DONT_TOUCH)\s*=", actual, re.I), "Unexpected core preservation attribute"
    guarded_write = "if(correction_step&&selected_mask[l])out_data[12*l+7+:5]<=corrected_high;"
    assert actual.count(guarded_write) == actual.count("<=corrected_high;") == 2
    assert "wire correction_step=SHARED&&output_space&&v2&&(|work_mask);" in actual
    assert "generate if(CURRENT8&&SHARED)begin:current8_bad_correction" in actual
    assert "wire[5:0]work_mask=busy?pending_mask:bad_mask;" in actual
    # Verify the unchanged priority selector, including its zero default.
    selector = """ always @* begin
  selected_lane=0;selected_mask=0;
  if(work_mask[0])begin selected_lane=0;selected_mask=6'b000001;end
  else if(work_mask[1])begin selected_lane=1;selected_mask=6'b000010;end
  else if(work_mask[2])begin selected_lane=2;selected_mask=6'b000100;end
  else if(work_mask[3])begin selected_lane=3;selected_mask=6'b001000;end
  else if(work_mask[4])begin selected_lane=4;selected_mask=6'b010000;end
  else if(work_mask[5])begin selected_lane=5;selected_mask=6'b100000;end
 end"""
    assert actual.count(selector) == 1
    timing_original = (FROZEN.parent / "guard_add_selective_timing.sv").read_text()
    timing_actual = (P / "guard_add_selective_isolated_timing.sv").read_text()
    timing_expected = timing_original.replace("guard_add_selective_timing", "guard_add_selective_isolated_timing")
    timing_expected = timing_expected.replace("guard_add_selective #(.V(V)) core", "guard_add_selective_isolated #(.V(V),.ISOLATE(1)) core")
    old_top_lines = "\n".join(f"`GUARD_ADD_SELECTIVE_TOP(top_guard_add_selective_v{v},{v})" for v in range(4))
    assert timing_expected.count(old_top_lines) == 1
    timing_expected = timing_expected.replace(old_top_lines, "`GUARD_ADD_SELECTIVE_TOP(top_guard_add_selective_isolated_v3,3)")
    assert timing_actual == timing_expected, "Fixture changed beyond renamed core and sole V3 top"
    return {
        "status": "pass", "frozen_sha256": sha(FROZEN), "folded_sha256": sha(ISOLATED),
        "frozen_fixture_sha256": sha(FROZEN.parent / "guard_add_selective_timing.sv"),
        "folded_fixture_sha256": sha(P / "guard_add_selective_isolated_timing.sv"),
        "precise_changes": ["Module rename and V=3/ISOLATE=1 defaults", "One-hot masked OR of HU and current sign, with zero adjustment when selected_mask is zero"],
        "corrected_high_write_sites": 2, "new_core_preservation_attributes": False,
        "fixture_preservation_attributes": "Original attributes retained identically; none added for isolation",
        "scheduler_register_reset_and_dsp_logic": "Byte-equivalent after the two specified substitutions (newline-normalized)",
        "source_diff": "".join(difflib.unified_diff(original.splitlines(True), actual.splitlines(True), fromfile="frozen", tofile="folded")),
    }


def scalar_review():
    checked = exceptional = fast_small_count = fast_copy_only = 0
    minimum = maximum = 0
    for u in range(-1024, 1024):
        hu, ru = divmod(u, 128)
        assert -8 <= hu <= 7 and 0 <= ru < 128
        for i in range(-128, 128):
            hi, ri = divmod(i, 128)
            sign_i = int(i < 0)
            assert hi == -sign_i and hi in (-1, 0) and 0 <= ri < 128
            carry, low = divmod(ru + ri, 128)
            reference_high, reference_low = divmod(u + i, 128)
            assert carry in (0, 1)
            assert reference_high == hu + hi + carry and reference_low == low
            fast_small = -128 <= u <= 127
            fast_copy = carry == sign_i
            if fast_small:
                recovered_high = carry - int(u < 0) - sign_i
                fast_small_count += 1
            elif fast_copy:
                recovered_high = hu
                fast_copy_only += 1
            else:
                assert carry != sign_i
                adjustment = -1 if sign_i else 1
                assert hi + carry == adjustment
                recovered_high = hu + adjustment
                exceptional += 1
            assert recovered_high == reference_high
            reconstructed = 128 * recovered_high + low
            assert reconstructed == u + i and -2048 <= reconstructed <= 2047
            assert -16 <= recovered_high <= 15
            minimum = min(minimum, reconstructed)
            maximum = max(maximum, reconstructed)
            checked += 1
    assert checked == 524288 and exceptional == 229376
    return {"status": "pass", "scalar_pairs": checked, "exceptional_pairs": exceptional,
            "fast_small_pairs": fast_small_count, "fast_copy_only_pairs": fast_copy_only,
            "sum_range": [minimum, maximum],
            "certificate": "Bad lanes have c != sign(I8), hence hI+c is exactly +1 or -1; hU plus adjustment is the exact quotient."}


def one_hot_review():
    cases = 0
    for work in range(64):
        selected_mask = work & -work
        selected_lane = selected_mask.bit_length() - 1 if selected_mask else 0
        assert selected_mask.bit_count() <= 1
        assert bool(selected_mask) == bool(work)
        assert 0 <= selected_lane < 6
        # The exact checked RTL uses a bitwise masked OR, so each lane/value
        # can be checked independently; inactive terms are identically zero.
        # All 64 sign vectors are included for every lane/nibble case.
        for varied_lane, nibble, signs in itertools.product(range(6), range(16), range(64)):
            hu = [(3 * lane + 5) & 15 for lane in range(6)]
            hu[varied_lane] = nibble
            masked_hu = masked_negative = 0
            for lane in range(6):
                bit = (selected_mask >> lane) & 1
                masked_hu |= hu[lane] & (15 if bit else 0)
                masked_negative |= ((signs >> lane) & 1) & bit
            if selected_mask:
                assert masked_hu == hu[selected_lane]
                assert masked_negative == ((signs >> selected_lane) & 1)
                folded_hu = masked_hu - 16 if masked_hu & 8 else masked_hu
                folded_adjustment = -1 if masked_negative else 1
                original_hu = hu[selected_lane] - 16 if hu[selected_lane] & 8 else hu[selected_lane]
                original_adjustment = -1 if (signs >> selected_lane) & 1 else 1
                assert folded_hu == original_hu and folded_adjustment == original_adjustment
                assert -16 <= folded_hu + folded_adjustment <= 15
            else:
                assert masked_hu == masked_negative == 0
                folded_hu = folded_adjustment = 0
                assert folded_hu + folded_adjustment == 0
            cases += 1
    assert cases == 393216
    return {"status": "pass", "work_masks": 64, "lane_nibble_sign_vector_cases": cases,
            "certificate": "Priority selected_mask is one-hot-or-zero. Each masked OR term vanishes unless selected; a selected lane equals the original mux, and the all-zero mask forces both arithmetic operands to zero.",
            "scope": "All work masks, each lane/nibble independently, all 64 current-sign vectors; bitwise separability checked against the exact RTL source. Not all 16**6 membrane vectors enumerated."}


def write_implication_review():
    cases = writes = last_busy_cases = blocked_exception_cases = stale_invalid_cases = 0
    for bad_mask, pending_mask in itertools.product(range(64), repeat=2):
        for busy, v2, out_valid, out_ready, rst in itertools.product((0, 1), repeat=5):
            work = pending_mask if busy else bad_mask
            selected_mask = work & -work
            next_mask = work & ~selected_mask
            output_space = bool(not out_valid or out_ready)
            selected_any = bool(selected_mask)
            correction_step = bool(output_space and v2 and work)  # SHARED=1
            actual_high_write = bool(not rst and output_space and (busy or v2) and correction_step and selected_mask)
            if actual_high_write:
                assert selected_any
                writes += 1
            if not rst and busy and v2 and work and not next_mask and output_space:
                assert selected_any and actual_high_write
                last_busy_cases += 1
            if not rst and v2 and work and not output_space:
                assert selected_any and not actual_high_write
                blocked_exception_cases += 1
            if not v2 and work:
                assert selected_any and not actual_high_write
                stale_invalid_cases += 1
            if rst:
                assert not actual_high_write
            cases += 1
    assert cases == 131072 and writes > 0 and last_busy_cases > 0
    return {"status": "pass", "binary_combinations": cases,
            "actual_high_write_combinations": writes, "last_busy_correction_combinations": last_busy_cases,
            "blocked_exception_combinations": blocked_exception_cases,
            "invalid_exception_combinations": stale_invalid_cases,
            "implication": "Every high-part write implies selected_any. Last busy corrections are active. Blocked and stale-invalid exceptions may keep arithmetic active but write no output.",
            "scope": "Combinational implication over a superset of reachable states; no sequential/formal reachability proof."}


def review():
    return {"status": "pass", "reviewer": "isolation_review subagent",
            "review_script_sha256": sha(Path(__file__)),
            "domain": "V=3, ISOLATE=1; signed11 membrane plus statically signed8 current; exact signed12 sum",
            "source_review": source_review(), "scalar_algebra": scalar_review(),
            "one_hot_selection": one_hot_review(), "write_implication": write_implication_review(),
            "limits": ["No RTL simulator run by this reviewer", "No sequential reset/backpressure or reachability proof", "No routing or SDF timing check", "No proof synthesis retains isolation", "No measured switching or energy result"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="Recompute saved result without writing")
    args = ap.parse_args()
    result = review()
    path = P / "review_checks.json"
    if args.check:
        assert json.loads(path.read_text()) == result, "Saved review differs"
    else:
        assert not path.exists(), "Preserve existing review; use --check"
        path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "pass", "scalar_pairs": result["scalar_algebra"]["scalar_pairs"],
                      "exceptional_pairs": result["scalar_algebra"]["exceptional_pairs"],
                      "one_hot_cases": result["one_hot_selection"]["lane_nibble_sign_vector_cases"],
                      "control_combinations": result["write_implication"]["binary_combinations"],
                      "check_only": args.check}))


if __name__ == "__main__":
    main()
