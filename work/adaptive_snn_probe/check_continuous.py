"""Independent scalar ceiling oracle for E5 and THREE-ALWAYS adaptive E7.

The source driver holds valid, all payload bits (including poisoned tail bits),
and coefficient while backpressured. Simulator checks count, order, cancellation,
four *advancing* clocks, and input/output stability separately from this oracle.
"""
from pathlib import Path
import ctypes, hashlib, json, os, random, re, subprocess, sys

P = Path(__file__).resolve().parent
R = P / 'results'
V = Path('C:/AMDDesignTools/2025.2/Vivado')

from check_stream_pipeline import free, write_stim, test_frames

def hashes(variant='pipeline'):
    return {n: hashlib.sha256((P/n).read_bytes()).hexdigest()
            for n in ['continuous_leak.sv', 'tb_continuous_leak.sv',
                      'check_stream_pipeline.py', 'check_continuous.py',
                      'check_continuous_models.py', 'make_continuous.py']}

def policy(u, d, e, variant='pipeline'):
    n = min(3, len(u)); x = u[:n]
    fit6 = n == 3 and all(-32 <= v <= 31 for v in x)
    fit7 = n == 3 and all(-64 <= v <= 63 for v in x)
    assert e in (5,7)
    narrow = e == 7 and (fit6 or (d <= 25 and fit7))
    bypass = d == 0 or not any(x)
    # Both engines consume the same three-output groups; only placement changes.
    take = n
    return take, int(narrow), bypass

def simulate(tag, frames, dc, stall, variant='pipeline', cw=0):
    assert cw == 0, 'This trial tests unsigned CW0 only'
    wd = R/tag; wd.mkdir(parents=True, exist_ok=True); write_stim(wd,frames)
    stimulus_hash = hashlib.sha256((wd/'stream_stim.txt').read_bytes()).hexdigest()
    counterpart = R/tag.replace('continuous','stream_pipeline_whole',1)/'stream_stim.txt'
    matched_whole_stimulus = None
    if counterpart.exists():
        matched_whole_stimulus = stimulus_hash == hashlib.sha256(counterpart.read_bytes()).hexdigest()
        assert matched_whole_stimulus, ('Continuous/WHOLE stimulus differs',str(counterpart))
    stamp = hashes(); print(tag,'free GiB',round(free(),2),'frames',len(frames),flush=True)
    assert free() > 1.2
    stem = 'continuous_leak'
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
    assert 'CONTINUOUS PASS' in z.stdout, z.stdout[-4000:]
    assert hashes() == stamp, 'Source changed during simulation'
    rows = []
    for e in (5,7):
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
        if e == 7:
            gates = re.search(r'CONTINUOUS E7 GATE M1_HOLDS (\d+) R2_HOLDS (\d+) NARROW_M1 (\d+) NARROW_R2 (\d+)',z.stdout)
            assert gates, z.stdout[-5000:]
            row.update(lut_m1_hold_checks=int(gates[1]),lut_r2_hold_checks=int(gates[2]),
                       lut_m1_narrow_holds=int(gates[3]),lut_r2_narrow_holds=int(gates[4]))
            assert row['lut_m1_hold_checks'] > 0 and row['lut_r2_hold_checks'] > 0
            if expected_narrow:
                assert row['lut_m1_narrow_holds'] > 0 and row['lut_r2_narrow_holds'] > 0
        if stall: assert row['input_stall_checks'] > 0 and row['output_stall_checks'] > 0
        if not stall and not any(f[2] for f in frames): assert row['clocks'] == row['requests']+4
        rows.append(row); print(row,flush=True)
    result = dict(source_hashes=stamp,constant_delta=dc,backpressure=bool(stall),frames=len(frames),
                  tested_engines=[5,7],
                  stimulus_sha256=stimulus_hash,matched_whole_stimulus=matched_whole_stimulus,
                  centered_wide=bool(cw),wide_residual_encoding='centered' if cw else 'unsigned',
                  lut_style='root-selected default STYLE; no checker override',
                  identity_policy='E5/E7 always consume three available neurons, including delta0 wide groups',
                  real_neurons=sum(len(f[0]) for f in frames),acceptance_to_handshake_advances=4,
                  source_contract='valid and complete payload held while backpressured',rows=rows)
    (R/(tag+'_checks.json')).write_text(json.dumps(result,indent=2))
    return result

if __name__ == '__main__':
    small = '--small' in sys.argv; frames = test_frames(small)
    cw = int(sys.argv[sys.argv.index('--cw')+1]) if '--cw' in sys.argv else 0
    assert cw == 0
    prefix = 'continuous'
    for dc,stall in [(25,0),(-1,1)]:
        simulate(f'{prefix}_{"smoke" if small else "main"}_{dc}_{stall}',frames,dc,stall,cw=cw)
