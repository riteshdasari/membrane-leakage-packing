"""Prepare explicit xelab SDF-root controls; keep both rejected probes."""
from pathlib import Path
import ast
import hashlib
import json

P=Path(__file__).resolve().parent
base=P/'run_shadow_context_v2.py'
before=base.read_text()
old="'-transport_int_delays', '-pulse_r', '0'"
new="'-sdfmax', 'tb_sequential_energy_replay=' + str(wd / 'shadow_paths.sdf').replace('\\\\', '/'),\n         '-transport_int_delays', '-pulse_r', '0'"
assert before.count(old)==1
zero=before.replace(old,new)
assert zero.replace(new,old)==before
ast.parse(zero)
hundred=zero
for option in ('pulse_r','pulse_int_r','pulse_e','pulse_int_e'):
    a=f"'-{option}', '0'";c=f"'-{option}', '100'"
    assert hundred.count(a)==1
    hundred=hundred.replace(a,c)
ast.parse(hundred)
outputs=[P/'run_shadow_context_v3.py',P/'run_shadow_context_v3_pulse100.py']
assert not any(x.exists()for x in outputs)
for path,content in zip(outputs,(zero,hundred)):
    path.write_text(content,newline='\n')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
record=dict(status='prepared_only',vendor_jobs_launched=False,
            original_zero_and_absolute_call_attempts_retained=True,
            zero_runner_change='Explicit xelab -sdfmax at tb_sequential_energy_replay for copied shadow/canary SDF; all other commands unchanged.',
            sensitivity_runner_change='Only four pulse-limit percentages changed from0to100 relative to explicit-root zero runner.',
            original_DUT_SDF_and_netlist_unchanged=True,
            positive_canary_and_all_known_row_checks_unchanged=True,
            source_sha256={str(x):sha(x)for x in [Path(__file__),base,*outputs]},
            scope='Causal diagnostic only, not acceptance of original failed LUT hardware replay.')
(P/'shadow_cli_preparation.json').write_text(json.dumps(record,indent=2)+'\n')
print('Prepared explicit-root zero/100 diagnostic controls, no launch.')
