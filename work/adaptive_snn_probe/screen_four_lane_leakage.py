"""Four-lane exact residual packing and bounded saved-trace schedule screen.

No RTL/simulation/Vivado/model changes. Standard-library arithmetic plus saved
NumPy trace read; at most one small membrane frame is converted at a time.
Every compared controller sees the same ordered window of up to FOUR int11 U.
Fixed3 may return a fourth exact identity U0..10 by copying it beside its three
arithmetic lanes. All-identity issue suppression is an analytical ideal; its
controller/output mux cost is unimplemented and applied to every policy.
"""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
from pathlib import Path
from collections import defaultdict
from datetime import datetime,timezone
import hashlib,json,re
import numpy as np

P=Path(__file__).resolve().parent;R=P/'results'
FILES=[Path(__file__).name,'stream_pipeline_whole_leak.sv',
 'results/adaptive_delta_model_25_1/expected.npz','results/adaptive_delta_model_input.json',
 'results/adaptive_delta_stress_25_1/expected.npz','results/adaptive_delta_stress_input.json',
 'results/stream_pipeline_whole_models_checks.json','results/stream_pipeline_whole_stress_checks.json']
POLICIES=[('fixed3',None),('fixed3_identity4_copy',None)]+[(f'adaptive4_int{w}_or_fixed3',w)for w in range(2,8)]+[('fixed4_full_range',11)]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def pins():return {n:sha(P/n)for n in FILES}
def leak(u,d):return -((-(u*(256-d)))//256)
def identity(u):return 0<=u<=10
def folded4(u,d):
 h=u//4;r=u%4;hp=d*h;q=hp//64;phi=hp%64
 lowprod=d*r;carry=(4*phi+lowprod)//256
 return u-q-carry,u-q,phi,lowprod
def schedule(frames):
 counters={name:defaultdict(int)for name,w in POLICIES}
 for frame in frames:
  for name,width in POLICIES:
   c=counters[name];c['frames']+=1;c['neurons']+=len(frame);pos=0
   while pos<len(frame):
    u=frame[pos:pos+4];quad=False;copy4=False
    if name=='fixed3':take=min(3,len(u))
    elif name=='fixed4_full_range':take=len(u);quad=len(u)==4
    else:
     copy4=len(u)==4 and identity(u[3])
     quad=width is not None and len(u)==4 and not copy4 and all(-(1<<(width-1))<=v<(1<<(width-1))for v in u)
     take=4 if copy4 or quad else min(3,len(u))
    changing=[v!=leak(v,25)for v in u[:take]]
    assert all((v!=leak(v,25))==(not identity(v))for v in u[:take])
    c['requests']+=1;c['changed_neurons']+=sum(changing);c['nonzero_neurons']+=sum(v!=0 for v in u[:take])
    c['identity_neurons']+=sum(not x for x in changing)
    c['quad_math_requests']+=quad;c['fourth_identity_copy_requests']+=copy4
    if any(changing):
     c['productive_dsp_issues']+=1
     capacity=4 if(name=='fixed4_full_range'or quad)else 3
     used=u[:min(take,capacity)]
     c['issued_lane_capacity']+=capacity
     c['valid_issued_lanes']+=len(used)
     c['changing_issued_lanes']+=sum(v!=leak(v,25)for v in used)
     c['nonzero_issued_lanes']+=sum(v!=0 for v in used)
     if quad:c['productive_quad_issues']+=1
    else:c['all_identity_bypass_requests']+=1
    pos+=take
   assert pos==len(frame)
 for c in counters.values():
  c['productive_quad_issues']+=0
  c['continuous_clock_proxy']=c['requests']+4
  c['frame_drained_clock_proxy']=c['requests']+4*c['frames']
  assert c['changing_issued_lanes']==c['changed_neurons']
  c['changing_per_productive_issue']=c['changing_issued_lanes']/c['productive_dsp_issues']
  c['changing_fraction_of_issued_capacity']=c['changing_issued_lanes']/c['issued_lane_capacity']
 return [dict(policy=name,declared_narrow_bits=width,**dict(counters[name]))for name,width in POLICIES]
def compare(rows):
 base=next(r for r in rows if r['policy']=='fixed3_identity4_copy')
 return [dict(policy=r['policy'],baseline=base['policy'],request_saving_fraction=1-r['requests']/base['requests'],
   productive_issue_saving_fraction=1-r['productive_dsp_issues']/base['productive_dsp_issues'],
   changed_per_issue_ratio=r['changing_per_productive_issue']/base['changing_per_productive_issue'])for r in rows if r['declared_narrow_bits']is not None]
def main():
 stamp=pins();scalar=0;mins=128;maxprod=-1;maxsum=-1;pre_min=1024;pre_max=-1024
 for d in range(32):
  for u in range(-1024,1024):
   result,pre,phi,prod=folded4(u,d)
   assert result==leak(u,d)
   assert 0<=prod<128 and 0<=4*phi+prod<512
   assert -1024<=pre<=1023
   mins=min(mins,prod);maxprod=max(maxprod,prod);maxsum=max(maxsum,4*phi+prod)
   pre_min=min(pre_min,pre);pre_max=max(pre_max,pre);scalar+=1
 residual=0
 for d in range(32):
  for packed_r in range(256):
   r=[(packed_r>>(2*i))&3 for i in range(4)]
   A=sum(r[i]<<(7*i)for i in range(4));assert A<2**23
   product=d*A;assert product<2**28
   assert all(((product>>(7*i))&127)==d*r[i]for i in range(4));residual+=1
 # Root's alternative packs3-bit residuals, recovering each known carry. Since
 # delta*r never127 on delta0..31,r0..7, incoming carry cannot create an extra
 # outgoing carry. The exact upper bit is independent of the previous lane.
 res3_scalar=0;res3_packed=0
 for d in range(32):
  for u in range(-1024,1024):
   h=u//8;r=u%8;hp=d*h;q=hp//32;phi=hp%32
   assert u-q-(d*r+8*phi)//256==leak(u,d)
   assert (d*r+8*phi)//256==((d*r)//8+phi)//32
   if d==25:assert (d*r)//8==3*r
   res3_scalar+=1
  for code in range(4096):
   r=[(code>>(3*i))&7 for i in range(4)]
   A=sum(r[i]<<(7*i)for i in range(4));product=d*A
   carry=[int(d*v>=128)for v in r]
   assert all(d*v!=127 for v in r)
   for i in range(4):
    incoming=carry[i-1]if i else 0
    observed=(product>>(7*i))&127
    recovered=((observed-incoming)&127)+(carry[i]<<7)
    assert recovered==d*r[i]
   res3_packed+=1
 for r in range(4):assert (25*r)//4==6*r
 # A seven-bit product field cannot absorb the generic fractional C term.
 bad_u=-1;bad_d=25;bad_phi=(bad_d*(bad_u//4))%64
 bad_field=bad_d*(bad_u%4)+4*bad_phi
 assert bad_field==231 and bad_field>=128
 model=np.load(R/'adaptive_delta_model_25_1/expected.npz')['groups']
 text=(R/'adaptive_delta_model_input.json').read_text()
 pattern=r'"seed":(\d+),"t":\d+,"layer":\d+,"image":\d+,"start":(\d+),"blocks":(\d+),"neurons":(\d+)'
 records=[tuple(map(int,m))for m in re.findall(pattern,text)];assert len(records)==9216;del text
 def model_frames():
  for seed,start,blocks,neurons in records:yield model[start:start+blocks].reshape(-1)[:neurons].tolist()
 models=schedule(model_frames())
 stress=np.load(R/'adaptive_delta_stress_25_1/expected.npz')['groups']
 stresses=schedule((u.tolist()for u in stress))
 for rows,reference in [(models,'stream_pipeline_whole_models_checks.json'),(stresses,'stream_pipeline_whole_stress_checks.json')]:
  ref=json.loads((R/reference).read_text());fixed=next(r for r in ref['rows']if r['engine']==4)
  observed=next(r for r in rows if r['policy']=='fixed3')
  assert observed['requests']==fixed['requests']and observed['neurons']==fixed['neurons']and fixed['mismatches']==0
 assert pins()==stamp,'Pinned source/input changed'
 result=dict(created_utc=datetime.now(timezone.utc).isoformat(),source_hashes=stamp,
  scope='Four-lane exact arithmetic/schedule screen; no RTL or hardware measurement',
  interface='Every policy sees up to four ordered fullint11 membranes. Four-output capacity/lookahead differs from current three-input RTL and is not implemented.',
  math=dict(scalar_cases=scalar,residual_packed_cases=residual,mismatches=0,
   A='r0+(r1<<7)+(r2<<14)+(r3<<21), ri=Ui mod4; A<2^23 fits signed25',
   P='delta*A, each seven-bit field is delta*ri in[0,93]; no interlane carry',
   correction='Ui=4hi+ri; q=floor(delta*hi/64),phi=(delta*hi)mod64; leak=Ui-q-floor((4phi+delta*ri)/256)',
   residual_product_min=mins,residual_product_max=maxprod,fraction_plus_product_max=maxsum,
   pre_min=pre_min,pre_max=pre_max,
   fractional_C_counterexample=dict(U=bad_u,delta=bad_d,phi=bad_phi,field=bad_field,seven_bit_limit=127),
   implication='Exact four-lane fullint11 operation is algebraically possible only with retained high/fraction corrections here. It also creates a fixed4 comparator; four lanes alone do not establish an adaptive contribution.'),
  alternative_three_bit_residue=dict(scalar_cases=res3_scalar,packed_quad_cases=res3_packed,mismatches=0,
   recovered_product='p_i=(((observed7_i-carry_(i-1))mod128)+128*carry_i),carry_i=[delta*r_i>=128],carry_-1=0',
   invariant='delta*r_i never127 fordelta0..31,r0..7, so an incoming carry cannot create a different outgoing carry.',
   exact_correction='U=8h+r; q=floor(delta*h/32),phi=delta*h mod32; leak=U-q-floor((delta*r+8phi)/256).',
   constant25_simplification='floor(25r/8)=3r, so final fractional carry=floor((3r+phi)/32) can be computed without DSP multiplication.',
   constant25_two_bit_simplification='floor(25r/4)=6r forr0..3, so residual2 final carry=floor((6r+phi)/64) also needs no DSP multiplication.',
   hardware_tradeoff='Atfit6, residual3 usesh3/q3 plus5 fractional bits and6-bit pre perlane,44 metadata bits versus48 forresidual2. Correcting packed residual carry and selecting the full fallback still costs hardware.',
   programmable_scope='Arithmetic proof coversdelta0..31; carry_i is then coefficient/r-dependent and its controller cost is unmeasured.'),
  activity_definition='Changed U differs from exact ceil(231U/256); U0..10 identity values are not counted as productive DSP scalar work.',
  analytical_identity_bypass='Suppress issues when every consumed value is an exact identity; fixed3 may return a fourth identity beside its three arithmetic lanes. Hardware control/mux cost unmeasured and afforded to every adaptive policy.',
  models=dict(rows=models,comparisons=compare(models)),stress=dict(rows=stresses,comparisons=compare(stresses)),
  limitations=['High/fraction product,carry reconstruction,metadata and four-input/output storage/control costs are unimplemented.',
   'Fixed4 full-range arithmetic and LUT4 are necessary strong baselines for a hardware trial.',
   'Nearzero constantbeta231 leakage is itself a cheap piecewise LUT mapping; even negative values counted as changing do not prove DSP necessity.',
   'Identity controller can skip clocked DSP work only if metadata/output logic also reconstructs the exact unchanged result; generic engine-specific bypass bits cannot be substituted blindly.',
   'Four-clock latency is an inherited schedule proxy, not measured or proved for a new four-lane RTL.',
   'No reorder/compression of changing neurons, training, dataset download, power or fullSNN latency claim.'])
 out=R/'four_lane_leakage_screen.json';out.write_text(json.dumps(result,indent=2))
 print('FOUR LANE SCREEN PASS',out,'scalar',scalar,'packed',residual)
 for dataset in ['models','stress']:
  for row in result[dataset]['rows']:
   print(dataset,row['policy'],'requests',row['requests'],'productiveissues',row['productive_dsp_issues'],'quadissues',row['productive_quad_issues'],'changed/issue',round(row['changing_per_productive_issue'],5))
if __name__=='__main__':main()
