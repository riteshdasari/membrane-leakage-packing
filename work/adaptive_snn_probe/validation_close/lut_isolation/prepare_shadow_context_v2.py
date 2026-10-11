"""Retain failed v1 canary and prepare explicit absolute SDF annotation."""
from pathlib import Path
import ast
import json
import shutil
import sys

P=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.path.insert(0,str(P.parent.parent/'selective_energy_trial'))
import run_selective_energy as b

old=P/'shadow_context_v1'
new=P/'shadow_context_v2'
assert not new.exists()
prep=b.read(old/'preparation.json')
b.verify(prep['source_sha256']);b.verify(prep['prepared_sha256'])
failed=b.read(old/'run_a0/diagnostic.json')
assert failed['status']=='rejected_incomplete_or_unverified_causal_diagnostic'
assert not failed['gates']['shadow_and_canary_SDF_accepted']
assert not failed['gates']['positive_228ps_timing_canary']
new.mkdir()
for name in ('CARRY4_vendor.v','shadow_paths.sdf','run.tcl'):
    shutil.copyfile(old/name,new/name)
before=(old/'monitor_shadow.sv').read_text()
call='initial $sdf_annotate("shadow_paths.sdf");'
assert before.count(call)==1
absolute=(new/'shadow_paths.sdf').as_posix()
after=before.replace(call,f'initial $sdf_annotate("{absolute}",,,,"tool_control");')
assert after.replace(f'initial $sdf_annotate("{absolute}",,,,"tool_control");',call)==before
(new/'monitor_shadow.sv').write_text(after,newline='\n')
runner=P/'run_shadow_context_v2.py'
assert not runner.exists()
original=(P/'run_shadow_context.py').read_text()
assert original.count("P / 'shadow_context_v1'")==1
updated=original.replace("P / 'shadow_context_v1'","P / 'shadow_context_v2'")
ast.parse(updated)
runner.write_text(updated,newline='\n')
record=prep.copy()
record.update(status='prepared_not_run',reason='v1 missing second SDF acceptance and failed positive timing canary; explicit absolute SDF plus tool_control corner selector',
              original_v1_attempt_retained=True,original_DUT_netlist_and_SDF_unchanged=True,
              source_sha256=prep['source_sha256']|b.pins([Path(__file__),old/'preparation.json',old/'run_a0/diagnostic.json',P/'run_shadow_context.py',runner]),
              prepared_sha256=b.pins([new/name for name in ('CARRY4_vendor.v','monitor_shadow.sv','shadow_paths.sdf','run.tcl')]))
b.write(new/'preparation.json',record)
print('Prepared v2: same live probe, explicit absolute SDF annotation; no vendor launch.')
