"""One conservative common-clock diagnostic after LUT functional-pass/SDF9-fail."""
from pathlib import Path
import json,hashlib,math
P=Path(__file__).resolve().parent
def put(n,s):
    p=P/n;assert not p.exists();p.write_text(s,encoding='utf-8',newline='\n')
tcl=(P/'common9.tcl').read_text()
tcl=tcl.replace('!= 6.0','!= 9.0').replace('-period 9.0','-period 12.0').replace('-max 4.5','-max 6.0').replace('-min 4.5','-min 6.0').replace('COMMON9_RETIMED','COMMON12_RETIMED')
put('common12.tcl',tcl)
s=(P/'run_stage4_common9.py').read_text()
s=s.replace("complete=read(P/'stage4_route_acceptance_v4.json')","complete=read(P/'stage4_common9_acceptance.json')")
s=s.replace("P/'common9.tcl'","P/'common12.tcl'").replace("P/'stage4_route_acceptance_v4.json'","P/'stage4_common9_acceptance.json'")
a=s.index('        retry=P/');b=s.index("        d=read(p);",a)
s=s[:a]+"        p=P/'hardware'/f'common9_e{e}_a0/hardware.json'\n"+s[b:]
s=s.replace("d['clock_period_ns']==6","d['clock_period_ns']==9")
s=s.replace("f'common9_e{e}_a0'","f'common12_e{e}_a0'").replace("hardware/common9_job_a0","hardware/common12_job_a0")
s=s.replace("wd,'common9'","wd,'common12'").replace('COMMON9_RETIMED','COMMON12_RETIMED').replace('COMMON9 ACCEPTANCE','COMMON12 ACCEPTANCE')
s=s.replace('clock_period_ns=9','clock_period_ns=12').replace('external_input_phase_ns=4.5','external_input_phase_ns=6.0').replace("'stage4_common9_acceptance.json',dict(","'stage4_common12_acceptance.json',dict(")
s=s.replace('operated at common9ns with matched falling-edge4.5ns','operated at common12ns with matched falling-edge6ns')
put('run_stage4_common12.py',s)
tb=(P/'tb_energy9.sv').read_text().replace('begin #9;forever #4.5','begin #12;forever #6')
put('tb_energy12.sv',tb)
put('export12.tcl',(P/'export9.tcl').read_text().replace('!= 9.0','!= 12.0'))
put('power12.tcl',(P/'power9.tcl').read_text().replace('!= 9.0','!= 12.0'))
first_drive=24+math.ceil((121-24)/12)*12;assert first_drive==132
a=(P/'audit_power9_v2.py').read_text().replace('9000','12000').replace('126000','132000').replace('duration//4500','duration//6000').replace('1000/4.5','1000/6')
a=a.replace("d['clock_period_ns']==9","d['clock_period_ns']==12").replace("hardware['clock_period_ns'] == 9","hardware['clock_period_ns'] == 12").replace('clock_period_ns=9','clock_period_ns=12')
put('audit_power12.py',a)
s=(P/'run_stage4_energy9_v2.py').read_text()
for old,new in(('stage4_energy9_v2_preparation.json','stage4_energy12_preparation.json'),('common9_e','common12_e'),('tb_energy9.sv','tb_energy12.sv'),('export9.tcl','export12.tcl'),('power9.tcl','power12.tcl'),('audit_power9_v2.py','audit_power12.py'),('golden9_e','golden12_e'),('export9_e','export12_e'),('replay9_e','replay12_e'),('power9_e','power12_e'),('stage4_energy9_progress.json','stage4_energy12_progress.json')):s=s.replace(old,new)
s=s.replace('9000','12000').replace('126000','132000').replace('clock_period_ns=9','clock_period_ns=12')
s=s.replace('    for e in range(6):','    for e in (2,0,1,3,4,5):')
needle="        for label,fn in(('golden',golden),('export',export),('replay',replay),('power',power)):\n"
s=s.replace(needle,"        if e!=2 and state['failures']:\n            state['gated_remaining_reason']='LUT baseline did not pass conservative12ns replay; remaining12ns reruns would not resolve that failure. Accepted9ns DSP comparisons remain separately saved.';break\n"+needle)
put('run_stage4_energy12.py',s)
paths=[P/n for n in ('prepare_stage4_common12.py','common12.tcl','run_stage4_common12.py','tb_energy12.sv','export12.tcl','power12.tcl','audit_power12.py','run_stage4_energy12.py','run_stage4_energy9_v2.py','audit_power9_v2.py','stage4_energy9_progress.json')]
p=P/'hardware/lut_functional_diagnostic_a0/diagnostic.json';d=json.loads(p.read_text());assert d['status']=='functional_mapping_pass';paths.append(p)
put('stage4_energy12_preparation.json',json.dumps(dict(status='prepared',clock_period_ns=12,first_raw_drive_ns=first_drive,input_phase_ns=6,gate='LUT12 replay first; continue all six12ns energy rows only after it passes. Failure is retained and limits claims rather than waiving checks.',source_sha256={str(x):hashlib.sha256(x.read_bytes()).hexdigest()for x in paths}),indent=2)+'\n')
