"""New thin one-edge LIF feedback harness; no pinned source is modified."""
from pathlib import Path
import hashlib,json,sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;ROOT=P.parent


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    target=P/'tb_native.sv';assert not target.exists()
    source=ROOT/'natural_frontier_trial/tb_native.sv';tb=source.read_text()
    old=''' frontier_natural #(.E(E))dut(.clk(clk),.rst(rst),.in_valid(iv),.out_ready(orr),
  .u_in(raw_u),.i_in(raw_i),.available(av),.in_ready(ir),.take(take),
  .out_valid(ov),.out_count(nout),.out_data(answer),.narrow_mode(mode));'''
    new=''' generate if(E==3)begin:adaptive_lut
 adaptive_natural_lut dut(.clk(clk),.rst(rst),.in_valid(iv),.out_ready(orr),
  .u_in(raw_u),.i_in(raw_i),.available(av),.in_ready(ir),.take(take),
  .out_valid(ov),.out_count(nout),.out_data(answer),.narrow_mode(mode));
 end else begin:dsp_family
 frontier_natural #(.E(E==0?5:(E==1?2:4)))dut(.clk(clk),.rst(rst),.in_valid(iv),.out_ready(orr),
  .u_in(raw_u),.i_in(raw_i),.available(av),.in_ready(ir),.take(take),
  .out_valid(ov),.out_count(nout),.out_data(answer),.narrow_mode(mode));
 end endgenerate'''
    assert tb.count(old)==1;tb=tb.replace(old,new)
    assert tb.count('  if(E==0)expected_take=(av<6)?av:6;')==1
    tb=tb.replace('  if(E==0)expected_take=(av<6)?av:6;\n','')
    tb=tb.replace('if(E==5)begin','if(E==0||E==3)begin').replace('((E==5)&&(expected_take>5))','((E==0||E==3)&&(expected_take>5))')
    tb=tb.replace('wire[5:0]done;','wire[3:0]done;').replace('e<6;','e<4;')
    tb=tb.replace('tb_frontier_u13_compare','tb_natural_lif_compare').replace('FRONTIER_U13_COMPARE','NATURAL_LIF_COMPARE')
    target.write_text(tb)
    (P/'harness_preparation.json').write_text(json.dumps(dict(source_file=str(source),source_sha256=sha(source),
        generator_sha256=sha(__file__),generated_tb_sha256=sha(target),
        scope='Only core mapping to four one-edge comparators and completion top change; integer/protocol oracle retained'),indent=2)+'\n')
    print('NATURAL LIF HARNESS PREPARED',flush=True)


if __name__=='__main__':main()
