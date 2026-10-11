`timescale 1ns/1ps
`ifndef ENGINE_ID
 `define ENGINE_ID 2
`endif
// Replay native pre-rising pin rows through the frozen launch/capture fixture.
// No traffic decisions depend on delayed fixture ready. No timing checks waived.
module tb_sequential_energy_replay16;
 reg clk=0;initial begin #12;forever #6 clk=~clk;end
 reg rst=1,iv=0,orr=1;
 reg[31:0]u=0;reg[17:0]beta=0;reg[1:0]av=0;
 wire ir,ov,mode;wire[1:0]take,nout;wire[31:0]data;
 // The runner supplies DUT_TOP as the exported top name.
 `DUT_TOP dut(.clk(clk),.rst(rst),.in_valid(iv),.out_ready(orr),
  .u_in(u),.beta_in(beta),.available(av),.in_ready(ir),.out_valid(ov),
  .take(take),.out_count(nout),.out_data(data),.narrow_mode(mode));
 integer fd,status,rows,first,last,n=0,idx,running,done,rst0,iv0,orr0,av0;
 integer ir0,take0,ov0,nout0,mode0,corr0,advance0,busy0;
 reg[31:0]u0;reg[17:0]beta0;reg[31:0]data0;
 reg[38:0]expected[0:3];
 reg[3:0]known[0:3];
 integer indices[0:3];
 integer checked=0,valid_checked=0,roi_started=0,completed=0;
 string filename;
 task compare_row(input integer slot);
  reg[38:0]got;
  begin
   got={ir,take,ov,nout,data,mode};
   // Controls are always compared. Invalid data may be uninitialized in the
   // native trace; valid or known native data must match bit-exactly.
   if(got!==expected[slot])
    $fatal(1,"REPLAY mismatch E%0d row%0d got%h expected%h",`ENGINE_ID,indices[slot],got,expected[slot]);
   checked=checked+1;if(expected[slot][35])valid_checked=valid_checked+1;
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

 // Observation only. Original DUT, SDF, comparison and complete input stream
 // remain unchanged; no force/release, altered clock or acceptance bypass.
 wire[3:0] probe_s=dut.fixture.core.\lut.lane[0].r_reg[15]_i_4 .S;
 wire[3:0] probe_di=dut.fixture.core.\lut.lane[0].r_reg[15]_i_4 .DI;
 wire probe_ci=dut.fixture.core.\lut.lane[0].r_reg[15]_i_4 .CI;
 wire probe_cy=dut.fixture.core.\lut.lane[0].r_reg[15]_i_4 .CYINIT;
 wire[3:0] probe_si=dut.fixture.core.\lut.lane[0].r_reg[15]_i_4 .S_in;
 wire[3:0] probe_dii=dut.fixture.core.\lut.lane[0].r_reg[15]_i_4 .DI_in;
 wire probe_cii=dut.fixture.core.\lut.lane[0].r_reg[15]_i_4 .CI_in;
 wire probe_cyi=dut.fixture.core.\lut.lane[0].r_reg[15]_i_4 .CYINIT_in;
 wire[3:0] probe_co=dut.fixture.core.\lut.lane[0].r_reg[15]_i_4 .CO;
 wire[3:0] probe_fb=dut.fixture.core.\lut.lane[0].r_reg[15]_i_4 .CO_fb;
 wire[3:0] probe_o=dut.fixture.core.\lut.lane[0].r_reg[15]_i_4 .O;
 wire[2:0] probe_parent_o=dut.fixture.core.p_0_in[23:21];
 wire probe_upstream_ci=dut.fixture.core.\lut.lane[0].r_reg[12]_i_2_n_0 ;
 wire probe_d14=dut.fixture.core.\lut.lane[0].r_reg[14] .D;
 wire probe_q14=dut.fixture.core.\lut.lane[0].r_reg[14] .Q;
 wire probe_c14=dut.fixture.core.\lut.lane[0].r_reg[14] .C;
 wire probe_ce14=dut.fixture.core.\lut.lane[0].r_reg[14] .CE;
 realtime probe_last_input=0;
 always @(probe_si or probe_dii or probe_cii or probe_cyi or probe_fb)
   probe_last_input=$realtime;
 task automatic probe_snapshot(input string label_name);
   reg[3:0] expected_o,expected_co;
   reg carry;
   begin
     carry=probe_cii|probe_cyi;
     for(integer k=0;k<4;k=k+1)begin
       expected_o[k]=probe_si[k]^carry;
       expected_co[k]=probe_si[k]?carry:probe_dii[k];
       carry=expected_co[k];
     end
     $display("FIXED16_SNAPSHOT %s T%0.3f ROW%0d AGE%0.3f S%h DI%h CI%b CY%b SI%h DII%h CII%b CYI%b CO%h FB%h O%h PARENT_O%h UPSTREAM_CI%b EXPECT_O%h EXPECT_CO%h D14%b Q14%b CLK%b CE%b",
       label_name,$realtime,n,$realtime-probe_last_input,probe_s,probe_di,probe_ci,probe_cy,
       probe_si,probe_dii,probe_cii,probe_cyi,probe_co,probe_fb,probe_o,probe_parent_o,
       probe_upstream_ci,expected_o,expected_co,probe_d14,probe_q14,probe_c14,probe_ce14);
   end
 endtask
 task automatic probe_event(input string signal_name,input integer bit_number,input reg value);
   if(n>=2172&&n<=2177)
     $display("FIXED16_EVENT T%0.3f ROW%0d SIGNAL%s BIT%0d VALUE%b",$realtime,n,signal_name,bit_number,value);
 endtask
 always @(probe_ci)probe_event("CI_port",0,probe_ci);
 always @(probe_cii)probe_event("CI_in",0,probe_cii);
 always @(probe_upstream_ci)probe_event("CI_upstream",0,probe_upstream_ci);
 always @(probe_cy)probe_event("CY_port",0,probe_cy);
 always @(probe_d14)probe_event("D14",0,probe_d14);
 always @(probe_q14)probe_event("Q14",0,probe_q14);
 generate for(genvar k=0;k<4;k=k+1)begin:probe_bits
   always @(probe_s[k])probe_event("S_port",k,probe_s[k]);
   always @(probe_si[k])probe_event("S_in",k,probe_si[k]);
   always @(probe_di[k])probe_event("DI_port",k,probe_di[k]);
   always @(probe_dii[k])probe_event("DI_in",k,probe_dii[k]);
   always @(probe_co[k])probe_event("CO",k,probe_co[k]);
   always @(probe_fb[k])probe_event("CO_fb",k,probe_fb[k]);
   always @(probe_o[k])probe_event("O",k,probe_o[k]);
 end endgenerate
 // Fixed known-row window includes settled inputs immediately before each
 // potential affected core capture and the first retained mismatch at2175.
 always @(posedge probe_c14)if(n>=2172&&n<=2177)begin
   #0.001;probe_snapshot("capture_plus1ps");
   #0.999;probe_snapshot("capture_plus1ns");
 end
 always @(negedge probe_c14)if(n>=2172&&n<=2177)begin
   #0.001;probe_snapshot("halfcycle_plus1ps");
 end
 initial begin
   #26208.000;probe_snapshot("window_begin");
   #29.999;probe_snapshot("before26238_capture");
   #0.002;probe_snapshot("after26238_capture");
   #11.998;probe_snapshot("before26250_capture");
   #0.002;probe_snapshot("after26250_capture");
   $display("FIXED16_PROBE_WINDOW_COMPLETE");
 end

endmodule
