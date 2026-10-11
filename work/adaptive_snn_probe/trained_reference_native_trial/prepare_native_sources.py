"""Create one new comparison harness; all frozen cores remain untouched."""
from pathlib import Path
import hashlib
import json

P=Path(__file__).resolve().parent
SRC=P.parent/'residue_frontier_trial/tb_frontier_compare.sv'
DST=P/'tb_restored_reference_compare.sv'

def replace_once(text,old,new):
    assert text.count(old)==1,(old,text.count(old))
    return text.replace(old,new)

def main():
    assert not DST.exists()
    original=SRC.read_text();text=original
    text=replace_once(text,'module frontier_driver #(parameter E=0)','module restored_reference_driver #(parameter E=0)')
    old=''' guard_add_frontier #(.E(E))dut(.clk(clk),.rst(rst),.in_valid(iv),.out_ready(orr),
  .u_in(raw_u),.i_in(raw_i),.available(av),.in_ready(ir),.take(take),
  .out_valid(ov),.out_count(nout),.out_data(answer),.narrow_mode(mode));'''
    new=''' generate if(E<6)begin:original
  guard_add_frontier #(.E(E))dut(.clk(clk),.rst(rst),.in_valid(iv),.out_ready(orr),
   .u_in(raw_u),.i_in(raw_i),.available(av),.in_ready(ir),.take(take),
   .out_valid(ov),.out_count(nout),.out_data(answer),.narrow_mode(mode));
 end else if(E<12)begin:f5
  guard_add_frontier_f5 #(.E(E-6))dut(.clk(clk),.rst(rst),.in_valid(iv),.out_ready(orr),
   .u_in(raw_u),.i_in(raw_i),.available(av),.in_ready(ir),.take(take),
   .out_valid(ov),.out_count(nout),.out_data(answer),.narrow_mode(mode));
 end else begin:static_narrow
  guard_add_static_narrow_eight dut(.clk(clk),.rst(rst),.in_valid(iv),.out_ready(orr),
   .u_in(raw_u),.i_in(raw_i),.available(av),.in_ready(ir),.take(take),
   .out_valid(ov),.out_count(nout),.out_data(answer),.narrow_mode(mode));
 end endgenerate'''
    text=replace_once(text,old,new)
    text=replace_once(text,'raw_u={8{11\'d1023}};raw_i={8{11\'d127}};',
                      "raw_u={8{11'd127}};raw_i={8{11'd127}};")
    start=text.index('  expected_take=(av<8)?av:8;')
    end=text.index('  if(source_held)begin',start)
    text=text[:start]+'''  expected_take=(av<8)?av:8;
  if(E==0||E==6)expected_take=(av<6)?av:6;
  if(E==5||E==11)begin
   expected_take=(av<((E==11)?5:6))?av:((E==11)?5:6);
   for(integer lane=((E==11)?5:6);lane<8;lane=lane+1)begin
    uu=$signed(raw_u[11*lane+:11]);
    if(expected_take==lane&&av>lane&&uu>=-128&&uu<=127)expected_take=lane+1;
   end
  end
  if(take!==4'(expected_take)||mode!==(((E==5)&&(expected_take>6))||((E==11)&&(expected_take>5))))$fatal(1,"Frontier prefix/mode E%0d",E);
  if(E==12&&iv&&ir)begin
   for(integer lane=0;lane<av;lane=lane+1)begin
    uu=$signed(raw_u[11*lane+:11]);
    if(uu<-128||uu>127)$fatal(1,"Static comparator received wide U");
   end
  end
'''+text[end:]
    start=text.index('module tb_frontier_compare;')
    text=text[:start]+'''`ifndef STATIC_COMPARATOR
 `define STATIC_COMPARATOR 0
`endif
module tb_restored_reference_compare;
 localparam ENGINES=12+`STATIC_COMPARATOR;
 reg clk=0;always #3 clk=~clk;
 wire[ENGINES-1:0]done;
 generate for(genvar e=0;e<ENGINES;e=e+1)begin:engines
  restored_reference_driver #(.E(e))driver(clk,done[e]);
 end endgenerate
 initial begin wait(&done);$display("RESTORED_REFERENCE_COMPARE PASS STALL %0d ENGINES %0d",`STALL,ENGINES);$finish;end
endmodule
'''
    DST.write_text(text)
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    record=dict(status='created',source_tb_sha256=sha(SRC),generated_tb_sha256=sha(DST),
        generator_sha256=sha(__file__),changes=['Instantiate all6 original plus all6 F5 cores and optional staticU8 core',
            'Independent prefix oracle for engine5 F6 and engine11 F5',
            'Legal U127 in common reset-canceled in-flight prelude',
            'Assert consumed staticU8 domain', 'Rename harness; reset/stall/poisoned-tail/four-advance body preserved'])
    (P/'tb_source_provenance.json').write_text(json.dumps(record,indent=2)+'\n')

if __name__=='__main__':main()
