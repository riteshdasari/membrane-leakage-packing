"""Exact mixed-third fractional-C algebra and saved-trace schedule screen.

Numerical/scheduling only. No RTL, reorder, hardware build, downloaded data or
model modification. An optional any-outlier policy is an optimistic selection
reference whose switching/reordering hardware is not implemented or priced.
"""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
from collections import defaultdict
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re
import numpy as np

P=Path(__file__).resolve().parent;R=P/'results'
POLICIES=['current_adaptive','fixed_pair','fixed_triple','mixed_designated_third','mixed_any_outlier_ideal']
FILES=[Path(__file__).name,'stream_pipeline_whole_leak.sv',
 'results/adaptive_delta_model_25_1/expected.npz','results/adaptive_delta_model_input.json',
 'results/adaptive_delta_stress_25_1/expected.npz','results/adaptive_delta_stress_input.json',
 'results/stream_pipeline_whole_models_checks.json','results/stream_pipeline_whole_stress_checks.json']
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def pins():return {f:sha(P/f)for f in FILES}
def oracle(u,d):return -((-(u*(256-d)))//256)
def scalar_fold(u,d):
 h=u//32;r=u%32;hp=d*h;q=hp//8;phi=hp%8
 pre=u-q;field=d*r+32*phi
 return pre-field//256,pre,field
def fit7(u):return -64<=u<=63
def fit6(u):return -32<=u<=31
def eligible(values,d,name):
 if len(values)!=3:return False
 if name=='fixed_triple':return True
 if name=='fixed_pair':return False
 if d>25:return all(fit6(v)for v in values)
 if name=='current_adaptive':return all(fit7(v)for v in values)
 if name=='mixed_designated_third':return fit7(values[0])and fit7(values[1])
 if name=='mixed_any_outlier_ideal':return sum(fit7(v)for v in values)>=2
 raise ValueError(name)
def counts(frames):
 counters={name:defaultdict(int)for name in POLICIES}
 for u,d in frames:
  for name in POLICIES:
   c=counters[name]
   c['frames']+=1;c['neurons']+=len(u);pos=0
   while pos<len(u):
    values=u[pos:pos+3];n=len(values);triple=eligible(values,d,name)
    thirdzero=n==3 and values[2]==0
    take=3 if n==3 and(triple or thirdzero)else min(2,n)
    bypass=d==0 or all(v==0 for v in values)
    c['requests']+=1;c['triple_requests']+=triple;c['bypass_requests']+=bypass
    c['arithmetic_issues']+=not bypass;c['triple_issues']+=triple and not bypass
    if take==3 and not triple:c['zero_third_requests']+=1
    if name.startswith('mixed')and triple:
     if not all(fit7(v)for v in values):c['mixed_wide_third_requests']+=1
     if name=='mixed_any_outlier_ideal'and not(fit7(values[0])and fit7(values[1])):
      c['requests_needing_lane_selection']+=1
    pos+=take
   assert pos==len(u)
 for c in counters.values():
  c['continuous_clocks_proxy']=c['requests']+4
  c['frame_drained_clocks_proxy']=c['requests']+4*c['frames']
 return [dict(policy=name,**dict(counters[name]))for name in POLICIES]
def compare(rows):
 by={r['policy']:r for r in rows};result=[]
 for name in ['mixed_designated_third','mixed_any_outlier_ideal']:
  a=by[name]
  for baseline in ['current_adaptive','fixed_pair','fixed_triple']:
   b=by[baseline]
   result.append(dict(policy=name,baseline=baseline,
    request_saving_fraction=1-a['requests']/b['requests'],
    issue_saving_fraction=1-a['arithmetic_issues']/b['arithmetic_issues'],
    continuous_clock_saving_fraction=1-a['continuous_clocks_proxy']/b['continuous_clocks_proxy'],
    frame_drained_clock_saving_fraction=1-a['frame_drained_clocks_proxy']/b['frame_drained_clocks_proxy']))
 return result
def analyze(frames,reference):
 rows=counts(frames);ref=json.loads((R/reference).read_text())
 assert ref['constant_delta']==25 and not ref['backpressure']
 by={r['policy']:r for r in rows}
 for name,e in [('current_adaptive',0),('fixed_pair',1),('fixed_triple',4)]:
  rr=next(r for r in ref['rows']if r['engine']==e)
  assert rr['mismatches']==0
  for key in ['requests','neurons','arithmetic_issues','bypass_requests']:
   assert by[name][key]==rr[key],(name,key,by[name][key],rr[key])
  assert by[name]['continuous_clocks_proxy']==rr['clocks']
 return dict(rows=rows,comparisons=compare(rows),completed_reference=reference,baseline_schedule_crosscheck=True)
def main():
 stamp=pins();fullcases=0;smallcases=0;field_min=1024;field_max=-1;pre_min=1024;pre_max=-1024
 for d in range(26):
  for u in range(-1024,1024):
   result,pre,field=scalar_fold(u,d)
   assert result==oracle(u,d)
   assert 0<=field<=999 and -1024<=pre<=1023
   field_min=min(field_min,field);field_max=max(field_max,field)
   pre_min=min(pre_min,pre);pre_max=max(pre_max,pre);fullcases+=1
 for d in range(32):
  for u in range(-32,32):
   result,pre,field=scalar_fold(u,d)
   assert result==oracle(u,d)and 0<=field<=999 and -32<=pre<=31
   smallcases+=1
 # Current signed-top multiplier layout: A top residue is shifted down by16,
 # C adds16*delta in top field, leaving the same positive folded field.
 narrow_values=[-64,-63,-33,-32,-31,-17,-16,-15,-1,0,1,15,16,17,31,32,33,62,63]
 wide_values=[-1024,-1023,-1000,-513,-512,-511,-257,-256,-255,-129,-128,-127,-65,-64,-63,-33,-32,-31,-17,-16,-15,-1,0,1,15,16,17,31,32,33,63,64,65,127,128,129,255,256,257,511,512,513,1000,1022,1023]
 packed_cases=0
 for d in [0,1,7,8,15,16,24,25]:
  for a in narrow_values:
   for b in narrow_values:
    for c in wide_values:
     values=[a,b,c];res=[u%32 for u in values];frac=[(d*(u//32))%8 for u in values]
     A=res[0]+(res[1]<<10)+((res[2]-16)<<20)
     C=(32*frac[0])+((32*frac[1])<<10)+((16*d+32*frac[2])<<20)
     product=d*A+C
     assert 0<=product<2**30
     for lane,u in enumerate(values):
      field=(product>>(10*lane))&1023
      expected,pre,scalar=scalar_fold(u,d)
      assert field==scalar
      assert pre-field//256==expected==oracle(u,d)
     packed_cases+=1
 model=np.load(R/'adaptive_delta_model_25_1/expected.npz')['groups']
 # Extract just seed/index signatures, avoiding allocation of all saved current,
 # state and spike arrays or a second full Python membrane list. One frame is
 # converted at a time; numerical workload storage remains well below50 MiB.
 text=(R/'adaptive_delta_model_input.json').read_text()
 pattern=r'"seed":(\d+),"t":\d+,"layer":\d+,"image":\d+,"start":(\d+),"blocks":(\d+),"neurons":(\d+)'
 records=[tuple(map(int,m))for m in re.findall(pattern,text)]
 assert len(records)==9216;del text
 def model_frames(seed=None):
  for se,start,blocks,neurons in records:
   if seed is None or se==seed:
    yield model[start:start+blocks].reshape(-1)[:neurons].tolist(),25
 models=analyze(model_frames(),'stream_pipeline_whole_models_checks.json')
 models['by_seed']=[dict(seed=seed,rows=counts(model_frames(seed)))for seed in sorted({r[0]for r in records})]
 stress=np.load(R/'adaptive_delta_stress_25_1/expected.npz')['groups'].tolist()
 stress_frames=[(u,25)for u in stress]
 stresses=analyze(stress_frames,'stream_pipeline_whole_stress_checks.json')
 stress_meta=json.loads((R/'adaptive_delta_stress_input.json').read_text())
 stresses['by_reset']=[dict(reset='hard'if rec['hard_reset']else'subtractive',rows=counts(stress_frames[rec['start']:rec['start']+rec['groups']]))for rec in stress_meta]
 assert pins()==stamp,'Pinned files changed during numerical screen'
 result=dict(created_utc=datetime.now(timezone.utc).isoformat(),source_hashes=stamp,
  scope='Exact mixed-third packing algebra and greedy saved-trace schedules; hardware not implemented',
  contract=dict(delta_le25='First two signed7 membranes; designated third arbitrary signedint11; all use five-bit residuals and fractional DSP C.',
   delta_gt25='Three only if all actual membranes fit signed6, matching the current narrower safety condition.',
   correction='U=32h+r,0<=r<32; hp=delta*h; pre=U-floor(hp/8),phi=hp mod8; Pfield=delta*r+32phi; result=pre-floor(Pfield/256).',
   metadata='firsttwo pre values signed7 each; third pre signed11:25 bits versus current21-bit triple metadata. Full originalint11 state remains unchanged.',
   source_order='Designated-third policy processes ordered windows with no neuron reordering or rotations.',
   ideal_any_outlier='At leasttwo of the three membranes fit signed7; mapping the sole wide membrane to the third DSP lane requires selector/output-order hardware not implemented here.'),
  arithmetic=dict(full_int11_scalar_cases=fullcases,narrow6_scalar_cases=smallcases,packed_adversarial_triples=packed_cases,
   mismatches=0,field_min=field_min,field_max=field_max,pre_min=pre_min,pre_max=pre_max,
   proof='For delta<=25,r<=31,phi<=7: field<=31*25+32*7=999<1024. Centering the top product by16 and adding16*delta in its C field reconstructs the same nonnegative field, so no interlane carry.'),
  models=models,stress=stresses,
  limitations=['No RTL implementation, scheduling controller synthesis, route, bandwidth, power or total neuron-update latency measured.',
   'The additional third full-width correction, wider metadata and full-width output subtraction cost hardware; reduced issue count alone is not a win.',
   'Fixed full-range triple already uses the same algebra atdelta25; this candidate is its asymmetric mixed-width correction variant, not arithmetic packing first-ever novelty.',
   'Optional any-outlier reference requires lane selection and restoration of source order; no free reordering assumed in the designated-third result.',
   'Saved beta231 model traces reflect changed reference leakage parameters and contain no new training/model download.',
   'Four-clock drain proxies exclude source lookahead, address movement, state memory and dependent neuron updates.'])
 dest=R/'mixed_third_leakage_screen.json';dest.write_text(json.dumps(result,indent=2))
 print('MIXED THIRD SCREEN PASS',dest,'scalar',fullcases,'packedtriples',packed_cases)
 for dataset in ['models','stress']:
  for r in result[dataset]['rows']:
   print(dataset,r['policy'],'requests',r['requests'],'issues',r['arithmetic_issues'],'clocks_proxy',r['continuous_clocks_proxy'])
if __name__=='__main__':main()
