from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent
assert not(P/'run_stage4_native_v4.py').exists()
source=(P/'run_stage4_native_v3.py').read_text().replace('_a2','_a3').replace('stage4_native_acceptance_v3.json','stage4_native_acceptance_v4.json')
source=source.replace("'-v','2',",'')
(P/'run_stage4_native_v4.py').write_text(source,encoding='utf-8')
(P/'native_v4_preparation.json').write_text(json.dumps(dict(status='prepared_execution_environment_retry',
    cause='Bundled GCC fails to start inside sandbox with Illegal System DLL Relocation. Same GCC --version succeeds outside sandbox.',
    execution='Run unchanged datapath, tb_native_v3 and stimulus through the reviewed unsandboxed command. Remove verbose2 diagnostics only.',
    pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in[Path(__file__),P/'run_stage4_native_v3.py',P/'run_stage4_native_v4.py',P/'tb_native_v3.sv',P/'hardware/native_main_s0_a2/tool_2.log']}),indent=2)+'\n',encoding='utf-8')
