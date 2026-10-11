from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent
assert not(P/'tb_native_v3.sv').exists()
source=(P/'tb_native_v2.sv').read_text()
source=source.replace('count[e]!==qc[e][head[e]%8][1:0]','count[e]!==qc[e][head[e]%8]')
(P/'tb_native_v3.sv').write_text(source,encoding='utf-8')
runner=(P/'run_stage4_native_v2.py').read_text().replace('tb_native_v2.sv','tb_native_v3.sv').replace('_a1','_a2').replace('stage4_native_acceptance_v2.json','stage4_native_acceptance_v3.json')
runner=runner.replace("'-mt','off','-debug','typical'","'-mt','off','-v','2','-debug','typical'")
(P/'run_stage4_native_v3.py').write_text(runner,encoding='utf-8')
(P/'native_v3_preparation.json').write_text(json.dumps(dict(status='prepared_verbose_diagnostic_retry',
    change='Remove a part-select of a dynamically indexed integer scoreboard element. Nonnegative count1/2 comparison is equivalent at full integer width. Enable compiler verbose2 diagnostics.',
    unchanged_hardware_and_vectors=True,
    pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in[Path(__file__),P/'tb_native_v2.sv',P/'tb_native_v3.sv',P/'run_stage4_native_v3.py',P/'hardware/native_main_s0_a1/tool_2.log']}),indent=2)+'\n',encoding='utf-8')
