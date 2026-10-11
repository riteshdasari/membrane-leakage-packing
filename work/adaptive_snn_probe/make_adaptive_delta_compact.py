"""One targeted, exact retiming experiment; preserve the first implementation."""
from pathlib import Path
P=Path(__file__).resolve().parent
s=(P/'adaptive_delta_leak.sv').read_text()
s=s.replace('wire[6*B-1:0]computed;','''wire[6*B-1:0]computed;
 wire[2*B-1:0]adjusted;
 generate if(E==0||E==1)begin:precorrect
  for(genvar l=0;l<2;l=l+1)begin:lane
   wire signed[B-1:0]u=l==0?s0:s1;
   wire signed[B-9:0]upper=u[B-1:8];
   wire signed[B-8:0]h={upper[B-9],upper}+$signed({{(B-8){1'b0}},u[7]});
   wire signed[5:0]dc={1'b0,coef};
   // For signed int11, h is [-4,4], so delta*h fits signed int8.
   (* use_dsp="no" *) wire signed[B-4:0]hp=h*dc;
   assign adjusted[l*B+:B]=u-hp;
  end
 end else assign adjusted={s1,s0};endgenerate''')
s=s.replace("else original0<={{(3*B){1'b0}},s2,s1,s0};", "else original0<={{(3*B){1'b0}},{{(B-5){s2[4]}},s2[4:0]},adjusted};")
start=s.index('   wire signed[B-9:0]upper=u[B-1:8];',s.index('begin:dsp_path'))
end=s.index('   wire signed[1:0]small_floor=',start)
s=s[:start]+'''   // floor(delta*r/256) is [-16,15]; the 128 bias vanishes mod 32.
   wire signed[4:0]low_floor=p[16*l+12-:5];
'''+s[end:]
s=s.replace('wire signed[B-1:0]answer=narrow_q?orig-small_floor:orig-hi-low_floor;', '''wire signed[4:0]narrow_orig=orig[4:0];
   wire signed[4:0]narrow_answer=narrow_orig-small_floor;
   wire signed[B-1:0]answer=narrow_q?narrow_answer:orig-low_floor;''')
old='''    else for(integer j=0;j<6;j=j+1)begin
     if(result_pos==j)u_out[j*B+:B]<=computed[0+:B];
     if(result_pos+1==j)u_out[j*B+:B]<=computed[B+:B];
     if(narrow_q&&result_pos+2==j)u_out[j*B+:B]<=computed[2*B+:B];
    end'''
new='''    else case(result_pos)
     0:begin u_out[0+:B]<=computed[0+:B];u_out[B+:B]<=computed[B+:B];
      if(narrow_q)u_out[2*B+:B]<=computed[2*B+:B];end
     2:begin u_out[2*B+:B]<=computed[0+:B];u_out[3*B+:B]<=computed[B+:B];end
     3:begin u_out[3*B+:B]<=computed[0+:B];u_out[4*B+:B]<=computed[B+:B];u_out[5*B+:B]<=computed[2*B+:B];end
     4:begin u_out[4*B+:B]<=computed[0+:B];u_out[5*B+:B]<=computed[B+:B];end
    endcase'''
assert old in s;s=s.replace(old,new)
s=s.replace('adaptive_delta_leak','adaptive_delta_compact').replace('delta_dsp','delta_compact_dsp').replace('top_delta_','top_delta_compact_')
(P/'adaptive_delta_compact.sv').write_text(s)
t=(P/'tb_adaptive_delta_leak.sv').read_text().replace('adaptive_delta_leak','adaptive_delta_compact')
(P/'tb_adaptive_delta_compact.sv').write_text(t)
for oldname,newname in [('check_adaptive_delta_leak.py','check_adaptive_delta_compact.py'),('route_adaptive_delta_leak.tcl','route_adaptive_delta_compact.tcl'),('run_adaptive_delta_route.py','run_adaptive_delta_compact_route.py')]:
 t=(P/oldname).read_text().replace('adaptive_delta_leak','adaptive_delta_compact').replace('adaptive_delta_', 'adaptive_delta_compact_')
 # The first substitution already changes the source name; undo double prefix.
 t=t.replace('adaptive_delta_compact_compact','adaptive_delta_compact')
 (P/newname).write_text(t)
print('Compact variant generated; first source unchanged',flush=True)
