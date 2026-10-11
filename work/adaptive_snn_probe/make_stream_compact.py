"""Isolated structural repairs and a matched fixed DSP/LUT hybrid baseline."""
from pathlib import Path
P=Path(__file__).resolve().parent
s=(P/'stream_offset_leak.sv').read_text()
def change(a,b):
 global s
 assert s.count(a)==1,a
 s=s.replace(a,b)
change('// E6: absolute-int5 adaptive triple only (isolates offset-policy cost).',
 '// E5: fixed DSP pair plus one exact LUT lane. E6: direct signed-int5 triple.')
change('wire always3=(E==3)||(E==4);','wire always3=(E==3)||(E==4)||(E==5);')
change('if(E==0||E==1||E==4||E==6)','if(E==0||E==1||E==4||E==5||E==6)')
change('assign a=narrow?an:aw;assign c=narrow?cn:cw;',
 '''wire[24:0]direct_a={u2[4:0],5'b0,{~u1[4],u1[3:0]},5'b0,{~u0[4],u0[3:0]}};
   wire[9:0]direct_k=10'd512-({5'b0,coef}<<4);
   wire[47:0]direct_c={28'b0,direct_k,direct_k};
   assign a=narrow?(E==6?direct_a:an):aw;
   assign c=narrow?(E==6?direct_c:cn):cw;''')
change("assign encoded=bypass?raw:(narrow?nmeta:{11'b0,wide_meta});",
 '''wire signed[16:0]hybrid_x={{6{u2[10]}},u2};
   (* use_dsp="no" *) wire signed[16:0]hybrid_product;
   if(DC==25)assign hybrid_product=(hybrid_x<<<4)+(hybrid_x<<<3)+hybrid_x;
   else assign hybrid_product=u2*dc;
   wire[10:0]hybrid_leak=u2-(hybrid_product>>>8);
   wire[32:0]direct_meta={18'b0,u2[4:0],u1[4:0],u0[4:0]};
   assign encoded=bypass?raw:(narrow?(E==6?direct_meta:nmeta):{E==5?hybrid_leak:11'b0,wide_meta});
   // Shared upper increment; each lane needs only its low five-bit carry.
   wire[5:0]upper=meta1[10:5],upper_next=upper+6'd1;''')
change('wire signed[10:0]narrow_answer=h+residual_leak;',
 '''wire[5:0]low_sum={1'b0,meta1[4:0]}+{1'b0,rem_leak};
    wire[10:0]shared_answer={low_sum[5]?upper_next:upper,low_sum[4:0]};
    wire signed[4:0]direct_u=meta1[5*l+:5];
    wire signed[1:0]direct_floor=l==2?prod[9:8]:{~prod[9],prod[8]};
    wire signed[4:0]direct_result=direct_u-direct_floor;
    wire signed[10:0]narrow_answer=E==6?{{6{direct_result[4]}},direct_result}:shared_answer;''')
change('end else assign decoded[22+:11]=n1?narrow_answer:0;',
 'end else assign decoded[22+:11]=n1?narrow_answer:(E==5?meta1[32:22]:0);')
s=s.replace('stream_offset_leak','stream_compact_leak').replace('stream_leak_dsp','stream_compact_dsp').replace('top_stream_','top_stream_compact_')
s+='\n`STREAM_TOP(top_stream_compact_hybrid_const,5,25)\n`STREAM_TOP(top_stream_compact_hybrid_prog,5,-1)\n`STREAM_TOP(top_stream_compact_absolute_prog,6,-1)\n'
(P/'stream_compact_leak.sv').write_text(s)
tb=(P/'tb_stream_offset_leak.sv').read_text().replace('stream_offset_leak','stream_compact_leak').replace('wire[5:0]done;','wire[6:0]done;')
tb=tb.replace('initial begin wait(&done);',"stream_driver #(.E(5))g(clk,done[6]);\n initial begin wait(&done);")
(P/'tb_stream_compact_leak.sv').write_text(tb)
c=(P/'check_stream_offset.py').read_text()
c=c.replace("stem='stream_offset_leak'if variant=='offset'else'stream_centered_leak'","stem='stream_compact_leak'")
c=c.replace('e in [3,4]','e in [3,4,5]').replace('[0,1,2,3,4,6]','[0,1,2,3,4,5,6]').replace("f'stream_offset_", "f'stream_compact_")
(P/'check_stream_compact.py').write_text(c)
models=(P/'check_stream_offset_models.py').read_text().replace('from check_stream_offset import simulate','from check_stream_compact import simulate')
models=models.replace("tag=f'stream_{variant}_models'","tag='stream_compact_models'").replace("f'stream_{variant}_stress'","'stream_compact_stress'")
(P/'check_stream_compact_models.py').write_text(models)
t=(P/'route_stream_offset.tcl').read_text().replace('stream_offset_leak.sv','stream_compact_leak.sv')
(P/'route_stream_compact.tcl').write_text(t)
runner=(P/'run_stream_offset_route.py').read_text().replace('stream_offset_leak.sv','stream_compact_leak.sv').replace('stream_offset_main_25_0_checks.json','stream_compact_main_25_0_checks.json').replace('stream_offset_hardware.json','stream_compact_hardware.json').replace('route_stream_offset.tcl','route_stream_compact.tcl')
(P/'run_stream_compact_route.py').write_text(runner)
print('Created compact/shared-carry variants and fixed DSP/LUT hybrid; original preserved')
