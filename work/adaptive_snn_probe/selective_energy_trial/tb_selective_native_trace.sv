`timescale 1ns/1ps
// Capture the unmodified native PROFILE1/STAll0 driver at a 6ns clock.
// Each row describes signals immediately before its next rising edge.
// Eighteen whitespace-separated columns, with no header:
// idx running done rst iv out_ready available Uhex17 Ihex17 in_ready take
// out_valid out_count out_datahex18 mode correction advance busy.
// Row0 samples at6.020ns; each subsequent row is6ns later. Each driver's
// final row precedes its final retirement; no post-done rows are written.
module tb_selective_native_trace;
 reg clk=0;always #3 clk=~clk;
 wire[1:0]done;
 reg[1:0]trace_closed=0;
 integer trace0,trace1,index0=0,index1=0;
 guard_add_selective_driver #(.V(0))fixed_driver(clk,done[0]);
 guard_add_selective_driver #(.V(1))adaptive_driver(clk,done[1]);
 initial begin
  if(`PROFILE!=1||`STALL!=0)$fatal(1,"Native trace requires PROFILE1 STALL0");
  trace0=$fopen("native_trace0.txt","w");
  trace1=$fopen("native_trace1.txt","w");
  if(!trace0||!trace1)$fatal(1,"Cannot open native trace files");
 end
 always @(negedge clk)begin
  // The frozen driver changes source controls on this falling edge. Capture
  // after those settle, and long before the next rising edge at+3ns.
  #0.020;
  if(!trace_closed[0])begin
   if(done[0])begin $fclose(trace0);trace_closed[0]=1'b1;end
   else begin
    $fwrite(trace0,"%0d %0d %0d %0d %0d %0d %0d %017h %017h %0d %0d %0d %0d %018h %0d %0d %0d %0d\n",
     index0,fixed_driver.running,fixed_driver.done,fixed_driver.rst,
     fixed_driver.iv,fixed_driver.orr,fixed_driver.av,fixed_driver.raw_u,fixed_driver.raw_i,
     fixed_driver.ir,fixed_driver.take,fixed_driver.ov,fixed_driver.nout,fixed_driver.answer,
     fixed_driver.mode,fixed_driver.correction_signal,fixed_driver.advance_signal,fixed_driver.busy_signal);
    index0=index0+1;
   end
  end
  if(!trace_closed[1])begin
   if(done[1])begin $fclose(trace1);trace_closed[1]=1'b1;end
   else begin
    $fwrite(trace1,"%0d %0d %0d %0d %0d %0d %0d %017h %017h %0d %0d %0d %0d %018h %0d %0d %0d %0d\n",
     index1,adaptive_driver.running,adaptive_driver.done,adaptive_driver.rst,
     adaptive_driver.iv,adaptive_driver.orr,adaptive_driver.av,adaptive_driver.raw_u,adaptive_driver.raw_i,
     adaptive_driver.ir,adaptive_driver.take,adaptive_driver.ov,adaptive_driver.nout,adaptive_driver.answer,
     adaptive_driver.mode,adaptive_driver.correction_signal,adaptive_driver.advance_signal,adaptive_driver.busy_signal);
    index1=index1+1;
   end
  end
 end
 initial begin
  wait(&done);
  // Drivers set done on a rising edge. Let the next falling-edge capture
  // close both files before termination, so Tcl can finish activity output.
  wait(&trace_closed);
  $display("SELECTIVE_NATIVE_TRACE PASS ROWS0 %0d ROWS1 %0d",index0,index1);
  $finish;
 end
endmodule
