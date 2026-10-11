"""Independent integer oracle for whole unsigned products folded into DSP C.

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
            for n in ['stream_pipeline_whole_leak.sv', 'tb_stream_pipeline_whole_leak.sv',
                      'check_stream_pipeline.py', 'check_stream_pipeline_whole.py']}

def policy(u, d, e, variant='pipeline'):
    n = min(3, len(u)); x = u[:n]
    fit6 = n == 3 and all(-32 <= v <= 31 for v in x)
    fit7 = n == 3 and all(-64 <= v <= 63 for v in x)
    narrow = (e == 0 and (fit6 or (d <= 25 and fit7))) or (e == 6 and fit6)
    bypass = d == 0 or not any(x)
    # Encoded bypass keeps the regular pair/triple representation. Identity alone
    # does not authorize a third wide membrane in engines with a pair fallback.
    take = 3 if n == 3 and (e in [3,4,5] or narrow or x[2] == 0) else min(2,n)
    return take, int(narrow), bypass

def simulate(tag, frames, dc, stall, variant='pipeline', cw=0):
    assert cw in (0,1), 'CW is unsigned(0) or centered(1) wide-residual encoding'
    wd = R/tag; wd.mkdir(parents=True, exist_ok=True); write_stim(wd,frames)
    stimulus_hash = hashlib.sha256((wd/'stream_stim.txt').read_bytes()).hexdigest()
    counterpart = R/tag.replace('stream_pipeline_whole','stream_pipeline',1)/'stream_stim.txt'
    matched_original_stimulus = None
    if counterpart.exists():
        matched_original_stimulus = stimulus_hash == hashlib.sha256(counterpart.read_bytes()).hexdigest()
        assert matched_original_stimulus, ('Whole/default stimulus differs',str(counterpart))
    stamp = hashes(); print(tag,'free GiB',round(free(),2),'frames',len(frames),flush=True)
    assert free() > 1.2
    stem = 'stream_pipeline_whole_leak'
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
    assert 'STREAM PIPELINE WHOLE PASS' in z.stdout, z.stdout[-4000:]
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
                  tested_engines=list(range(7)),
                  stimulus_sha256=stimulus_hash,matched_original_stimulus=matched_original_stimulus,
                  centered_wide=bool(cw),wide_residual_encoding='centered' if cw else 'unsigned',
                  lut_style='root-selected default STYLE; no checker override',
                  identity_policy='regular metadata; no third wide lane from identity alone',
                  real_neurons=sum(len(f[0]) for f in frames),acceptance_to_handshake_advances=4,
                  source_contract='valid and complete payload held while backpressured',rows=rows)
    (R/(tag+'_checks.json')).write_text(json.dumps(result,indent=2))
    return result

if __name__ == '__main__':
    small = '--small' in sys.argv; frames = test_frames(small)
    cw = int(sys.argv[sys.argv.index('--cw')+1]) if '--cw' in sys.argv else 0
    assert cw in (0,1)
    prefix = 'stream_pipeline_whole_centered' if cw else 'stream_pipeline_whole'
    for dc,stall in [(25,0),(-1,1)]:
        simulate(f'{prefix}_{"smoke" if small else "main"}_{dc}_{stall}',frames,dc,stall,cw=cw)
