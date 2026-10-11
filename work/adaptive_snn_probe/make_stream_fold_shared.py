"""Factor the coefficient-only rounding table once, before per-lane h selection."""
from pathlib import Path
P=Path(__file__).resolve().parent;s=(P/'stream_fold_leak.sv').read_text()
a='''wire[11:0]nq;wire[8:0]nf;'''
b='''wire[11:0]nq;wire[8:0]nf;
  wire[5:0]round8={1'b0,coef}+6'd7,round4={1'b0,coef}+6'd3;
  wire signed[3:0]q_pos={2'b0,coef[4:3]};
  wire signed[3:0]q_neg=-$signed({1'b0,round8[5:3]});
  wire signed[3:0]q_twoneg=-$signed(round4[5:2]);
  wire[2:0]f_neg=3'd0-coef[2:0],f_twoneg=3'd0-{coef[1:0],1'b0};'''
assert s.count(a)==1;s=s.replace(a,b)
a='''(* use_dsp="no" *) wire signed[6:0]hp;
   wire signed[6:0]hx={{5{h[1]}},h};
   if(DC==25)assign hp=(hx<<<4)+(hx<<<3)+hx;else assign hp=h*dc;
   assign nq[4*l+:4]=hp[6:3];assign nf[3*l+:3]=hp[2:0];'''
b='''if(E==6)begin:one_sign
    assign nq[4*l+:4]=h[1]?q_neg:4'd0;
    assign nf[3*l+:3]=h[1]?f_neg:3'd0;
   end else begin:two_high_bits
    assign nq[4*l+:4]=h[1]?(h[0]?q_neg:q_twoneg):(h[0]?q_pos:4'd0);
    assign nf[3*l+:3]=h[1]?(h[0]?f_neg:f_twoneg):(h[0]?coef[2:0]:3'd0);
   end'''
assert s.count(a)==1;s=s.replace(a,b).replace('stream_fold','stream_fold_shared')
(P/'stream_fold_shared_leak.sv').write_text(s)
for name in ['tb_stream_fold_leak.sv','check_stream_fold.py','check_stream_fold_models.py','route_stream_fold.tcl','run_stream_fold_route.py']:
 (P/name.replace('stream_fold','stream_fold_shared')).write_text((P/name).read_text().replace('stream_fold','stream_fold_shared'))
print('Created shared coefficient-only q/f table; policy and layout unchanged')
