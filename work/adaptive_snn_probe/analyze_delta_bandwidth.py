"""Explicit memory counterfactuals; these are not implemented RAM interfaces."""
from pathlib import Path
import math,json
P=Path(__file__).resolve().parent;R=P/'results';out=[]
for r in json.loads((R/'adaptive_delta_profile.json').read_text())['rows']:
 for ports in [1,2,3,6]:
  transfer=math.ceil(6/ports);groups=r['groups'];n=r['narrow_nonzero_groups'];z=r['zero_groups']
  # Replace the atomic read and atomic output availability with serialized
  # transfers, without overlap. Zero detection still requires reading state.
  extra=2*(transfer-1)*groups
  fixed=r['fixed_complete_group_cycles']+extra
  adaptive=r['adaptive_complete_group_cycles']+extra
  # Ideal double-buffered upper ceiling, not the implemented one-group-at-a-time core.
  # Even an issue-only pipeline cannot exceed its operand/write bandwidth.
  wide=max(3,transfer);small=max(2,transfer)
  ideal_saving=(wide-small)*n/(wide*(groups-z))
  out.append(dict(seed=r['seed'],saved_leak_shift=r['saved_leak_shift'],hard_reset=r['hard_reset'],
   state_read_and_write_values_per_clock=ports,serialized_fixed_cycles=fixed,serialized_adaptive_cycles=adaptive,
   serialized_cycle_saving=1-adaptive/fixed,ideal_overlapped_issue_bandwidth_saving=ideal_saving))
(R/'adaptive_delta_bandwidth.json').write_text(json.dumps(dict(rows=out,notes=[
 'Implemented interface transfers all six int11 values atomically, with a register bank and no intergroup overlap',
 'Serialized read/write costs are analytic scenarios, not synthesized memory wrappers',
 'Ideal overlap ceiling assumes enough buffers and perfectly overlapped independent reads/writes; controller and buffer costs omitted',
 'At two values/clock, both three-lane and two-lane issue pipelines need at least three memory clocks per six-neuron group']),indent=2))
print('BANDWIDTH SCENARIOS',len(out),flush=True)
