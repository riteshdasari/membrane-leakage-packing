"""Independent signed11 U+I -> signed12 ordered-window oracle.

No RTL tools run without --run. --models uses saved ceil(231U/256) plus the
recorded synaptic current, with both operands checked to fit signed11. This
checks sums only; threshold/reset replay and classification are separate.
"""
from pathlib import Path
import argparse
import ctypes
import hashlib
import json
import os
import random
import re
import subprocess

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
P = Path(__file__).resolve().parent
R = P / 'results'
V = Path('C:/AMDDesignTools/2025.2/Vivado')
MODEL_INPUTS = ['adaptive_delta_model_25_1/expected.npz', 'adaptive_delta_model_input.json']
SOURCES = ['guard_add.sv', 'tb_guard_add.sv', 'check_guard_add.py']
ENGINES = [0, 1, 2, 3]


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def hashes():
    return {name: sha(P / name) for name in SOURCES}


def model_input_hashes():
    return {name: sha(R / name) for name in MODEL_INPUTS}


def free():
    class Mem(ctypes.Structure):
        _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong),
                    ('total', ctypes.c_ulonglong), ('free', ctypes.c_ulonglong),
                    ('rest', ctypes.c_ulonglong * 5)]
    memory = Mem()
    memory.length = ctypes.sizeof(memory)
    assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory))
    return memory.free / 2 ** 30


def policy(u, current, engine):
    """Scalar prefix policy, independent of the DSP encoding/decoding algebra."""
    assert engine in ENGINES and len(u) == len(current) and u
    x, y = u[:6], current[:6]
    n = len(x)
    suffix_copy = engine in (0, 1) and n >= 5 and y[4] == 0
    full_copy = suffix_copy and (n == 5 or y[5] == 0)
    narrow = (engine == 0 and not full_copy and n >= 5
              and all(-64 <= value <= 63 for value in x + y))
    copy = suffix_copy and not narrow
    if engine in (2, 3) or narrow:
        take = n
    elif copy:
        take = 6 if n == 6 and y[5] == 0 else 5
    else:
        take = min(4, n)
    return take, int(narrow), bool(copy)


def frames(small=False):
    out = []
    rng = random.Random(864209)
    edges = [-1024, -1023, -65, -64, -63, -1, 0, 1, 62, 63, 64, 1022, 1023]
    scalar = edges if small else range(-1024, 1024)
    # Every signed11 scalar meets every boundary in both operand orders. Each
    # six-value frame also exercises negative/positive sum extrema and copies.
    for value in scalar:
        for boundary in edges:
            u = [value, boundary, value, 1023, value, 0]
            current = [boundary, value, -1024, value, 0, value]
            out.append((u, current, 0))
    # Every signed7 operand pair appears at each of the six lane positions,
    # surrounded by guard-bit carry/sign extrema. Nonzero sentinels at I4/I5
    # make most vectors actually select E0 narrow rather than wide-copy.
    narrow_values = [-64, -63, -1, 0, 1, 62, 63] if small else range(-64, 64)
    sentinels = [(-64, -64), (-64, 63), (63, -64), (63, 63), (0, 1), (-1, 1)]
    for a in narrow_values:
        for b in narrow_values:
            for lane in range(6):
                pairs = sentinels.copy()
                pairs[lane] = (a, b)
                out.append(([p[0] for p in pairs], [p[1] for p in pairs], 0))
    # Explicit range transitions, copy priority (including narrow-fit copies),
    # output extrema and tails, with signed11 poisoned tails supplied by the TB.
    vectors = [
        ([-64] * 6, [-64] * 6), ([63] * 6, [63] * 6),
        ([-1024] * 6, [-1024] * 6), ([1023] * 6, [1023] * 6),
        ([-1024, 1023] * 3, [1023, -1024] * 3),
        ([-65, -64, -1, 0, 63, 64], [1, -1, 63, -64, 1, -1]),
        ([64, -65, 1023, -1024, 999, -999], [1, 1, -1, -1, 0, 0]),
        ([64, -65, 1023, -1024, 999, -999], [1, 1, -1, -1, 0, 1]),
        ([-64, -63, -1, 0, 62, 63], [1, 1, 1, 1, 0, 0]),
        ([-64, -63, -1, 0, 62, 63], [1, 1, 1, 1, 0, 1]),
        ([-64, -63, -1, 0, 62, 63], [1, 1, 1, 1, 1, 0]),
        ([0] * 6, [0] * 6), ([1023] * 6, [0] * 6),
    ]
    for n in range(1, 13):
        for u, current in vectors:
            out.append(((u * 2)[:n], (current * 2)[:n], n % 3))
    # Each high4/low7 decomposition extrema meets every residual low-bit carry
    # pattern, including negative arithmetic shifts in DSP metadata recovery.
    for bits in range(64):
        u = [([-1024, -128, -1, 0, 127, 1023][lane] & ~1)
             + ((bits >> lane) & 1) for lane in range(6)]
        current = [1023, -1024, -65, -64, 63, 64]
        out.append((u, current, 0))
    for j in range(100 if small else 3000):
        n = rng.randrange(1, 41)
        if j % 7 == 0:
            u = [rng.randrange(-1024, 1024) for _ in range(n)]
            current = [0] * n
        elif j % 5 == 0:
            u = [rng.randrange(-64, 64) for _ in range(n)]
            current = [rng.randrange(-64, 64) for _ in range(n)]
        else:
            u = [rng.randrange(-1024, 1024) for _ in range(n)]
            current = [rng.randrange(-1024, 1024) for _ in range(n)]
            if j % 3 == 0:
                current = [0 if lane % 6 >= 4 else value for lane, value in enumerate(current)]
        out.append((u, current, rng.randrange(1, 4) if j % 9 == 0 else 0))
    return out


def model_frames():
    pin = model_input_hashes()
    import numpy as np
    with np.load(R / MODEL_INPUTS[0]) as saved:
        groups = saved['groups'].astype(np.int64)
    ledger = json.loads((R / MODEL_INPUTS[1]).read_text())['ledger']
    assert len(ledger) == 9216
    out = []
    for record in ledger:
        raw = groups[record['start']:record['start'] + record['blocks']].reshape(-1)[:record['neurons']]
        # Independent mathematical identity: ceil(231U/256)=U-floor(25U/256).
        leaked = raw - (25 * raw) // 256
        current = np.asarray(record['current'], dtype=np.int64)
        assert current.shape == leaked.shape
        assert np.all((-1024 <= leaked) & (leaked <= 1023)), 'Leaked operand exceeds signed11'
        assert np.all((-1024 <= current) & (current <= 1023)), 'Current operand exceeds signed11'
        out.append((leaked.tolist(), current.tolist(), 0))
    assert sum(len(u) for u, current, gap in out) == 635904
    assert model_input_hashes() == pin, 'Model inputs changed while loading'
    return out, pin


def write_stimulus(path, stimulus):
    with path.open('w') as output:
        output.write(str(len(stimulus)) + '\n')
        for u, current, gap in stimulus:
            assert 1 <= len(u) <= 4096 and len(current) == len(u) and gap >= 0
            assert all(-1024 <= value <= 1023 for value in u + current)
            output.write(f'{len(u)} {gap}\n')
            output.writelines(f'{a & 2047:03x} {b & 2047:03x}\n' for a, b in zip(u, current))


def simulate(tag, stimulus, stall, model_pin=None):
    wd = R / tag
    wd.mkdir(parents=True, exist_ok=True)
    pin = hashes()
    if model_pin is not None:
        assert model_input_hashes() == model_pin, 'Model inputs changed before simulation'
    write_stimulus(wd / 'stream_stim.txt', stimulus)
    stimulus_pin = sha(wd / 'stream_stim.txt')
    assert free() > 1.2, 'Insufficient free RAM for simulation'
    print(tag, 'free GiB', round(free(), 2), flush=True)
    temp = wd / 'tmp'
    temp.mkdir(exist_ok=True)
    env = os.environ.copy()
    env['TEMP'] = str(temp)
    env['TMP'] = str(temp)
    commands = [
        f'"{V}/bin/xvlog.bat" -sv -d "STALL={stall}" "{P}/guard_add.sv" "{P}/tb_guard_add.sv"',
        f'"{V}/bin/xvlog.bat" "{V}/data/verilog/src/glbl.v"',
        f'"{V}/bin/xelab.bat" -mt off -L unisims_ver tb_guard_add glbl -s sim',
        f'"{V}/bin/xsim.bat" sim -R',
    ]
    for i, command in enumerate(commands):
        assert hashes() == pin, 'Source changed before RTL tool execution'
        z = subprocess.run(command, shell=True, cwd=wd, env=env, capture_output=True, text=True)
        (wd / f'tool_{i}.log').write_text(z.stdout + z.stderr)
        assert z.returncode == 0, z.stdout[-4000:] + z.stderr[-1000:]
    assert 'GUARD_ADD PASS' in z.stdout, z.stdout[-4000:]
    assert hashes() == pin, 'Source changed during simulation'
    assert sha(wd / 'stream_stim.txt') == stimulus_pin, 'Stimulus changed during simulation'
    rows = []
    real_operations = sum(len(u) for u, current, gap in stimulus)
    for engine in ENGINES:
        positions = [0] * len(stimulus)
        expected_requests = expected_narrow = expected_copy = 0
        for u, current, gap in stimulus:
            pos = 0
            while pos < len(u):
                take, narrow, copy = policy(u[pos:], current[pos:], engine)
                expected_requests += 1
                expected_narrow += narrow
                expected_copy += copy
                pos += take
        count = 0
        output_path = wd / f'stream_out{engine}.txt'
        with output_path.open() as output:
            for line in output:
                fid, pos, n, placeholder, bits, ac, rc, mode = line.split()
                fid, pos, n, placeholder, ac, rc, mode = map(int, [fid, pos, n, placeholder, ac, rc, mode])
                bits = int(bits, 16)
                assert placeholder == 0 and 0 <= fid < len(stimulus) and 0 <= bits < (1 << 72), line
                u, current, gap = stimulus[fid]
                assert pos == positions[fid] and pos < len(u), (engine, line)
                take, narrow, copy = policy(u[pos:], current[pos:], engine)
                assert (n, mode) == (take, narrow), (engine, line)
                got = [(bits >> (12 * lane)) & 4095 for lane in range(6)]
                # Plain signed integer addition; no packed-arithmetic algebra.
                want = [(a + b) & 4095 for a, b in zip(u[pos:pos+n], current[pos:pos+n])] + [0] * (6 - n)
                assert got == want, (engine, line, u[pos:pos+n], current[pos:pos+n], got, want)
                positions[fid] += n
                count += 1
                if not stall:
                    assert rc - ac == 4, (engine, line)
        assert positions == [len(u) for u, current, gap in stimulus] and count == expected_requests
        match = re.search(rf'GUARD_ADD E {engine} REQUESTS (\d+) NEURONS (\d+) NARROW (\d+) COPY (\d+) CLOCKS (\d+) INPUT_STALLS (\d+) OUTPUT_STALLS (\d+)', z.stdout)
        assert match, z.stdout[-4000:]
        req, neurons, narrow, copies, clocks, ins, outs = map(int, match.groups())
        assert (req, neurons, narrow, copies) == (expected_requests, real_operations, expected_narrow, expected_copy)
        if not stall and not any(gap for u, current, gap in stimulus):
            assert clocks == req + 4
        if stall:
            assert ins > 0 and outs > 0
        rows.append(dict(engine=engine, requests=req, neurons=neurons,
                         arithmetic_issues=req if engine != 3 else 0,
                         narrow_requests=narrow, copy_requests=copies, clocks=clocks,
                         input_stall_checks=ins, output_stall_checks=outs,
                         latency_checks=req, mismatches=0,
                         output_sha256=sha(output_path)))
        print(rows[-1], flush=True)
    if model_pin is not None:
        assert model_input_hashes() == model_pin, 'Model inputs changed during simulation'
    result = dict(source_hashes=pin, backpressure=bool(stall), frames=len(stimulus), rows=rows,
                  stimulus_sha256=stimulus_pin, stimulus_file=f'{tag}/stream_stim.txt',
                  tested_engines=ENGINES, expected_engines=ENGINES, model_input_sha256=model_pin,
                  validation_kind='saved_model_addition_replay' if model_pin is not None else ('smoke' if tag.startswith('guard_add_smoke') else 'full_integer_stress'),
                  source_contract='valid and both complete raw six-value payloads held until acceptance; input valid low during reset',
                  acceptance_to_handshake_advances=4, integer_operation='signed11 U + signed11 I -> exact signed12 sum',
                  retirement_columns=['frame', 'position', 'count', 'coefficient_placeholder0', 'out72_hex', 'acceptance_clock', 'retirement_clock', 'narrow_mode'],
                  policy='E0 prefers full-window zero-current suffix copy, then all signed7 av5/6, then prefix4 plus zero-current suffix; E1 prefix4 plus zero-current suffix; E2/E3 all available',
                  scope='Six-value ordered addition primitive; no memory source/controller or SNN threshold/reset/classification claim')
    (R / (tag + '_checks.json')).write_text(json.dumps(result, indent=2))
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run', action='store_true')
    ap.add_argument('--small', action='store_true')
    ap.add_argument('--models', action='store_true')
    args = ap.parse_args()
    assert not (args.small and args.models), 'Choose smoke or model replay'
    if not args.run:
        print('No RTL tools run. Use --run [--small|--models] after source freeze.',
              {name: sha(P / name) if (P / name).exists() else 'not yet supplied' for name in SOURCES})
        return
    if args.models:
        stimulus, model_pin = model_frames()
    else:
        stimulus, model_pin = frames(args.small), None
    stem = 'guard_add_models' if args.models else ('guard_add_smoke' if args.small else 'guard_add_main')
    for stall in [0, 1]:
        simulate(stem + f'_{stall}', stimulus, stall, model_pin)


if __name__ == '__main__':
    main()
