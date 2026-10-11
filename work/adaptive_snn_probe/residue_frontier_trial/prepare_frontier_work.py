"""Prepare unchanged saved groups or exact U11/I8 frontier stress work."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

P = Path(__file__).resolve().parent
ARCHIVE = P.parent / 'common_layout_trial/results/selective_models_p1_0/stream_stim.txt'
LEDGER = P.parent / 'results/adaptive_delta_model_input.json'

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def signed(v, width):
    return v - (1 << width) if v & (1 << (width - 1)) else v

def load_groups(path):
    groups = []
    with Path(path).open() as f:
        total = int(f.readline())
        for gid in range(total):
            n, gap = map(int, f.readline().split())
            assert 1 <= n <= 4096 and gap >= 0
            pairs = []
            for _ in range(n):
                ub, ib = [int(x, 16) for x in f.readline().split()]
                assert 0 <= ub < 2048 and 0 <= ib < 2048
                u, i = signed(ub, 11), signed(ib, 11)
                assert -128 <= i <= 127, (gid, i)
                pairs.append((u, i))
            groups.append((gap, pairs))
        assert not f.read().strip()
    return groups

def take_for(engine, pairs, pos):
    av = min(8, len(pairs) - pos)
    if engine == 0:
        return min(av, 6)
    if engine != 5:
        return av
    n = min(av, 6)
    if av > 6 and -128 <= pairs[pos + 6][0] <= 127:
        n = 7
        if av > 7 and -128 <= pairs[pos + 7][0] <= 127:
            n = 8
    return n

def issue_counts(groups):
    result = []
    for engine in range(6):
        histogram = {str(n): 0 for n in range(1, 9)}
        requests = 0
        for _, pairs in groups:
            pos = 0
            while pos < len(pairs):
                n = take_for(engine, pairs, pos)
                histogram[str(n)] += 1
                requests += 1
                pos += n
        result.append(dict(engine=engine, requests=requests, take_histogram=histogram))
    return result

def stress_groups():
    # Every ordered (signed11 U, signed8 I) scalar pair occurs once here.
    groups = [(0, [(u, i) for i in range(-128, 128)]) for u in range(-1024, 1024)]
    boundaries_u = [-1024, -993, -129, -128, -33, -32, -1, 0, 15, 16, 31, 32, 126, 127, 128, 129, 991, 1023]
    boundaries_i = [-128, -127, -33, -32, -1, 0, 1, 31, 32, 126, 127]
    # Mixed prefix eligibility, radix carries, extreme highs, and all valid tails.
    for length in range(1, 65):
        for phase in range(8):
            pairs = [(boundaries_u[(j * 5 + phase) % len(boundaries_u)],
                      boundaries_i[(j * 7 + phase) % len(boundaries_i)])
                     for j in range(length)]
            groups.append((phase % 3, pairs))
    for u6, u7 in [(-129, 0), (128, 127), (-128, 128), (127, -129), (-128, 127), (0, 0)]:
        for i in boundaries_i:
            pairs = [(boundaries_u[(j + i) % len(boundaries_u)], i) for j in range(6)]
            pairs += [(u6, i), (u7, i)]
            groups.append((0, pairs))
    return groups

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--kind', choices=['models', 'main'], required=True)
    parser.add_argument('--directory', type=Path, required=True)
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True)
    dst = args.directory / 'stream_stim.txt'
    out = args.directory / 'workload.json'
    assert not dst.exists() and not out.exists(), 'Refuse to overwrite work'
    pins = {str(Path(__file__).resolve()): sha(__file__), str(P / 'CONTRACT.md'): sha(P / 'CONTRACT.md')}
    metadata = []
    if args.kind == 'models':
        groups = load_groups(ARCHIVE)
        ledger = json.loads(LEDGER.read_text())
        assert len(groups) == len(ledger['ledger']) == 9216
        assert sum(len(v) for _, v in groups) == 635904
        for gid, ((gap, pairs), rec) in enumerate(zip(groups, ledger['ledger'])):
            assert gap == 0 and rec['neurons'] == len(pairs)
            assert len(pairs) == (128 if rec['layer'] == 0 else 10)
            assert [i for _, i in pairs] == rec['current']
            # Existing ordering is seed, timestep, layer, image; images within
            # a layer are independent. Preserve it rather than inventing a
            # per-image alternation absent from the archived workload.
            if gid:
                prev = ledger['ledger'][gid-1]
                assert tuple(prev[k] for k in ['seed','t','layer','image']) < tuple(
                    rec[k] for k in ['seed','t','layer','image'])
            metadata.append({k: rec[k] for k in ['seed', 't', 'layer', 'image', 'neurons', 'threshold']})
        pins.update({str(ARCHIVE): sha(ARCHIVE), str(LEDGER): sha(LEDGER)})
        dst.write_bytes(ARCHIVE.read_bytes())
        assert sha(dst) == sha(ARCHIVE)
    else:
        groups = stress_groups()
        with dst.open('w', newline='\n') as f:
            f.write(f'{len(groups)}\n')
            for gap, pairs in groups:
                f.write(f'{len(pairs)} {gap}\n')
                for u, i in pairs:
                    f.write(f'{u & 2047:03x} {i & 2047:03x}\n')
        assert groups == load_groups(dst)
    offsets, cumulative = [], 0
    for gid, (gap, pairs) in enumerate(groups):
        row = dict(group=gid, scalar_offset=cumulative, neurons=len(pairs), gap=gap,
                   supply2_minimum_clocks=(len(pairs) + 1) // 2)
        if metadata:
            row.update(metadata[gid])
        offsets.append(row)
        cumulative += len(pairs)
    result = dict(status='pass', kind=args.kind, groups=len(groups), neurons=cumulative,
                  stimulus_file=str(dst.resolve()), stimulus_sha256=sha(dst), source_sha256=pins,
                  group_boundaries=offsets, predicted_issues=issue_counts(groups),
                  exhaustive_scalar_pairs=524288 if args.kind == 'main' else 0,
                  supply2_minimum_clocks=sum(r['supply2_minimum_clocks'] for r in offsets),
                  supply_scope='Analytic per-dependent-group two-neuron input-supply lower bound; excludes pipeline/group-drain, arrival and memory arbitration costs.',
                  model_scope='Saved beta231 integer reference; same operands/group order; no original trained-accuracy claim.' if metadata else 'All U11/I8 scalar pairs plus structured packed boundaries/tails.')
    out.write_text(json.dumps(result, indent=2) + '\n')
    print('FRONTIER_WORK PASS', args.kind, 'GROUPS', len(groups), 'NEURONS', cumulative)

if __name__ == '__main__':
    main()
