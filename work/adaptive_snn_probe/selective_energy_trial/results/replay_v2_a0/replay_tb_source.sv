`timescale 1ns/1ps
`ifndef ROUTE_VARIANT
 `define ROUTE_VARIANT 2
`endif
// Replay native pre-rising pin rows through the frozen launch/capture fixture.
// No traffic decisions depend on delayed fixture ready. No timing checks waived.
module tb_selective_route_replay;
 reg clk=0;always #3 clk=~clk;
 reg rst=1,iv=0,orr=1;
 reg[65:0]u=0,i=0;reg[2:0]av=0;
 wire ir,ov,mode;wire[2:0]take,nout;wire[71:0]data;
 // The runner supplies DUT_TOP as the exported top name.
 `DUT_TOP dut(.clk(clk),.rst(rst),.in_valid(iv),.out_ready(orr),
  .u_in(u),.i_in(i),.available(av),.in_ready(ir),.out_valid(ov),
  .take(take),.out_count(nout),.out_data(data),.narrow_mode(mode));
 integer fd,status,rows,first,last,n=0,idx,running,done,rst0,iv0,orr0,av0;
 integer ir0,take0,ov0,nout0,mode0,corr0,advance0,busy0;
 reg[65:0]u0,i0;reg[71:0]data0;
 reg[80:0]expected[0:3];
 reg[3:0]known[0:3];
 integer indices[0:3];
 integer checked=0,valid_checked=0,roi_started=0,completed=0;
 string filename;
 task compare_row(input integer slot);
  reg[80:0]got;
  begin
   got={ir,take,ov,nout,data,mode};
   // Controls are always compared. Invalid data may be uninitialized in the
   // native trace; valid or known native data must match bit-exactly.
   if(got[80:76]!==expected[slot][80:76] || got[75:73]!==expected[slot][75:73] || got[0]!==expected[slot][0])
    $fatal(1,"REPLAY control mismatch V%0d row%0d got%h expected%h",`ROUTE_VARIANT,indices[slot],got,expected[slot]);
   if(known[slot][0] && got[72:1]!==expected[slot][72:1])
    $fatal(1,"REPLAY data mismatch V%0d row%0d got%h expected%h",`ROUTE_VARIANT,indices[slot],got,expected[slot]);
   checked=checked+1;if(expected[slot][76])valid_checked=valid_checked+1;
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
    status=$fscanf(fd,"%d %d %d %d %d %d %d %h %h %d %d %d %d %h %d %d %d %d\n",
     idx,running,done,rst0,iv0,orr0,av0,u0,i0,ir0,take0,ov0,nout0,data0,mode0,corr0,advance0,busy0);
    if(status!=18||idx!=n||done!=0)$fatal(1,"Bad native row%0d fields%0d",n,status);
    rst=rst0;iv=iv0;orr=orr0;av=av0;u=u0;i=i0;
    expected[n%4]={1'(ir0),3'(take0),1'(ov0),3'(nout0),data0,1'(mode0)};
    known[n%4][0]=!$isunknown(data0);indices[n%4]=n;
   end else begin rst=0;iv=0;orr=1;av=0;u=0;i=0;end
   if(n==first)begin
    roi_started=1;$display("REPLAY ROI_START V%0d TIME_NS %0.3f ROW %0d",`ROUTE_VARIANT,$realtime,n);
   end
   // Two falling-edge rows account for one input and one output register.
   #2.000;
   if(n>=2)compare_row((n-2)%4);
  end
  $fclose(fd);
  if(!roi_started||checked!=rows)$fatal(1,"Replay count mismatch");
  completed=1;
  $display("SELECTIVE_ROUTE_REPLAY PASS V%0d ROWS %0d CHECKED %0d VALID_ROWS %0d TIME_NS %0.3f",`ROUTE_VARIANT,rows,checked,valid_checked,$realtime);
  // Tcl closes SAIF after its declared interval; never terminate first.
 end
 initial begin #10000000;if(!completed)$fatal(1,"Replay timeout");end
endmodule
