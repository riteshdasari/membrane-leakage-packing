"""Restore the saved original IF references without training or truncation."""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
from pathlib import Path
import hashlib
import json
import sys
sys.dont_write_bytecode = True
import numpy as np

P = Path(__file__).resolve().parent
ORIGINAL = P.parent
R = ORIGINAL / 'results'
sys.path.insert(0, str(ORIGINAL))
import probe


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def take_for(name, pairs, pos):
    av = min(8, len(pairs) - pos)
    if name == 'fixed6':
        return min(av, 6)
    if name == 'fixed8':
        return av
    full = int(name[1:])
    n = min(av, full)
    while n < av and -128 <= pairs[pos + n][0] <= 127:
        n += 1
    return n


def add_group(stat, pairs, name, layer):
    pos = 0
    while pos < len(pairs):
        n = take_for(name, pairs, pos)
        selected = pairs[pos:pos+n]
        if name != 'fixed6':
            packed_u = sum((u % 32) << (6*j) for j, (u, i) in enumerate(selected))
            packed_i = sum((i % 32) << (6*j) for j, (u, i) in enumerate(selected))
            packed_sum = packed_u + packed_i
            assert packed_sum < (1 << 48)
            for j, (u, i) in enumerate(selected):
                residue = (packed_sum >> (6*j)) & 63
                high = u // 32 + i // 32 + (residue >> 5)
                assert -256 <= high <= 255
                if name.startswith('F') and j >= int(name[1:]):
                    assert -8 <= high <= 7
                assert high * 32 + (residue & 31) == u + i
        stat['requests'] += 1
        stat['take_histogram'][str(n)] += 1
        stat['by_layer'][str(layer)]['requests'] += 1
        pos += n
    stat['groups'] += 1
    stat['scalar_updates'] += len(pairs)
    stat['by_layer'][str(layer)]['groups'] += 1
    stat['by_layer'][str(layer)]['scalar_updates'] += len(pairs)


def new_stats():
    return dict(requests=0, groups=0, scalar_updates=0,
                take_histogram={str(k): 0 for k in range(1, 9)},
                by_layer={str(k): dict(requests=0, groups=0, scalar_updates=0) for k in range(2)})


def main():
    folder = P / 'original_if'
    assert not folder.exists(), 'Preserve all previous preparation attempts'
    folder.mkdir()
    configurations = [r for r in json.loads((R/'final_selected.json').read_text())['models']
                      if r['leak_shift'] is None]
    assert sorted(r['seed'] for r in configurations) == [0, 1, 2]
    prior = json.loads((R/'exact_inference.json').read_text())['models']
    ledger, metadata, profiles = [], [], []
    stream_path = folder / 'stream_stim.txt'
    with stream_path.open('w', newline='\n') as stream:
        stream.write('9216\n')
        for cfg in sorted(configurations, key=lambda r: r['seed']):
            seed = cfg['seed']
            data = np.load(R/f'model_seed{seed}.npz')
            weights = [data['w0'].astype(np.int64), data['w1'].astype(np.int64)]
            x, labels = data['test_x'], data['test_y']
            assert x.shape == (360, 64) and labels.shape == (360,)
            assert [w.shape for w in weights] == [(64, 128), (128, 10)]
            certificates = []
            for li, w in enumerate(weights):
                lower = np.minimum(w, 0).sum(0)
                upper = np.maximum(w, 0).sum(0)
                assert int(lower.min()) >= -128 and int(upper.max()) <= 127
                # Zero start, binary input, positive subtractive threshold:
                # after t steps U lies in [t*L,t*H], independent of input sequence.
                assert int((31*lower).min()) >= -4096 and int((31*upper).max()) <= 4095
                assert int((32*lower).min()) >= -8192 and int((32*upper).max()) <= 8191
                certificates.append(dict(layer=li, current_lower=lower.tolist(), current_upper=upper.tolist(),
                                         U_before_step32_lower=(31*lower).tolist(), U_before_step32_upper=(31*upper).tolist(),
                                         sum_after_step32_lower=(32*lower).tolist(), sum_after_step32_upper=(32*upper).tolist()))
            predictions, records = probe.reference(weights, cfg['thresholds'], x, None)
            accuracy = float(np.mean(predictions == labels))
            assert accuracy == cfg['reference_accuracy']
            previous, = [r for r in prior if r['seed'] == seed and r['leak_shift'] is None
                         and not r['hard_reset'] and r['mode'] == 0]
            assert accuracy == previous['reference_accuracy']
            state = [np.zeros((360, w.shape[1]), dtype=np.int64) for w in weights]
            counts = np.zeros((360, 10), dtype=np.int64)
            reference_counts = np.zeros_like(counts)
            rng = np.random.default_rng(123)
            statistics = {name: new_stats() for name in ('fixed6', 'fixed8', 'F5', 'F6')}
            ranges = [dict(layer=li, U_min=0, U_max=0, current_min=0, current_max=0,
                           sum_min=0, sum_max=0, postreset_min=0, postreset_max=0,
                           U11_violations=0, U13_violations=0, I8_violations=0) for li in range(2)]
            for timestep in range(32):
                spikes = rng.random(x.shape) < x
                for li, w in enumerate(weights):
                    rec = records[2*timestep+li]
                    old = state[li]
                    current = spikes.astype(np.int64) @ w
                    summed = old + current
                    # Independent quotient/remainder reconstruction before using exact state feedback.
                    field = old % 32 + current % 32
                    reconstructed = 32*(old//32 + current//32 + field//32) + field % 32
                    assert np.array_equal(reconstructed, summed)
                    fired = reconstructed >= cfg['thresholds'][li]
                    next_state = reconstructed - fired*cfg['thresholds'][li]
                    assert rec[0] == li and np.array_equal(spikes, rec[2])
                    assert np.array_equal(old, rec[1]) and np.array_equal(summed, rec[3])
                    assert np.array_equal(fired, rec[4])
                    assert np.array_equal(next_state, rec[3] - rec[4]*cfg['thresholds'][li])
                    row = ranges[li]
                    for name, values in (('U', old), ('current', current), ('sum', summed), ('postreset', next_state)):
                        row[name+'_min'] = min(row[name+'_min'], int(values.min()))
                        row[name+'_max'] = max(row[name+'_max'], int(values.max()))
                    row['U11_violations'] += int(np.count_nonzero((old < -1024) | (old > 1023)))
                    row['U13_violations'] += int(np.count_nonzero((old < -4096) | (old > 4095)))
                    row['I8_violations'] += int(np.count_nonzero((current < -128) | (current > 127)))
                    assert not row['U13_violations'] and not row['I8_violations']
                    for image in range(48):
                        pairs = [(int(u), int(i)) for u, i in zip(old[image], current[image])]
                        for name, stat in statistics.items():
                            add_group(stat, pairs, name, li)
                        stream.write(f'{len(pairs)} 0\n')
                        for u, i in pairs:
                            assert -4096 <= u <= 4095 and -128 <= i <= 127
                            stream.write(f'{u & 8191:04x} {i & 8191:04x}\n')
                        ledger.append(dict(seed=seed, t=timestep, layer=li, image=image, neurons=len(pairs),
                                           threshold=cfg['thresholds'][li], leak_shift=None, hard_reset=False,
                                           postleak_U=[u for u, i in pairs], current=[i for u, i in pairs],
                                           incoming_spikes=spikes[image].astype(int).tolist(),
                                           expected_state=next_state[image].tolist(), expected_spikes=fired[image].astype(int).tolist()))
                    state[li] = next_state
                    spikes = fired
                    if li == 1:
                        reference_counts += rec[4]
                counts += spikes
            assert np.array_equal(counts, reference_counts)
            assert np.array_equal(counts.argmax(1), predictions)
            for stat in statistics.values():
                stat['service_clocks_no_output_stalls_with_group_drains'] = stat['requests'] + 4*stat['groups']
                for part in stat['by_layer'].values():
                    part['service_clocks_no_output_stalls_with_group_drains'] = part['requests'] + 4*part['groups']
            for name in ('F5', 'F6'):
                statistics[name]['service_change_percent_vs_fixed8'] = 100*(statistics[name]['service_clocks_no_output_stalls_with_group_drains']/statistics['fixed8']['service_clocks_no_output_stalls_with_group_drains']-1)
            metadata.append(dict(seed=seed, leak_shift=None, hard_reset=False, sampled_images=48,
                                 all_images=360, all_images_reference_accuracy=accuracy,
                                 sampled_reference_accuracy=float(np.mean(predictions[:48] == labels[:48])),
                                 labels=labels[:48].tolist(), expected_counts=counts[:48].tolist(),
                                 thresholds=cfg['thresholds'], weights_file=str((R/f'model_seed{seed}.npz').resolve()),
                                 weights_sha256=sha(R/f'model_seed{seed}.npz')))
            profiles.append(dict(seed=seed, thresholds=cfg['thresholds'], all360_reference_accuracy=accuracy,
                                 sampled48_reference_accuracy=metadata[-1]['sampled_reference_accuracy'],
                                 static_binary_input_certificate=certificates, layer_ranges=ranges,
                                 original_U11_violations=sum(r['U11_violations'] for r in ranges),
                                 U13_I8_supported=True, scheduled_first48=statistics,
                                 exact_software_states_spikes_counts_classes_match=True))
            print('ORIGINAL_IF RESTORED', seed, 'ACCURACY', accuracy, 'U11_FAILURES', profiles[-1]['original_U11_violations'],
                  'CLOCKS F5/F6/FIXED8', *[statistics[k]['service_clocks_no_output_stalls_with_group_drains'] for k in ('F5','F6','fixed8')], flush=True)
            del records
    assert len(ledger) == 9216 and sum(r['neurons'] for r in ledger) == 635904
    ledger_path = folder/'reference_ledger.json'
    ledger_path.write_text(json.dumps(dict(metadata=metadata, ledger=ledger), separators=(',', ':'))+'\n')
    inputs = [Path(__file__), ORIGINAL/'probe.py', ORIGINAL/'base.py', R/'final_selected.json', R/'exact_inference.json',
              *(R/f'model_seed{seed}.npz' for seed in range(3))]
    result = dict(status='pass', profiles=profiles, groups=9216, scalar_updates=635904,
                  source_sha256={str(path.resolve()):sha(path) for path in inputs},
                  stream_sha256=sha(stream_path), ledger_sha256=sha(ledger_path),
                  semantics='Saved quantized/calibrated64-128-10ANN-to-integerSNNconversion; originalIF, subtractive reset,32steps, full360-imagebatch rng123. No retraining or direct SNN training.',
                  domain='Exact signed13 membrane plus signed8 current to signed14 sum. U11 violations retained; no clipping or operand changes.',
                  certificate='For each neuron, all binary input sums lie in[L,H], withL<=0<=H. Positive subtractive reset maps fired sums to nonnegative state; induction gives state aftertsteps in[tL,tH]. Thus before each of32steps U liesin[31L,31H]. Hardware output14bits covers the final32ndsum.',
                  scope='Software restoration and exact physical48bit residue packing only. Native RTL and routed power remain separate required jobs.')
    (folder/'profile.json').write_text(json.dumps(result, indent=2)+'\n')
    files = {str(path.resolve()):sha(path) for path in folder.iterdir() if path.is_file()}
    (folder/'manifest.json').write_text(json.dumps(dict(status='pass', files=files), indent=2)+'\n')


if __name__ == '__main__':
    main()
