"""Independent scalar checks for retimed hybrid/LUT and direct original E2/E3.

--run is required to launch RTL tools. Original stimuli, policy and saved model
operands are imported read-only; all four variants must also retire identical
text bytes. The numeric oracle is ordinary signed integer U+I addition.
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
SOURCES = ['guard_add_retime.sv', 'tb_guard_add_retime.sv',
           'check_guard_add_retime.py', 'check_guard_add_retime_snn.py',
           '../guard_add.sv', '../check_guard_add.py']


def sha(path):
    result = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


ORACLE_SHA = sha(ORIGINAL / 'check_guard_add.py')
sys.path.insert(0, str(ORIGINAL))
import check_guard_add as original
assert sha(ORIGINAL / 'check_guard_add.py') == ORACLE_SHA, 'Original oracle changed during import'
free = original.free
frames = original.frames
model_frames = original.model_frames
model_input_hashes = original.model_input_hashes


def hashes():
    assert sha(ORIGINAL / 'check_guard_add.py') == ORACLE_SHA, 'Imported original oracle changed'
    return {name: sha(P / name) for name in SOURCES}


def policy(u, current):
    return original.policy(u, current, 2)


def simulate(tag, stimulus, stall, model_pin=None):
    wd = R / tag
    wd.mkdir(parents=True, exist_ok=True)
    pin = hashes()
    if model_pin is not None:
        assert model_input_hashes() == model_pin, 'Saved model inputs changed before simulation'
    original.write_stimulus(wd / 'stream_stim.txt', stimulus)
    stimulus_pin = sha(wd / 'stream_stim.txt')
    counterpart = ORIGINAL / 'results' / tag.replace('retime_', 'guard_add_', 1) / 'stream_stim.txt'
    # Full suites must reuse exactly the archived source bytes, not merely the
    # same operation count. Smoke remains available before an archived smoke.
    matched_original = counterpart.is_file() and sha(counterpart) == stimulus_pin
    if not tag.startswith('retime_smoke'):
        assert matched_original, ('Original/retimed stimulus differs', counterpart)
    assert free() > 1.2, 'Insufficient free RAM for simulation'
    print(tag, 'free GiB', round(free(), 2), flush=True)
    temporary = wd / 'tmp'
    temporary.mkdir(exist_ok=True)
    env = os.environ.copy()
    env['TEMP'] = str(temporary)
    env['TMP'] = str(temporary)
    commands = [
        f'"{VIVADO}/bin/xvlog.bat" -sv -d "STALL={stall}" "{P}/guard_add_retime.sv" "{ORIGINAL}/guard_add.sv" "{P}/tb_guard_add_retime.sv"',
        f'"{VIVADO}/bin/xvlog.bat" "{VIVADO}/data/verilog/src/glbl.v"',
        f'"{VIVADO}/bin/xelab.bat" -mt off -L unisims_ver tb_guard_add_retime glbl -s sim',
        f'"{VIVADO}/bin/xsim.bat" sim -R',
    ]
    for index, command in enumerate(commands):
        assert hashes() == pin, 'Source changed before RTL tool execution'
        done = subprocess.run(command, shell=True, cwd=wd, env=env, capture_output=True, text=True)
        (wd / f'tool_{index}.log').write_text(done.stdout + done.stderr, encoding='utf-8')
        assert done.returncode == 0, done.stdout[-4000:] + done.stderr[-1000:]
    assert 'GUARD_ADD_RETIME PASS' in done.stdout, done.stdout[-4000:]
    assert hashes() == pin and sha(wd / 'stream_stim.txt') == stimulus_pin, 'Source/stimulus changed during simulation'
    # All four formats have the same always-six policy, clocks and sums.
    # Compare actual bytes against direct original E2 in bounded chunks.
    for variant in (0, 1, 3):
        with (wd / 'stream_out2.txt').open('rb') as reference:
            with (wd / f'stream_out{variant}.txt').open('rb') as output:
                while True:
                    expected = reference.read(1024 * 1024)
                    assert output.read(1024 * 1024) == expected, 'Retirement bytes differ between retimed and direct original baselines'
                    if not expected:
                        break
    expected_requests = expected_narrow = expected_copy = 0
    for u, current, gap in stimulus:
        pos = 0
        while pos < len(u):
            take, narrow, copy = policy(u[pos:], current[pos:])
            expected_requests += 1
            expected_narrow += narrow
            expected_copy += copy
            pos += take
    total_operations = sum(len(u) for u, current, gap in stimulus)
    rows = []
    for variant in VARIANTS:
        positions = [0] * len(stimulus)
        count = 0
        output_path = wd / f'stream_out{variant}.txt'
        with output_path.open() as output:
            for line in output:
                fid, pos, n, placeholder, bits, accepted, retired, mode = line.split()
                fid, pos, n, placeholder, accepted, retired, mode = map(int, [fid, pos, n, placeholder, accepted, retired, mode])
                packed = int(bits, 16)
                assert placeholder == 0 and 0 <= fid < len(stimulus) and 0 <= packed < (1 << 72), line
                u, current, gap = stimulus[fid]
                assert pos == positions[fid] and pos < len(u), (variant, line)
                take, narrow, copy = policy(u[pos:], current[pos:])
                assert (n, mode) == (take, narrow), (variant, line)
                got = [(packed >> (12 * lane)) & 4095 for lane in range(6)]
                want = [(a + b) & 4095 for a, b in zip(u[pos:pos+n], current[pos:pos+n])] + [0] * (6 - n)
                assert got == want, (variant, line, got, want)
                positions[fid] += n
                count += 1
                if not stall:
                    assert retired - accepted == 4, (variant, line)
        assert positions == [len(u) for u, current, gap in stimulus] and count == expected_requests
        match = re.search(rf'GUARD_ADD_RETIME V {variant} REQUESTS (\d+) NEURONS (\d+) NARROW (\d+) COPY (\d+) CLOCKS (\d+) INPUT_STALLS (\d+) OUTPUT_STALLS (\d+)', done.stdout)
        assert match, done.stdout[-4000:]
        req, neurons, narrow, copies, clocks, ins, outs = map(int, match.groups())
        assert (req, neurons, narrow, copies) == (expected_requests, total_operations, expected_narrow, expected_copy)
        if not stall and not any(gap for u, current, gap in stimulus):
            assert clocks == req + 4
        if stall:
            assert ins > 0 and outs > 0
        rows.append(dict(variant=variant, reference_engine=2 if variant in (0, 2) else 3,
                         requests=req, neurons=neurons, arithmetic_issues=req if variant in (0, 2) else 0,
                         narrow_requests=narrow, copy_requests=copies, clocks=clocks,
                         input_stall_checks=ins, output_stall_checks=outs,
                         latency_checks=req, mismatches=0, output_sha256=sha(output_path)))
        print(rows[-1], flush=True)
    assert len({row['output_sha256'] for row in rows}) == 1
    assert hashes() == pin
    if model_pin is not None:
        assert model_input_hashes() == model_pin, 'Saved model inputs changed during simulation'
    result = dict(source_hashes=pin, backpressure=bool(stall), frames=len(stimulus), rows=rows,
                  stimulus_sha256=stimulus_pin, stimulus_file=f'{tag}/stream_stim.txt',
                  original_stimulus_file=str(counterpart), matched_original_stimulus=matched_original,
                  outputs_byte_identical=True, tested_variants=VARIANTS, expected_variants=VARIANTS,
                  model_input_sha256=model_pin, model_input_base='../results',
                  validation_kind='saved_model_addition_replay' if model_pin is not None else ('smoke' if tag.startswith('retime_smoke') else 'full_integer_stress'),
                  source_contract='valid and both entire raw six-value payloads held until acceptance; input valid low during reset',
                  acceptance_to_handshake_advances=4, integer_operation='signed11 U + signed11 I -> exact signed12 sum',
                  reference_variants=[2, 3], reference_operation='Original guard_add E2/E3 instantiated directly in the testbench',
                  retirement_columns=['frame', 'position', 'count', 'coefficient_placeholder0', 'out72_hex', 'acceptance_clock', 'retirement_clock', 'narrow_mode'],
                  scope='Exact hybrid/LUT baseline-retiming equivalence; no memory, power, board or trained-accuracy claim')
    (R / (tag + '_checks.json')).write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--small', action='store_true')
    parser.add_argument('--models', action='store_true')
    args = parser.parse_args()
    assert not (args.small and args.models), 'Choose smoke or saved model replay'
    if not args.run:
        print('No RTL tools run; use --run after source freeze.',
              {name: sha(P / name) if (P / name).exists() else 'not yet supplied' for name in SOURCES})
        return
    pin = hashes()
    if args.models:
        stimulus, model_pin = model_frames()
    else:
        stimulus, model_pin = frames(args.small), None
    assert hashes() == pin, 'Source changed while preparing stimuli'
    stem = 'retime_models' if args.models else ('retime_smoke' if args.small else 'retime_main')
    for stall in (0, 1):
        simulate(stem + f'_{stall}', stimulus, stall, model_pin)
        assert hashes() == pin, 'Source changed between stall cohorts'


if __name__ == '__main__':
    main()
