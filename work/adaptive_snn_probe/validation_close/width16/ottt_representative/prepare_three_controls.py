"""Prepare explicit native0/1/2→E5/E1/E6 without modifying pinned predecessor copies."""
from pathlib import Path
import ast,hashlib,json,sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def pins(ps):return{str(p):sha(p)for p in ps}
def change(t,a,b):assert t.count(a)>=1,a;return t.replace(a,b)
def main():
    assert not(P/'preparation_rep3.json').exists()
    tb=(P/'tb_native16.sv').read_text()
    tb=change(tb,'module tb_sequential_leak16;','module tb_sequential_leak16_rep3;')
    tb=change(tb,'localparam integer ENGINES=`SHIFT_COHORT?7:6;','localparam integer ENGINES=3; // native0/1/2 map explicitly toE5/E1/E6')
    tb=change(tb,'.E(g),.B(16)','.E(g==0?5:(g==1?1:6)),.B(16)')
    tb=change(tb,'((e==0||e==5)&&t==2)','(e==0&&t==2)')
    native=(P/'run_native16_rep.py').read_text()
    native=change(native,"P/'preparation_v2.json'","P/'preparation_rep3.json'")
    native=change(native,"P/'tb_native16.sv'","P/'tb_native16_rep3.sv'")
    native=change(native,"'tb_sequential_leak16'","'tb_sequential_leak16_rep3'")
    native=change(native,"    for e,want_requests in enumerate(co['expected_requests_by_engine']):","    for index,e in enumerate((5,1,6)):\n        want_requests=co['expected_requests_by_engine'][e]")
    native=change(native,"artifact_sha256=pins([wd/f'out{e}.txt'for e in range(len(rows))]+([wd/f'trace{e}.txt'for e in range(len(rows))]if args.capture else[]))","artifact_sha256=pins([wd/f'out{i}.txt'for i in range(3)]+([wd/f'trace{i}.txt'for i in range(3)]if args.capture else[]))")
    native=change(native,"wd/f'out{e}.txt'","wd/f'out{index}.txt'")
    native=change(native,"trace=wd/f'trace{e}.txt'","trace=wd/f'trace{index}.txt'")
    native=change(native,"pattern=rf'LEAK_NATIVE E {e}","pattern=rf'LEAK_NATIVE E {index}")
    native=change(native,"rows.append(dict(engine=e,requests=req","rows.append(dict(engine=e,native_index=index,requests=req")
    energy=(P/'run_energy16_rep_12.py').read_text()
    energy=change(energy,"P/'energy16_preparation.json'","P/'energy16_preparation_rep3.json'")
    energy=change(energy,"P/'preparation_v2.json'","P/'preparation_rep3.json'")
    energy=change(energy,"P/'audit_power16_rep_12.py'","P/'audit_power16_rep3_12.py'")
    energy=change(energy,"trace=checkfile.parent/f'trace{e}.txt'","trace=checkfile.parent/f\"trace{row['native_index']}.txt\"")
    energy=change(energy,"native_row=row,native_check_file=str(check)","native_row=row,native_trace_file=str(trace),native_check_file=str(check)")
    energy=change(energy,'all(0<=e<=6 for e in engines)','all(e in(5,1,6)for e in engines)')
    audit=(P/'audit_power16_rep_12.py').read_text()
    audit=change(audit,"trace=checkfile.parent/f'trace{e}.txt';assert sha(trace)==d['trace_sha256']","trace=Path(d['native_trace_file']);assert trace==checkfile.parent/f\"trace{row['native_index']}.txt\";assert sha(trace)==d['trace_sha256']\n    assert row['native_index']=={5:0,1:1,6:2}[e]")
    outputs=[]
    for name,text in[('tb_native16_rep3.sv',tb),('run_native16_rep3.py',native),('run_energy16_rep3_12.py',energy),('audit_power16_rep3_12.py',audit)]:
        file=P/name;assert not file.exists()
        if file.suffix=='.py':ast.parse(text)
        file.write_text(text,encoding='utf-8');outputs.append(file)
    prep=json.loads((P/'preparation_v2.json').read_text())
    record=prep|dict(status='source_prepared_native3_explicit_mapping',native_engine_indices=[5,1,6],source_sha256=prep['source_sha256']|pins([Path(__file__),P/'preparation_v2.json',P/'run_native16_rep.py',P/'run_energy16_rep_12.py',P/'audit_power16_rep_12.py',P/'tb_native16.sv']),artifact_sha256=prep['artifact_sha256']|pins(outputs))
    (P/'preparation_rep3.json').write_text(json.dumps(record,indent=2)+'\n')
    energyrecord=record|dict(source_sha256=record['source_sha256']|pins([P/'preparation_rep3.json']))
    (P/'energy16_preparation_rep3.json').write_text(json.dumps(energyrecord,indent=2)+'\n')
    print(json.dumps(dict(status=record['status'],mapping=record['native_engine_indices'],no_vendor=True)))
if __name__=='__main__':main()
