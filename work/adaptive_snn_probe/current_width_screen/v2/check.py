"""Exact endpoint cost screen when trained layers exceed signed8 current.

Only register bounds are derived. No RTL synthesis or runtime benchmark claim.
"""
from pathlib import Path
import json,hashlib
P=Path(__file__).resolve().parent
def bits(lo,hi):
    b=1
    while lo<-(1<<(b-1))or hi>=(1<<(b-1)):b+=1
    return b
def endpoints(b):return -(1<<(b-1)),(1<<(b-1))-1
def base_range(ub,ib):
    ul,uh=endpoints(ub);il,ih=endpoints(ib)
    return ul//32+il//32,uh//32+ih//32
assert not(P/'results.json').exists()
rows=[]
for ub in(8,10,11,12,13,16,20,24):
    for ib in(8,10,11,12,16,20):
        full=base_range(ub,ib);tail=base_range(8,ib)
        f,t=bits(*full),bits(*tail)
        assert f==max(ub,ib)-4 and t==max(8,ib)-4
        for u in sorted(set([*endpoints(ub),-128,-1,0,127])):
            if not endpoints(ub)[0]<=u<=endpoints(ub)[1]:continue
            for i in(*endpoints(ib),-1,0):
                raw=u%32+i%32;base=u//32+i//32
                reconstructed=32*(base+raw//32)+raw%32
                assert reconstructed==u+i
                assert full[0]<=base<=full[1]
                if -128<=u<=127:assert tail[0]<=base<=tail[1]
        sum_bits=max(ub,ib)+1
        native_lanes=4 if sum_bits<=12 else 2 if sum_bits<=24 else 1 if sum_bits<=48 else 0
        # The original3 signed4 tail registers are legal ONLY for signed8 I.
        rows.append(dict(generic_U_bits=ub,generic_I_bits=ib,sum_bits=sum_bits,
            full_high_base_range=list(full),tail_U8_high_base_range=list(tail),
            full_high_base_bits=f,tail_high_base_bits=t,
            fixed8_metadata_FF=5+8*f,adaptive5full_3U8_metadata_FF=5+5*f+3*t,
            adaptive_FF_saving_vs_fixed8=3*(f-t),native_DSP_lanes=native_lanes,
            native_hybrid_FF=None if not native_lanes else 5+(8-native_lanes)*sum_bits,
            original_four_bit_tail_metadata_legal=ib==8,
            narrowing_U_alone_saves_metadata=f>t))
result=dict(status='pass_exact_endpoint_and_register_bound_screen',rows=rows,
    source_sha256={str(Path(__file__).resolve()):hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
    formula='Eight radix32 residue fields with guard; full base requires max(Ubits,Ibits)-4 signed bits; U8-tail base requires max(8,Ibits)-4. Fivefull+threetail saves3*max(Ubits-max(8,Ibits),0) explicit FFs against full8.',
    conclusion='When Ibits>=Ubits, narrowing only U saves no high-base metadata. The current signed4 narrow metadata is not legal for a wider current. A real benchmark must prove I8 or use a new equally controlled exact design.',
    limitations=['Generic full signed-word endpoints, not model-specific sum certificates',
        'No area,slice,timing,energy,eligibility or trained-model result',
        'Version2 adds the legal native ONE48 option for sum widths above24; original cost-screen omission is retained',
        'Native mode must be selected from actual certified operand+sum widths in specialized workloads',
        'Joint U-and-I range admission would be a different policy and requires full exactness and strongest controls'])
(P/'results.json').write_text(json.dumps(result,indent=2)+'\n')
print('CURRENT WIDTH SCREEN PASS',len(rows),'no saving cases',sum(not r['narrowing_U_alone_saves_metadata']for r in rows))
