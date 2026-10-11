"""Light software screen of one fixed-layout exact ordered admission mechanism.

No HDL or existing evidence changes. No control, routing, memory or energy claim.
"""
from pathlib import Path
import hashlib
import json
import sys
sys.dont_write_bytecode = True

P = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def groups(path):
    with Path(path).open() as source:
        count = int(source.readline())
        for gid in range(count):
            n, gap = map(int, source.readline().split())
            assert 1 <= n <= 4096 and gap >= 0
            pairs = []
            for _ in range(n):
                u, current = (int(x, 16) for x in source.readline().split())
                assert 0 <= u < 2048 and 0 <= current < 2048
                u = u - 2048 if u & 1024 else u
                current = current - 2048 if current & 1024 else current
                assert -128 <= current <= 127
                pairs.append((u, current))
            yield gid, gap, pairs
        assert not source.read().strip()


def requests(pairs, full):
    pos = 0
    count = 0
    histogram = [0] * 9
    while pos < len(pairs):
        av = min(8, len(pairs) - pos)
        take = min(av, full)
        while take < av and -128 <= pairs[pos + take][0] <= 127:
            take += 1
        assert 1 <= take <= av
        for u, current in pairs[pos:pos+take]:
            assert -1024 <= u <= 1023 and -128 <= current <= 127
        count += 1
        histogram[take] += 1
        pos += take
    return count, histogram


def cohort(path, metadata=None):
    total = [dict(full_lanes=full, requests=0, scalar_updates=0, groups=0, source_gap_clocks=0,
                  take_histogram=[0]*9, by_seed_layer={}) for full in range(1, 9)]
    for gid, gap, pairs in groups(path):
        assert gap == 0 or metadata is None
        key = None
        if metadata is not None:
            rec = metadata[gid]
            assert len(pairs) == rec['neurons'] == (128 if rec['layer'] == 0 else 10)
            assert [current for _, current in pairs] == rec['current']
            key = str(rec['seed']) + ':' + str(rec['layer'])
        for row in total:
            count, histogram = requests(pairs, row['full_lanes'])
            row['requests'] += count
            row['scalar_updates'] += len(pairs)
            row['groups'] += 1
            row['source_gap_clocks'] += gap
            row['take_histogram'] = [a+b for a,b in zip(row['take_histogram'],histogram)]
            if key is not None:
                part = row['by_seed_layer'].setdefault(key,dict(requests=0,scalar_updates=0,groups=0))
                part['requests'] += count
                part['scalar_updates'] += len(pairs)
                part['groups'] += 1
    if metadata is not None:
        assert total[0]['groups'] == len(metadata)
    for row in total:
        full = row['full_lanes']
        row['high_base_precision_bits_saved_per_stage'] = 3*(8-full)
        row['three_metadata_stages_logical_bits_saved'] = 9*(8-full)
        row['output_sign_extension_logical_bits_saved'] = 3*(8-full)
        row['total_logical_register_bit_reduction_vs_fixed8'] = 12*(8-full)
        row['service_no_gap_no_output_stall_group_drain_clocks'] = row['requests'] + 4*row['groups']
        row['service_no_output_stall_including_source_gaps_group_drain_clocks'] = row['requests'] + 4*row['groups'] + row['source_gap_clocks']
        for part in row['by_seed_layer'].values():
            part['service_no_gap_no_output_stall_group_drain_clocks'] = part['requests'] + 4*part['groups']
    base = total[-1]
    for row in total:
        row['extra_requests_vs_fixed8'] = row['requests'] - base['requests']
        row['extra_requests_percent_vs_fixed8'] = 100*(row['requests']/base['requests'] - 1)
        key = 'service_no_gap_no_output_stall_group_drain_clocks'
        row['extra_service_percent_vs_fixed8'] = 100*(row[key]/base[key] - 1)
        physical_key = 'service_no_output_stall_including_source_gaps_group_drain_clocks'
        row['extra_service_including_gaps_percent_vs_fixed8'] = 100*(row[physical_key]/base[physical_key] - 1)
        for name, part in row['by_seed_layer'].items():
            fixed = base['by_seed_layer'][name]
            part['extra_requests_vs_fixed8'] = part['requests'] - fixed['requests']
            part['extra_service_percent_vs_fixed8'] = 100*(part[key]/fixed[key] - 1)
    return total


def main():
    out = P/'results/prefix_generalization_screen.json'
    assert not out.exists(), 'Preserve previous screen'
    models = P/'results/native_models_0_a1/stream_stim.txt'
    stress = P/'results/native_main_0_a0/stream_stim.txt'
    ledger = P.parent/'results/adaptive_delta_model_input.json'
    oldchecks = P/'results/native_models_0_a1/frontier_checks.json'
    stresschecks = P/'results/native_main_0_a0/frontier_checks.json'
    metadata = json.loads(ledger.read_text())['ledger']
    mrows = cohort(models, metadata)
    del metadata
    srows = cohort(stress)
    for path, rows in ((oldchecks,mrows),(stresschecks,srows)):
        native = json.loads(path.read_text())
        assert native['status'] == 'pass'
        for full, engine in ((6,5),(8,2)):
            actual = native['rows'][engine]
            predicted = rows[full-1]
            assert predicted['requests'] == actual['requests']
            assert predicted['scalar_updates'] == actual['neurons']
            assert predicted['service_no_output_stall_including_source_gaps_group_drain_clocks'] == actual['service_clocks']
    result = dict(status='pass',source_sha256={str(path.resolve()):sha(path)
                  for path in (Path(__file__),models,stress,ledger,oldchecks,stresschecks)},
                  models=mrows,stress=srows,
                  arithmetic='Fixed8 radix32 unsigned residue fields; first F lanes have signed7 high recovery, remaining lanes signed4 only when actual U fits signed8. Ordered prefix stops at first inadmissible narrow tail. I is always statically signed8. No consumed value changes.',
                  service_scope='Exact software request counts; no-output-stall service adds four drain clocks per dependent group plus recorded intergroup source gaps. F6 and F8 are cross-checked against measured native service for both saved and stress streams. Other F variants are predicted, not native RTL service.',
                  resource_scope='Logical high-base width reductions only. Register-bit figures are a structural upper opportunity matching this pipeline, not synthesized FF savings. Monitor/encoding/count control/mapping/timing/storage/energy cost unmeasured.',
                  control_scope='Up to8-F actual-U signed8 predicates and ordered prefix count selection replace two such predicates in F6. Their gates and routing are not priced here.',
                  exactness_scope='Admission/range and work screen only; unchanged F6/F8 counts cross-checked to passed RTL. Other F variants are not RTL, sequentially verified or routed.',
                  workload_scope='Same saved beta231 integer traces and full-domain/structured stress, without new training, downloads, padding or neuron reorder.')
    out.write_text(json.dumps(result,indent=2)+'\n')
    for name, rows in (('models',mrows),('stress',srows)):
        for row in rows:
            print(name,row['full_lanes'],row['requests'],row['extra_requests_percent_vs_fixed8'],
                  row['extra_service_percent_vs_fixed8'],row['total_logical_register_bit_reduction_vs_fixed8'])


if __name__ == '__main__':
    main()
