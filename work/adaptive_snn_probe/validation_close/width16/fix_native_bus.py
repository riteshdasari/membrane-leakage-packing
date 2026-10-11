"""Precompile repair for seven-engine scoreboard bus; original preparation retained."""
from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent
p=P/'tb_native16.sv';s=p.read_text();assert s.count('wire[5:0]ir,ov,narrow;')==1
before=hashlib.sha256(p.read_bytes()).hexdigest()
p.write_text(s.replace('wire[5:0]ir,ov,narrow;','wire[ENGINES-1:0]ir,ov,narrow;'),encoding='utf-8')
old=json.loads((P/'preparation.json').read_text());old['status']='prepared_uncompiled_unrouted_v2'
old['precompile_repair']='Seven-engine testbench ready/valid/narrow bus must use ENGINES; six-engine frozen testbench copied with6-bit bus corrected before any compile.'
old['superseded_preparation_sha256']=hashlib.sha256((P/'preparation.json').read_bytes()).hexdigest()
old['old_testbench_sha256']=before
old['artifact_sha256'][str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
old['source_sha256'][str(Path(__file__))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
(P/'preparation_v2.json').write_text(json.dumps(old,indent=2)+'\n')
print('WIDTH16 PRECOMPILE BUS REPAIR PREPARATION_V2',flush=True)
