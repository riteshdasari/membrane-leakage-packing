"""Serial, memory-gated measurement of frozen exact-correction implementations.

No tool launches without --run. Native trace, export, replay and power are
separate stages. Failed attempts retain their logs; original evidence is read-only.
"""
from pathlib import Path
from ctypes import wintypes
import argparse
import ctypes
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent
R = P / 'results'
COMMON = P.parent / 'common_layout_trial'
VIVADO = Path('C:/AMDDesignTools/2025.2/Vivado')
CORE_SHA = 'b5c7d724d642b2310c4e447eabccaf965a3aa520aaf2e04c5f93accd5dbb9e48'
STIMULUS = COMMON / 'results/selective_models_p1_0/stream_stim.txt'


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def pins(paths):
    return {str(Path(path).resolve()): sha(path) for path in sorted(set(paths), key=str)}


def verify(stamps):
    for name, stamp in stamps.items():
        assert sha(name) == stamp, ('Changed evidence', name)


def frozen():
    assert sha(COMMON / 'guard_add_selective.sv') == CORE_SHA
    saved = read(COMMON / 'results/selective_models_p1_0_checks.json')
    assert saved['profile'] == 1 and saved['backpressure'] is False
    assert sha(STIMULUS) == saved['stimulus_sha256']
    expected = {row['variant']: row for row in saved['rows']}
    assert expected[0]['clocks'] == 110596 and expected[1]['clocks'] == 110710
    assert expected[1]['correction_steps'] == 1008 and expected[1]['correction_freezes'] == 114
    paths = [STIMULUS, COMMON / 'results/selective_models_p1_0_checks.json']
    for name, stamp in saved['source_hashes'].items():
        path = COMMON / name
        assert sha(path) == stamp
        paths.append(path)
    for variant in (0, 1):
        path = STIMULUS.parent / f'stream_out{variant}.txt'
        assert sha(path) == expected[variant]['output_sha256']
        paths.append(path)
    hw = read(COMMON / 'results/selective_hardware.json')
    for variant in (2, 3):
        row, = [item for item in hw if item['variant'] == variant]
        assert row['target_ns'] == 6.0 and row['WNS_ns'] >= 0 and row['WHS_ns'] >= 0
        for name, stamp in row['source_sha256'].items():
            path = COMMON / name
            assert sha(path) == stamp
            paths.append(path)
        for name, stamp in row['route_artifact_sha256'].items():
            path = COMMON / name
            assert sha(path) == stamp
            paths.append(path)
    paths.append(COMMON / 'results/selective_hardware.json')
    out = P.parents[2] / 'outputs'
    for stem in ('membrane_selective_correction_trial', 'membrane_i8_fixed_comparison_trial'):
        paths.extend(out / (stem + suffix) for suffix in ('.md', '.summary.json', '.manifest.json'))
    return pins(paths)


class Memory(ctypes.Structure):
    _fields_ = [('length', wintypes.DWORD), ('load', wintypes.DWORD),
                ('total', ctypes.c_ulonglong), ('free', ctypes.c_ulonglong),
                ('rest', ctypes.c_ulonglong * 5)]


def free():
    memory = Memory()
    memory.length = ctypes.sizeof(memory)
    assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory))
    return memory.free / 2**30


class ProcessEntry(ctypes.Structure):
    _fields_ = [('dwSize', wintypes.DWORD), ('cntUsage', wintypes.DWORD),
        ('th32ProcessID', wintypes.DWORD), ('th32DefaultHeapID', ctypes.c_size_t),
        ('th32ModuleID', wintypes.DWORD), ('cntThreads', wintypes.DWORD),
        ('th32ParentProcessID', wintypes.DWORD), ('pcPriClassBase', wintypes.LONG),
        ('dwFlags', wintypes.DWORD), ('szExeFile', wintypes.WCHAR * 260)]


class ProcessMemory(ctypes.Structure):
    _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD)] + [
        (name, ctypes.c_size_t) for name in ('PeakWorkingSetSize', 'WorkingSetSize',
        'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage',
        'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage')]


def tree_working_set(pid):
    """Sample descendant RSS sum; shared pages may be counted more than once."""
    kernel = ctypes.windll.kernel32
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessEntry)]
    kernel.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessEntry)]
    snap = kernel.CreateToolhelp32Snapshot(2, 0)
    assert snap != wintypes.HANDLE(-1).value
    parent = {}
    entry = ProcessEntry()
    entry.dwSize = ctypes.sizeof(entry)
    try:
        more = kernel.Process32FirstW(snap, ctypes.byref(entry))
        while more:
            parent[entry.th32ProcessID] = entry.th32ParentProcessID
            more = kernel.Process32NextW(snap, ctypes.byref(entry))
    finally:
        kernel.CloseHandle(snap)
    targets = {pid}
    while True:
        enlarged = targets | {child for child, par in parent.items() if par in targets}
        if enlarged == targets:
            break
        targets = enlarged
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    psapi = ctypes.windll.psapi
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE,
        ctypes.POINTER(ProcessMemory), wintypes.DWORD]
    total = 0
    for target in targets:
        handle = kernel.OpenProcess(0x1010, False, target)
        if not handle:
            continue
        try:
            memory = ProcessMemory()
            memory.cb = ctypes.sizeof(memory)
            if psapi.GetProcessMemoryInfo(handle, ctypes.byref(memory), memory.cb):
                total += memory.WorkingSetSize
        finally:
            kernel.CloseHandle(handle)
    return total / 2**30


def job(argv, wd, label, stamps, gate):
    verify(stamps)
    available = free()
    print(label, 'free GiB', round(available, 3), flush=True)
    assert available > gate, ('Insufficient free RAM', label, available, gate)
    temporary = wd / 'tmp'
    temporary.mkdir(exist_ok=True)
    env = os.environ.copy()
    env['TEMP'] = env['TMP'] = str(temporary)
    env['OPENBLAS_NUM_THREADS'] = env['OMP_NUM_THREADS'] = '1'
    start = time.time()
    peak, minimum, samples = 0.0, available, 0
    log = wd / (label + '.log')
    with log.open('w', encoding='utf-8') as output:
        # Vivado's Windows .bat option parser needs quoted -d NAME=VALUE tokens.
        # These are fixed local paths/options, not arbitrary user shell text.
        assert all('"' not in str(arg) and '\n' not in str(arg) for arg in argv)
        command = ' '.join('"' + str(arg) + '"' for arg in argv)
        process = subprocess.Popen(command,
            shell=True, cwd=wd, env=env, stdout=output, stderr=subprocess.STDOUT)
        while process.poll() is None:
            minimum = min(minimum, free())
            peak = max(peak, tree_working_set(process.pid))
            samples += 1
            time.sleep(1)
        code = process.wait()
    metadata = dict(argv=list(map(str, argv)), cwd=str(wd), returncode=code,
        seconds=round(time.time()-start, 2), free_GiB_at_start=available,
        sampled_min_free_GiB=minimum, sampled_peak_tool_tree_RSS_sum_GiB=peak,
        memory_samples=samples, sample_period_seconds=1,
        memory_scope='Descendant working-set sum may double-count shared pages; sampled, not unique physical peak',
        source_sha256=stamps, log_sha256=sha(log))
    write(wd / (label + '.job.json'), metadata)
    verify(stamps)
    assert code == 0, (label, log.read_text(errors='replace')[-6000:])
    return log


def stage_dir(stage, variant, attempt):
    suffix = '' if variant is None else f'_v{variant}'
    wd = R / f'{stage}{suffix}_a{attempt}'
    assert not wd.exists(), ('Attempt directory exists; retain evidence and use another --attempt', wd)
    wd.mkdir(parents=True)
    return wd


def native(attempt, base):
    wd = stage_dir('native_models_0', None, attempt)
    stamps = base | pins([P / 'tb_selective_native_trace.sv',
        P / 'verify_selective_native_trace.py', Path(__file__), P / 'CONTRACT.md'])
    shutil.copyfile(STIMULUS, wd / 'stream_stim.txt')
    stamps.update(pins([wd / 'stream_stim.txt']))
    write(wd / 'provenance.json', stamps)
    commands = [
        [VIVADO/'bin/xvlog.bat', '-sv', '-d', 'STALL=0', '-d', 'PROFILE=1',
            COMMON/'guard_add_selective.sv', COMMON.parent/'guard_add.sv',
            COMMON.parent/'baseline_retime_trial/guard_add_retime.sv',
            COMMON/'tb_guard_add_selective.sv', P/'tb_selective_native_trace.sv'],
        [VIVADO/'bin/xvlog.bat', VIVADO/'data/verilog/src/glbl.v'],
        [VIVADO/'bin/xelab.bat', '-mt', 'off', '-debug', 'typical',
            '-L', 'unisims_ver', 'tb_selective_native_trace', 'glbl', '-s', 'sim'],
        [VIVADO/'bin/xsim.bat', 'sim', '-R']]
    for index, command in enumerate(commands):
        log = job(command, wd, f'tool_{index}', stamps, 1.2)
    assert 'SELECTIVE_NATIVE_TRACE PASS' in log.read_text(errors='replace')
    log = job([sys.executable, '-B', P/'verify_selective_native_trace.py',
        '--directory', wd, '--output', wd/'native_checks.json'], wd, 'verify', stamps, 0.1)
    assert (wd / 'native_checks.json').is_file()
    verify(stamps)
    print('NATIVE COMPLETE', wd, flush=True)
    return wd


def export(variant, attempt, base):
    wd = stage_dir('export', variant, attempt)
    stamps = base | pins([P/'selective_energy_tools.tcl', Path(__file__), P/'CONTRACT.md'])
    dcp = COMMON/f'results/top_guard_add_selective_v{variant}_route/design.dcp'
    write(wd/'provenance.json', stamps)
    job([VIVADO/'bin/vivado.bat', '-mode', 'batch', '-log', 'vivado.log',
        '-journal', 'vivado.jou', '-source', P/'selective_energy_tools.tcl',
        '-tclargs', 'export', variant, dcp, wd], wd, 'export', stamps, 2.3)
    assert (wd/'routed.v').is_file() and (wd/'routed.sdf').is_file()
    write(wd/'artifacts.json', pins([wd/'routed.v', wd/'routed.sdf', wd/'provenance.json']))
    print('EXPORT COMPLETE', variant, wd, flush=True)
    return wd


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--stage', choices=('native', 'export', 'replay', 'power'), default='native')
    parser.add_argument('--variant', type=int, choices=(2,3))
    parser.add_argument('--attempt', type=int, default=0)
    args = parser.parse_args()
    if not args.run:
        print('No tools launched; stages require --run and unchanged frozen evidence.')
        return
    assert args.attempt >= 0
    base = frozen()
    if args.stage == 'native':
        assert args.variant is None
        native(args.attempt, base)
    elif args.stage == 'export':
        assert args.variant in (2,3)
        export(args.variant, args.attempt, base)
    else:
        raise RuntimeError('Replay/power orchestration pending audited replay protocol; no tool launched')
    verify(base)


if __name__ == '__main__':
    main()
