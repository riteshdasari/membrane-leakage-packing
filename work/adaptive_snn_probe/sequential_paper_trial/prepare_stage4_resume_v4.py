"""Resume interrupted batch using new attempt directories and completed synthesis only."""
from pathlib import Path
import json,hashlib
P=Path(__file__).resolve().parent
s=(P/'run_stage4_route_v3.py').read_text()
s=s.replace("f'route_e{e}_a2';assert not wd.exists()","f'route_e{e}_a3';assert not wd.exists()")
s=s.replace("original=P/'hardware'/f'route_e{e}_a0'","original=P/'hardware'/f'route_e{e}_a2'\n    if not(original/'synth/design.dcp').exists()or not(original/'synth/provenance.txt').exists():original=P/'hardware'/f'route_e{e}_a0'")
s=s.replace("'stage4_route_progress_v3.json'","'stage4_route_progress_v4.json'").replace("'stage4_route_acceptance_v3.json'","'stage4_route_acceptance_v4.json'")
s=s.replace("P/'stage4_native_acceptance_v4.json',P/'stage4_route_v3_preparation.json'","P/'stage4_native_acceptance_v4.json',P/'stage4_resume_v4_preparation.json',P/'stage4_route_v3_preparation.json'")
s=s.replace("verify(read(P/'stage4_route_v3_preparation.json')['source_sha256'])","verify(read(P/'stage4_route_v3_preparation.json')['source_sha256']);verify(read(P/'stage4_resume_v4_preparation.json')['source_sha256'])")
p=P/'run_stage4_route_v4.py';assert not p.exists();p.write_text(s,encoding='utf-8',newline='\n')
paths=[P/'prepare_stage4_resume_v4.py',P/'run_stage4_route_v4.py',P/'run_stage4_route_v3.py']
p=P/'stage4_resume_v4_preparation.json';assert not p.exists();p.write_text(json.dumps(dict(status='prepared',reason='Human interruption stopped route attempt a2. Preserve it and run fresh placement/routing in a3, reusing only source-pinned completed synthesis.',source_sha256={str(x):hashlib.sha256(x.read_bytes()).hexdigest()for x in paths}),indent=2)+'\n')
