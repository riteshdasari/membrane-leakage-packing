"""E7 actual GLIF/native and strict energy plumbing; preserve all active main files."""
from pathlib import Path
import ast,hashlib,json
P=Path(__file__).resolve().parent;ALT=P/'lutceil_e7'
assert not(ALT/'followup_v2_preparation.json').exists()
runner=(ALT/'run_native16_lutceil.py').read_text()
runner=runner.replace("['general','shift128','actual128']","['general','shift128','actual128','actual_glif']")
runner=runner.replace("P.parent/'domain_acceptance.json'","P.parent/'domain_acceptance_glif_v2.json'")
ast.parse(runner);(ALT/'run_native16_lutceil_v2.py').write_text(runner,encoding='utf-8')
audit=(P/'audit_power16_12.py').read_text()
audit=audit.replace("OLD=P.parent.parent/'selective_energy_trial'","OLD=P.parent.parent.parent/'selective_energy_trial'")
audit=audit.replace('e in range(7)','e in range(8)').replace('engine in range(7)','engine in range(8)')
audit=audit.replace("cohort['expected_requests_by_engine'][e]","cohort['expected_requests_by_engine'][2 if e==7 else e]")
audit=audit.replace("trace=checkfile.parent/f'trace{e}.txt'","trace=Path(d['native_trace_file'])\n    assert trace==checkfile.parent/f\"trace{row.get('native_index',e)}.txt\"")
audit=audit.replace('[1,1,0,2,1,1,0][engine]','[1,1,0,2,1,1,0,0][engine]')
ast.parse(audit);(ALT/'audit_power16_lutceil_12.py').write_text(audit,encoding='utf-8')
(ALT/'export16_12.tcl').write_bytes((P/'export16_12.tcl').read_bytes())
power=(P/'power16_12.tcl').read_text().replace('$engine > 6','$engine > 7').replace('Engine outside 0..6','Engine outside 0..7')
(ALT/'power16_12.tcl').write_text(power,encoding='utf-8')
(ALT/'tb_energy16_12.sv').write_bytes((P/'tb_energy16_12.sv').read_bytes())
energy=(P/'run_energy16_12.py').read_text()
energy=energy.replace('ROOT=P.parent.parent','ROOT=P.parent.parent.parent')
energy=energy.replace("P/'energy16_preparation.json'","P.parent/'energy16_preparation.json'")
energy=energy.replace("P/'preparation_v2.json'","P/'preparation.json'")
energy=energy.replace("P/'domain_acceptance_glif_v2.json'","P.parent/'domain_acceptance_glif_v2.json'")
energy=energy.replace("P/'leak_core16.sv'","P/'leak_core16_lutceil.sv'").replace("P/'timing16.sv'","P/'timing16_lutceil.sv'")
energy=energy.replace("P/'audit_power16_12.py'","P/'audit_power16_lutceil_12.py'")
energy=energy.replace("top_sequential_leak16_e{e}","top_sequential_leak16_lutceil_e{e}")
energy=energy.replace("trace=checkfile.parent/f'trace{e}.txt'","trace=checkfile.parent/f\"trace{row.get('native_index',e)}.txt\"")
energy=energy.replace("native_check_file=str(check),native_check_sha256=sha(check)","native_check_file=str(check),native_check_sha256=sha(check),native_trace_file=str(trace)")
energy=energy.replace('all(0<=e<=6 for e in engines)','all(e==7 for e in engines)')
energy=energy.replace("if ARGS.workload=='glif':assert all(e<=5 for e in engines)","assert engines==[7]")
# Pin new E7 auditor/power/replay files separately, while the shared main audit stays immutable.
needle="    prep=read(P.parent/'energy16_preparation.json');verify(prep['source_sha256']);verify(prep['artifact_sha256'])"
assert energy.count(needle)==1
energy=energy.replace(needle,needle+"\n    variant=read(P/'followup_v2_preparation.json');verify(variant['source_sha256']);verify(variant['artifact_sha256'])")
needle="    return prep['source_sha256']|prep['artifact_sha256']|core['source_sha256']|core['artifact_sha256']|pins("
assert energy.count(needle)==1
energy=energy.replace(needle,"    return variant['source_sha256']|variant['artifact_sha256']|prep['source_sha256']|prep['artifact_sha256']|core['source_sha256']|core['artifact_sha256']|pins(")
ast.parse(energy);(ALT/'run_energy16_lutceil_12.py').write_text(energy,encoding='utf-8')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inputs=[Path(__file__),ALT/'preparation.json',ALT/'run_native16_lutceil.py',P/'run_energy16_12.py',P/'audit_power16_12.py',P/'energy16_preparation.json',P/'domain_acceptance_glif_v2.json']
outputs=[ALT/n for n in('run_native16_lutceil_v2.py','audit_power16_lutceil_12.py','export16_12.tcl','power16_12.tcl','tb_energy16_12.sv','run_energy16_lutceil_12.py')]
answer=dict(status='prepared_unexecuted_v2',engine=7,native_index=6,coefficient_contract='allbeta0..256',B=16,fixture_FF=94,
            source_sha256={str(p):sha(p)for p in inputs},artifact_sha256={str(p):sha(p)for p in outputs},
            compile_options=dict(native='run_native16_lutceil_v2.py --cohort actual_glif --stall0 --capture1 --attempt NAME',
                 energy="run_energy16_lutceil_12.py --workload glif --native-acceptance ABS_NATIVE/acceptance.json --route-dir-template 'ABS_ROUTE_WITH_{engine}' --engines7 --attempt NAME"),
            note='E7 is nativeindex6 alongside0..5; energy independently binds trace6 and expected request count from fixed2 index2. No source or timed evidence from original E2 is changed.')
(ALT/'followup_v2_preparation.json').write_text(json.dumps(answer,indent=2)+'\n')
print(json.dumps({k:answer[k]for k in('status','engine','native_index','compile_options')},indent=2),flush=True)
