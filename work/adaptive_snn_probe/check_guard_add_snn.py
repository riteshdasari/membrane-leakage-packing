"""Saved SNN threshold/reset replay from exact RTL membrane-plus-current sums.

The input leakage was computed in Python for a saved beta231 reference. This
is not full SNN RTL, new training, or original trained-model accuracy evidence.
"""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
from pathlib import Path
import hashlib
import json
import numpy as np

P = Path(__file__).resolve().parent
R = P/'results'

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()

def main():
    from check_guard_add import free, hashes, model_input_hashes
    assert free() > 1.2, 'Insufficient free RAM for saved replay'
    ledger_path = R/'adaptive_delta_model_input.json'
    ledger = json.loads(ledger_path.read_text())
    records = ledger['ledger']
    source = hashes()
    reconstruction_pin = sha(Path(__file__))
    input_pin = model_input_hashes()
    reference = dict(ledger=sha(ledger_path),
                     raw_membranes=sha(R/'adaptive_delta_model_25_1/expected.npz'))
    rows = []
    outputs = {}
    assert len(records) == 9216
    for stall in (0, 1):
        tag = f'guard_add_models_{stall}'
        checked = json.loads((R/(tag+'_checks.json')).read_text())
        assert checked['source_hashes'] == source and checked['model_input_sha256'] == input_pin
        assert checked['frames'] == len(records) and checked['backpressure'] == bool(stall)
        assert checked['tested_engines'] == checked['expected_engines'] == list(range(4))
        for engine in range(4):
            row = next(r for r in checked['rows'] if r['engine'] == engine)
            assert row['mismatches'] == 0 and row['neurons'] == 635904
            output = R/tag/f'stream_out{engine}.txt'
            output_pin = sha(output)
            assert row['output_sha256'] == output_pin
            sums = [[] for _ in records]
            with output.open() as stream:
                for line in stream:
                    fid, pos, count, placeholder, bits, ac, rc, mode = line.split()
                    fid, pos, count, placeholder = map(int, (fid, pos, count, placeholder))
                    assert 0 <= fid < len(records) and placeholder == 0
                    assert len(sums[fid]) == pos and 1 <= count <= 6
                    packed = int(bits, 16)
                    values = [(packed >> (12*l)) & 4095 for l in range(count)]
                    sums[fid].extend(v-4096 if v >= 2048 else v for v in values)
            counts = {m['seed']: np.zeros((48, 10), np.int64) for m in ledger['metadata']}
            state_bad = spike_bad = neurons = 0
            for rec, summed in zip(records, sums):
                assert len(summed) == rec['neurons']
                state = np.array(summed, dtype=np.int64)
                fired = state >= rec['threshold']
                state -= fired*rec['threshold']
                state_bad += int(np.count_nonzero(state != rec['expected_state']))
                spike_bad += int(np.count_nonzero(fired != rec['expected_spikes']))
                neurons += len(state)
                if rec['layer'] == 1:
                    counts[rec['seed']][rec['image']] += fired
            assert state_bad == spike_bad == 0 and neurons == 635904
            models = []
            for meta in ledger['metadata']:
                count = counts[meta['seed']]
                assert np.array_equal(count, meta['expected_counts'])
                classification = count.argmax(1)
                accuracy = float(np.mean(classification == meta['labels']))
                assert accuracy == meta['sampled_reference_accuracy']
                models.append(dict(seed=meta['seed'], images=48, accuracy=accuracy,
                                   spike_counts_matched=True))
            assert sha(output) == output_pin, 'Output changed during replay'
            outputs[str(output.relative_to(P))] = output_pin
            rows.append(dict(engine=engine, backpressure=bool(stall), neurons=neurons,
                             state_mismatches=state_bad, spike_mismatches=spike_bad,
                             model_rows=models))
            print('GUARD ADD SNN', engine, 'stall', stall,
                  'states/spikes/counts/classifications match', flush=True)
    assert hashes() == source and model_input_hashes() == input_pin
    assert sha(Path(__file__)) == reconstruction_pin
    result = dict(source_hashes=source, reconstruction_script_sha256=reconstruction_pin,
                  reference_hashes=reference, output_hashes=outputs, rows=rows,
                  scope='Python leakage followed by RTL membrane-plus-current addition and Python threshold/subtractive-reset replay',
                  limitations=['Saved beta231 reference; original trained leakage was changed.',
                               '144 sampled images across three saved seeds; no new training or download.',
                               'No full SNN RTL, state-memory implementation, host, power or board test.',
                               'Addition primitive accepts two signed11 operands and returns signed12; full state-format handling is not implemented.'])
    (R/'guard_add_snn_checks.json').write_text(json.dumps(result, indent=2))
    print('GUARD ADD SNN PASS', flush=True)

if __name__ == '__main__':
    main()
