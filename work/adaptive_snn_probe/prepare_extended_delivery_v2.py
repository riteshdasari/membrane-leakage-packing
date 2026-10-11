"""Retain the failed CP1252 publication and generate a UTF8 retry."""
from pathlib import Path
P=Path(__file__).resolve().parent
for old,new in(('publish_extended_followup.py','publish_extended_followup_v2.py'),
                ('verify_extended_followup.py','verify_extended_followup_v2.py')):
    text=(P/old).read_text(encoding='utf-8')
    text=text.replace("'membrane_adaptive_extended_checks'","'membrane_adaptive_extended_checks_v2'")
    text=text.replace(".read_text()", ".read_text(encoding='utf-8')")
    text=text.replace("p.write_text(json.dumps(v,indent=2)+'\\n')", "p.write_text(json.dumps(v,indent=2)+'\\n',encoding='utf-8')")
    text=text.replace("rp.write_text('\\n'.join(lines)+'\\n')", "rp.write_text('\\n'.join(lines)+'\\n',encoding='utf-8')")
    text=text.replace("ROOT/'verify_extended_followup.py'", "ROOT/'verify_extended_followup_v2.py'")
    text=text.replace("ROOT/'finish_extended_followup.py',sp,rp", "ROOT/'finish_extended_followup.py',ROOT/'prepare_extended_delivery_v2.py',ROOT/'publish_extended_followup.py',ROOT/'verify_extended_followup.py',sp,rp")
    assert not (P/new).exists();(P/new).write_text(text,encoding='utf-8')
print('Prepared UTF8 retry; original failed outputs and scripts retained.')
