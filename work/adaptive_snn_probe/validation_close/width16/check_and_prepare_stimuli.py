"""Exhaustive signed16 scalar/split mathematics and independent native stimuli."""
from pathlib import Path
import hashlib,json,time
import numpy as np
P=Path(__file__).resolve().parent
TRIAL=P.parent.parent/'sequential_paper_trial'
SAMPLE=P.parent/'benchmarks/profile16_a0/actual_operand_frames.txt'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,o):(P/n).write_text(json.dumps(o,indent=2)+'\n')
def read_groups(p):
    lines=iter(p.read_text().splitlines());n=int(next(lines));groups=[]
    for _ in range(n):
        count=int(next(lines));groups.append([tuple(map(int,next(lines).split()))for j in range(count)])
    assert next(lines,None)is None
    return groups
def take(e,group,pos):
    if pos+1==len(group)or e==4:return 1
    a,b=group[pos];c,d=group[pos+1]
    if e in(2,3,6):return 2
    if e==1:return 2 if b==d else 1
    return 2 if b==d and -256<=a<=255 and -256<=c<=255 and(e==5 or b>=64)else 1
def write_stim(label,groups,engines):
    n=sum(map(len,groups));assert 0<n<=400000
    path=P/(label+'_stim.txt');outputs=P/(label+'_expected.npz')
    end=0;flat=[]
    with path.open('w',encoding='utf-8',newline='\n')as f:
        f.write(str(n)+'\n')
        for group in groups:
            end+=len(group)
            for u,b in group:
                assert -32768<=u<=32767 and 0<=b<=256
                f.write(f'{u} {b} {end}\n');flat.append((u,b))
    a=np.array(flat,dtype=np.int64);wanted=-np.floor_divide(-(a[:,0]*a[:,1]),256)
    np.savez_compressed(outputs,U=a[:,0],beta=a[:,1],expected_leak=wanted,frame_lengths=np.array(list(map(len,groups))))
    counts=[0]*engines
    for e in range(engines):
        for group in groups:
            pos=0
            while pos<len(group):pos+=take(e,group,pos);counts[e]+=1
    return dict(stimulus_file=str(path),expected_outputs_file=str(outputs),operations=n,groups=len(groups),
                expected_requests_by_engine=counts,expected_unstalled_min_max_latency=2,
                artifact_sha256={str(p):sha(p)for p in[path,outputs]})
def main():
    assert not(P/'domain_plan.json').exists(),'Retain completed/partial trials.'
    prep=json.loads((P/'preparation_v2.json').read_text())
    for pins in(prep['source_sha256'],prep['artifact_sha256']):
        for name,want in pins.items():assert sha(Path(name))==want
    assert json.loads((TRIAL/'stage3_algebra.json').read_text())['status']=='pass'
    assert SAMPLE.exists() and sha(SAMPLE)=='226439adadccf3b4d3165b52b100c35cee7375976dff0d06377abcd58cafd119'
    plan=dict(status='declared_before_checks',full_U_domain=[-32768,32767],coefficient_domain=[0,256],
        full_width_fixed_across_workloads=16,membrane_unit='unchanged256 in both trained models',
        pair_U_domain=[-256,255],arithmetic='ceil(beta*U/256)',
        scalar_and_split_exhaustive_cases=65536*257,shift128_exhaustive_cases=65536,
        original_narrow_pair_algebra='reuse unchanged signed9 E5 arithmetic exhaustive67,371,008cases, and E0 subset50,593,792cases from frozenstage3',
        general_native='all65536 signed16 scalar values with cycling beta; every signed9 firstlane and beta with deterministic secondlane; fullwidth boundary pairs for everybeta;2000random4operandgroups; unchanged actualOTTsample',
        shift_native='all65536 signed16 values beta128, boundary/widebursts, unchanged actualOTTsample;7engines including shiftE6',
        sample_native='unchanged OTTprofile16actualsample only,7engines; sample is coverage/stress notrepresentativeenergy',
        no_hardware_result_before_native_compile=True,source_sha256={str(p):sha(p)for p in[Path(__file__),P/'preparation_v2.json',TRIAL/'stage3_algebra.json',SAMPLE]})
    save('domain_plan.json',plan);start=time.monotonic()
    u=np.arange(-32768,32768,dtype=np.int64)
    for b in range(257):
        oracle=-np.floor_divide(-(u*b),256)
        scalar=(u*b+255)>>8
        fixedsplit=(u>>8)*b+(((u&255)*b+255)>>8)
        assert np.array_equal(oracle,scalar)and np.array_equal(oracle,fixedsplit)
        # Explicit emulation of RTL's signed17 high product / 16-bit result.
        h=u>>8;product=h*(b&255);hp=(h<<8)if b==256 else product
        assert np.array_equal(hp+(((u&255)*b+255)>>8),oracle)
        assert np.all((-32768<=oracle)&(oracle<=32767))
    shift=(u>>1)+(u&1);assert np.array_equal(shift,-np.floor_divide(-u,2))
    sample=read_groups(SAMPLE);assert sum(map(len,sample))==7335
    assert all(b==128 and -32768<=v<=32767 for g in sample for v,b in g)
    general=[]
    for i in range(0,65536,2):general.append([(i-32768,i%257),(i+1-32768,(i+1)%257)])
    for b in range(257):
        for a in range(-256,256):general.append([(a,b),(((a+256)*73%512)-256,b)])
    boundary=(-32768,-32767,-16384,-10221,-10220,-8192,-4096,-2049,-2048,-1024,-257,-256,-4,-3,-2,-1,0,1,127,128,255,256,257,1023,2047,2048,4095,8191,10562,16383,32766,32767)
    for b in range(257):
        for a in boundary:general.append([(a,b),(-a-1,b)])
    rng=np.random.default_rng(629117)
    for _ in range(2000):general.append([(int(rng.integers(-32768,32768)),int(rng.integers(257)))for j in range(4)])
    general+=sample
    shgroups=[[(i-32768,128),(i+1-32768,128)]for i in range(0,65536,2)]
    for a in boundary:shgroups.append([(a,128),(-a-1,128)])
    for length in(1,3,8,64,256):
        for a in(-32768,-257,-256,255,256,32767):shgroups.append([(a,128)]*length)
    shgroups+=sample
    cohorts={'general':write_stim('general',general,6),'shift128':write_stim('shift128',shgroups,7),'actual128':write_stim('actual128',sample,7)}
    answer=dict(status='pass_mathematics_and_stimulus_preparation_no_RTL_run',signed16_scalar_cases=65536*257,
        signed16_fixed_split_cases=65536*257,shift128_cases=65536,arithmetic_mismatches=0,
        original_unchanged_narrow_pair_proof_sha256=sha(TRIAL/'stage3_algebra.json'),cohorts=cohorts,
        source_sha256=plan['source_sha256']|{str(P/'domain_plan.json'):sha(P/'domain_plan.json')},
        elapsed_seconds=time.monotonic()-start,hardware_validation_status='notcompiled,notrouted; cannotclaimB16hardwareinferenceyet',
        sample_scope='OTTstress/coverage sample includes full12bit exceptions; norescaling, clipping orcoefficientretuning')
    save('domain_acceptance.json',answer)
    print(json.dumps({k:answer[k]for k in('status','signed16_scalar_cases','arithmetic_mismatches','cohorts','elapsed_seconds')},indent=2),flush=True)
if __name__=='__main__':main()
