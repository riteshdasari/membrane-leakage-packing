"""Reconstruct saved SNN states/spikes from exact quad RTL leakage outputs.

This checks an existing reference whose leakage was changed to beta231/256.
It is not a closed-loop SNN accelerator simulation or a newly trained model.
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
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    from check_quad import free, hashes
    assert free() > 1.2, 'Insufficient free RAM for reference reconstruction'
    ledger_path = R/'adaptive_delta_model_input.json'
    ledger = json.loads(ledger_path.read_text())
    records = ledger['ledger']
    source = hashes()
    reference = {'ledger': sha(ledger_path),
                 'raw_membranes': sha(R/'adaptive_delta_model_25_1/expected.npz')}
    rows = []
    checked_outputs = {}
    for stall in (0, 1):
        tag = f'quad_models_{stall}'
        checked = json.loads((R/(tag+'_checks.json')).read_text())
        assert checked['source_hashes'] == source
        assert checked['delta'] == 25 and checked['frames'] == len(records)
        for e in range(5):
            assert next(x for x in checked['rows'] if x['engine'] == e)['mismatches'] == 0
            output = R/tag/f'stream_out{e}.txt'
            membranes = [[] for _ in records]
            with output.open() as stream:
                for line in stream:
                    fid, pos, n, delta, bits, *_ = line.split()
                    fid, pos, n, delta = map(int, (fid, pos, n, delta))
                    assert delta == 25 and len(membranes[fid]) == pos
                    packed = int(bits, 16)
                    values = [(packed >> (11*l)) & 2047 for l in range(n)]
                    membranes[fid].extend(v-2048 if v >= 1024 else v for v in values)
            counts = {m['seed']: np.zeros((48, 10), np.int64) for m in ledger['metadata']}
            state_bad = spike_bad = neurons = 0
            for rec, leaked in zip(records, membranes):
                assert len(leaked) == rec['neurons']
                state = np.array(leaked) + np.array(rec['current'])
                fired = state >= rec['threshold']
                state -= fired * rec['threshold']
                state_bad += int(np.count_nonzero(state != rec['expected_state']))
                spike_bad += int(np.count_nonzero(fired != rec['expected_spikes']))
                neurons += len(leaked)
                if rec['layer'] == 1:
                    counts[rec['seed']][rec['image']] += fired
            assert state_bad == spike_bad == 0
            model_rows = []
            for metadata in ledger['metadata']:
                counted = counts[metadata['seed']]
                assert np.array_equal(counted, metadata['expected_counts'])
                accuracy = float(np.mean(counted.argmax(1) == metadata['labels']))
                assert accuracy == metadata['sampled_reference_accuracy']
                model_rows.append(dict(seed=metadata['seed'], images=48,
                                       accuracy=accuracy, spike_counts_matched=True))
            rows.append(dict(engine=e, backpressure=bool(stall), neurons=neurons,
                             state_mismatches=state_bad, spike_mismatches=spike_bad,
                             model_rows=model_rows))
            checked_outputs[str(output.relative_to(P))] = sha(output)
            print('QUAD SNN RECONSTRUCTION', e, 'stall', stall,
                  'states/spikes/counts/classifications match', flush=True)
    assert hashes() == source and sha(ledger_path) == reference['ledger']
    result = dict(source_hashes=source, reconstruction_script_sha256=sha(Path(__file__)),
                  reference_hashes=reference, output_hashes=checked_outputs, rows=rows,
                  scope='RTL leakage outputs plus Python current/threshold/subtractive-reset replay',
                  limitations=['Saved beta231 reference; original trained leakage was changed.',
                               '144 sampled images across three saved seeds; no new training/download.',
                               'No full SNN RTL, state-memory implementation, host, power or board test.'])
    (R/'quad_snn_checks.json').write_text(json.dumps(result, indent=2))
    print('QUAD SNN RECONSTRUCTION PASS', flush=True)

if __name__ == '__main__':
    main()
