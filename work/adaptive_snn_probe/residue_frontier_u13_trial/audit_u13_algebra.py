"""Independent finite-domain arithmetic/admission audit; no RTL/tool jobs."""
from pathlib import Path
import hashlib
import itertools
import json
import sys
sys.dont_write_bytecode=True
import numpy as np
P=Path(__file__).resolve().parent


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def signed(bits,width):
    return (bits & ((1<<width)-1)) - ((bits >> (width-1)) & 1)*(1<<width)


def prefix(available,u):
    count=min(available,5)
    while count<available and -128<=u[count]<=127:count+=1
    return count


def recover(u,i,radix,high_width):
    field=(u%radix)+(i%radix)
    base=signed((u//radix+i//radix)&((1<<high_width)-1),high_width)
    high=signed((base+field//radix)&((1<<high_width)-1),high_width)
    return signed(((high & ((1<<high_width)-1))*radix+field%radix),high_width+radix.bit_length()-1)


def main():
    output=P/'prepared_algebra_checks.json'
    assert not output.exists(),'Preserve independent arithmetic preparation'
    manifest=json.loads((P/'rtl_preparation_manifest.json').read_text())
    for key in ('source_sha256','prepared_sha256'):
        assert all(sha(p)==v for p,v in manifest[key].items())
    scalars=0
    currents=np.arange(-128,128,dtype=np.int64)[None,:]
    full_high_min=10**9;full_high_max=-10**9
    six_high_min=10**9;six_high_max=-10**9
    for start in range(-4096,4096,128):
        u=np.arange(start,start+128,dtype=np.int64)[:,None]
        expected=u+currents
        assert np.array_equal(recover(u,currents,32,9),expected)
        assert np.array_equal(recover(u,currents,128,7),expected)
        assert np.array_equal(signed(((u&((1<<24)-1))+(currents&((1<<24)-1)))&((1<<24)-1),24),expected)
        assert np.array_equal(signed((u+currents)&((1<<14)-1),14),expected)
        high=(u+currents)//32;six=(u+currents)//128
        full_high_min=min(full_high_min,int(high.min()));full_high_max=max(full_high_max,int(high.max()))
        six_high_min=min(six_high_min,int(six.min()));six_high_max=max(six_high_max,int(six.max()))
        scalars+=expected.size
    u=np.arange(-128,128,dtype=np.int64)[:,None]
    assert np.array_equal(recover(u,currents,32,4),u+currents)
    narrow_pairs=int((u+currents).size)
    admissions=0;packed_cases=0
    extreme=[-4096,-129,-128,-127,-33,-32,-1,0,31,32,126,127,128,4095]
    for av,fit in itertools.product(range(9),itertools.product((False,True),repeat=3)):
        values=[extreme[(l+av)%len(extreme)] for l in range(8)]
        for l in range(5,8):values[l]=127 if fit[l-5] else (-129 if l%2 else 128)
        count=prefix(av,values)
        assert 0<=count<=av and (av==0 or count>=min(av,5))
        assert all(-128<=values[l]<=127 for l in range(5,count))
        assert count==av or not(-128<=values[count]<=127)
        bit_predicate=[((value&8191)>>8)==(31 if (value&128) else 0) for value in values]
        assert all(bit_predicate[l]==(-128<=values[l]<=127) for l in range(8))
        admissions+=1
        for current in (-128,-127,-33,-32,-1,0,31,32,126,127):
            inputs=[(values[l],current if l%2 else -1) for l in range(8)]
            a=sum((v%32)<<(6*l) for l,(v,i) in enumerate(inputs))
            b=sum((i%32)<<(6*l) for l,(v,i) in enumerate(inputs))
            physical=a+b;assert physical<1<<48
            recovered=[]
            for l,(v,i) in enumerate(inputs):
                field=(physical>>(6*l))&63
                assert field==(v%32)+(i%32)
                hw=4 if l>=5 else 9
                # RTL narrows ignored tails too, and output masking hides them.
                hu=signed((v>>5)&7,3) if l>=5 else v//32
                base=signed((hu+i//32)&((1<<hw)-1),hw)
                high=signed((base+(field>>5))&((1<<hw)-1),hw)
                result=32*high+(field&31)
                recovered.append(result if l<count else 0)
            assert recovered==[v+i if l<count else 0 for l,(v,i) in enumerate(inputs)]
            a6=sum((v%128)<<(8*l) for l,(v,i) in enumerate(inputs[:6]))
            b6=sum((i%128)<<(8*l) for l,(v,i) in enumerate(inputs[:6]))
            physical6=a6+b6;assert physical6<1<<48
            for l,(v,i) in enumerate(inputs[:6]):
                field=(physical6>>(8*l))&255
                assert field==(v%128)+(i%128)
                assert 128*(v//128+i//128+(field>>7))+(field&127)==v+i
            packed_cases+=1
    assert scalars==2097152 and narrow_pairs==65536 and admissions==72
    assert (full_high_min,full_high_max)==(-132,131)
    assert (six_high_min,six_high_max)==(-33,32)
    record=dict(status='pass',full_U13_I8_scalar_pairs=scalars,narrow_U8_I8_scalar_pairs=narrow_pairs,
        admission_cases=admissions,mixed_packed_cases=packed_cases,
        full_radix32_high_range=[full_high_min,full_high_max],fixed6_radix128_high_range=[six_high_min,six_high_max],
        output_signed14_range=[-4224,4222],eight_field_unsigned_sum_max=62,six_field_unsigned_sum_max=254,
        source_sha256={str(Path(__file__)):sha(__file__),**manifest['source_sha256']},
        prepared_sha256=manifest['prepared_sha256'],
        scope='Independent algebra/encoding/prefix preparation only; native RTL/protocol and routed timing/energy still pending')
    output.write_text(json.dumps(record,indent=2)+'\n')
    print('U13 ALGEBRA PASS',scalars,narrow_pairs,admissions,packed_cases,flush=True)


if __name__=='__main__':main()
