"""Preserve the first prototype; create a simpler monitor and shared high helper."""
from pathlib import Path
P=Path(__file__).resolve().parent
s=(P/'stream_offset_leak.sv').read_text()
def change(a,b):
 global s
 assert s.count(a)==1,a;s=s.replace(a,b)
change('// E0: absolute-int5 OR equal-upper-bits shared offset, else fixed wide pair.',
 '// E0: equal centered-bin high parts, one shared exact correction; else wide pair.')
change('wire coherent=(u0[10:5]==u1[10:5])&&(u0[10:5]==u2[10:5]);',
 '''wire signed[6:0]ch0=$signed({u0[10],u0[10:5]})+$signed({6'b0,u0[4]});
 wire signed[6:0]ch1=$signed({u1[10],u1[10:5]})+$signed({6'b0,u1[4]});
 wire signed[6:0]ch2=$signed({u2[10],u2[10:5]})+$signed({6'b0,u2[4]});
 wire coherent=(ch0==ch1)&&(ch0==ch2);''')
change('(E==0&&(absfit||coherent))','(E==0&&coherent)')
change('wire signed[6:0]bh=base[10:4];',
 '''wire signed[6:0]bh=E==0?ch0:$signed(base[10:4]);
  wire signed[3:0]wide_h0=$signed({u0[10],u0[10:8]})+$signed({3'b0,u0[7]});
  wire signed[6:0]multiply_high=(E==0&&!narrow)?$signed({{3{wide_h0[3]}},wide_h0}):bh;''')
change('wire signed[12:0]bx={{6{bh[6]}},bh};','wire signed[12:0]bx={{6{multiply_high[6]}},multiply_high};')
change('else assign z=bh*dc;','else assign z=multiply_high*dc;')
change('wire signed[10:0]base_leak=base-(z>>>4);',
 'wire signed[10:0]base_leak=E==0?((bx<<<5)-(z>>>3)):(base-(z>>>4));')
change("wire[32:0]nmeta={3'b0,res2,res1,res0,z[3:0],base_leak};",
 "wire[32:0]nmeta=E==0?{4'b0,u2[4:0],u1[4:0],u0[4:0],z[2:0],base_leak}:{3'b0,res2,res1,res0,z[3:0],base_leak};")
change('(* use_dsp="no" *) wire signed[7:0]hp=h*dc;',
 '''(* use_dsp="no" *) wire signed[7:0]hp;
   if(E==0&&l==0)assign hp=z[7:0];else assign hp=h*dc;''')
change('assign a=narrow?an:aw;assign c=narrow?cn:cw;',
 '''wire[24:0]center_a={u2[4:0],5'b0,{~u1[4],u1[3:0]},5'b0,{~u0[4],u0[3:0]}};
   wire[9:0]center_k=10'd512-({5'b0,coef}<<4);
   wire[47:0]center_c={28'b0,center_k,center_k};
   assign a=narrow?(E==0?center_a:an):aw;assign c=narrow?(E==0?center_c:cn):cw;''')
change('wire signed[10:0]residual_leak={6\'b0,rem_leak};',
 '''wire signed[4:0]sr=meta1[14+5*l+:5];
    wire signed[1:0]sf=l==2?prod[9:8]:{~prod[9],prod[8]};
    wire[3:0]scarry={1'b0,prod[7:5]}+{1'b0,meta1[13:11]};
    wire signed[4:0]srem=sr-sf-$signed({4'b0,scarry[3]});
    wire signed[10:0]residual_leak=E==0?{{6{srem[4]}},srem}:{6'b0,rem_leak};''')
s=s.replace('stream_offset_leak','stream_centered_leak').replace('stream_leak_dsp','stream_centered_dsp').replace('top_stream_','top_stream_centered_')
(P/'stream_centered_leak.sv').write_text(s)
tb=(P/'tb_stream_offset_leak.sv').read_text().replace('stream_offset_leak','stream_centered_leak')
(P/'tb_stream_centered_leak.sv').write_text(tb)
tcl=(P/'route_stream_offset.tcl').read_text().replace('stream_offset_leak.sv','stream_centered_leak.sv')
(P/'route_stream_centered.tcl').write_text(tcl)
runner=(P/'run_stream_offset_route.py').read_text().replace('stream_offset_leak.sv','stream_centered_leak.sv').replace('stream_offset_main_25_0_checks.json','stream_centered_main_25_0_checks.json').replace('stream_offset_hardware.json','stream_centered_hardware.json').replace('route_stream_offset.tcl','route_stream_centered.tcl')
(P/'run_stream_centered_route.py').write_text(runner)
print('Created isolated centered prototype; original sources preserved')
