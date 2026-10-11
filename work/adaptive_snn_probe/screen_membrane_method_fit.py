"""Small independent numerical method-fit screen; Python standard library only.

No Vivado, downloads, large arrays, model changes or active RTL edits. It checks
representation/leakage identities and gives threshold counterexamples, rather
than claiming area, latency, accuracy or literature novelty.
"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json

P=Path(__file__).resolve().parent;R=P/'results'
RTL=P/'stream_pipeline_whole_leak.sv'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def leak(u,d):return -((-(u*(256-d)))//256)
def split_leak(u,d,e):
 scale=1<<e;m=u//scale;r=u%scale
 high_product=d*scale*m
 high_q=high_product//256;fraction=high_product%256
 return u-high_q-(fraction+d*r)//256
def main():
 pin=sha(RTL);cases=0;discarded_differences=0;commutation_differences=0
 discard_examples=[];commute_examples=[]
 for u in range(-1024,1024):
  for d in range(256):
   for e in range(11):
    assert split_leak(u,d,e)==leak(u,d),(u,d,e)
    cases+=1
  # Current delta25 contract; compress by one right shift without residue.
  reconstructed=2*(u//2)
  if leak(reconstructed,25)!=leak(u,25):
   discarded_differences+=1
   if len(discard_examples)<5:
    discard_examples.append(dict(U=u,compressed_m=u//2,reconstructed_U=reconstructed,
       reference_leak=leak(u,25),discarded_residue_leak=leak(reconstructed,25)))
  if u%2==0 and 2*leak(u//2,25)!=leak(u,25):
   commutation_differences+=1
   if len(commute_examples)<5:
    commute_examples.append(dict(U=u,m=u//2,reference_leak=leak(u,25),scaled_unit_leak=2*leak(u//2,25)))
 # All current-supported scalar inputs can spill/restitch high/low bits exactly.
 spills=0
 for u in range(-1024,1024):
  # Narrow signed7 plus exact upper spill. Base remains original integer unit.
  low=((u+64)%128)-64;high=(u-low)//128
  assert u==128*high+low
  for d in range(32):
   assert leak(128*high+low,d)==leak(u,d);spills+=1
 # For arbitrary odd U, stochastic divide2 has exact unbiased reconstructed U.
 stochastic=0;threshold_disagreements=0
 for u in range(-1024,1024):
  m=u//2;rem=u%2;lower=2*m;upper=2*(m+1)
  assert (2-rem)*lower+rem*upper==2*u
  stochastic+=1
  if rem:
   assert u==lower+1
   assert (lower>=u)!=(u>=u)  # One equally likely outcome misses threshold U.
   threshold_disagreements+=1
 # A constant3/2 multiplier needs no generic variable multiplier: retain one
 # fractional bit with numerator3U, or explicitly floor when using integer U.
 rational_cases=0;odd_half_cases=0
 for u in range(-1024,1024):
  numerator=(u<<1)+u
  assert numerator==3*u
  assert u+(u//2)==(3*u)//2
  odd_half_cases+=u%2
  rational_cases+=1
 # Small positive examples show the practical threshold failure plainly.
 loss_u=15;loss_ref=leak(loss_u,25);loss_drop=leak(2*(loss_u//2),25)
 assert (loss_ref,loss_drop)==(14,13)
 commute_u=12;commute_ref=leak(commute_u,25);commute_naive=2*leak(commute_u//2,25)
 assert (commute_ref,commute_naive)==(11,12)
 sr_u=15;sr_lower=14;sr_upper=16
 sr_leak_num=231*15;sr_floor=sr_leak_num//256;sr_frac=sr_leak_num%256
 assert (sr_floor,sr_frac)==(13,137)
 assert sha(RTL)==pin,'Pinned RTL changed during this numerical screen'
 result=dict(created_utc=datetime.now(timezone.utc).isoformat(),
  scope='Numerical representation and threshold method-fit; no RTL simulation, trained-model approximation study, hardware or literature result',
  source_sha256={RTL.name:pin},script_sha256={Path(__file__).name:sha(Path(__file__))},
  current_mechanism=dict(operation='U-floor(delta*U/256), exact signed int11 leakage',
   state='Full signed-int11 U remains in the original integer unit. It is not divided or multiplied during format adaptation.',
   selection='Three signed7 membranes if delta<=25 and all U are within[-64,63]; otherwise three signed6 membranes if all U are within[-32,31]; otherwise two full-range membranes.',
   guard='Safety is checked before issue. It does not deliberately overflow a packed lane and then recover an unknown carry.',
   fallback='The same original int11 membranes use the wide two-lane arithmetic; there is no persistent wider state migration.'),
  experiments=[
   dict(name='Generic exact mantissa plus residue leakage identity',cases=cases,mismatches=0,
    domain=dict(U=[-1024,1023],delta=[0,255],e=[0,10]),
    equation='U=2^e*m+r,0<=r<2^e; H=delta*2^e*m; Q=floor(H/256),F=H mod256; leak(U)=U-Q-floor((F+delta*r)/256)',
    distinction='This experiment proves generic algebra. Current DSP RTL supports delta0..31 only.',
    fit='Exact if all residue/carry bits and their correction are retained; overhead and lane-safety still need hardware measurement.'),
   dict(name='Exact signed narrow payload plus high spill',cases=spills,mismatches=0,
    equation='low=((U+64) mod128)-64; high=(U-low)/128; U=128*high+low',
    fit='An exact high/low spill can preserve U, but spill bandwidth/storage/control is added work. It is not a new novelty claim by itself.'),
   dict(name='Discarding one mantissa residue bit',scalar_inputs=2048,changed_leak_outputs=discarded_differences,
    examples=discard_examples,threshold_counterexample=dict(U=loss_u,delta=25,threshold=14,
      exact_leak=loss_ref,shift_drop_leak=loss_drop,exact_spike=True,shift_drop_spike=False),
    fit='Fails current exact-output contract whenever discarded bits matter; retaining residue repairs arithmetic.'),
   dict(name='Leakage rounding does not commute with exact state scaling',even_inputs=1024,
    differing_scaled_leak_outputs=commutation_differences,examples=commute_examples,
    threshold_counterexample=dict(U=commute_u,delta=25,threshold=12,
      exact_leak=commute_ref,naive_double_leak_of_half=commute_naive,exact_spike=False,naive_spike=True),
    fit='Even when U is exactly divisible by2, ordinary integer leakage in the half unit is not generally the same update. Residue/correction or aligned rounding conditions are required.'),
   dict(name='Stochastic divide2 is unbiased but spikes differ',scalar_inputs=stochastic,
    unbiased_reconstruction_mismatches=0,odd_inputs_with_threshold_disagreement=threshold_disagreements,
    counterexample=dict(U=sr_u,threshold=15,lower_membrane=sr_lower,upper_membrane=sr_upper,
      each_probability=.5,expected_membrane=15,reference_spike=True,rounded_spike_probability=.5),
    leakage_rounding_counterexample=dict(U=15,beta_q8=231,real_leak_numerator=sr_leak_num,
      real_leak_denominator=256,stochastic_lower=sr_floor,stochastic_upper=sr_floor+1,
      upper_probability_numerator=sr_frac,upper_probability_denominator=256,
      threshold=14,declared_ceiling_reference_spike=True,stochastic_spike_probability=sr_frac/256),
    fit='Possible approximate SNN direction with separate training/accuracy/statistical evaluation; not exact recovery or a drop-in exact-output optimization.'),
   dict(name='Constant times1.5',scalar_inputs=rational_cases,shift_add_mismatches=0,
    odd_inputs_requiring_half_fraction=odd_half_cases,
    exact_fractional_encoding='Keep numerator3U=(U<<1)+U with one fractional bit.',
    floored_integer_encoding='floor(1.5U)=U+floor(U/2).',
    fit='Constant1.5 does not inherently require a general real multiplier. Discarding the half bit or changing state units without matching every update/threshold/reset can change SNN behavior.')],
  strongest_exact_integration='Use actual U to choose a proved-safe packed format; retain full integer state and exact high/low or spill correction. Test the same correction machinery in fixed DSP and LUT baselines. A persistent exponent with residue is a representation option, not a free hardware gain.',
  novelty_limits=['This screen does not read or verify the mentor\'s guard-bit paper. Root literature review must identify its precise contract and compare that mechanism.',
   'Exact spill, guard bits, split products, mantissa/exponent and stochastic rounding are broad established concepts. A literal first-ever claim is unsupported here.',
   'The local LUT triple and fixed hybrid are matched primitive baselines, not reproduced FireFly accelerators.'],
  limitations=['No downloads or models modified.','No FPGA synthesis, routing, occupancy, speed, power or accelerator measurement.',
   'No general SNN classification-loss prediction follows from the numerical threshold counterexamples.',
   'Exponent/residue spills may simply relocate reconstruction cost to the consumer; fair end-to-end cost is required.'])
 R.mkdir(exist_ok=True);dest=R/'membrane_method_fit_checks.json';dest.write_text(json.dumps(result,indent=2))
 print('METHOD FIT PASS',dest,'generic split cases',cases,'exact spill cases',spills)
 print('Discarded-bit leakage differences',discarded_differences,'scaled-even leakage differences',commutation_differences)
 print('No Vivado, downloads or active source edits')
if __name__=='__main__':main()
