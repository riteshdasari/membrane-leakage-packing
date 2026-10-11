"""Prepare original-IF groups or exhaustive signed13/signed8 native work."""
from pathlib import Path
import argparse
import hashlib
import json

P = Path(__file__).resolve().parent
ARCHIVE = P/'original_if/stream_stim.txt'
LEDGER = P/'original_if/reference_ledger.json'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def signed(bits, width):
    return bits - (1 << width) if bits & (1 << (width-1)) else bits


def load_groups(path):
    groups = []
    with Path(path).open() as handle:
        total = int(handle.readline())
        for gid in range(total):
            n, gap = map(int, handle.readline().split())
            assert 1 <= n <= 4096 and gap >= 0
            pairs = []
            for _ in range(n):
                values = handle.readline().split()
                assert len(values) == 2
                u_bits, i_bits = (int(x, 16) for x in values)
                assert 0 <= u_bits < 8192 and 0 <= i_bits < 8192
                u, i = signed(u_bits, 13), signed(i_bits, 13)
                assert -128 <= i <= 127, (gid, i)
                pairs.append((u, i))
            groups.append((gap, pairs))
        assert not handle.read().strip()
    return groups


def take_for(engine, pairs, pos):
    av = min(8, len(pairs)-pos)
    if engine == 0:
        return min(av, 6)
    if engine != 5:
        return av
    n = min(av, 5)
    while n < av and -128 <= pairs[pos+n][0] <= 127:
        n += 1
    return n


def issue_counts(groups):
    records = []
    for engine in range(6):
        histogram = {str(n):0 for n in range(1,9)}
        count = 0
        for _, pairs in groups:
            pos = 0
            while pos < len(pairs):
                n = take_for(engine, pairs, pos)
                count += 1
                histogram[str(n)] += 1
                pos += n
        records.append(dict(engine=engine, requests=count, take_histogram=histogram))
    return records


def stress_groups():
    groups = [(0, [(u, i) for i in range(-128,128)]) for u in range(-4096,4096)]
    u_edges = [-4096,-4065,-1025,-1024,-1023,-257,-256,-129,-128,-127,-33,-32,-1,0,15,16,31,32,126,127,128,129,255,256,1023,1024,4063,4095]
    i_edges = [-128,-127,-33,-32,-1,0,1,31,32,126,127]
    for length in range(1,65):
        for phase in range(8):
            groups.append((phase%3, [(u_edges[(j*5+phase)%len(u_edges)],i_edges[(j*7+phase)%len(i_edges)]) for j in range(length)]))
    # All three adaptive tail positions, including failure at each prefix.
    tails = [(-129,0,0),(128,127,-128),(-128,128,127),(127,-129,0),(-128,127,128),(-128,127,-129),(0,0,0),(127,-128,127)]
    for values in tails:
        for current in i_edges:
            groups.append((0, [(u_edges[(j+current)%len(u_edges)],current) for j in range(5)] + [(u,current) for u in values]))
    return groups


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind', choices=('models','main'), required=True)
    parser.add_argument('--directory', type=Path, required=True)
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True)
    stimulus, workload = args.directory/'stream_stim.txt', args.directory/'workload.json'
    assert not stimulus.exists() and not workload.exists(), 'Preserve previous workload'
    sources = {str(Path(__file__).resolve()):sha(__file__)}
    if (P/'CONTRACT.md').exists():
        sources[str(P/'CONTRACT.md')] = sha(P/'CONTRACT.md')
    metadata = []
    if args.kind == 'models':
        profile = json.loads((P/'original_if/profile.json').read_text())
        assert profile['status'] == 'pass' and profile['stream_sha256'] == sha(ARCHIVE) and profile['ledger_sha256'] == sha(LEDGER)
        for path, digest in profile['source_sha256'].items():
            assert sha(path) == digest
        groups = load_groups(ARCHIVE)
        ledger = json.loads(LEDGER.read_text())
        assert len(groups) == len(ledger['ledger']) == 9216
        assert sum(len(v) for _,v in groups) == 635904
        for gid, ((gap,pairs), rec) in enumerate(zip(groups,ledger['ledger'])):
            assert gap == 0 and len(pairs) == rec['neurons'] == (128 if rec['layer']==0 else 10)
            assert pairs == list(zip(rec['postleak_U'],rec['current']))
            assert rec['leak_shift'] is None and not rec['hard_reset']
            if gid:
                previous = ledger['ledger'][gid-1]
                assert tuple(previous[k] for k in ('seed','t','layer','image')) < tuple(rec[k] for k in ('seed','t','layer','image'))
            metadata.append({k:rec[k] for k in ('seed','t','layer','image','neurons','threshold')})
        stimulus.write_bytes(ARCHIVE.read_bytes())
        assert sha(stimulus) == sha(ARCHIVE)
        sources.update({str(path):sha(path) for path in (ARCHIVE,LEDGER,P/'original_if/profile.json',P/'restore_original_if.py')})
        sources.update(profile['source_sha256'])
    else:
        groups = stress_groups()
        assert len(groups[:8192]) == 8192
        assert sum(len(v) for _,v in groups[:8192]) == 2097152
        with stimulus.open('w',newline='\n') as handle:
            handle.write(f'{len(groups)}\n')
            for gap,pairs in groups:
                handle.write(f'{len(pairs)} {gap}\n')
                for u,i in pairs:
                    handle.write(f'{u&8191:04x} {i&8191:04x}\n')
        assert groups == load_groups(stimulus)
    offsets, cumulative = [], 0
    for gid,(gap,pairs) in enumerate(groups):
        row = dict(group=gid,scalar_offset=cumulative,neurons=len(pairs),gap=gap,
                   supply2_minimum_clocks=(len(pairs)+1)//2)
        if metadata:
            row.update(metadata[gid])
        offsets.append(row)
        cumulative += len(pairs)
    result = dict(status='pass',kind=args.kind,groups=len(groups),neurons=cumulative,
                  stimulus_file=str(stimulus.resolve()),stimulus_sha256=sha(stimulus),source_sha256=sources,
                  group_boundaries=offsets,predicted_issues=issue_counts(groups),
                  exhaustive_scalar_pairs=2097152 if args.kind=='main' else 0,
                  supply2_minimum_clocks=sum(r['supply2_minimum_clocks'] for r in offsets),
                  supply_scope='Analytic two-neuron delivery lower bound per dependent group; no memory/scheduler hardware is modeled.',
                  model_scope='Unchanged original savedIF conversion, full360batch RNG, orderedfirst48 groups. ExactU13/I8 contract; no clipping.' if metadata else 'EveryU13/I8 pair plus mixed boundaries, all valid tails and actualU8 admission boundaries.')
    workload.write_text(json.dumps(result,indent=2)+'\n')
    print('U13_WORK PASS',args.kind,'GROUPS',len(groups),'NEURONS',cumulative,flush=True)


if __name__ == '__main__':
    main()
