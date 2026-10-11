"""Verify one isolated provisional-high decode change against the frozen selective parent.

Only --run launches RTL tools. Profile0 retains full signed11 currents; profile1
maps stress currents to signed8 and tests the statically signed8-current cores.
Saved-model operands remain unchanged in both profiles. Every retirement byte and physical timing row must match the frozen parent.
Adaptive/fixed rows also retain their independent integer-oracle checks.
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
VIVADO = Path('C:/AMDDesignTools/2025.2/Vivado')
VARIANTS = [0, 1, 2, 3]
SOURCES = ['guard_add_selective_decode.sv', 'tb_guard_add_selective_decode.sv',
           'check_guard_add_selective_decode.py', 'check_guard_add_selective_decode_snn.py',
           'guard_add_common.sv', '../guard_add.sv', '../check_guard_add.py',
           '../baseline_retime_trial/guard_add_retime.sv', 'guard_add_selective.sv']


def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1048576), b''):
            value.update(chunk)
    return value.hexdigest()


ORACLE_SHA = sha(ORIGINAL / 'check_guard_add.py')
sys.path.insert(0, str(ORIGINAL))
import check_guard_add as original
import check_guard_add_selective as parent_selective
assert sha(ORIGINAL / 'check_guard_add.py') == ORACLE_SHA
free = original.free
frames = original.frames
model_frames = original.model_frames
model_input_hashes = original.model_input_hashes


def hashes():
    assert sha(ORIGINAL / 'check_guard_add.py') == ORACLE_SHA
    return {name: sha(P / name) for name in SOURCES}


PARENT_CORE_SHA = 'b5c7d724d642b2310c4e447eabccaf965a3aa520aaf2e04c5f93accd5dbb9e48'


def parent_hashes():
    pin = parent_selective.hashes()
    assert pin['guard_add_selective.sv'] == PARENT_CORE_SHA, 'Frozen parent selective core changed'
    return pin


def signed8_profile(stimulus):
    return [(u, [((i + 128) % 256) - 128 for i in current], gap)
            for u, current, gap in stimulus]


def fast_certificate(u, current):
    current8 = -128 <= current <= 127
    carry = ((u & 127) + (current & 127)) >> 7
    return current8 and ((-128 <= u <= 127) or carry == int(current < 0))


def window_stats(stimulus):
    requests = jobs = freezes = 0
    for u, current, gap in stimulus:
        for pos in range(0, len(u), 6):
            k = sum(not fast_certificate(a, b)
                    for a, b in zip(u[pos:pos+6], current[pos:pos+6]))
            jobs += k
            freezes += max(k - 1, 0)
            requests += 1
    return requests, jobs, freezes


def check_archived_stimulus(path, stimulus):
    """Independently verify source frames against original archived text."""
    with path.open() as stream:
        assert int(stream.readline()) == len(stimulus)
        for u, current, gap in stimulus:
            assert tuple(map(int, stream.readline().split())) == (len(u), gap)
            for a, b in zip(u, current):
                assert tuple(int(x, 16) for x in stream.readline().split()) == (a & 2047, b & 2047)
        assert not stream.read().strip()


def simulate(tag, stimulus, original_stimulus, stall, profile, kind, model_pin=None):
    wd = R / tag
    wd.mkdir(parents=True, exist_ok=True)
    pin = hashes()
    parent_pin = parent_hashes()
    parent_tag = tag.replace('selective_decode_', 'selective_', 1)
    parent_check_path = R / (parent_tag + '_checks.json')
    parent_check_pin = sha(parent_check_path)
    parent_data = json.loads(parent_check_path.read_text())
    assert parent_data['source_hashes'] == parent_pin
    assert parent_data['profile'] == profile and parent_data['backpressure'] == bool(stall)
    assert parent_data['tested_variants'] == parent_data['expected_variants'] == VARIANTS
    parent_output_pins = {}
    for variant in VARIANTS:
        path = R / parent_tag / f'stream_out{variant}.txt'
        stamp = sha(path)
        assert stamp == next(row for row in parent_data['rows'] if row['variant'] == variant)['output_sha256']
        parent_output_pins[str(path.relative_to(P))] = stamp
    if profile:
        assert all(-128 <= i <= 127 for _, current, _ in stimulus for i in current)
    if model_pin is not None:
        assert stimulus == original_stimulus and model_input_hashes() == model_pin
    if profile and kind != 'models':
        assert stimulus == signed8_profile(original_stimulus)
    else:
        assert stimulus == original_stimulus
    original.write_stimulus(wd / 'stream_stim.txt', stimulus)
    stimulus_pin = sha(wd / 'stream_stim.txt')
    assert parent_data['stimulus_sha256'] == stimulus_pin
    assert sha(R / parent_data['stimulus_file']) == stimulus_pin
    counterpart = ORIGINAL / 'results' / f'guard_add_{kind}_{stall}' / 'stream_stim.txt'
    original_pin = sha(counterpart) if counterpart.is_file() else None
    if kind != 'smoke':
        assert original_pin is not None, counterpart
        check_archived_stimulus(counterpart, original_stimulus)
        assert sha(counterpart) == original_pin
        if not profile or kind == 'models':
            assert original_pin == stimulus_pin, 'Unchanged stimulus differs from archived original'
    assert free() > 1.2, 'Insufficient free RAM for simulation'
    print(tag, 'free GiB', round(free(), 2), flush=True)
    tmp = wd / 'tmp'
    tmp.mkdir(exist_ok=True)
    env = os.environ.copy()
    env['TEMP'] = str(tmp)
    env['TMP'] = str(tmp)
    commands = [
        f'"{VIVADO}/bin/xvlog.bat" -sv -d "STALL={stall}" -d "PROFILE={profile}" "{P}/guard_add_selective_decode.sv" "{ORIGINAL}/guard_add.sv" "{ORIGINAL}/baseline_retime_trial/guard_add_retime.sv" "{P}/tb_guard_add_selective_decode.sv"',
        f'"{VIVADO}/bin/xvlog.bat" "{VIVADO}/data/verilog/src/glbl.v"',
        f'"{VIVADO}/bin/xelab.bat" -mt off -L unisims_ver tb_guard_add_selective_decode glbl -s sim',
        f'"{VIVADO}/bin/xsim.bat" sim -R',
    ]
    for index, command in enumerate(commands):
        assert hashes() == pin, 'Source changed before tool execution'
        assert parent_hashes() == parent_pin, 'Parent functional sources changed'
        done = subprocess.run(command, shell=True, cwd=wd, env=env, capture_output=True, text=True)
        (wd / f'tool_{index}.log').write_text(done.stdout + done.stderr, encoding='utf-8')
        assert done.returncode == 0, done.stdout[-4000:] + done.stderr[-1000:]
    assert 'GUARD_ADD_SELECTIVE_DECODE PASS' in done.stdout, done.stdout[-4000:]
    assert hashes() == pin and sha(wd / 'stream_stim.txt') == stimulus_pin
    # Fixed selective-domain reference and direct retimed E2/E3 have identical
    # policy and physical service. Adaptive clock columns are checked separately.
    for variant in (0, 3):
        with (wd / 'stream_out2.txt').open('rb') as reference:
            with (wd / f'stream_out{variant}.txt').open('rb') as output:
                while True:
                    expected = reference.read(1048576)
                    assert output.read(1048576) == expected, 'Fixed retirement bytes differ'
                    if not expected:
                        break
    expected_requests, exception_jobs, expected_freezes = window_stats(stimulus)
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
                k = sum(not fast_certificate(a, b) for a, b in zip(u[pos:pos+n], current[pos:pos+n]))
                latency = retired - accepted
                assert latency >= 4 + (max(k - 1, 0) if variant == 1 else 0)
                if not stall and variant != 1:
                    assert latency == 4
                latency_histogram[latency] = latency_histogram.get(latency, 0) + 1
                numeric.update(f'{fid} {pos} {n} {packed:018x}\n'.encode('ascii'))
                positions[fid] += n
                count += 1
        assert positions == [len(u) for u, current, gap in stimulus] and count == expected_requests
        match = re.search(rf'GUARD_ADD_SELECTIVE_DECODE V {variant} REQUESTS (\d+) NEURONS (\d+) CLOCKS (\d+) INPUT_STALLS (\d+) OUTPUT_STALLS (\d+) CORRECTION_FREEZES (\d+) CORRECTION_STEPS (\d+) MAX_CORRECTION_FREEZE_RUN (\d+) MIN_LATENCY (\d+) MAX_LATENCY (\d+)', done.stdout)
        assert match, done.stdout[-4000:]
        req, neurons, clocks, ins, outs, freezes, correction_steps, max_freeze_run, latency_min, latency_max = map(int, match.groups())
        assert (req, neurons) == (expected_requests, total_operations)
        assert freezes == (expected_freezes if variant == 1 else 0)
        assert correction_steps == (exception_jobs if variant == 1 else 0)
        assert 0 <= max_freeze_run <= 5
        assert (max_freeze_run > 0) == (freezes > 0)
        assert latency_min == min(latency_histogram) and latency_max == max(latency_histogram)
        if not stall and not any(gap for _, _, gap in stimulus):
            assert clocks == req + 4 + freezes
        if stall:
            assert ins > 0 and outs > 0
        rows.append(dict(variant=variant, core_variant=variant+2*profile if variant < 2 else None,
                         reference_engine=variant if variant >= 2 else None,
                         requests=req, neurons=neurons, arithmetic_issues=req if variant != 3 else 0,
                         clocks=clocks, input_stall_checks=ins, output_stall_checks=outs,
                         correction_freezes=freezes, correction_steps=correction_steps,
                         max_internal_correction_freeze_run=max_freeze_run,
                         expected_exception_jobs=exception_jobs if variant == 1 else 0,
                         latency_checks=req, physical_latency_min=latency_min, physical_latency_max=latency_max,
                         physical_latency_histogram={str(k): v for k, v in sorted(latency_histogram.items())},
                         mismatches=0, output_sha256=sha(output_path), numeric_retirement_sha256=numeric.hexdigest()))
        print(rows[-1], flush=True)
    assert rows == parent_data['rows'], 'Decode optimization changed numeric or physical timing rows'
    for variant in VARIANTS:
        with (R / parent_tag / f'stream_out{variant}.txt').open('rb') as reference:
            with (wd / f'stream_out{variant}.txt').open('rb') as output:
                while True:
                    expected = reference.read(1048576)
                    assert output.read(1048576) == expected, 'Decode retirement bytes differ from frozen parent'
                    if not expected:
                        break
    assert parent_hashes() == parent_pin and sha(parent_check_path) == parent_check_pin
    assert all(sha(P / path) == stamp for path, stamp in parent_output_pins.items())
    assert len({row['numeric_retirement_sha256'] for row in rows}) == 1, 'Numeric retirement order differs'
    assert len({row['output_sha256'] for row in rows if row['variant'] != 1}) == 1
    assert hashes() == pin
    if original_pin is not None:
        assert sha(counterpart) == original_pin, 'Archived original stimulus changed'
    if model_pin is not None:
        assert model_input_hashes() == model_pin
    result = dict(source_hashes=pin, parent_source_hashes=parent_pin,
                  parent_check_file=str(parent_check_path.relative_to(P)), parent_check_sha256=parent_check_pin,
                  parent_output_hashes=parent_output_pins, outputs_byte_identical_to_parent=True, parent_rows_identical=True,
                  profile=profile, backpressure=bool(stall), frames=len(stimulus), rows=rows,
                  stimulus_sha256=stimulus_pin, stimulus_file=f'{tag}/stream_stim.txt',
                  original_stimulus_file=str(counterpart), original_stimulus_sha256=original_pin,
                  source_frames_match_original_archive=kind != 'smoke',
                  matched_original_stimulus=(original_pin == stimulus_pin),
                  stress_current_transform='signed8((I+128)%256-128)' if profile and kind != 'models' else 'identity',
                  fixed_outputs_byte_identical=True, numeric_outputs_order_identical=True,
                  tested_variants=VARIANTS, expected_variants=VARIANTS,
                  tested_core_variants=[2*profile, 2*profile+1],
                  model_input_sha256=model_pin, model_input_base='../results',
                  validation_kind='saved_model_addition_replay' if model_pin is not None else ('smoke' if kind == 'smoke' else 'full_integer_stress'),
                  source_contract='valid and entire raw payload held until acceptance; binary unavailable tails arbitrary; input valid low during reset',
                  operand_domain='signed11 U, sign-extended signed8 I' if profile else 'signed11 U, signed11 I',
                  acceptance_to_handshake_preceding_advances=4,
                  advance_convention='Pre-edge step stored at acceptance; acceptance edge counted, handshake edge not yet counted. Internal correction freezes do not advance.',
                  integer_operation='exact signed12 U+I', reference_variants=[2, 3],
                  reference_operation='Retimed guard_add_retime E2/E3 full11 instantiated directly; local0 is the matched fixed correction reference',
                  expected_exception_jobs=exception_jobs, expected_extra_correction_freezes=expected_freezes,
                  scope='Selective exact high-part correction; physical service clocks measured in RTL; no memory, power, board or trained-accuracy claim')
    (R / (tag + '_checks.json')).write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--small', action='store_true')
    parser.add_argument('--models', action='store_true')
    parser.add_argument('--profile', type=int, choices=(0, 1))
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
    for profile in ((args.profile,) if args.profile is not None else (0, 1)):
        stimulus = signed8_profile(original_stimulus) if profile and not args.models else original_stimulus
        for stall in (0, 1):
            simulate(f'selective_decode_{kind}_p{profile}_{stall}', stimulus, original_stimulus,
                     stall, profile, kind, model_pin)
            assert hashes() == pin


if __name__ == '__main__':
    main()
