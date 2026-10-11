"""Independent exact offset-binary arithmetic screen; no RTL or model jobs."""
from pathlib import Path
import hashlib
import json
import random

P = Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def signed(bits, width):
    return bits - (1 << width) if bits & (1 << (width - 1)) else bits

def field(a, b, payload):
    modulus = 1 << payload
    bias = modulus >> 1
    ea = (a & (modulus - 1)) ^ bias
    eb = (b & (modulus - 1)) ^ bias
    total = ea + eb
    assert 0 <= total <= (modulus << 1) - 2
    return signed(total ^ modulus, payload + 1)

def packed(u, current, available):
    copy5 = available >= 5 and current[4] == 0
    fullcopy = copy5 and (available == 5 or current[5] == 0)
    narrow = available >= 5 and not fullcopy and all(
        -64 <= value <= 63 for value in u[:available] + current[:available])
    take = (available if narrow else
            (6 if copy5 and available == 6 and current[5] == 0 else
             (5 if copy5 else min(4, available))))
    payload = 7 if narrow else 11
    width = payload + 1
    order = list(range(6)) if narrow else [0, 1, 3, 2]
    mask = (1 << payload) - 1
    bias = 1 << (payload - 1)
    a = sum(((u[lane] & mask) ^ bias) << (width*f) for f, lane in enumerate(order))
    b = sum(((current[lane] & mask) ^ bias) << (width*f) for f, lane in enumerate(order))
    result = a + b
    assert 0 <= result < (1 << 48)
    got = [0] * 6
    for f, lane in enumerate(order):
        bits = (result >> (width*f)) & ((1 << width)-1)
        got[lane] = signed(bits ^ (1 << payload), width)
    if not narrow:
        got[4:6] = u[4:6]
    got[take:] = [0] * (6-take)
    want = [u[lane] + current[lane] for lane in range(take)] + [0] * (6-take)
    assert got == want, (u, current, available, narrow, take, got, want)
    return int(narrow), int(copy5 and not narrow)

def main():
    scalar_counts = {}
    for payload in (7, 11):
        lo, hi = -(1 << (payload-1)), (1 << (payload-1))
        count = 0
        for a in range(lo, hi):
            for b in range(lo, hi):
                assert field(a, b, payload) == a + b
                count += 1
        scalar_counts[str(payload)] = count
    edges = [-1024,-1023,-65,-64,-63,-1,0,1,62,63,64,1022,1023]
    cases = narrow_count = copy_count = 0
    for a in edges:
        for b in edges:
            for available in range(1, 7):
                u = [a,b,a,b,a,b]
                current = [b,a,b,a,0,b]
                n, c = packed(u, current, available)
                cases += 1; narrow_count += n; copy_count += c
    rng = random.Random(761408)
    for j in range(100000):
        available = rng.randrange(1,7)
        bound = 64 if j % 3 else 1024
        u = [rng.randrange(-bound,bound) for _ in range(6)]
        current = [rng.randrange(-bound,bound) for _ in range(6)]
        if j % 5 == 0:
            current[4] = 0
        if j % 7 == 0:
            current[4] = current[5] = 0
        for lane in range(available,6):
            u[lane] = -1024 if lane % 2 else 1023
            current[lane] = 1023 if lane % 2 else -1024
        n, c = packed(u, current, available)
        cases += 1; narrow_count += n; copy_count += c
    out = dict(script_sha256=sha(Path(__file__)),
               core_sha256=sha(P/'guard_add_layout.sv'),
               exhaustive_scalar_pairs=scalar_counts,
               packed_cases=cases, narrow_cases=narrow_count, copy_cases=copy_count,
               mismatches=0, physical_wide_order=[0,1,3,2], physical_narrow_order=list(range(6)),
               scope='Mathematical encoding/decoding only; both variants share this algebra. No RTL, timing, RAM, model accuracy or power claim.')
    (P/'results').mkdir(exist_ok=True)
    (P/'results'/'layout_arithmetic_screen.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
    print('LAYOUT ARITHMETIC PASS', json.dumps(out),flush=True)

if __name__ == '__main__':
    main()
