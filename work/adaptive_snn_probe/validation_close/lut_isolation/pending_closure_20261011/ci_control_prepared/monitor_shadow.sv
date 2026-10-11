`timescale 1ns/1ps
`ifndef ENGINE_ID
 `define ENGINE_ID 2
`endif
// Replay native pre-rising pin rows through the frozen launch/capture fixture.
// No traffic decisions depend on delayed fixture ready. No timing checks waived.
module tb_sequential_energy_replay;
 reg clk=0;initial begin #12;forever #6 clk=~clk;end
 reg rst=1,iv=0,orr=1;
 reg[23:0]u=0;reg[17:0]beta=0;reg[1:0]av=0;
 wire ir,ov,mode;wire[1:0]take,nout;wire[23:0]data;
 // The runner supplies DUT_TOP as the exported top name.
 `DUT_TOP dut(.clk(clk),.rst(rst),.in_valid(iv),.out_ready(orr),
  .u_in(u),.beta_in(beta),.available(av),.in_ready(ir),.out_valid(ov),
  .take(take),.out_count(nout),.out_data(data),.narrow_mode(mode));
 integer fd,status,rows,first,last,n=0,idx,running,done,rst0,iv0,orr0,av0;
 integer ir0,take0,ov0,nout0,mode0,corr0,advance0,busy0;
 reg[23:0]u0;reg[17:0]beta0;reg[23:0]data0;
 reg[30:0]expected[0:3];
 reg[3:0]known[0:3];
 integer indices[0:3];
 integer checked=0,valid_checked=0,roi_started=0,completed=0;
 string filename;
 task compare_row(input integer slot);
  reg[30:0]got;
  begin
   got={ir,take,ov,nout,data,mode};
   // Controls are always compared. Invalid data may be uninitialized in the
   // native trace; valid or known native data must match bit-exactly.
   if(got!==expected[slot])
    $fatal(1,"REPLAY mismatch E%0d row%0d got%h expected%h",`ENGINE_ID,indices[slot],got,expected[slot]);
   checked=checked+1;if(expected[slot][27])valid_checked=valid_checked+1;
  end
 endtask
 initial begin
  for(integer k=0;k<4;k=k+1)begin known[k]=0;indices[k]=-1;expected[k]=0;end
  if(!$value$plusargs("TRACE=%s",filename)||!$value$plusargs("ROWS=%d",rows)||
     !$value$plusargs("ROI_FIRST=%d",first)||!$value$plusargs("ROI_LAST=%d",last))$fatal(1,"Replay arguments missing");
  fd=$fopen(filename,"r");if(!fd)$fatal(1,"Cannot open native trace");
  // Let installed GSR finish, then retain the entire native reset prelude.
  #121;
  for(n=0;n<rows+2;n=n+1)begin
   @(negedge clk);
   if(n<rows)begin
    status=$fscanf(fd,"%d %d %d %d %d %h %h %d %d %d %d %h %d %d %d\n",
     idx,rst0,iv0,orr0,av0,u0,beta0,ir0,take0,ov0,nout0,data0,mode0,corr0,busy0);
    if(status!=15||idx!=n||$isunknown(data0))$fatal(1,"Bad native row%0d fields%0d",n,status);
    rst=rst0;iv=iv0;orr=orr0;av=av0;u=u0;beta=beta0;
    expected[n%4]={1'(ir0),2'(take0),1'(ov0),2'(nout0),data0,1'(mode0)};
    known[n%4][0]=1;indices[n%4]=n;
   end else begin rst=0;iv=0;orr=1;av=0;u=0;beta=0;end
   if(n==first)begin
    roi_started=1;$display("REPLAY ROI_START V%0d TIME_NS %0.3f ROW %0d",`ENGINE_ID,$realtime,n);
   end
   // Two falling-edge rows account for one input and one output register.
   #2.000;
   if(n>=2)compare_row((n-2)%4);
  end
  $fclose(fd);
  if(!roi_started||checked!=rows)$fatal(1,"Replay count mismatch");
  completed=1;
  $display("FRONTIER_ROUTE_REPLAY PASS E%0d ROWS %0d CHECKED %0d VALID_ROWS %0d TIME_NS %0.3f",`ENGINE_ID,rows,checked,valid_checked,$realtime);
  // Tcl closes SAIF after its declared interval; never terminate first.
 end
 initial begin #10000000;if(!completed)$fatal(1,"Replay timeout");end

 wire[3:0]ds=dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .S;
 wire[3:0]di=dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .DI;
 wire ci=dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CI;
 wire[3:0]co=dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CO;
 wire[3:0]doo=dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .O;
 wire rd=dut.fixture.core.\lut.lane[0].r_reg[9] .D;
 wire rq=dut.fixture.core.\lut.lane[0].r_reg[9] .Q;
 wire rc=dut.fixture.core.\lut.lane[0].r_reg[9] .C;
 wire re=dut.fixture.core.\lut.lane[0].r_reg[9] .CE;
 wire[19:0]product=dut.fixture.core.\lut.lane[0].product ;
 always @(ds or di or ci or co or doo or rd or rq or rc or re or product)
  if(n>=910&&n<=916)$display("DBG T%0.3f ROW%0d S%h DI%h CI%b CO%h O%h D%b Q%b CLK%b CE%b PRODUCT%h",$realtime,n,ds,di,ci,co,doo,rd,rq,rc,re,product);


 wire cii=dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CI_in;
 wire cyi=dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CYINIT_in;
 wire[3:0] sii=dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .S_in;
 wire[3:0] dii=dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .DI_in;
 wire[3:0] fbi=dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CO_fb;
 wire[3:0] truth_o=sii^fbi;
 wire[3:0] truth_co=(sii&fbi)|(~sii&dii);
 always @(ds or di or ci or doo or co or cii or cyi or sii or dii or fbi or truth_o or truth_co)
   if(n>=913&&n<=915)
     $strobe("INTERNAL T%0.3f ROW%0d PORT_S%h PORT_DI%h PORT_CI%b CI_IN%b CY_IN%b S_IN%h DI_IN%h CO_FB%h CO%h O%h TRUTH_O%h TRUTH_CO%h",$realtime,n,ds,di,ci,cii,cyi,sii,dii,fbi,co,doo,truth_o,truth_co);
 always @(posedge rc)
   if(n>=913&&n<=915)
     $strobe("EDGE T%0.3f ROW%0d CI_IN%b S_IN%h CO_FB%h O%h TRUTH_O%h D%b Q%b",$realtime,n,cii,sii,fbi,doo,truth_o,rd,rq);


 // Diagnostic addition only: the routed DUT, replay and original model are unchanged.
 // Direct hierarchical port connections retain the live waveform, without
 // reconstructing same-timestamp #0 ordering from the earlier text dump.
 wire[3:0] shadow_co,shadow_o;
 CARRY4 shadow(.CI(dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CI),.CYINIT(dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CYINIT),
   .DI(dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .DI),.S(dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .S),.CO(shadow_co),.O(shadow_o));
 reg[3:0] canary_s=0;
 wire[3:0] canary_co,canary_o;
 CARRY4 canary(.CI(1'b0),.CYINIT(1'b0),.DI(4'b0),.S(canary_s),
   .CO(canary_co),.O(canary_o));
 initial begin
   #200.000; canary_s=1;
   #0.050;
   if(canary_o!==4'h0 || canary_co!==4'h0)$fatal(1,"CAUSAL_CANARY_FAIL before50ps O%h CO%h",canary_o,canary_co);
   #0.550;
   if(canary_o!==4'h1 || canary_co!==4'h0)$fatal(1,"CAUSAL_CANARY_FAIL after600ps O%h CO%h",canary_o,canary_co);
   $display("CAUSAL_CANARY_PASS POSITIVE50PS_SETTLED600PS checks2");
 end
 integer observed_event_sequence=0;
 realtime original_last=0,shadow_last=0;
 task automatic event_line(input string scope_name,input string signal_name,
                           input integer bit_index,input reg value);
   if($realtime>=11098.000 && $realtime<=11106.100)begin
     observed_event_sequence=observed_event_sequence+1;
     $display("CAUSAL_EVENT SEQ%0d T%0.3f ROW%0d SCOPE%s SIGNAL%s BIT%0d VALUE%b",
       observed_event_sequence,$realtime,n,scope_name,signal_name,bit_index,value);
   end
 endtask
 always @(dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .S_in or dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .DI_in or dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CI_in or dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CYINIT_in or dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CO_fb)
   original_last=$realtime;
 always @(shadow.S_in or shadow.DI_in or shadow.CI_in or shadow.CYINIT_in or shadow.CO_fb)
   shadow_last=$realtime;
 always @(dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CI)event_line("original","CI_port",0,dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CI);
 always @(dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CYINIT)event_line("original","CYINIT_port",0,dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CYINIT);
 always @(dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CI_in)event_line("original","CI_in",0,dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CI_in);
 always @(shadow.CI)event_line("shadow","CI_port",0,shadow.CI);
 always @(shadow.CYINIT)event_line("shadow","CYINIT_port",0,shadow.CYINIT);
 always @(shadow.CI_in)event_line("shadow","CI_in",0,shadow.CI_in);
 generate for(genvar bit_number=0;bit_number<4;bit_number=bit_number+1)begin:causal_bits
   always @(dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .S[bit_number])event_line("original","S_port",bit_number,dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .S[bit_number]);
   always @(dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .S_in[bit_number])event_line("original","S_in",bit_number,dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .S_in[bit_number]);
   always @(dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .DI[bit_number])event_line("original","DI_port",bit_number,dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .DI[bit_number]);
   always @(dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CO[bit_number])event_line("original","CO",bit_number,dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CO[bit_number]);
   always @(dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CO_fb[bit_number])event_line("original","CO_fb",bit_number,dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CO_fb[bit_number]);
   always @(dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .O[bit_number])event_line("original","O",bit_number,dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .O[bit_number]);
   always @(shadow.S[bit_number])event_line("shadow","S_port",bit_number,shadow.S[bit_number]);
   always @(shadow.S_in[bit_number])event_line("shadow","S_in",bit_number,shadow.S_in[bit_number]);
   always @(shadow.DI[bit_number])event_line("shadow","DI_port",bit_number,shadow.DI[bit_number]);
   always @(shadow.CO[bit_number])event_line("shadow","CO",bit_number,shadow.CO[bit_number]);
   always @(shadow.CO_fb[bit_number])event_line("shadow","CO_fb",bit_number,shadow.CO_fb[bit_number]);
   always @(shadow.O[bit_number])event_line("shadow","O",bit_number,shadow.O[bit_number]);
 end endgenerate
 task automatic snapshot(input string label_name);
   reg[3:0] expected_o,expected_co;
   reg carry;
   begin
     carry=dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CI_in|dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CYINIT_in;
     for(integer bit_number=0;bit_number<4;bit_number=bit_number+1)begin
       expected_o[bit_number]=dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .S_in[bit_number]^carry;
       expected_co[bit_number]=dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .S_in[bit_number]?carry:dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .DI_in[bit_number];
       carry=expected_co[bit_number];
     end
     $display("CAUSAL_SNAPSHOT %s T%0.3f ROW%0d ORIG_AGE%0.3f SHADOW_AGE%0.3f ORIG_S%h SHADOW_S%h ORIG_CI%b SHADOW_CI%b ORIG_DI%h SHADOW_DI%h ORIG_CO%h SHADOW_CO%h ORIG_FB%h SHADOW_FB%h ORIG_O%h SHADOW_O%h EXPECT_O%h EXPECT_CO%h D%b Q%b",
       label_name,$realtime,n,$realtime-original_last,$realtime-shadow_last,
       dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .S_in,shadow.S_in,dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CI_in,shadow.CI_in,dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .DI_in,shadow.DI_in,
       dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CO,shadow.CO,dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CO_fb,shadow.CO_fb,dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .O,shadow.O,
       expected_o,expected_co,rd,rq);
   end
 endtask
 initial begin
   #11100.500; snapshot("after_last_glitch");
   #0.500; snapshot("plus500ps");
   #4.999; snapshot("before_capture");
   #0.002; snapshot("after_capture");
   $display("CAUSAL_PROBE_SNAPSHOTS_COMPLETE");
 end
 always @(posedge rc)if(n>=913&&n<=915)begin
   #0.001; snapshot("capture_edge_plus1ps");
 end


 // Bounded causal intervention only. This is never hardware/energy evidence.
 initial begin
   if($test$plusargs("MASK_CI"))begin
     #11098.000;
     $display("CI_INTERVENTION_BEGIN T%0.3f PRE_CI%b",$realtime,dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CI);
     force dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CI=1'b0;
     #9.000;
     release dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CI;
     $display("CI_INTERVENTION_END T%0.3f CI%b",$realtime,dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CI);
   end
 end

endmodule
