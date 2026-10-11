"""Read-only checks for isolated V3 versus the frozen adaptive reference.

Checks archived source, stimulus and retirement pins; repeats plain signed U+I
for all retired valid lanes; demands byte-identical physical-clock columns and
reset/control equivalence reported by the shadow testbench. No tools launch.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import sys

sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent
COMMON = P.parent / 'common_layout_trial'
ENERGY = P.parent / 'selective_energy_trial'
CORE_SHA = 'b5c7d724d642b2310c4e447eabccaf965a3aa520aaf2e04c5f93accd5dbb9e48'
DRIVER_SHA = '52245a991b24ffd91bc99207eb208482ab211316eb4ed1a25134c189b0f155e2'


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def equal_bytes(left, right):
    with Path(left).open('rb') as expected, Path(right).open('rb') as actual:
        while True:
            chunk = expected.read(1048576)
            assert actual.read(1048576) == chunk, ('Bytes differ', str(left), str(right))
            if not chunk:
                break


def signed11(raw):
    assert 0 <= raw < 2048
    return raw - 2048 if raw >= 1024 else raw


def arithmetic(stimulus, retirement):
    requests = operations = 0
    numeric = hashlib.sha256()
    latency = {}
    with Path(stimulus).open() as source, Path(retirement).open() as result:
        frames = int(source.readline())
        assert frames > 0
        for frame in range(frames):
            count, gap = map(int, source.readline().split())
            assert 1 <= count <= 4096 and gap >= 0
            values = []
            for _ in range(count):
                u, current = [signed11(int(value, 16)) for value in source.readline().split()]
                assert -128 <= current <= 127
                values.append((u, current))
            for position in range(0, count, 6):
                tokens = result.readline().split()
                assert len(tokens) == 8, ('Missing/invalid retirement row', frame, position)
                fid, pos, n, unused, bits, accept, retire, mode = tokens
                fid, pos, n, unused, accept, retire, mode = map(int, (fid, pos, n, unused, accept, retire, mode))
                assert (fid, pos, n, unused, mode) == (frame, position, min(6, count-position), 0, 0)
                packed = int(bits, 16)
                assert 0 <= packed < 2**72 and retire-accept >= 4
                want = sum(((u+i) & 4095) << (12*lane)
                           for lane, (u, i) in enumerate(values[position:position+n]))
                assert packed == want, ('Integer U+I/tail mismatch', frame, position)
                numeric.update(f'{fid} {pos} {n} {packed:018x}\n'.encode('ascii'))
                delta = retire-accept
                latency[str(delta)] = latency.get(str(delta), 0)+1
                requests += 1
                operations += n
        assert not source.read().strip() and not result.read().strip()
    return dict(requests=requests, neurons=operations, frames=frames,
                numeric_retirement_sha256=numeric.hexdigest(),
                physical_latency_histogram=dict(sorted(latency.items(), key=lambda item: int(item[0]))))


def verify_case(directory, kind, stall, policy=1, log_path=None, trace_reference=None):
    directory = Path(directory).resolve()
    assert kind in ('main', 'models') and stall in (0, 1)
    assert sha(COMMON/'guard_add_selective.sv') == CORE_SHA
    assert sha(COMMON/'tb_guard_add_selective.sv') == DRIVER_SHA
    tag = f'selective_{kind}_p1_{stall}'
    check_file = COMMON/'results'/f'{tag}_checks.json'
    check_pin = sha(check_file)
    archive = json.loads(check_file.read_text(encoding='utf-8'))
    assert archive['profile'] == 1 and archive['backpressure'] == bool(stall)
    assert archive['tested_core_variants'] == [2, 3]
    assert archive['integer_operation'] == 'exact signed12 U+I'
    source_pins = {}
    for name, stamp in archive['source_hashes'].items():
        path = COMMON/name
        assert sha(path) == stamp, ('Archived source changed', path)
        source_pins[str(path.resolve())] = stamp
    if archive['model_input_sha256']:
        for name, stamp in archive['model_input_sha256'].items():
            path = COMMON.parent/'results'/name
            assert sha(path) == stamp, ('Saved model input changed', path)
            source_pins[str(path.resolve())] = stamp
    expected = next(row for row in archive['rows'] if row['variant'] == 1)
    assert expected['core_variant'] == 3 and expected['mismatches'] == 0
    archived_stimulus = COMMON/'results'/archive['stimulus_file']
    archived_output = COMMON/'results'/tag/'stream_out1.txt'
    assert sha(archived_stimulus) == archive['stimulus_sha256']
    assert sha(archived_output) == expected['output_sha256']
    stimulus = directory/'stream_stim.txt'
    reference = directory/'stream_out1.txt'
    isolated = directory/'isolated_stream_out1.txt'
    pins = {str(path): sha(path) for path in (stimulus, reference, isolated)}
    equal_bytes(stimulus, archived_stimulus)
    equal_bytes(reference, archived_output)
    equal_bytes(isolated, archived_output)
    checked = arithmetic(stimulus, isolated)
    for field in ('requests', 'neurons', 'numeric_retirement_sha256', 'physical_latency_histogram'):
        assert checked[field] == expected[field], ('Retirement statistic changed', field)
    assert checked['frames'] == archive['frames']
    log_path = Path(log_path) if log_path else directory/'tool_3.log'
    log_pin = sha(log_path)
    log = log_path.read_text(encoding='utf-8', errors='replace')
    assert not re.search(r'(^|\n)\s*(FATAL|ERROR|Error|Fatal)\s*:', log)
    marker = re.search(r'OPERAND_ISOLATION PASS POLICY (\d+) STALL (\d+) REQUESTS (\d+) RETIREMENTS (\d+) NEURONS (\d+) CLOCKS (\d+) CORRECTION_STEPS (\d+) CORRECTION_FREEZES (\d+) PIN_CHECKS (\d+) PRELUDE_SAMPLES (\d+) RESET_SAMPLES (\d+) TRACE_ROWS (\d+)', log)
    assert marker, ('No shadow-testbench PASS', log_path)
    names = ['policy', 'stall', 'requests', 'retirements', 'neurons', 'clocks',
             'correction_steps', 'correction_freezes', 'pin_checks',
             'prelude_samples', 'reset_samples', 'trace_rows']
    stats = dict(zip(names, map(int, marker.groups())))
    assert stats['policy'] == policy and stats['stall'] == stall
    assert stats['retirements'] == stats['requests'] == checked['requests']
    for name in ('requests', 'neurons', 'clocks', 'correction_steps', 'correction_freezes'):
        assert stats[name] == expected[name], ('Physical service changed', name)
    assert stats['prelude_samples'] > 0 and stats['reset_samples'] > 0
    assert stats['pin_checks'] >= 2*stats['trace_rows']
    trace_check = None
    trace = directory/'isolated_native_trace1.txt'
    if trace.exists():
        assert kind == 'models' and stall == 0, 'Archived energy trace exists only for saved-model STALL0'
        trace_reference = Path(trace_reference) if trace_reference else ENERGY/'results/native_models_0_a1/native_trace1.txt'
        equal_bytes(trace, trace_reference)
        trace_check = dict(file=str(trace), sha256=sha(trace),
                           reference=str(trace_reference), reference_sha256=sha(trace_reference),
                           matched_all_eighteen_columns=True)
    assert sha(check_file) == check_pin and sha(log_path) == log_pin
    for path, stamp in source_pins.items():
        assert sha(path) == stamp
    for path, stamp in pins.items():
        assert sha(path) == stamp
    return dict(status='pass', kind=kind, backpressure=bool(stall), policy=policy,
                source_sha256=source_pins, archived_check_file=str(check_file),
                archived_check_sha256=check_pin, archived_retirement_file=str(archived_output),
                archived_retirement_sha256=sha(archived_output), stimulus_sha256=sha(stimulus),
                candidate_file_sha256=pins, log_file=str(log_path), log_sha256=log_pin,
                arithmetic=checked, physical_service=stats, trace=trace_check,
                matched_archived_retirement_bytes=True, matched_reference_retirement_bytes=True,
                output_controls_and_internal_service_cycle_identical=True,
                reset_and_backpressure_preludes_checked=True,
                scope='Exact signed11 U plus signed8 I; six fixed lanes; measurement of RTL cycle equivalence only, no timing/power/energy claim.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--kind', choices=('main', 'models'), required=True)
    parser.add_argument('--stall', type=int, choices=(0, 1), required=True)
    parser.add_argument('--policy', type=int, default=1)
    parser.add_argument('--log', type=Path)
    parser.add_argument('--trace-reference', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = verify_case(args.directory, args.kind, args.stall, args.policy,
                         args.log, args.trace_reference)
    path = args.output or args.directory/'isolation_checks.json'
    path.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print('OPERAND ISOLATION CHECK PASS', path, result['physical_service'], flush=True)


if __name__ == '__main__':
    main()
