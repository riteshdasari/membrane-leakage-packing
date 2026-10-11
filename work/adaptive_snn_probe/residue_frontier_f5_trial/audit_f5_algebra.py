"""Exact scalar/range/prefix and parent-source audit; no HDL/tool jobs."""
from pathlib import Path
import hashlib
import itertools
import json
import sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audit():
    old=P.parent/'residue_frontier_trial'
    parent=(old/'guard_add_frontier.sv').read_text()
    child=(P/'guard_add_frontier_f5.sv').read_text()
    # Reverse only the declared E5 changes and module identifier. This proves
    # that all comparator datapath source remains exactly the frozen parent's.
    reconstructed=child.replace('guard_add_frontier_f5','guard_add_frontier')
    reconstructed=reconstructed.replace('five full-range lanes and three exact signed8-U lanes',
                                        'six full-range lanes and two exact signed8-U lanes')
    reconstructed=reconstructed.replace('  wire tail5_fits8=(u_in[11*5+8+:3]=={3{u_in[11*5+7]}});\n','')
    new="  wire[3:0]adaptive_prefix=(available<=5)?available:\n       (!tail5_fits8?4'd5:\n        ((available<=6||!tail6_fits8)?4'd6:\n         ((available>=8&&tail7_fits8)?4'd8:4'd7)));"
    original="  wire[3:0]adaptive_prefix=(available<=6)?available:\n       (!tail6_fits8?4'd6:((available>=8&&tail7_fits8)?4'd8:4'd7));"
    assert new in reconstructed
    reconstructed=reconstructed.replace(new,original).replace('(take>5)','(take>6)').replace('E==5&&l>=5','E==5&&l>=6')
    assert reconstructed==parent,'Undeclared comparator/datapath change'
    fixture=(P/'guard_add_frontier_f5_timing.sv').read_text().replace('guard_add_frontier_f5','guard_add_frontier')
    assert fixture==(old/'guard_add_frontier_timing.sv').read_text()
    scalar=small=0
    ranges={False:[1000,-1000],True:[1000,-1000]}
    for u in range(-1024,1024):
        for current in range(-128,128):
            hu,ru=divmod(u,32);hi,ri=divmod(current,32)
            carry,low=divmod(ru+ri,32);base=hu+hi;high=base+carry
            assert ru+ri<=62 and -64<=base<=63 and -64<=high<=63
            assert high*32+low==u+current
            ranges[False]=[min(ranges[False][0],high),max(ranges[False][1],high)]
            scalar+=1
            if -128<=u<=127:
                assert -8<=base<=7 and -8<=high<=7 and -256<=u+current<=255
                ranges[True]=[min(ranges[True][0],high),max(ranges[True][1],high)]
                small+=1
    # All three narrow-tail membership masks and all legal availabilities.
    policies=0
    for av in range(9):
        for fits in itertools.product((False,True),repeat=3):
            rtl=av if av<=5 else (5 if not fits[0] else
                  (6 if av<=6 or not fits[1] else (8 if av>=8 and fits[2] else 7)))
            mathematical=min(av,5)
            while mathematical<av and fits[mathematical-5]:mathematical+=1
            assert rtl==mathematical
            assert all(fits[lane-5] for lane in range(5,rtl))
            policies+=1
    assert scalar==524288 and small==65536 and ranges[False]==[-36,35] and ranges[True]==[-8,7]
    return dict(status='pass',exhaustive_scalar_pairs=scalar,narrow_scalar_pairs=small,
                full_high_range=ranges[False],narrow_high_range=ranges[True],prefix_availability_mask_cases=policies,
                fixed_engine_source_unchanged=True,fixture_source_unchanged=True,
                source_sha256={str(path.resolve()):sha(path) for path in
                    (Path(__file__),P/'guard_add_frontier_f5.sv',P/'guard_add_frontier_f5_timing.sv',
                     old/'guard_add_frontier.sv',old/'guard_add_frontier_timing.sv')},
                scope='Exact scalar algebra, valid-tail admission and declared source-only E5 delta; no sequential HDL/timing/resource/power proof')


if __name__=='__main__':
    result=audit();out=P/'prepared_algebra_checks.json'
    assert not out.exists(),'Preserve prepared audit'
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
