"""Standalone narrow-domain cost ablation; no tools, no wide support claim."""
from pathlib import Path
import ast,hashlib,json,time
import numpy as np
P=Path(__file__).resolve().parent;A=P/'static9_e8';TRIAL=P.parent.parent/'sequential_paper_trial'
A.mkdir(parents=True,exist_ok=True);assert not(A/'plan.json').exists()
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
inputs=[Path(__file__),P/'leak_core16.sv',P/'leak_dsp.sv',P/'timing16.sv',P/'route16.tcl',P/'tb_native16.sv',TRIAL/'stage3_algebra.json',TRIAL/'check_stage3_algebra.py']
plan=dict(status='declared_before_ablation_tests',engine=8,full_port_bits=16,stored_domain_signed_bits=9,
          legal_U=[-256,255],coefficient=[0,256],fixture_FF=94,
          mapping='Static2lanepairwhenavailable2andcoefequal; scalar signed9 whencoefficientsdiffer oronlyoneavailable. Everyinputsignextended9to16.',
          excludes='Noactualmembrane range detectors, no signed16 fallback. Unsupportedwideinputs mustfailcaller checks. Not a full16baseline.',
          comparison='E5 vsE8 resources measure combinedactualrangeadmission andfull16support cost, notliteralcontroller-only area because synthesis maymergeoptimizations.',
          exactness='Reuse unchangedE5pairalgebra67,371,008exhaustivecases; independentlycheck131,584signed9scalarcases; nativesame2controls E5/E8 narrowdata acrossallbeta,randomcompatible/incompatiblecoeffs andendboundaries.',
          source_sha256={str(p):sha(p)for p in inputs})
(A/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
assert json.loads((TRIAL/'stage3_algebra.json').read_text())['status']=='pass'
start=time.monotonic();u=np.arange(-256,256,np.int64)if False else np.arange(-256,256,dtype=np.int64)
for beta in range(257):
    want=-np.floor_divide(-(u*beta),256);signed9scalar=(u*beta+255)>>8
    assert np.array_equal(want,signed9scalar)and np.all((-256<=want)&(want<=255))
original=(P/'leak_core16.sv').read_text();core=original.replace('module sequential_leak16 #','module sequential_leak_static9 #').replace('E=0,B=16','E=8,B=16')
core=core.replace('E==5','E==8')
for line in(' wire fits0=(raw0[B-1:9]=={(B-9){raw0[8]}});\n',' wire fits1=(raw1[B-1:9]=={(B-9){raw1[8]}});\n'):
    assert core.count(line)==1;core=core.replace(line,'')
old=' wire pair_ok=(available==2)&&fits0&&fits1&&same&&((E==8)||(coef0>=64));'
assert core.count(old)==1;core=core.replace(old,' wire pair_ok=(available==2)&&same;')
old=' wire[24:0]full_a={{(25-B){raw0[B-1]}},raw0};'
assert core.count(old)==1;core=core.replace(old," wire[24:0]full_a={{16{raw0[8]}},raw0[8:0]}; // signed9-only scalar contract")
core=core.replace('// Exact ceil(beta*U/256), signed16 U, unsigned9 beta0..256.',
    '// E8 NARROW-DOMAIN ABLATION ONLY: signed9 U signextended on16-bitports.\n// Exact ceil(beta*U/256), beta0..256. Noactualrangeadmission/full16support.')
(A/'leak_core_static9.sv').write_text(core,encoding='utf-8');(A/'leak_dsp.sv').write_bytes((P/'leak_dsp.sv').read_bytes())
timing=(P/'timing16.sv').read_text().replace('sequential_leak16','sequential_leak_static9')
timing=timing[:timing.index('`GUARD_ADD_FRONTIER_TOP(top_')]+'`GUARD_ADD_FRONTIER_TOP(top_sequential_leak_static9_e8,8)\n`undef GUARD_ADD_FRONTIER_TOP\n'
(A/'timing_static9.sv').write_text(timing,encoding='utf-8')
route=(P/'route16.tcl').read_text().replace('^top_sequential_leak16_e[0-6]$','^top_sequential_leak_static9_e8$').replace('$here/leak_core16.sv','$here/leak_core_static9.sv').replace('$here/timing16.sv','$here/timing_static9.sv')
(A/'route_static9.tcl').write_text(route,encoding='utf-8')
tb=(P/'tb_native16.sv').read_text().replace('tb_sequential_leak16','tb_sequential_static9')
tb=tb.replace('localparam integer ENGINES=`SHIFT_COHORT?7:6;','localparam integer ENGINES=2;')
needle='  sequential_leak16 #(.E(g),.B(16))dut(clk,rst,iv[g],oready[g],u[g],beta[g],avail[g],ir[g],ov[g],take[g],count[g],data[g],narrow[g]);'
replacement='''  if(g==0)begin:full16_reference
   sequential_leak16 #(.E(5),.B(16))dut(clk,rst,iv[g],oready[g],u[g],beta[g],avail[g],ir[g],ov[g],take[g],count[g],data[g],narrow[g]);
  end else begin:narrow_only_ablation
   sequential_leak_static9 #(.E(8),.B(16))dut(clk,rst,iv[g],oready[g],u[g],beta[g],avail[g],ir[g],ov[g],take[g],count[g],data[g],narrow[g]);
  end'''
assert tb.count(needle)==1;tb=tb.replace(needle,replacement)
tb=tb.replace('values[i]<-32768||values[i]>32767','values[i]<-256||values[i]>255')
tb=tb.replace('   if(`SHIFT_COHORT&&coefs[i]!=128)$fatal(1,"Shift cohort requires beta128 at row%0d",i);','')
tb=tb.replace('(e==0||e==5)','(e==0||e==1)')
(A/'tb_static9.sv').write_text(tb,encoding='utf-8')
groups=[]
for beta in range(257):
    for value in range(-256,256):groups.append([(value,beta),(((value+256)*73%512)-256,beta)])
rng=np.random.default_rng(52791)
for _ in range(2000):groups.append([(int(rng.integers(-256,256)),int(rng.integers(257)))for j in range(int(rng.integers(1,6)))])
for beta in range(257):
    for value in(-256,-255,-4,-3,-2,-1,0,1,254,255):groups.append([(value,beta)])
stim=A/'narrow_stim.txt';N=sum(map(len,groups));end=0;flat=[];requests=0
assert N<=400000
with stim.open('w',newline='\n')as stream:
    stream.write(str(N)+'\n')
    for group in groups:
        end+=len(group);pos=0
        while pos<len(group):
            pair=pos+1<len(group)and group[pos][1]==group[pos+1][1]
            requests+=1;pos+=2 if pair else 1
        for value,beta in group:stream.write(f'{value} {beta} {end}\n');flat.append((value,beta))
arr=np.array(flat,np.int64);expected=-np.floor_divide(-(arr[:,0]*arr[:,1]),256)
np.savez_compressed(A/'narrow_expected.npz',U=arr[:,0],beta=arr[:,1],expected_leak=expected,frame_lengths=np.array(list(map(len,groups))))
files=[A/n for n in('leak_core_static9.sv','leak_dsp.sv','timing_static9.sv','route_static9.tcl','tb_static9.sv','narrow_stim.txt','narrow_expected.npz')]
answer=dict(status='software_proof_and_native_preparation_pass_uncompiled_unrouted',B=16,legal_state_domain_bits=9,engine=8,
    signed9_scalar_cases=512*257,scalar_mismatches=0,reused_pair_exhaustive_cases=67371008,
    fixture_FF=94,launch_FF=55,capture_FF=39,expected_DSP=1,
    native_operations=N,native_expected_requests_by_index=[requests,requests],native_engine_indices=[5,8],
    source_sha256=plan['source_sha256']|{str(A/'plan.json'):sha(A/'plan.json')},artifact_sha256={str(p):sha(p)for p in files},
    elapsed_seconds=time.monotonic()-start,interpretation=plan['comparison'],
    compile_options=dict(native='xvlog -sv -d STALL=0|1 -d CAPTURE=0|1 ../leak_core16.sv leak_core_static9.sv leak_dsp.sv tb_static9.sv; xelab -mt off -debug typical -L unisims_ver tb_sequential_static9 glbl',
                         route='vivado -source route_static9.tcl -tclargs top_sequential_leak_static9_e8 12 HASH fresh NEW_ATTEMPT'))
(A/'preparation.json').write_text(json.dumps(answer,indent=2)+'\n')
print(json.dumps({k:answer[k]for k in('status','signed9_scalar_cases','native_operations','native_expected_requests_by_index','interpretation')},indent=2),flush=True)
