"""Matched signed11-U/signed8-I fixed-datapath checks.

Only --run launches RTL tools. Full stress reuses the original frozen generator
with I mapped by ((I+128)%256)-128; saved-model operands remain unchanged.
All four fixed implementations must retire byte-identical rows, including
physical clock columns, and match the archived selective-profile1 fixed V2.
The numeric oracle is ordinary signed integer U+I, without DSP-layout algebra.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent
R = P / 'results'
ORIGINAL = P.parent
ARCHIVE = ORIGINAL / 'common_layout_trial'
VIVADO = Path('C:/AMDDesignTools/2025.2/Vivado')
VARIANTS = [0, 1, 2, 3]
SOURCES = ['guard_add_i8_fixed.sv', 'tb_guard_add_i8_fixed.sv',
           'check_guard_add_i8_fixed.py', 'check_guard_add_i8_fixed_snn.py',
           '../common_layout_trial/guard_add_selective.sv',
           '../baseline_retime_trial/guard_add_retime.sv',
           '../guard_add.sv', '../check_guard_add.py']
FROZEN_SOURCE_SHA256 = {
    '../common_layout_trial/guard_add_selective.sv': 'b5c7d724d642b2310c4e447eabccaf965a3aa520aaf2e04c5f93accd5dbb9e48',
    '../baseline_retime_trial/guard_add_retime.sv': '0409a89ead96866abee93ee4829210eb093d682a886a847bbf22557e1bd14efc',
    '../guard_add.sv': 'f89019a87185b046a95819f70cf0c9d83f2fe20ee0a5a0e253a2702e9629a907',
    '../check_guard_add.py': '1c7212164c029217679c8348427204c80b855c99b5b4b16d05ecdcf8f53aa834',
}
LABELS = ['matched_i8_hybrid_E2', 'matched_i8_all_LUT_E3',
          'frozen_i8_fixed_residue_V2', 'frozen_full_i11_retimed_hybrid_E2']


def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1048576), b''):
            value.update(chunk)
    return value.hexdigest()


ORACLE_SHA = sha(ORIGINAL / 'check_guard_add.py')
assert ORACLE_SHA == FROZEN_SOURCE_SHA256['../check_guard_add.py']
sys.path.insert(0, str(ORIGINAL))
import check_guard_add as original
assert sha(ORIGINAL / 'check_guard_add.py') == ORACLE_SHA
free = original.free
frames = original.frames
model_frames = original.model_frames
model_input_hashes = original.model_input_hashes


def hashes():
    result = {name: sha(P / name) for name in SOURCES}
    for name, pin in FROZEN_SOURCE_SHA256.items():
        assert result[name] == pin, ('Frozen reference changed', name)
    return result


def signed8_profile(stimulus):
    return [(u, [((i + 128) % 256) - 128 for i in current], gap)
            for u, current, gap in stimulus]


def equal_bytes(left, right):
    with left.open('rb') as expected, right.open('rb') as got:
        while True:
            chunk = expected.read(1048576)
            assert got.read(1048576) == chunk, ('Retirement/stimulus bytes differ', left, right)
            if not chunk:
                break


def check_archived_stimulus(path, stimulus):
    with path.open() as stream:
        assert int(stream.readline()) == len(stimulus)
        for u, current, gap in stimulus:
            assert tuple(map(int, stream.readline().split())) == (len(u), gap)
            for a, b in zip(u, current):
                assert tuple(int(x, 16) for x in stream.readline().split()) == (a & 2047, b & 2047)
        assert not stream.read().strip()


def archive_reference(kind, stall):
    """Rehash the completed profile1 evidence rather than trust its JSON label."""
    tag = f'selective_{kind}_p1_{stall}'
    check_path = ARCHIVE / 'results' / (tag + '_checks.json')
    check_pin = sha(check_path)
    checked = json.loads(check_path.read_text())
    assert checked['profile'] == 1 and checked['backpressure'] == bool(stall)
    assert checked['tested_variants'] == checked['expected_variants'] == VARIANTS
    assert checked['tested_core_variants'] == [2, 3]
    assert checked['fixed_outputs_byte_identical'] and checked['numeric_outputs_order_identical']
    assert checked['acceptance_to_handshake_preceding_advances'] == 4
    assert checked['integer_operation'] == 'exact signed12 U+I'
    for name, pin in checked['source_hashes'].items():
        assert sha(ARCHIVE / name) == pin, ('Archived selective source changed', name)
    fixed = next(row for row in checked['rows'] if row['variant'] == 0)
    assert fixed['core_variant'] == 2 and fixed['mismatches'] == 0
    assert fixed['correction_freezes'] == fixed['correction_steps'] == 0
    stimulus_path = ARCHIVE / 'results' / checked['stimulus_file']
    output_path = ARCHIVE / 'results' / tag / 'stream_out0.txt'
    assert sha(stimulus_path) == checked['stimulus_sha256']
    assert sha(output_path) == fixed['output_sha256']
    assert sha(check_path) == check_pin
    evidence = dict(check_file=str(check_path.relative_to(P.parent)), check_sha256=check_pin,
                    stimulus_file=str(stimulus_path.relative_to(P.parent)),
                    stimulus_sha256=checked['stimulus_sha256'],
                    output_file=str(output_path.relative_to(P.parent)), output_sha256=fixed['output_sha256'],
                    source_hashes=checked['source_hashes'], local_variant=0, frozen_core_variant=2)
    return stimulus_path, output_path, checked, fixed, evidence


def simulate(tag, stimulus, original_stimulus, stall, kind, model_pin=None):
    wd = R / tag
    wd.mkdir(parents=True, exist_ok=True)
    pin = hashes()
    assert all(-1024 <= u <= 1023 and -128 <= i <= 127
               for membrane, current, _ in stimulus for u, i in zip(membrane, current))
    if model_pin is not None:
        assert stimulus == original_stimulus and model_input_hashes() == model_pin
    else:
        assert stimulus == signed8_profile(original_stimulus)
    original.write_stimulus(wd / 'stream_stim.txt', stimulus)
    stimulus_pin = sha(wd / 'stream_stim.txt')
    counterpart = ORIGINAL / 'results' / f'guard_add_{kind}_{stall}' / 'stream_stim.txt'
    original_pin = sha(counterpart) if counterpart.is_file() else None
    archive_pin = archive_fixed = None
    if kind != 'smoke':
        assert original_pin is not None, counterpart
        check_archived_stimulus(counterpart, original_stimulus)
        assert sha(counterpart) == original_pin
        archived_stim, archived_output, archive_check, archive_fixed, archive_pin = archive_reference(kind, stall)
        equal_bytes(archived_stim, wd / 'stream_stim.txt')
        if model_pin is not None:
            assert archive_check['model_input_sha256'] == model_pin
            assert original_pin == stimulus_pin
        else:
            assert archive_check['stress_current_transform'] == 'signed8((I+128)%256-128)'
    assert free() > 1.2, 'Insufficient free RAM for simulation'
    print(tag, 'free GiB', round(free(), 2), flush=True)
    tmp = wd / 'tmp'
    tmp.mkdir(exist_ok=True)
    env = os.environ.copy()
    env['TEMP'] = str(tmp)
    env['TMP'] = str(tmp)
    commands = [
        f'"{VIVADO}/bin/xvlog.bat" -sv -d "STALL={stall}" "{P}/guard_add_i8_fixed.sv" "{ARCHIVE}/guard_add_selective.sv" "{ORIGINAL}/baseline_retime_trial/guard_add_retime.sv" "{ORIGINAL}/guard_add.sv" "{P}/tb_guard_add_i8_fixed.sv"',
        f'"{VIVADO}/bin/xvlog.bat" "{VIVADO}/data/verilog/src/glbl.v"',
        f'"{VIVADO}/bin/xelab.bat" -mt off -L unisims_ver tb_guard_add_i8_fixed glbl -s sim',
        f'"{VIVADO}/bin/xsim.bat" sim -R',
    ]
    for index, command in enumerate(commands):
        assert hashes() == pin, 'Source changed before tool execution'
        done = subprocess.run(command, shell=True, cwd=wd, env=env, capture_output=True, text=True)
        (wd / f'tool_{index}.log').write_text(done.stdout + done.stderr, encoding='utf-8')
        assert done.returncode == 0, done.stdout[-4000:] + done.stderr[-1000:]
    assert 'GUARD_ADD_I8_FIXED PASS' in done.stdout, done.stdout[-4000:]
    assert hashes() == pin and sha(wd / 'stream_stim.txt') == stimulus_pin
    for variant in (0, 1, 3):
        equal_bytes(wd / 'stream_out2.txt', wd / f'stream_out{variant}.txt')
    if archive_pin is not None:
        equal_bytes(archived_output, wd / 'stream_out2.txt')
    expected_requests = sum((len(u) + 5) // 6 for u, current, gap in stimulus)
    total_operations = sum(len(u) for u, current, gap in stimulus)
    rows = []
    for variant in VARIANTS:
        positions = [0] * len(stimulus)
        count = 0
        numeric = hashlib.sha256()
        latency_histogram = {}
        output_path = wd / f'stream_out{variant}.txt'
        with output_path.open() as output:
            for line in output:
                fid, pos, n, placeholder, bits, accepted, retired, mode = line.split()
                fid, pos, n, placeholder, accepted, retired, mode = map(int, [fid, pos, n, placeholder, accepted, retired, mode])
                packed = int(bits, 16)
                assert placeholder == mode == 0 and 0 <= fid < len(stimulus)
                assert 0 <= packed < (1 << 72) and pos == positions[fid]
                u, current, gap = stimulus[fid]
                assert pos < len(u) and n == min(6, len(u) - pos)
                got = [(packed >> (12 * lane)) & 4095 for lane in range(6)]
                want = [(a + b) & 4095 for a, b in zip(u[pos:pos+n], current[pos:pos+n])] + [0] * (6 - n)
                assert got == want, (variant, line, got, want)
                latency = retired - accepted
                assert latency >= 4
                if not stall:
                    assert latency == 4
                latency_histogram[latency] = latency_histogram.get(latency, 0) + 1
                numeric.update(f'{fid} {pos} {n} {packed:018x}\n'.encode('ascii'))
                positions[fid] += n
                count += 1
        assert positions == [len(u) for u, current, gap in stimulus] and count == expected_requests
        match = re.search(rf'GUARD_ADD_I8_FIXED V {variant} REQUESTS (\d+) NEURONS (\d+) CLOCKS (\d+) INPUT_STALLS (\d+) OUTPUT_STALLS (\d+) MIN_LATENCY (\d+) MAX_LATENCY (\d+) DIRECTED_CASES (\d+)', done.stdout)
        assert match, done.stdout[-4000:]
        req, neurons, clocks, ins, outs, latency_min, latency_max, directed = map(int, match.groups())
        assert (req, neurons, directed) == (expected_requests, total_operations, 12)
        assert latency_min == min(latency_histogram) and latency_max == max(latency_histogram)
        if not stall and not any(gap for _, _, gap in stimulus):
            assert clocks == req + 4
        if stall:
            assert ins > 0 and outs > 0
        if archive_fixed is not None:
            assert (req, neurons, clocks, ins, outs) == tuple(archive_fixed[key] for key in
                ('requests', 'neurons', 'clocks', 'input_stall_checks', 'output_stall_checks'))
        rows.append(dict(variant=variant, label=LABELS[variant],
                         core_engine=variant+2 if variant<2 else None,
                         reference_core_variant=2 if variant==2 else None,
                         reference_engine=2 if variant==3 else None,
                         requests=req, neurons=neurons, arithmetic_issues=req if variant != 1 else 0,
                         clocks=clocks, input_stall_checks=ins, output_stall_checks=outs,
                         correction_freezes=0, correction_steps=0,
                         latency_checks=req, physical_latency_min=latency_min, physical_latency_max=latency_max,
                         physical_latency_histogram={str(k): v for k, v in sorted(latency_histogram.items())},
                         directed_boundary_cases=directed, mismatches=0, output_sha256=sha(output_path),
                         numeric_retirement_sha256=numeric.hexdigest()))
        print(rows[-1], flush=True)
    assert len({row['output_sha256'] for row in rows}) == 1
    assert len({row['numeric_retirement_sha256'] for row in rows}) == 1
    assert len({row['clocks'] for row in rows}) == 1
    assert hashes() == pin
    if original_pin is not None:
        assert sha(counterpart) == original_pin, 'Archived original stimulus changed'
    if archive_pin is not None:
        _, _, _, _, end_pin = archive_reference(kind, stall)
        assert archive_pin == end_pin
    if model_pin is not None:
        assert model_input_hashes() == model_pin
    result = dict(source_hashes=pin, frozen_source_sha256=FROZEN_SOURCE_SHA256,
                  profile=1, backpressure=bool(stall), frames=len(stimulus), rows=rows,
                  stimulus_sha256=stimulus_pin, stimulus_file=f'{tag}/stream_stim.txt',
                  original_stimulus_file=str(counterpart), original_stimulus_sha256=original_pin,
                  source_frames_match_original_archive=kind != 'smoke',
                  matched_original_stimulus=(original_pin == stimulus_pin), archive_reference=archive_pin,
                  matched_archived_fixed_retirement=archive_pin is not None,
                  stress_current_transform='identity' if model_pin is not None else 'signed8((I+128)%256-128)',
                  fixed_outputs_byte_identical=True, outputs_byte_identical=True,
                  numeric_outputs_order_identical=True, physical_clock_columns_identical=True,
                  tested_variants=VARIANTS, expected_variants=VARIANTS, tested_core_engines=[2, 3],
                  model_input_sha256=model_pin, model_input_base='../results',
                  validation_kind='saved_model_addition_replay' if model_pin is not None else ('smoke' if kind == 'smoke' else 'full_integer_stress'),
                  source_contract='valid and entire raw payload held until acceptance; only available currents signed8; ignored binary tails arbitrary; input valid low during reset',
                  operand_domain='signed11 U, sign-extended signed8 I',
                  acceptance_to_handshake_preceding_advances=4,
                  advance_convention='Pre-edge step stored at acceptance; acceptance edge counted, handshake edge not yet counted.',
                  integer_operation='exact signed12 U+I', reference_variants=[2, 3],
                  reference_operation='Direct frozen guard_add_selective V2 and guard_add_retime E2, plus archived selective profile1 fixed V2 retirement bytes',
                  directed_prelude=['12 exact extrema/tail cases', 'stalled completed output held',
                                    'zero available creates no output', 'reset cancels stalled output',
                                    'reset cancels unfinished pipeline'],
                  scope='Matched fixed exact addition; physical service clocks measured in RTL; no memory, power, board or trained-accuracy claim')
    (R / (tag + '_checks.json')).write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--small', action='store_true')
    parser.add_argument('--models', action='store_true')
    args = parser.parse_args()
    assert not (args.small and args.models)
    if not args.run:
        print('No RTL tools run; use --run after freeze.',
              {name: sha(P / name) if (P / name).exists() else 'not supplied' for name in SOURCES})
        return
    pin = hashes()
    if args.models:
        original_stimulus, model_pin = model_frames()
    else:
        original_stimulus, model_pin = frames(args.small), None
    assert hashes() == pin
    kind = 'models' if args.models else ('smoke' if args.small else 'main')
    stimulus = original_stimulus if args.models else signed8_profile(original_stimulus)
    for stall in (0, 1):
        simulate(f'i8_fixed_{kind}_{stall}', stimulus, original_stimulus, stall, kind, model_pin)
        assert hashes() == pin


if __name__ == '__main__':
    main()
