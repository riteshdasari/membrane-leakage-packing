"""Isolated signed16 fallback, unchanged E0..E5 logic and shift-only control."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
TRIAL=HERE.parent.parent/'sequential_paper_trial'
HERE.mkdir(parents=True,exist_ok=True)
assert not(HERE/'preparation.json').exists()
original=(TRIAL/'leak_core.sv').read_text()
core=original.replace('signed12 U','signed16 U').replace('module sequential_leak #','module sequential_leak16 #').replace('E=0,B=12','E=0,B=16')
marker=' end else begin:two_scalar'
assert core.count(marker)==1
shift=''' end else if(E==6)begin:shift128
  // Declared model-specific beta128 control: ceil(U/2), all signed16 values.
  // beta input is irrelevant to its arithmetic; caller must supply beta128.
  for(genvar l=0;l<2;l=l+1)begin:lane
   wire signed[B-1:0]u=u_q[l*B+:B];
   (* use_dsp="no" *)wire signed[B-1:0]half=u>>>1;
   (* use_dsp="no" *)wire signed[B-1:0]rounded_half=half+{{(B-1){1'b0}},u[0]};
   reg[B-1:0]r=0;
   always @(posedge clk)if(rst)r<=0;else if(issue)r<=count1>l?rounded_half:{B{1'b0}};
   assign answer[l*B+:B]=r;
  end
 end else begin:two_scalar'''
core=core.replace(marker,shift)
core=core.replace('// E4 scalarDSP1, E5 membrane9/modulo2 post-correction reference.','// E4 scalarDSP1, E5 membrane9/modulo2 post-correction reference.\n// E6 model-specific exact shift2 control, legal only for beta128.')
old_lut=original[original.index(' end else if(E==2)begin:lut'):original.index(marker)]
new_lut=core[core.index(' end else if(E==2)begin:lut'):core.index(' end else if(E==6)begin:shift128')]
assert old_lut==new_lut,'Do not independently change LUT arithmetic.'
(HERE/'leak_core16.sv').write_text(core,encoding='utf-8')
dsp=(TRIAL/'leak_dsp.sv').read_text();(HERE/'leak_dsp.sv').write_text(dsp,encoding='utf-8')
timing=(TRIAL/'timing.sv').read_text().replace('sequential_leak','sequential_leak16')
timing=timing.replace('[23:0]','[31:0]').replace('47 launch FFs and 31 capture FFs = 78 fixture FFs','55 launch FFs and 39 capture FFs = 94 fixture FFs')
timing=timing.replace('sequential_leak16 #(.E(E))core','sequential_leak16 #(.E(E),.B(16))core')
timing=timing.replace('`undef GUARD_ADD_FRONTIER_TOP','`GUARD_ADD_FRONTIER_TOP(top_sequential_leak16_e6,6)\n`undef GUARD_ADD_FRONTIER_TOP')
(HERE/'timing16.sv').write_text(timing,encoding='utf-8')
route=(TRIAL/'route.tcl').read_text().replace('top_sequential_leak_e[0-5]','top_sequential_leak16_e[0-6]')
route=route.replace('$target != 6.0','$target ni {6 6.0 9 9.0 12 12.0}').replace('$here/leak_core.sv','$here/leak_core16.sv').replace('$here/timing.sv','$here/timing16.sv')
route=route.replace('!= 47','!= 55').replace('!= 31','!= 39').replace('expected 47/31','expected 55/39')
route=route.replace('set_input_delay -clock clk -max 1.0','set_input_delay -clock clk -max [expr {$target/2.0}]')
route=route.replace('set_input_delay -clock clk -min 0.1','set_input_delay -clock clk -min [expr {$target/2.0}]')
route=route.replace('a declared 1 ns setup / 0.1 ns minimum budget','a declared falling-edge phase target/2 for min/max input delay')
(HERE/'route16.tcl').write_text(route,encoding='utf-8')
tb=(TRIAL/'tb_native_v3.sv').read_text()
tb=tb.replace('module tb_sequential_leak;','''`ifndef SHIFT_COHORT
`define SHIFT_COHORT 0
`endif
module tb_sequential_leak16;
 localparam integer ENGINES=`SHIFT_COHORT?7:6;''')
tb=tb.replace('[5:0]iv','[ENGINES-1:0]iv').replace('[0:5]','[0:ENGINES-1]').replace('[23:0]','[31:0]')
tb=tb.replace('g<6','g<ENGINES').replace('e<6','e<ENGINES').replace('completed==6','completed==ENGINES')
tb=tb.replace('sequential_leak #(.E(g))','sequential_leak16 #(.E(g),.B(16))')
tb=tb.replace('values[i]<-2048||values[i]>2047','values[i]<-32768||values[i]>32767')
tb=tb.replace('  end\n  $fclose(fd);','   if(`SHIFT_COHORT&&coefs[i]!=128)$fatal(1,"Shift cohort requires beta128 at row%0d",i);\n  end\n  $fclose(fd);',1)
tb=tb.replace('[0+:12]','[0+:16]').replace('[12+:12]','[16+:16]')
tb=tb.replace('&4095','&65535').replace('<<12','<<16').replace('expected[23:0]','expected[31:0]').replace('%06h','%08h')
(HERE/'tb_native16.sv').write_text(tb,encoding='utf-8')
for ns in (9,12):
    replay=(TRIAL/f'tb_energy{ns}.sv').read_text().replace('[23:0]','[31:0]').replace('[30:0]','[38:0]').replace('[27]','[35]')
    replay=replay.replace('tb_sequential_energy_replay','tb_sequential_energy_replay16')
    (HERE/f'tb_energy16_{ns}.sv').write_text(replay,encoding='utf-8')
inputs=[Path(__file__),TRIAL/'leak_core.sv',TRIAL/'leak_dsp.sv',TRIAL/'timing.sv',TRIAL/'route.tcl',TRIAL/'tb_native_v3.sv',TRIAL/'tb_energy9.sv',TRIAL/'tb_energy12.sv']
outputs=[HERE/n for n in('leak_core16.sv','leak_dsp.sv','timing16.sv','route16.tcl','tb_native16.sv','tb_energy16_9.sv','tb_energy16_12.sv')]
pins=lambda ps:{str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in ps}
answer=dict(status='prepared_uncompiled_unrouted',B=16,full_U_domain=[-32768,32767],narrow_U_domain=[-256,255],
    coefficient_domain=[0,256],shift_control=dict(engine=6,legal_coefficient=128,arithmetic='(signedU>>>1)+(U&1)',DSP=0),
    fixture_FF=94,launch_FF=55,capture_FF=39,expected_DSP_by_engine=[1,1,0,2,1,1,0],
    LUT_E2_arithmetic_block_identical_to_frozen_original=True,source_sha256=pins(inputs),artifact_sha256=pins(outputs),
    compile_options=dict(native_general='xvlog -sv -d STALL=0 -d CAPTURE=1 -d SHIFT_COHORT=0 leak_core16.sv leak_dsp.sv tb_native16.sv; xelab -mt off -debug typical -L unisims_ver tb_sequential_leak16 glbl',
                         native_model128='same with SHIFT_COHORT=1; input stim.txt beta must all be128',
                         route='vivado -mode batch -source route16.tcl -tclargs top_sequential_leak16_eN 6.0|9.0|12.0 SOURCEHASH fresh ATTEMPT_DIR',
                         delayed_replay='tb_energy16_9.sv or tb_energy16_12.sv, top tb_sequential_energy_replay16, DUT_TOP=top_sequential_leak16_eN, ENGINE_ID=N; native traces use8hexU/data'),
    exclusions='No Vivado compile, timing, RTL exactness, area or power result yet; E6 is beta128-only baseline, not a general coefficient multiplier')
(HERE/'preparation.json').write_text(json.dumps(answer,indent=2)+'\n')
print(json.dumps(answer,indent=2),flush=True)
