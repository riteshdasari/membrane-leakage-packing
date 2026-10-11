"""Independent exact scalar and mixed eight-field bound checks; no vendor tools."""
from pathlib import Path
import hashlib,json,random
P=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def signed(value,bits):return value-(1<<bits)if value&(1<<(bits-1))else value
def main():
    assert not(P/'algebra_certificate.json').exists()
    count=0;fullbase=set();fullhigh=set();narrowbase=set();narrowhigh=set()
    for u in range(-1024,1024):
        for i in range(-128,128):
            total=(u%32)+(i%32);base=(u//32)+(i//32);high=base+(total//32)
            assert 0<=total<=62 and -64<=base<=high<=63
            bits=((high&127)<<5)|(total&31)
            assert signed(bits,12)==u+i
            fullbase.add(base);fullhigh.add(high);count+=1
            if -128<=u<=127:
                assert -8<=base<=high<=7
                bits=((high&15)<<5)|(total&31);assert signed(bits,9)==u+i
                narrowbase.add(base);narrowhigh.add(high)
    rng=random.Random(84113);vectors=0;boundary=(-1024,-129,-128,-33,-32,-1,0,31,32,127,128,1023)
    for idx in range(20176):
        pairs=[(boundary[(idx+3*l)%len(boundary)]if idx<176 else rng.randrange(-1024,1024),rng.randrange(-128,128))for l in range(8)]
        ab=sum((u%32)<<(6*l)for l,(u,i)in enumerate(pairs));c=sum((i%32)<<(6*l)for l,(u,i)in enumerate(pairs));p=ab+c
        assert p<1<<48
        for l,(u,i)in enumerate(pairs):
            low=(p>>(6*l))&63;high=(u//32)+(i//32)+(low>>5)
            assert signed(((high&127)<<5)|(low&31),12)==u+i
        vectors+=1
    value=dict(status='pass',scalar_pairs=count,narrow_pairs=65536,packed_vectors=vectors,
        full_base_range=[min(fullbase),max(fullbase)],full_high_range=[min(fullhigh),max(fullhigh)],
        narrow_base_range=[min(narrowbase),max(narrowbase)],narrow_high_range=[min(narrowhigh),max(narrowhigh)],
        physical_guard_field_max=62,source_sha256={str(Path(__file__).resolve()):sha(__file__),str(P/'core.sv'):sha(P/'core.sv')},
        scope='Integer algebra certificate only; RTL/protocol/native/routedcost separately validated')
    (P/'algebra_certificate.json').write_text(json.dumps(value,indent=2)+'\n');print('NATURAL U11 ALGEBRA PASS',count,vectors)
if __name__=='__main__':main()
