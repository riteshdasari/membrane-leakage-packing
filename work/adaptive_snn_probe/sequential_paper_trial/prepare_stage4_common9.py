"""Prepare a common operating clock and checkpoint-based recovery without datapath edits."""
from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent
def put(name,value):
    p=P/name;assert not p.exists();p.write_text(value,encoding='utf-8',newline='\n')
s=(P/'run_stage4_route_v4.py').read_text()
s=s.replace("f'route_e{e}_a3';assert not wd.exists()","f'route_e{e}_a4';assert not wd.exists()")
s=s.replace("original=P/'hardware'/f'route_e{e}_a2'","original=P/'hardware'/f'route_e{e}_a3'")
s=s.replace("if __name__=='__main__':main()","if __name__=='__main__':\n    import argparse\n    ap=argparse.ArgumentParser();ap.add_argument('--engine',type=int,choices=range(6),required=True);a=ap.parse_args();route(a.engine)")
put('run_stage4_route_checkpoint_retry.py',s)
tb=(P/'tb_energy.sv').read_text().replace('begin #6;forever #3','begin #9;forever #4.5')
put('tb_energy9.sv',tb)
put('export9.tcl',(P/'export.tcl').read_text().replace('!= 6.0','!= 9.0'))
put('power9.tcl',(P/'power.tcl').read_text().replace('!= 6.0','!= 9.0'))
audit=(P/'audit_power.py').read_text().replace('6000','9000').replace('duration//3000','duration//4500').replace('1000/3','1000/4.5')
audit=audit.replace("d['clock_period_ns']==6","d['clock_period_ns']==9").replace("hardware['clock_period_ns'] == 6","hardware['clock_period_ns'] == 9").replace('clock_period_ns=6','clock_period_ns=9')
put('audit_power9.py',audit)
s=(P/'run_stage4_energy.py').read_text()
s=s.replace("'stage4_energy_preparation.json'","'stage4_energy9_preparation.json'")
s=s.replace("f'route_e{e}_a3'","f'common9_e{e}_a0'")
for old,new in(('tb_energy.sv','tb_energy9.sv'),('export.tcl','export9.tcl'),('power.tcl','power9.tcl'),('audit_power.py','audit_power9.py'),('golden_e','golden9_e'),('export_e','export9_e'),('replay_e','replay9_e'),('power_e','power9_e'),('stage4_energy_progress.json','stage4_energy9_progress.json')):s=s.replace(old,new)
s=s.replace('6000','9000').replace('clock_period_ns=6','clock_period_ns=9')
put('run_stage4_energy9.py',s)
paths=[P/n for n in ('prepare_stage4_common9.py','run_stage4_route_checkpoint_retry.py','tb_energy9.sv','export9.tcl','power9.tcl','audit_power9.py','run_stage4_energy9.py')]
paths += [P/n for n in ('run_stage4_route_v4.py','tb_energy.sv','audit_power.py','run_stage4_energy.py')]
put('stage4_energy9_preparation.json',json.dumps(dict(status='prepared',clock_period_ns=9,input_phase_ns=4.5,reason='Common slower operating clock accommodates the exact LUT2 multiplier path; no arithmetic, interface or pipeline changed. Every implementation receives the same clock/phase and strict replay/power audit.',source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths}),indent=2)+'\n')
