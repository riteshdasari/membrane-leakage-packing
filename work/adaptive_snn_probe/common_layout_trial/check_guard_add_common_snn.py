"""Replay saved beta231 SNN threshold/reset from four exact common-layout/reference outputs.

Leakage is supplied in Python using the original saved-reference oracle. This
is eight output-file replays, not a full RTL SNN or trained-accuracy claim.
"""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
from pathlib import Path
import json
import sys
sys.dont_write_bytecode = True
import numpy as np
from check_guard_add_common import free, hashes, model_input_hashes, sha, VARIANTS

P = Path(__file__).resolve().parent
R = P / 'results'
REFERENCE = P.parent / 'results'


def main():
    assert free() > 1.2, 'Insufficient free RAM for saved replay'
    ledger_path = REFERENCE / 'adaptive_delta_model_input.json'
    ledger = json.loads(ledger_path.read_text())
    records = ledger['ledger']
    assert len(records) == 9216
    source = hashes()
    reconstruction_pin = sha(Path(__file__))
    input_pin = model_input_hashes()
    references = dict(ledger=sha(ledger_path), raw_membranes=sha(REFERENCE / 'adaptive_delta_model_25_1/expected.npz'))
    rows, outputs, checks = [], {}, {}
    for stall in (0, 1):
        tag = f'common_models_{stall}'
        check_path = R / (tag + '_checks.json')
        checks[check_path.name] = sha(check_path)
        checked = json.loads(check_path.read_text())
        assert checked['source_hashes'] == source and checked['model_input_sha256'] == input_pin
        assert checked['frames'] == 9216 and checked['backpressure'] == bool(stall)
        assert checked['tested_variants'] == checked['expected_variants'] == VARIANTS
        assert checked['outputs_byte_identical'] and checked['matched_original_stimulus']
        assert checked['acceptance_to_handshake_advances'] == 4
        assert checked['validation_kind'] == 'saved_model_addition_replay'
        assert sha(R / checked['stimulus_file']) == checked['stimulus_sha256']
        for variant in VARIANTS:
            checked_row = next(row for row in checked['rows'] if row['variant'] == variant)
            assert checked_row['mismatches'] == 0 and checked_row['neurons'] == 635904
            assert checked_row['latency_checks'] == checked_row['requests']
            output = R / tag / f'stream_out{variant}.txt'
            output_pin = sha(output)
            assert checked_row['output_sha256'] == output_pin
            sums = [[] for _ in records]
            with output.open() as stream:
                for line in stream:
                    fid, pos, count, placeholder, bits, accepted, retired, mode = line.split()
                    fid, pos, count, placeholder = map(int, [fid, pos, count, placeholder])
                    assert 0 <= fid < len(records) and placeholder == 0 and len(sums[fid]) == pos
                    assert 1 <= count <= 6
                    packed = int(bits, 16)
                    assert 0 <= packed < (1 << 72)
                    values = [(packed >> (12 * lane)) & 4095 for lane in range(count)]
                    sums[fid].extend(value - 4096 if value >= 2048 else value for value in values)
            counts = {meta['seed']: np.zeros((48, 10), np.int64) for meta in ledger['metadata']}
            state_bad = spike_bad = neurons = 0
            for record, summed in zip(records, sums):
                assert len(summed) == record['neurons']
                state = np.asarray(summed, dtype=np.int64)
                fired = state >= record['threshold']
                state -= fired * record['threshold']
                state_bad += int(np.count_nonzero(state != record['expected_state']))
                spike_bad += int(np.count_nonzero(fired != record['expected_spikes']))
                neurons += len(state)
                if record['layer'] == 1:
                    counts[record['seed']][record['image']] += fired
            assert state_bad == spike_bad == 0 and neurons == 635904
            models = []
            for meta in ledger['metadata']:
                got = counts[meta['seed']]
                assert np.array_equal(got, meta['expected_counts'])
                accuracy = float(np.mean(got.argmax(1) == meta['labels']))
                assert accuracy == meta['sampled_reference_accuracy']
                models.append(dict(seed=meta['seed'], images=48, accuracy=accuracy, spike_counts_matched=True))
            assert sha(output) == output_pin, 'Output changed during SNN replay'
            outputs[str(output.relative_to(P))] = output_pin
            rows.append(dict(variant=variant, backpressure=bool(stall), neurons=neurons,
                             state_mismatches=state_bad, spike_mismatches=spike_bad, model_rows=models))
            print('COMMON SNN', variant, 'stall', stall, 'states/spikes/counts/classifications match', flush=True)
        assert sha(check_path) == checks[check_path.name], 'Functional evidence changed during replay'
    assert hashes() == source and model_input_hashes() == input_pin
    assert sha(Path(__file__)) == reconstruction_pin
    result = dict(source_hashes=source, reconstruction_script_sha256=reconstruction_pin,
                  functional_check_sha256=checks, reference_hashes=references,
                  output_hashes=outputs, rows=rows, tested_variants=VARIANTS,
                  scope='Python leakage, exact RTL U+I common-layout/reference baseline outputs, Python threshold/subtractive-reset replay',
                  limitations=['Saved beta231 reference; original trained leakage was changed.',
                               '144 sampled images across three saved seeds; no new training or downloads.',
                               'Fixed common-layout correction only; no memory supply, power, host or board result.',
                               'No full SNN RTL or preservation claim for original trained-model accuracy.'])
    (R / 'common_snn_checks.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print('GUARD ADD COMMON SNN PASS', flush=True)


if __name__ == '__main__':
    main()
