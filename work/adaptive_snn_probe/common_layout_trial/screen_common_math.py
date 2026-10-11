"""Constant-memory exhaustive scalar and randomized packed-field exactness check."""
from pathlib import Path
import hashlib
import json
import random
import numpy as np
P = Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    operands = np.arange(-1024, 1024, dtype=np.int64)
    scalar = 0
    minimum, maximum = 999, -999
    for a in range(-1024, 1024):
        s = (a & 127) + (operands & 127)
        high = (a >> 7) + (operands >> 7) + (s >> 7)
        recovered = (high << 7) + (s & 127)
        assert np.array_equal(recovered, a + operands), a
        assert np.all((-16 <= high) & (high <= 15))
        minimum = min(minimum, int(high.min()))
        maximum = max(maximum, int(high.max()))
        scalar += len(operands)
    rng = random.Random(92171)
    packed = 0
    for _ in range(100000):
        u = [rng.randrange(-1024, 1024) for _ in range(6)]
        i = [rng.randrange(-1024, 1024) for _ in range(6)]
        ab = sum((a & 127) << (8*l) for l, a in enumerate(u))
        c = sum((a & 127) << (8*l) for l, a in enumerate(i))
        p = ab + c
        assert p < 1 << 48
        for l, (a, b) in enumerate(zip(u, i)):
            s = (p >> (8*l)) & 255
            high = (a >> 7) + (b >> 7) + (s >> 7)
            assert (high << 7) + (s & 127) == a+b
        packed += 1
    result = dict(script_sha256=sha(Path(__file__)), core_sha256=sha(P/'guard_add_common.sv'),
                  scalar_cases=scalar, packed_cases=packed, high_min=minimum,
                  high_max=maximum, mismatches=0,
                  operation='signed11 U+I -> signed12; six isolated unsigned7 residual additions',
                  scope='Arithmetic proof screen; not HDL, timing or adaptive-policy validation')
    (P/'results').mkdir(exist_ok=True)
    (P/'results/common_math_checks.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(result)

if __name__ == '__main__':
    main()
