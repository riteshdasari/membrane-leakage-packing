"""Prepare NEW U11 fixtures/oracles from immutable earlier harnesses."""
from pathlib import Path
import hashlib,json,sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;ROOT=P.parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def replace_once(text,old,new):
    assert text.count(old)==1,(old,text.count(old));return text.replace(old,new)
def main():
    assert all(not(P/name).exists() for name in ('tb_native.sv','timing.sv','route.tcl','source_preparation.json'))
    src=ROOT/'residue_frontier_trial/tb_frontier_compare.sv';tb=src.read_text()
    tb=tb.replace('guard_add_frontier #(.E(E))','natural_u11 #(.E(E))')
    old='''  if(E==0)expected_take=(av<6)?av:6;
  if(E==5)begin
   expected_take=(av<6)?av:6;
   uu=$signed(raw_u[66+:11]);
   if(av>6&&uu>=-128&&uu<=127)begin
    expected_take=7;uu=$signed(raw_u[77+:11]);
    if(av>7&&uu>=-128&&uu<=127)expected_take=8;
   end
  end'''
    new='''  if(E==0||E==4)begin
   expected_take=(av<5)?av:5;
   uu=$signed(raw_u[55+:11]);
   if(av>5&&uu>=-128&&uu<=127)begin
    expected_take=6;uu=$signed(raw_u[66+:11]);
    if(av>6&&uu>=-128&&uu<=127)begin
     expected_take=7;uu=$signed(raw_u[77+:11]);
     if(av>7&&uu>=-128&&uu<=127)expected_take=8;
    end
   end
  end'''
    tb=replace_once(tb,old,new).replace('((E==5)&&(expected_take>6))','((E==0||E==4)&&(expected_take>5))')
    tb=tb.replace('step-qstep[head%32]!=4','step-qstep[head%32]!=1').replace('cycle-qclk[head%32]<4','cycle-qclk[head%32]<1')
    tb=tb.replace('four-advance','one-advance').replace('below four','below one')
    tb=tb.replace('reg clk=0;always #3 clk=~clk;','reg clk=0;initial begin #6;forever #3 clk=~clk;end')
    tb=tb.replace('wire[5:0]done;','wire[4:0]done;').replace('e<6;','e<5;')
    tb=tb.replace('tb_frontier_compare','tb_natural_u11').replace('FRONTIER_COMPARE PASS','NATURAL_U11 PASS')
    (P/'tb_native.sv').write_text(tb)
    fixture=ROOT/'residue_frontier_trial/guard_add_frontier_timing.sv';timing=fixture.read_text()
    timing=timing.replace('guard_add_frontier_timing','natural_u11_timing').replace('guard_add_frontier #','natural_u11 #')
    timing=timing.replace('top_guard_add_frontier_e','top_natural_u11_e')
    timing=timing.replace('`GUARD_ADD_FRONTIER_TOP(top_natural_u11_e5,5)\n','')
    assert timing.count('`GUARD_ADD_FRONTIER_TOP(top_natural_u11_e')==5
    (P/'timing.sv').write_text(timing)
    routesrc=ROOT/'natural_frontier_trial/route.tcl';route=routesrc.read_text()
    route=route.replace('top_frontier_natural_e[0-5]','top_natural_u11_e[0-4]')
    route=route.replace(' read_verilog -sv $here/../guard_add.sv\n','').replace('read_verilog -sv $here/../frontier_natural.sv','read_verilog -sv $here/core.sv')
    route=route.replace('215','183').replace('123','107')
    (P/'route.tcl').write_text(route)
    sources=[src,fixture,routesrc,Path(__file__),P/'core.sv',P/'CONTRACT.md']
    value=dict(status='prepared',source_sha256={str(p):sha(p)for p in sources},
        generated_sha256={str(P/n):sha(P/n)for n in ('tb_native.sv','timing.sv','route.tcl')},
        scope='New U11 one-edge trial only; parent sources remain read-only; plain integer TB oracle retained')
    (P/'source_preparation.json').write_text(json.dumps(value,indent=2)+'\n')
    print('NATURAL U11 SOURCES PREPARED',flush=True)
if __name__=='__main__':main()
