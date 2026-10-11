"""Validate the replay clock phase independently before any 9 ns energy run."""
from pathlib import Path
import hashlib,json,math
P=Path(__file__).resolve().parent
startup=9;period=9;prelude=121
first_falling=startup+period
first_drive=first_falling+math.ceil((prelude-first_falling)/period)*period
assert first_drive==126
s=(P/'run_stage4_energy9.py').read_text().replace('129000','126000')
s=s.replace("'stage4_energy9_preparation.json'","'stage4_energy9_v2_preparation.json'")
s=s.replace("P/'audit_power9.py'","P/'audit_power9_v2.py'")
needle="    assert int(m[4])==expected_valid_rows and expected_valid_rows>0\n"
replacement=needle+'''    roi=re.search(r'REPLAY ROI_START V(\\d+) TIME_NS ([\\d.]+) ROW (\\d+)',log)
    assert roi and int(roi[1])==e and int(roi[3])==first
    assert abs(float(roi[2])*1000-(126000+first*9000))<0.001
'''
assert s.count(needle)==1;s=s.replace(needle,replacement)
for name,value in(('run_stage4_energy9_v2.py',s),('audit_power9_v2.py',(P/'audit_power9.py').read_text().replace('129000','126000'))):
    p=P/name;assert not p.exists();p.write_text(value,encoding='utf-8',newline='\n')
old=json.loads((P/'stage4_energy9_preparation.json').read_text())
paths=[P/n for n in ('prepare_stage4_energy9_v2.py','run_stage4_energy9_v2.py','audit_power9_v2.py','stage4_energy9_preparation.json')]
stamps=old['source_sha256']|{str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths}
p=P/'stage4_energy9_v2_preparation.json';assert not p.exists();p.write_text(json.dumps(dict(status='prepared',first_raw_drive_ns=first_drive,clock_period_ns=period,phase_check='Independent clock/prelude calculation and required observed ROI marker; an unexecuted text replacement had changed126000 to129000, corrected in new immutable files.',source_sha256=stamps),indent=2)+'\n')
