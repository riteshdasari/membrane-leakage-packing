"""Portable independent integer oracle checks, not a new FPGA benchmark."""
import random
from leakage_reference import execute,packed_pair,reference
rng=random.Random(417839);n=0
ends=[-256,-255,-4,-3,-2,-1,0,1,2,254,255]
for beta in range(257):
    for a in ends:
        for b in ends:
            result,info=packed_pair(a,b,beta)
            assert result==(reference(a,beta),reference(b,beta)),(a,b,beta)
            assert info['borrow']==int(info['x']<0)
            assert -(1<<24)<=info['A']<(1<<24)
            n+=1
for _ in range(100000):
    a,b,beta=rng.randrange(-256,256),rng.randrange(-256,256),rng.randrange(257)
    result,info=packed_pair(a,b,beta)
    assert result==(reference(a,beta),reference(b,beta))
    n+=1
for beta in [0,1,78,128,231,253,256]:
    for u in range(-32768,32768):
        assert reference(u,beta)==(u*beta+255)//256
        if beta==253:assert reference(u,beta)==u-((3*u)//256)
        if beta==128:assert reference(u,beta)==u//2+(u&1)
operands=[(rng.randrange(-32768,32768),rng.randrange(257)) for _ in range(10001)]
for i in range(0,6000,3):
    beta=rng.randrange(257);operands[i:i+2]=[(rng.randrange(-256,256),beta),(rng.randrange(-256,256),beta)]
values,trace=execute(operands)
assert values==[reference(u,b) for u,b in operands]
assert sum(x['count'] for x in trace)==len(operands)
print(f'PASS {n:,} narrow pairs, 458,752 wide scalar/constant checks, {len(operands):,} ordered scheduling operands')
