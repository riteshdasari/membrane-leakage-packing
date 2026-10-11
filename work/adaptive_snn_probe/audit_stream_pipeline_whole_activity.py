"""Independent lightweight recount of saved beta231 issue/lane accounting.

No imports from the activity implementation or controller policy. Reads saved
traces and checks existing reports without running Vivado or changing them.
Extra zero-copy/LUT-third counts are explicitly split by active/bypassed windows.
"""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
from pathlib import Path
from collections import defaultdict
import hashlib,json
import numpy as np

P=Path(__file__).resolve().parent;R=P/'results'
ENGINES=[0,6,1,4,5]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def oracle(u):
 # Floor-product identity computed independently by Python floor division.
 return u-(25*u)//256
def recount(frames):
 totals={e:defaultdict(int)for e in ENGINES}
 for frame in frames:
  for e in ENGINES:
   c=totals[e];c['neurons']+=len(frame);pos=0
   while pos<len(frame):
    values=frame[pos:pos+3];count=len(values)
    narrow=count==3 and ((e==0 and max(values)<=63 and min(values)>=-64)or(e==6 and max(values)<=31 and min(values)>=-32))
    fixed=e in [4,5]
    thirdzero=count==3 and values[2]==0
    take=3 if count==3 and(fixed or narrow or thirdzero)else min(2,count)
    bypass=all(v==0 for v in values)
    capacity=3 if e==4 or narrow else 2
    c['requests']+=1;c['narrow_requests']+=narrow;c['bypass_requests']+=bypass
    if take==3 and capacity==2:
     key='lut_third'if e==5 else'zero_third'
     c[key+'_bypass_operations'if bypass else key+'_active_operations']+=1
    if bypass:c['bypassed_neuron_operations']+=take
    else:
     c['dsp_issues']+=1;c['dsp_capacity_slots']+=capacity
     used=values[:min(take,capacity)];c['dsp_valid_lane_operations']+=len(used)
     c['dsp_nonzero_operations']+=sum(v!=0 for v in used)
     c['dsp_changing_operations']+=sum(v!=oracle(v)for v in used)
    if e==5 and take==3:
     c['lut_third_nonzero_operations']+=values[2]!=0
     c['lut_third_changing_operations']+=values[2]!=oracle(values[2])
    pos+=take
   assert pos==len(frame)
 for e,c in totals.items():
  c['arithmetic_issues']=c['dsp_issues']
  c['zero_third_copy_operations']=c['zero_third_active_operations']+c['zero_third_bypass_operations']
  c['lut_third_operations']=c['lut_third_active_operations']+c['lut_third_bypass_operations']
  accounted=c['dsp_valid_lane_operations']+c['bypassed_neuron_operations']+c['zero_third_active_operations']+c['lut_third_active_operations']
  assert accounted==c['neurons'],(e,accounted,c['neurons'])
 return totals
def main():
 report=R/'stream_pipeline_whole_activity.json';data=json.loads(report.read_text())
 for path,pin in data['source_hashes'].items():assert sha(P/path)==pin,(path,'Input pin mismatch')
 model=np.load(R/'adaptive_delta_model_25_1/expected.npz')['groups']
 ledger=json.loads((R/'adaptive_delta_model_input.json').read_text())
 frames=[model[r['start']:r['start']+r['blocks']].reshape(-1)[:r['neurons']].tolist()for r in ledger['ledger']]
 stress=np.load(R/'adaptive_delta_stress_25_1/expected.npz')['groups'].tolist()
 audited=[]
 for name,trace in [('models',frames),('stress',stress)]:
  counters=recount(trace);rows={r['engine']:r for r in data[name]['rows']}
  extra=[]
  for e,c in counters.items():
   r=rows[e]
   for key in ['requests','neurons','arithmetic_issues','narrow_requests','bypass_requests','bypassed_neuron_operations','dsp_issues','dsp_capacity_slots','dsp_valid_lane_operations','dsp_nonzero_operations','dsp_changing_operations','zero_third_copy_operations','lut_third_operations','lut_third_nonzero_operations','lut_third_changing_operations']:
    assert c[key]==r[key],(name,e,key,c[key],r[key])
   change_issue=c['dsp_changing_operations']/c['dsp_issues'];change_capacity=c['dsp_changing_operations']/c['dsp_capacity_slots']
   assert abs(change_issue-r['dsp_changing_operations_per_issued_dsp'])<1e-12
   assert abs(change_capacity-r['changing_fraction_of_issued_lane_capacity'])<1e-12
   extra.append(dict(engine=e,zero_third_active_operations=c['zero_third_active_operations'],zero_third_bypass_operations=c['zero_third_bypass_operations'],lut_third_active_operations=c['lut_third_active_operations'],lut_third_bypass_operations=c['lut_third_bypass_operations'],disjoint_neuron_accounting=c['neurons'],changed_operations_per_issue=change_issue,changed_fraction_of_capacity=change_capacity))
  whole=R/f'stream_pipeline_whole_{name}_checks.json';whole_data=json.loads(whole.read_text())
  assert whole_data['constant_delta']==25 and not whole_data['backpressure']
  for rr in whole_data['rows']:
   if rr['engine']not in ENGINES:continue
   for key in ['requests','neurons','arithmetic_issues','narrow_requests','bypass_requests']:assert rr[key]==rows[rr['engine']][key],(name,rr['engine'],key)
   assert rr['mismatches']==0
  for source,pin in whole_data['source_hashes'].items():assert sha(P/source)==pin
  audited.append(dict(dataset=name,rows=extra,whole_completed_simulation=str(whole.resolve()),whole_completed_simulation_sha256=sha(whole),whole_schedule_crosscheck=True))
 result=dict(scope='Independent beta231 numerical issue/lane recount; no toggle or hardware utilization measurement',
  reviewed_report_sha256=sha(report),script_sha256=sha(Path(__file__)),source_sha256=sha(P/'stream_pipeline_whole_leak.sv'),
  findings=['All reported issue/numerator/capacity counts and quoted ratios independently match.',
   'Zero-third-copy and LUT-third totals include bypass windows. They overlap bypassed-neuron totals, so those reported categories must not be added as disjoint counts.',
   'The extra rows here split active and bypass extra lanes; DSP valid operations + bypassed neurons + active extra lanes exactly equals real neurons.',
   'Completed WHOLE CW0 model/stress RTL schedules independently match the accounting.',
   'Changing is numerical U differs from exact ceiling-leaked U. Nonzero and numerical changing work are distinct; neither is measured DSP-clock utilization.',
   'Hybrid DSP usefulness excludes its separate LUT-third work and cannot alone determine total core throughput.'],
  audited=audited)
 dest=R/'stream_pipeline_whole_activity_audit.json';dest.write_text(json.dumps(result,indent=2))
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
