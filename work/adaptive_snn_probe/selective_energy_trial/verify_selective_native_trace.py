"""Independently verify 6ns native fixed/shared correction pin traces.

No simulator or synthesis tool is launched. The captured pre-rising controls
are used to reconstruct each accepted and retired transaction, ordinary U+I
arithmetic, four advancing edges, physical service, and the exact ROI. Invalid
output data may be unknown; all valid output data and relevant controls must be
known. Trace changes are not a power or energy measurement.
"""
from pathlib import Path
import argparse
from collections import deque
import hashlib
import json
import re
import sys

sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent
BASE = P.parent
ARCHIVE = BASE / 'common_layout_trial'
ARCHIVED_TAG = 'selective_models_p1_0'
ARCHIVED_CHECK = ARCHIVE / 'results' / (ARCHIVED_TAG + '_checks.json')
COLUMNS = ['trace_index', 'running', 'done', 'rst', 'in_valid', 'out_ready',
           'available', 'raw_u', 'raw_i', 'in_ready', 'take', 'out_valid',
           'out_count', 'out_data', 'narrow_mode', 'correction_signal',
           'advance_signal', 'busy_signal']
BOOLS = ['running', 'done', 'rst', 'in_valid', 'out_ready', 'in_ready',
         'out_valid', 'narrow_mode', 'correction_signal', 'advance_signal', 'busy_signal']
SOURCES = ['tb_selective_native_trace.sv', 'verify_selective_native_trace.py',
           '../common_layout_trial/guard_add_selective.sv',
           '../common_layout_trial/tb_guard_add_selective.sv',
           '../guard_add.sv', '../baseline_retime_trial/guard_add_retime.sv']


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1048576), b''):
            digest.update(chunk)
    return digest.hexdigest()


def hashes():
    return {name: sha(P / name) for name in SOURCES}


def equal_bytes(left, right):
    with Path(left).open('rb') as expected, Path(right).open('rb') as got:
        while True:
            chunk = expected.read(1048576)
            assert got.read(1048576) == chunk, ('Bytes differ', str(left), str(right))
            if not chunk:
                break


def signed11(value):
    return value - 2048 if value >= 1024 else value


def saved_references():
    pin = sha(ARCHIVED_CHECK)
    checked = json.loads(ARCHIVED_CHECK.read_text())
    assert checked['profile'] == 1 and not checked['backpressure']
    assert checked['frames'] == 9216 and checked['tested_core_variants'] == [2, 3]
    assert checked['validation_kind'] == 'saved_model_addition_replay'
    assert checked['stress_current_transform'] == 'identity' and checked['matched_original_stimulus']
    assert checked['acceptance_to_handshake_preceding_advances'] == 4
    for name, value in checked['source_hashes'].items():
        assert sha(ARCHIVE / name) == value, ('Frozen source changed', name)
    model_hashes = checked['model_input_sha256']
    for name, value in model_hashes.items():
        assert sha(BASE / 'results' / name) == value, ('Frozen model input changed', name)
    stimulus = ARCHIVE / 'results' / checked['stimulus_file']
    assert sha(stimulus) == checked['stimulus_sha256']
    outputs = {}
    for local_variant in (0, 1):
        row = next(row for row in checked['rows'] if row['variant'] == local_variant)
        assert row['core_variant'] == local_variant + 2 and row['mismatches'] == 0
        path = ARCHIVE / 'results' / ARCHIVED_TAG / f'stream_out{local_variant}.txt'
        assert sha(path) == row['output_sha256']
        outputs[str(local_variant)] = dict(file=str(path), sha256=row['output_sha256'])
    assert sha(ARCHIVED_CHECK) == pin
    return checked, dict(check_file=str(ARCHIVED_CHECK), check_sha256=pin,
                         source_hashes=checked['source_hashes'], model_input_sha256=model_hashes,
                         stimulus_file=str(stimulus), stimulus_sha256=checked['stimulus_sha256'],
                         outputs=outputs)


class StimulusCursor:
    """Read only one saved frame at a time; no copied scheduling formula."""
    def __init__(self, path):
        self.stream = Path(path).open()
        self.frame_count = int(self.stream.readline())
        assert self.frame_count == 9216
        self.frame = -1
        self.position = 0
        self.operations = 0
        self.read_frame()

    def read_frame(self):
        self.frame += 1
        self.position = 0
        if self.frame == self.frame_count:
            self.u, self.current = [], []
            assert not self.stream.read().strip()
            return
        count, gap = map(int, self.stream.readline().split())
        assert 1 <= count <= 4096 and gap == 0
        self.u, self.current = [], []
        for _ in range(count):
            raw_u, raw_i = (int(value, 16) for value in self.stream.readline().split())
            assert 0 <= raw_u < 2048 and 0 <= raw_i < 2048
            u, i = signed11(raw_u), signed11(raw_i)
            assert -128 <= i <= 127
            self.u.append(u)
            self.current.append(i)

    def accept(self, row, cycle, advances):
        assert self.frame < self.frame_count
        count = min(6, len(self.u) - self.position)
        assert row['available'] == row['take'] == count
        expected = 0
        bad = 0
        for lane in range(count):
            u = signed11((row['raw_u'] >> (11 * lane)) & 2047)
            current = signed11((row['raw_i'] >> (11 * lane)) & 2047)
            assert (u, current) == (self.u[self.position+lane], self.current[self.position+lane])
            assert -128 <= current <= 127
            expected |= ((u + current) & 4095) << (12 * lane)
            carry = ((u & 127) + (current & 127)) >> 7
            fast = (-128 <= u <= 127) or carry == int(current < 0)
            bad += int(not fast)
        value = dict(frame=self.frame, position=self.position, count=count,
                     expected=expected, accepted_cycle=cycle, accepted_trace_index=row['trace_index'],
                     accepted_advances=advances, exceptional_lanes=bad)
        self.operations += count
        self.position += count
        if self.position == len(self.u):
            self.read_frame()
        return value

    def close(self):
        self.stream.close()


def trace_rows(path):
    with Path(path).open() as stream:
        for index, line in enumerate(stream):
            tokens = line.split()
            assert len(tokens) == len(COLUMNS), ('Trace schema', str(path), index, len(tokens))
            raw = dict(zip(COLUMNS, tokens))
            row = {}
            row['trace_index'] = int(raw['trace_index'])
            assert row['trace_index'] == index
            for name in BOOLS:
                assert raw[name] in ('0', '1'), ('Unknown control', str(path), index, name, raw[name])
                row[name] = int(raw[name])
            for name in ('available', 'take', 'out_count'):
                assert re.fullmatch(r'[0-6]', raw[name]), ('Unknown/count domain', index, name, raw[name])
                row[name] = int(raw[name])
            for name in ('raw_u', 'raw_i'):
                assert re.fullmatch(r'[0-9a-fA-F]{17}', raw[name]), ('Unknown raw input', index, name)
                row[name] = int(raw[name], 16)
                assert row[name] < (1 << 66)
            data = raw['out_data']
            assert re.fullmatch(r'[0-9a-fA-FxXzZ]{18}', data), ('Bad output encoding', index, data)
            row['out_data'] = None if re.search(r'[xXzZ]', data) else int(data, 16)
            assert not row['done'], 'Post-done row included'
            assert row['in_ready'] == row['advance_signal']
            assert row['narrow_mode'] == 0 and row['take'] == row['available']
            if row['out_valid']:
                assert row['out_data'] is not None, ('Unknown valid output', index)
                assert 1 <= row['out_count'] <= 6
            yield row


def verify_variant(directory, variant, checked):
    trace_path = directory / f'native_trace{variant}.txt'
    output_path = directory / f'stream_out{variant}.txt'
    stimulus_path = directory / 'stream_stim.txt'
    trace_pin, output_pin = sha(trace_path), sha(output_path)
    archived = next(row for row in checked['rows'] if row['variant'] == variant)
    assert output_pin == archived['output_sha256']
    equal_bytes(ARCHIVE / 'results' / ARCHIVED_TAG / f'stream_out{variant}.txt', output_path)
    cursor = StimulusCursor(stimulus_path)
    queue = deque()
    previous = None
    running_first = first_accept = last_retire = None
    trace_count = advances = accepted = retired = neurons = corrections = freezes = 0
    freeze_run = freeze_max = input_stalls = output_stalls = 0
    expected_bad = unknown_invalid_data_rows = rst_rows = 0
    latency_histogram = {}
    numeric = hashlib.sha256()
    with output_path.open() as output:
        for row in trace_rows(trace_path):
            index = row['trace_index']
            trace_count += 1
            rst_rows += row['rst']
            unknown_invalid_data_rows += int(row['out_data'] is None and not row['out_valid'])
            if variant == 0:
                assert row['correction_signal'] == row['busy_signal'] == 0
            if not row['running']:
                assert running_first is None, 'Running returned to zero'
                previous = row
                continue
            if running_first is None:
                running_first = index
                assert index > 0 and previous is not None and not previous['running']
            assert row['rst'] == 0 and row['out_ready'] == 1
            cycle = index - running_first + 1
            if previous is not None and previous['running']:
                if previous['in_valid'] and not previous['in_ready']:
                    input_stalls += 1
                    for name in ('in_valid', 'available', 'raw_u', 'raw_i', 'take'):
                        assert row[name] == previous[name], ('Held input changed', index, name)
                if previous['out_valid'] and not previous['out_ready']:
                    output_stalls += 1
                    for name in ('out_valid', 'out_count', 'out_data'):
                        assert row[name] == previous[name], ('Held output changed', index, name)
            corrections += row['correction_signal']
            frozen = row['correction_signal'] and not row['advance_signal']
            freezes += int(frozen)
            freeze_run = freeze_run + 1 if frozen else 0
            freeze_max = max(freeze_max, freeze_run)
            if row['in_valid'] and row['in_ready'] and row['available']:
                item = cursor.accept(row, cycle, advances)
                queue.append(item)
                expected_bad += item['exceptional_lanes']
                accepted += 1
                neurons += item['count']
                if first_accept is None:
                    first_accept = index
            if row['out_valid'] and row['out_ready']:
                assert queue, ('Unmatched retirement', index)
                item = queue.popleft()
                assert row['out_count'] == item['count'] and row['out_data'] == item['expected']
                assert advances - item['accepted_advances'] == 4, ('Advance latency', index)
                latency = cycle - item['accepted_cycle']
                assert latency >= 4 + (max(item['exceptional_lanes'] - 1, 0) if variant == 1 else 0)
                if variant == 0:
                    assert latency == 4
                latency_histogram[latency] = latency_histogram.get(latency, 0) + 1
                line = (f"{item['frame']} {item['position']} {item['count']} 0 "
                        f"{item['expected']:018x} {item['accepted_cycle']} {cycle} 0\n")
                assert output.readline() == line, ('Trace/stream clock or sum mismatch', index)
                numeric.update(f"{item['frame']} {item['position']} {item['count']} {item['expected']:018x}\n".encode('ascii'))
                retired += 1
                last_retire = index
            advances += row['advance_signal']
            previous = row
        assert not output.read().strip(), 'Retirement rows remain beyond native trace'
    assert trace_count > 0 and previous is not None and previous['running']
    assert not queue and cursor.frame == cursor.frame_count and cursor.operations == 635904
    cursor.close()
    assert accepted == retired == 110592 and neurons == 635904
    assert expected_bad == 1008
    assert first_accept is not None and last_retire == trace_count - 1
    clocks = last_retire - first_accept + 1
    assert clocks == (110596 if variant == 0 else 110710) == archived['clocks']
    assert corrections == (0 if variant == 0 else 1008) == archived['correction_steps']
    assert freezes == (0 if variant == 0 else 114) == archived['correction_freezes']
    assert freeze_max == (0 if variant == 0 else 2) == archived['max_internal_correction_freeze_run']
    assert input_stalls == archived['input_stall_checks'] and output_stalls == 0
    assert {str(k): v for k, v in sorted(latency_histogram.items())} == archived['physical_latency_histogram']
    assert numeric.hexdigest() == archived['numeric_retirement_sha256']
    assert sha(trace_path) == trace_pin and sha(output_path) == output_pin
    return dict(variant=variant, core_variant=variant+2, status='pass',
                trace_file=str(trace_path), trace_sha256=trace_pin, trace_count=trace_count,
                retirement_file=str(output_path), retirement_sha256=output_pin,
                running_first_trace_index=running_first, first_accept_trace_index=first_accept,
                last_retire_trace_index=last_retire, roi_first_trace_index=first_accept,
                roi_last_trace_index=last_retire, roi_rows=clocks, service_clocks=clocks,
                roi_cycle_duration_ns=clocks*6,
                first_accept_rising_time_ns=9+first_accept*6,
                final_retire_rising_time_ns=9+last_retire*6,
                first_accept_to_final_retire_edge_span_ns=(clocks-1)*6,
                first_roi_trace_sample_time_ns=6.020+first_accept*6,
                last_roi_trace_sample_time_ns=6.020+last_retire*6,
                requests=accepted, retired_requests=retired, neurons=neurons,
                correction_steps=corrections, correction_freezes=freezes,
                max_correction_freeze_run=freeze_max, expected_exceptional_lanes=expected_bad,
                input_stall_checks=input_stalls, output_stall_checks=output_stalls,
                physical_latency_histogram={str(k): v for k, v in sorted(latency_histogram.items())},
                numeric_retirement_sha256=numeric.hexdigest(),
                reset_rows=rst_rows, unknown_invalid_output_data_rows=unknown_invalid_data_rows,
                unknown_valid_output_data_rows=0, post_done_rows=0,
                matched_archived_retirement_bytes=True, arithmetic_mismatches=0,
                trace_retirement_clock_columns_matched=True, four_advance_invariant_matched=True)


def verify_dir(directory):
    directory = Path(directory).resolve()
    sources = hashes()
    checked, reference = saved_references()
    stimulus = directory / 'stream_stim.txt'
    stimulus_pin = sha(stimulus)
    assert stimulus_pin == reference['stimulus_sha256']
    equal_bytes(reference['stimulus_file'], stimulus)
    rows = [verify_variant(directory, variant, checked) for variant in (0, 1)]
    assert hashes() == sources and sha(stimulus) == stimulus_pin
    assert saved_references()[1] == reference
    return dict(status='pass', source_hashes=sources, reference_hashes=reference,
                stimulus_file=str(stimulus), stimulus_sha256=stimulus_pin, rows=rows,
                trace_schema=COLUMNS, trace_columns=len(COLUMNS), trace_header=False,
                sampling='Falling edge +0.020ns, after native driver inputs settle, before next rising edge.',
                clock_period_ns=6, first_trace_sample_time_ns=6.020,
                first_trace_consuming_rising_time_ns=9,
                gsr_convention='Installed Xilinx glbl initial GSR; frozen driver first waits120ns; complete reset prelude retained.',
                trace_end='Each final row precedes that driver final rising-edge retirement; no post-done rows.',
                roi_definition='Inclusive first accepted work row through final retired work row.',
                roi_duration_convention='Inclusive cycle count times6ns; edge-to-edge span is one clock shorter. Actual routed SAIF duration must be audited separately.',
                source_contract='Frozen native PROFILE1 STALL0 drivers; only available currents signed8; binary ignored tails arbitrary.',
                scope='Native exactness, service, activity interval and pin trace attestation; no routed timing, power, energy or trained-accuracy claim.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = verify_dir(args.directory)
    path = args.output or (args.directory / 'native_trace_checks.json')
    path.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print('SELECTIVE NATIVE TRACE CHECK PASS', path, flush=True)
    for row in result['rows']:
        print({key: row[key] for key in ('variant', 'trace_count', 'first_accept_trace_index',
              'last_retire_trace_index', 'service_clocks', 'requests', 'neurons',
              'correction_steps', 'correction_freezes')}, flush=True)


if __name__ == '__main__':
    main()
