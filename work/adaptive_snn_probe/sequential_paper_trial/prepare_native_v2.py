from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent
assert not(P/'tb_native_v2.sv').exists()
tb=(P/'tb_native.sv').read_text()
tb=tb.replace('qt[0:5][0:400000],qc[0:5][0:400000]','qt[0:5][0:7],qc[0:5][0:7]')
for stem in('qt','qc'):
    for ptr in('tail','head'):
        tb=tb.replace(f'{stem}[e][{ptr}[e]]',f'{stem}[e][{ptr}[e]%8]')
tb=tb.replace('if(acc)begin','if(acc)begin\n      if(tail[e]-head[e]>=8)$fatal(1,"Scoreboard overflow");')
(P/'tb_native_v2.sv').write_text(tb,encoding='utf-8')
runner=(P/'run_stage4_native.py').read_text().replace('tb_native.sv','tb_native_v2.sv').replace('_a0','_a1').replace('stage4_native_acceptance.json','stage4_native_acceptance_v2.json')
(P/'run_stage4_native_v2.py').write_text(runner,encoding='utf-8')
record=dict(status='prepared_bounded_scoreboard_retry',retained_failure='hardware/native_main_s0_a0/tool_2.log',
    reason='Simulator generated C compilation failed without detailed C diagnostics. Retry uses an8-entry circular scoreboard instead of400001 entries per engine. The two-stage elastic core has at most2 outstanding requests; overflow is asserted.',
    unchanged_datapath=True,unchanged_stimulus_generation=True,
    pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in[Path(__file__),P/'tb_native.sv',P/'tb_native_v2.sv',P/'run_stage4_native.py',P/'run_stage4_native_v2.py',P/'hardware/native_main_s0_a0/tool_2.log']})
(P/'native_v2_preparation.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
