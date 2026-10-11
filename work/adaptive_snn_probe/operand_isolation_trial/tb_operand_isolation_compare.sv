`timescale 1ns/1ps
`ifndef ISOLATE_POLICY
 `define ISOLATE_POLICY 1
`endif
`ifndef CAPTURE_TRACE
 `define CAPTURE_TRACE 0
`endif
// The frozen PROFILE1/V1 driver schedules the reference V3. Its complete
// inputs are also presented to the isolated shadow; no second scheduler is
// introduced. Every output (including invalid data), ready, count, and the
// correction/advance/busy controls must agree before and after every edge.
module tb_operand_isolation_compare;
 reg clk=0;always #3 clk=~clk;
 wire done;
 guard_add_selective_driver #(.V(1))reference(clk,done);
 wire ir,ov,mode;wire[2:0]take,nout;wire[71:0]answer;
 guard_add_selective_isolated #(.V(3),.ISOLATE(`ISOLATE_POLICY))dut(
  .clk(clk),.rst(reference.rst),.in_valid(reference.iv),
  .out_ready(reference.orr),.u_in(reference.raw_u),.i_in(reference.raw_i),
  .available(reference.av),.in_ready(ir),.take(take),
  .out_valid(ov),.out_count(nout),.out_data(answer),.narrow_mode(mode));
 integer sink,trace_sink=0,trace_index=0,pin_checks=0;
 integer requests=0,retirements=0,neurons=0,first=-1,last=-1;
 integer corrections=0,freezes=0,prelude_samples=0,reset_samples=0;
 integer input_stalls=0,output_stalls=0;
 reg closed=0;
 task check_pins;
  begin
   pin_checks=pin_checks+1;
   if({ir,take,ov,nout,answer,mode}!==
      {reference.ir,reference.take,reference.ov,reference.nout,reference.answer,reference.mode})
    $fatal(1,"ISOLATION output/control mismatch at %0t sample %0d",$time,pin_checks);
   if({dut.correction_step,dut.advance,dut.busy}!==
      {reference.correction_signal,reference.advance_signal,reference.busy_signal})
    $fatal(1,"ISOLATION correction/advance/busy mismatch at %0t sample %0d",$time,pin_checks);
  end
 endtask
 initial begin
  if(`PROFILE!=1)$fatal(1,"Isolation verification requires PROFILE1");
  sink=$fopen("isolated_stream_out1.txt","w");
  if(!sink)$fatal(1,"Cannot open isolated retirement log");
  if(`CAPTURE_TRACE)begin
   if(`STALL!=0)$fatal(1,"Gate-replay trace requires STALL0");
   trace_sink=$fopen("isolated_native_trace1.txt","w");
   if(!trace_sink)$fatal(1,"Cannot open isolated trace");
  end
 end
 always @(negedge clk)begin
  #0.020;
  check_pins();
  if(!closed)begin
   if(done)begin
    $fclose(sink);
    if(`CAPTURE_TRACE)$fclose(trace_sink);
    closed=1;
   end else begin
    if(!reference.running)prelude_samples=prelude_samples+1;
    if(reference.rst)reset_samples=reset_samples+1;
    if(`CAPTURE_TRACE)begin
     // Same eighteen columns and sampling phase as the archived energy trace.
     $fwrite(trace_sink,"%0d %0d %0d %0d %0d %0d %0d %017h %017h %0d %0d %0d %0d %018h %0d %0d %0d %0d\n",
      trace_index,reference.running,done,reference.rst,reference.iv,reference.orr,reference.av,
      reference.raw_u,reference.raw_i,ir,take,ov,nout,answer,mode,
      dut.correction_step,dut.advance,dut.busy);
    end
    trace_index=trace_index+1;
    if(reference.running)begin
     if(reference.iv&&ir)begin
      requests=requests+1;neurons=neurons+take;
      if(first<0)first=reference.cycle+1;
     end
     if(reference.iv&&!ir)input_stalls=input_stalls+1;
     if(ov&&!reference.orr)output_stalls=output_stalls+1;
     if(dut.correction_step)corrections=corrections+1;
     if(dut.correction_step&&!dut.advance)freezes=freezes+1;
     if(ov&&reference.orr)begin
      // At this falling-edge sample the reference queue still names the
      // transaction retiring at the next rising edge. This avoids races with
      // its posedge queue updates and records the isolated DUT's actual data.
      $fwrite(sink,"%0d %0d %0d 0 %018h %0d %0d 0\n",
       reference.qframe[reference.head%32],reference.qstart[reference.head%32],
       nout,answer,reference.qclk[reference.head%32],reference.cycle+1);
      retirements=retirements+1;last=reference.cycle+1;
     end
    end
   end
  end
 end
 always @(posedge clk)begin #0.020;check_pins();end
 initial begin
  wait(done);wait(closed);#0.010;
  if(requests!=retirements||requests!=reference.accepted||neurons!=reference.neurons)
   $fatal(1,"ISOLATION request/retirement totals disagree");
  if(last-first+1!=reference.last-reference.first+1)
   $fatal(1,"ISOLATION physical service differs");
  if(corrections!=reference.correction_steps||freezes!=reference.correction_freezes)
   $fatal(1,"ISOLATION correction service differs");
  $display("OPERAND_ISOLATION PASS POLICY %0d STALL %0d REQUESTS %0d RETIREMENTS %0d NEURONS %0d CLOCKS %0d CORRECTION_STEPS %0d CORRECTION_FREEZES %0d PIN_CHECKS %0d PRELUDE_SAMPLES %0d RESET_SAMPLES %0d TRACE_ROWS %0d",
   `ISOLATE_POLICY,`STALL,requests,retirements,neurons,last-first+1,
   corrections,freezes,pin_checks,prelude_samples,reset_samples,trace_index);
  $finish;
 end
endmodule
