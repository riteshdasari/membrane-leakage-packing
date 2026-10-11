"""Independent integer oracle and ordered-window checks for the four-stage unit.

The source driver holds valid, all payload bits (including poisoned tail bits),
and coefficient while backpressured. Simulator checks count, order, cancellation,
four *advancing* clocks, and input/output stability separately from this oracle.
"""
from pathlib import Path
import ctypes, hashlib, json, os, random, re, subprocess, sys

P = Path(__file__).resolve().parent
R = P / 'results'
V = Path('C:/AMDDesignTools/2025.2/Vivado')

def free():
    class M(ctypes.Structure):
        _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong),
                    ('total', ctypes.c_ulonglong), ('free', ctypes.c_ulonglong),
                    ('rest', ctypes.c_ulonglong * 5)]
    m = M(); m.length = ctypes.sizeof(m)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return m.free / 2**30

def hashes(variant='pipeline'):
    return {n: hashlib.sha256((P/n).read_bytes()).hexdigest()
            for n in ['stream_pipeline_leak.sv', 'tb_stream_pipeline_leak.sv']}

def policy(u, d, e, variant='pipeline'):
    n = min(3, len(u)); x = u[:n]
    fit6 = n == 3 and all(-32 <= v <= 31 for v in x)
    fit7 = n == 3 and all(-64 <= v <= 63 for v in x)
    narrow = (e == 0 and (fit6 or (d <= 25 and fit7))) or (e == 6 and fit6)
    bypass = d == 0 or not any(x)
    take = 3 if n == 3 and (e in [3,4,5] or narrow or bypass or x[2] == 0) else min(2,n)
    return take, int(narrow), bypass

def write_stim(wd, frames):
    with (wd/'stream_stim.txt').open('w') as f:
        f.write(str(len(frames))+'\n')
        for u,d,gap in frames:
            assert 1 <= len(u) <= 4096 and all(-1024 <= x <= 1023 for x in u)
            f.write(f'{len(u)} {d} {gap}\n')
            f.writelines(f'{x&2047:03x}\n' for x in u)

def simulate(tag, frames, dc, stall, variant='pipeline', cw=0):
    assert cw in (0,1), 'CW is unsigned(0) or centered(1) wide-residual encoding'
    wd = R/tag; wd.mkdir(parents=True, exist_ok=True); write_stim(wd,frames)
    stamp = hashes(); print(tag,'free GiB',round(free(),2),'frames',len(frames),flush=True)
    assert free() > 1.2
    stem = 'stream_pipeline_leak'
    commands = [f'"{V}/bin/xvlog.bat" -sv -d "DC={dc}" -d "STALL={stall}" -d "CW={cw}" "{P}/{stem}.sv" "{P}/tb_{stem}.sv"',
                f'"{V}/bin/xvlog.bat" "{V}/data/verilog/src/glbl.v"',
                f'"{V}/bin/xelab.bat" -mt off -L unisims_ver tb_{stem} glbl -s sim',
                f'"{V}/bin/xsim.bat" sim -R']
    temp = wd/'tmp'; temp.mkdir(exist_ok=True)
    env = os.environ.copy(); env['TEMP'] = str(temp); env['TMP'] = str(temp)
    for i,c in enumerate(commands):
        z = subprocess.run(c,shell=True,cwd=wd,env=env,capture_output=True,text=True)
        (wd/f'tool_{i}.log').write_text(z.stdout+z.stderr)
        assert z.returncode == 0, z.stdout[-4000:]+z.stderr[-1000:]
    assert 'STREAM PIPELINE PASS' in z.stdout, z.stdout[-4000:]
    assert hashes() == stamp, 'Source changed during simulation'
    rows = []
    for e in range(7):
        outputs = (wd/f'stream_out{e}.txt').read_text().splitlines()
        positions = [0]*len(frames); bad = 0; expected_req = expected_issues = expected_narrow = 0
        for u,fd,gap in frames:
            pos = 0; d = dc if dc >= 0 else fd
            while pos < len(u):
                n,mm,by = policy(u[pos:],d,e)
                pos += n; expected_req += 1; expected_issues += not by; expected_narrow += mm
        assert len(outputs) == expected_req, (e,len(outputs),expected_req)
        for line in outputs:
            fid,pos,n,d,packed,ac,rc,mode = line.split()
            fid,pos,n,d,ac,rc,mode = map(int,[fid,pos,n,d,ac,rc,mode]); packed = int(packed,16)
            u,fd,gap = frames[fid]; fd = dc if dc >= 0 else fd
            nn,mm,by = policy(u[pos:],fd,e)
            assert (n,mode,d,pos) == (nn,mm,fd,positions[fid]), (e,line,u[pos:pos+3])
            got = [(packed>>(11*i))&2047 for i in range(3)]
            # Ceiling division of the signed mathematical product; no RTL packing algebra.
            expected = [(-((-(x*(256-d)))//256))&2047 for x in u[pos:pos+n]] + [0]*(3-n)
            if got != expected:
                bad += 1
                if bad <= 3: print('MISMATCH',e,line,u[pos:pos+n],got,expected,flush=True)
            positions[fid] += n
            if not stall: assert rc-ac == 4, (e,ac,rc)
        assert not bad, (tag,e,bad)
        assert positions == [len(f[0]) for f in frames]
        m = re.search(rf'STREAM E {e} REQUESTS (\d+) NEURONS (\d+) ISSUES (\d+) NARROW (\d+) BYPASS (\d+) CLOCKS (\d+) INPUT_STALLS (\d+) OUTPUT_STALLS (\d+)',z.stdout)
        assert m, (e,z.stdout[-5000:])
        row = dict(engine=e,requests=int(m[1]),neurons=int(m[2]),arithmetic_issues=int(m[3]),
                   narrow_requests=int(m[4]),bypass_requests=int(m[5]),clocks=int(m[6]),
                   input_stall_checks=int(m[7]),output_stall_checks=int(m[8]),mismatches=bad)
        assert row['requests'] == expected_req and row['arithmetic_issues'] == expected_issues
        assert row['narrow_requests'] == expected_narrow
        if stall: assert row['input_stall_checks'] > 0 and row['output_stall_checks'] > 0
        if not stall and not any(f[2] for f in frames): assert row['clocks'] == row['requests']+4
        rows.append(row); print(row,flush=True)
    result = dict(source_hashes=stamp,constant_delta=dc,backpressure=bool(stall),frames=len(frames),
                  centered_wide=bool(cw),wide_residual_encoding='centered' if cw else 'unsigned',
                  real_neurons=sum(len(f[0]) for f in frames),acceptance_to_handshake_advances=4,
                  source_contract='valid and complete payload held while backpressured',rows=rows)
    (R/(tag+'_checks.json')).write_text(json.dumps(result,indent=2))
    return result

def test_frames(small=False):
    rg = random.Random(73159); frames = []
    for d in ([25,0,31] if small else range(32)):
        for x in ([-1024,-1000,-513,-65,-64,-33,-32,-17,-16,-1,0,1,15,16,31,32,63,64,511,1000,1023] if small else range(-1024,1024)):
            b = (x//32)*32
            frames.extend([([x,b+31,b],d,0),([x,((x+1024)*97%2048)-1024,-x-1],d,0)])
    if not small:
        for a in range(-16,16):
            for b in range(-16,16):
                for c in range(-16,16): frames.append(([a,b,c],25,0))
        # All narrow input pairs at coefficient boundaries; the third sweeps bits
        # independently, stressing packed carry boundaries without padded neurons.
        for width,ds in [(6,[25,26,31]),(7,[24,25,26])]:
            lo = -(1<<(width-1)); size = 1<<width
            for d in ds:
                for a in range(lo,lo+size):
                    for b in range(lo,lo+size):
                        c = lo+((a-lo)*37+(b-lo)*19)%size
                        frames.append(([a,b,c],d,0))
        edges = [-65,-64,-33,-32,-1,0,1,31,32,63,64]
        for d in [0,1,24,25,26,31]:
            for a in edges:
                for b in edges:
                    for c in edges: frames.append(([a,b,c],d,0))
        # Explicit real one/two-neuron tails and changing coefficients/source gaps.
        for d in range(32):
            for n in range(1,9):
                frames.append(([[-1024,-64,-32,-1,0,31,63,1023][j] for j in range(n)],d,d%3))
    for j in range(100 if small else 3000):
        d = rg.randrange(32); length = rg.randrange(1,35)
        if j%7 == 0: u = [0]*length
        elif j%3 == 0:
            b = rg.randrange(-32,32)*32; u = [b+rg.randrange(32) for _ in range(length)]
        elif j%5 == 0: u = [rg.randrange(-64,64) for _ in range(length)]
        else: u = [rg.randrange(-1024,1024) for _ in range(length)]
        frames.append((u,d,rg.randrange(3) if j%9 == 0 else 0))
    return frames

if __name__ == '__main__':
    small = '--small' in sys.argv; frames = test_frames(small)
    cw = int(sys.argv[sys.argv.index('--cw')+1]) if '--cw' in sys.argv else 0
    assert cw in (0,1)
    prefix = 'stream_pipeline_centered' if cw else 'stream_pipeline'
    for dc,stall in [(25,0),(-1,1)]:
        simulate(f'{prefix}_{"smoke" if small else "main"}_{dc}_{stall}',frames,dc,stall,cw=cw)
