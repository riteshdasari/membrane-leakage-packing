"""Fold fractional correction into DSP C for adaptive and matched fixed triple."""
from pathlib import Path
P=Path(__file__).resolve().parent;s=(P/'stream_unsigned_leak.sv').read_text()
def change(a,b):
 global s
 assert s.count(a)==1,a;s=s.replace(a,b)
change('wire narrow=(available==3)&&((E==0&&(absfit||coherent))||(E==6&&absfit));',
 '''wire fit6=(u0[10:6]=={5{u0[5]}})&&(u1[10:6]=={5{u1[5]}})&&(u2[10:6]=={5{u2[5]}});
 wire fit7=(u0[10:7]=={4{u0[6]}})&&(u1[10:7]=={4{u1[6]}})&&(u2[10:7]=={4{u2[6]}});
 wire narrow=(available==3)&&((E==0&&(fit6||(coef<=25&&fit7)))||(E==6&&fit6));''')
change('localparam MW=E==4?57:33;', 'localparam MW=(E==4&&DC!=25)?57:33;\n localparam NB=E==6?6:7;')
change('wire[21:0]wide_meta;',
 '''wire[21:0]wide_meta;
  wire[11:0]nq;wire[8:0]nf;
  for(genvar l=0;l<3;l=l+1)begin:fold_pre
   wire signed[10:0]u=l==0?u0:(l==1?u1:u2);
   wire signed[1:0]h=E==6?$signed({u[5],u[5]}):$signed(u[6:5]);
   (* use_dsp="no" *) wire signed[6:0]hp;
   wire signed[6:0]hx={{5{h[1]}},h};
   if(DC==25)assign hp=(hx<<<4)+(hx<<<3)+hx;else assign hp=h*dc;
   assign nq[4*l+:4]=hp[6:3];assign nf[3*l+:3]=hp[2:0];
  end''')
change('assign wide_meta[l*11+:11]=u-hp;',
 '''wire signed[3:0]q=nq[4*l+:4];
   wire signed[7:0]correction=narrow?{{4{q[3]}},q}:hp;
   assign wide_meta[l*11+:11]=u-correction;''')
change('assign a=narrow?(E==6?direct_a:an):aw;\n   assign c=narrow?(E==6?direct_c:cn):cw;',
 '''wire[24:0]fold_a={~u2[4],u2[3:0],5'b0,u1[4:0],5'b0,u0[4:0]};
   wire[9:0]fold_top=({5'b0,coef}<<4)+({7'b0,nf[8:6]}<<5);
   wire[47:0]fold_c={18'b0,fold_top,2'b0,nf[5:3],5'b0,2'b0,nf[2:0],5'b0};
   assign a=narrow?fold_a:aw;assign c=narrow?fold_c:cw;''')
change("assign encoded=bypass?raw:(narrow?(E==6?direct_meta:nmeta):{E==5?hybrid_leak:11'b0,wide_meta});",
 '''wire signed[NB-1:0]fold_u2=u2[NB-1:0];
   wire signed[3:0]fold_q2=nq[11:8];
   wire signed[NB-1:0]fold_pre2=fold_u2-fold_q2;
   wire[32:0]fold_meta={{(33-3*NB){1'b0}},fold_pre2,wide_meta[11+:NB],wide_meta[0+:NB]};
   assign encoded=bypass?raw:(narrow?fold_meta:{E==5?hybrid_leak:11'b0,wide_meta});''')
change('wire signed[10:0]narrow_answer=E==6?{{6{direct_result[4]}},direct_result}:shared_answer;',
 '''wire signed[NB-1:0]fold_pre=meta1[NB*l+:NB];
    wire signed[NB-1:0]fold_floor={{(NB-2){1'b0}},prod[9:8]};
    wire signed[NB-1:0]fold_result=fold_pre-fold_floor;
    wire signed[10:0]narrow_answer={{(11-NB){fold_result[NB-1]}},fold_result};''')
change('end else begin:fixed_triple\n   wire[4:0]qf0=',
 '''end else if(DC==25)begin:fixed_folded_triple
   wire[29:0]fc;wire[32:0]fm;
   assign a={~u2[4],u2[3:0],5'b0,u1[4:0],5'b0,u0[4:0]};
   assign c={18'b0,fc};
   for(genvar l=0;l<3;l=l+1)begin:lane
    wire signed[10:0]u=l==0?u0:(l==1?u1:u2);
    wire signed[5:0]h=u[10:5];
    wire signed[10:0]hx={{5{h[5]}},h};
    (* use_dsp="no" *) wire signed[10:0]hp=(hx<<<4)+(hx<<<3)+hx;
    assign fm[11*l+:11]=u-(hp>>>3);
    assign fc[10*l+:10]=({7'b0,hp[2:0]}<<5)+(l==2?10'd400:10'd0);
    wire signed[10:0]pre=meta1[11*l+:11];
    wire signed[10:0]f={9'b0,p[10*l+8+:2]};
    assign decoded[11*l+:11]=pre-f;
   end
   assign encoded=bypass?raw:fm;
  end else begin:fixed_triple
   wire[4:0]qf0=''')
s=s.replace('stream_unsigned','stream_fold')
s=s.replace('// E0: absolute-int5 OR equal-upper-bits shared offset, else fixed wide pair.',
 '// E0: int7 triple for delta<=25 or int6 triple for all delta; else wide pair.')
s=s.replace('// E5: fixed DSP pair plus one exact LUT lane. E6: direct signed-int5 triple.',
 '// E5: fixed DSP pair plus exact LUT lane. E6: int6 adaptive. E4 folds C at DC25.')
(P/'stream_fold_leak.sv').write_text(s)
for name in ['tb_stream_unsigned_leak.sv','check_stream_unsigned.py','check_stream_unsigned_models.py','route_stream_unsigned.tcl','run_stream_unsigned_route.py']:
 text=(P/name).read_text().replace('stream_unsigned','stream_fold')
 if name=='check_stream_unsigned.py':
  a="narrow=(e==0 and eligible)or(e==6 and absolute)"
  b="fit6=n==3 and all(-32<=v<=31 for v in x)\n fit7=n==3 and all(-64<=v<=63 for v in x)\n narrow=(e==0 and (fit6 or (d<=25 and fit7)))or(e==6 and fit6)"
  assert text.count(a)==1;text=text.replace(a,b)
 (P/name.replace('unsigned','fold')).write_text(text)
print('Created isolated fractional-C folding and matched fixed-folded triple')
