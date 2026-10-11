"""Exact 48-bit guarded additions: arithmetic screen only, no hardware/model claim.

Operation U+I accepts two signed eleven-bit inputs and returns signed twelve-bit
results. Six-lane eligibility requires BOTH inputs of every consumed lane to fit
signed seven bits; fallback is four lanes. This is different from the leakage
trial and does not silently change the saved SNN update or its state width.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import random

P = Path(__file__).resolve().parent

def decode_pair(u, i, width):
    mask = (1 << (width - 1)) - 1
    encoded = (u & mask) + (i & mask)
    assert 0 <= encoded <= (1 << width) - 2
    corrected = encoded ^ (((u < 0) ^ (i < 0)) << (width - 1))
    got = corrected - (1 << width) if corrected >> (width - 1) else corrected
    assert got == u + i, (u, i, width, got)
    return got

def pack(u, i, width):
    assert len(u) == len(i) and width * len(u) == 48
    payload_mask = (1 << (width - 1)) - 1
    a = sum((x & payload_mask) << (width * n) for n, x in enumerate(u))
    b = sum((x & payload_mask) << (width * n) for n, x in enumerate(i))
    p = a + b
    assert p < 1 << 48
    for n, (x, y) in enumerate(zip(u, i)):
        field = (p >> (width * n)) & ((1 << width) - 1)
        corrected = field ^ (((x < 0) ^ (y < 0)) << (width - 1))
        got = corrected - (1 << width) if corrected >> (width - 1) else corrected
        assert got == x + y

def main():
    scalar = {}
    for width in (8, 12):
        bound = 1 << (width - 2)
        count = 0
        for u in range(-bound, bound):
            for i in range(-bound, bound):
                decode_pair(u, i, width)
                count += 1
        scalar[str(width)] = count
    rg = random.Random(900121)
    packed = {}
    for width, lanes in ((8, 6), (12, 4)):
        bound = 1 << (width - 2)
        extremes = [-bound, -bound + 1, -1, 0, 1, bound - 2, bound - 1]
        count = 0
        for u in extremes:
            for i in extremes:
                for shift in range(lanes):
                    xs = [u if k == shift else extremes[k % len(extremes)] for k in range(lanes)]
                    ys = [i if k == shift else extremes[-1 - k % len(extremes)] for k in range(lanes)]
                    pack(xs, ys, width)
                    count += 1
        for _ in range(50000):
            pack([rg.randrange(-bound, bound) for _ in range(lanes)],
                 [rg.randrange(-bound, bound) for _ in range(lanes)], width)
            count += 1
        packed[str(width)] = count
    result = dict(
        created_utc=datetime.now(timezone.utc).isoformat(),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        operation='Signed eleven-bit U plus signed eleven-bit I -> exact signed twelve-bit sum',
        narrow_domain='Every consumed U and I fits [-64,63]; six lanes with eight-bit fields',
        wide_domain='U and I in [-1024,1023]; four lanes with twelve-bit fields',
        packing='A=sum((U mod 2^(w-1))<<wl), B=sum((I mod 2^(w-1))<<wl), P=A+B',
        proof='Each field sum <=2^w-2, hence no interlane carry. XOR the guard bit with sign(U) XOR sign(I).',
        scalar_cases=scalar, packed_cases=packed, mismatches=0,
        comparison_requirement=['Fixed native four-lane DSP SIMD with equal identity copying.',
                                'Fixed six-output DSP-four-plus-LUT-two hybrid.',
                                'Fixed LUT six-lane implementation of the same sum.'],
        necessary_caveat='The fixed hybrid already produces six outputs without a range controller. '
                         'Adaptive packing has no automatic throughput advantage over that baseline.',
        limitations=['Arithmetic screen only: no DSP primitive simulation or synthesis.',
                     'No saved-model scheduling, accuracy, burst, memory or power evidence.',
                     'Output width twelve differs from the eleven-bit leakage output; state handling is undeclared.',
                     'This checks a candidate layout, not novelty or superiority.'])
    dest = P / 'results' / 'guarded_accumulation_layout_screen.json'
    dest.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2), flush=True)

if __name__ == '__main__':
    main()
