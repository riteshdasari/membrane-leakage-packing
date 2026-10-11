"""Exact full-domain algebra screen; no RTL resource or energy claims."""
from pathlib import Path
import hashlib
import json
import random

P = Path(__file__).resolve().parent


def scalar(u, current, residue_bits):
    radix = 1 << residue_bits
    hu, ru = divmod(u, radix)
    hi, ri = divmod(current, radix)
    residue_sum = ru+ri
    carry, low = divmod(residue_sum, radix)
    high = hu+hi+carry
    return radix*high+low, high, residue_sum


def packed(values, residue_bits, lanes):
    radix = 1 << residue_bits
    field_bits = residue_bits+1
    operand_a = sum((u % radix) << (field_bits*k) for k,(u,i) in enumerate(values))
    operand_b = sum((i % radix) << (field_bits*k) for k,(u,i) in enumerate(values))
    summed = operand_a+operand_b
    assert summed < 1 << 48
    results = []
    for k,(u,i) in enumerate(values):
        field = (summed >> (field_bits*k)) & ((1 << field_bits)-1)
        assert field == u % radix+i % radix
        carry, low = divmod(field, radix)
        results.append(radix*(u//radix+i//radix+carry)+low)
    return results


def main():
    target = P/'results/contribution_frontier_algebra.json'
    assert not target.exists(), 'Preserve prior experiment'
    results = []
    rng = random.Random(20261010)
    for bits in (7,5):
        lanes = 48//(bits+1)
        checks = 0
        high_min, high_max = 0,0
        for u in range(-1024,1024):
            for i in range(-128,128):
                result, high, summed = scalar(u,i,bits)
                assert result == u+i and summed < 1 << (bits+1)
                high_min = min(high_min,high); high_max = max(high_max,high)
                checks += 1
        high_width = next(width for width in range(1,13)
                          if -(1 << (width-1)) <= high_min and high_max < 1 << (width-1))
        packed_checks = 0
        extrema = (-1024,-129,-128,-33,-32,-17,-16,-1,0,15,16,31,32,127,128,1023)
        currents = (-128,-127,-33,-32,-1,0,1,31,32,126,127)
        for u in extrema:
            for i in currents:
                vector = [(u,i)]*lanes
                assert packed(vector,bits,lanes) == [u+i]*lanes
                packed_checks += 1
        for _ in range(20000):
            vector = [(rng.randrange(-1024,1024),rng.randrange(-128,128)) for _ in range(lanes)]
            assert packed(vector,bits,lanes) == [u+i for u,i in vector]
            packed_checks += 1
        results.append(dict(residue_bits=bits, field_bits=bits+1, lanes=lanes,
            exhaustive_scalar_pairs=checks, structured_random_packed_vectors=packed_checks,
            high_range=[high_min,high_max], signed_high_width=high_width, mismatches=0))
    script_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    value = dict(status='pass', domain='U signed11, I signed8, exact signed12 result',
        source_sha256=script_hash, random_seed=20261010, layouts=results,
        certificate='Each unsigned residue sum is <=2^(b+1)-2; no field overflows. The complete result is2^b*(hU+hI+carry)+low for every full-domain operand.',
        implication='Fixed8 using5-bit residues supports the same full input domain as fixed6 using7-bit residues. More lanes are not uniquely enabled by runtime membrane range selection.',
        scope='Algebra and software vector audit only. No RTL, routing, scheduling, memory bandwidth, resource, power or model-accuracy claim.')
    target.write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps(value,indent=2))


if __name__ == '__main__':
    main()
