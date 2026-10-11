`timescale 1ns/1ps
`ifndef STALL
 `define STALL 0
`endif
module stream_driver #(parameter E=0)(input wire clk,output reg done=0);
 reg rst=1,iv=0,orr=1;
 reg[43:0]raw=0;reg[2:0]av=0;
 wire ir,ov,mode;wire[2:0]take,nout;wire[43:0]answer;
 quad_leak #(.E(E))dut(.clk(clk),.rst(rst),.in_valid(iv),.out_ready(orr),
  .u_in(raw),.available(av),.in_ready(ir),.take(take),.out_valid(ov),.out_count(nout),.u_out(answer),.quad_mode(mode));
 integer source,sink,status,nframes,frame=-1,length,index,coef,gap,remaining_gap=0;
 reg[10:0]mem[0:4095];integer f,start,n,d,k;
 integer head=0,tail=0,qframe[0:31],qstart[0:31],qn[0:31],qd[0:31],qclk[0:31],qstep[0:31],qmode[0:31];
 integer cycle=0,step=0,accepted=0,retired=0,neurons=0,issues=0,narrow=0,bypasses=0,first=-1,last=-1;
 integer input_stalls=0,output_stalls=0;
 generate if(E!=4)begin:ce_audit
  always @(posedge clk)if(running&&!rst)begin
   if(dut.dsp_path.d.d.CEA2 !== (dut.advance&&dut.accept&&!dut.identity_request))$fatal(1,"AREG CE mismatch");
   if(dut.dsp_path.d.d.CEB2 !== (dut.advance&&dut.accept&&!dut.identity_request))$fatal(1,"BREG CE mismatch");
   if(dut.dsp_path.d.d.CEM !== (dut.advance&&dut.v0&&!dut.b0))$fatal(1,"MREG CE mismatch");
   if(dut.dsp_path.d.d.CEC !== (dut.advance&&dut.v0&&!dut.b0))$fatal(1,"CREG CE mismatch");
   if(dut.dsp_path.d.d.CEP !== (dut.advance&&dut.v1&&!dut.b1))$fatal(1,"PREG CE mismatch");
  end
 end endgenerate
 reg source_held=0;reg[43:0]source_raw;reg[2:0]source_av;reg[2:0]source_take;
 // Functional checks drive on the falling edge to avoid a DUT/source race.
 // Register-launched timing is a separate synthesis fixture, not this TB.
 reg running=0,exhausted=0,held=0;reg[43:0]hold_data;reg[2:0]hold_count;
 task read_frame;
  begin
   frame=frame+1;
   if(frame==nframes)begin exhausted=1;index=0;length=0;end
   else begin
    status=$fscanf(source,"%d %d %d\n",length,coef,gap);
    if(status!=3||length<1||length>4096||coef!=25||gap<0)$fatal(1,"Bad constant25 input frame");
    for(k=0;k<length;k=k+1)begin status=$fscanf(source,"%h\n",mem[k]);if(status!=1)$fatal(1,"Bad membrane");end
    index=0;remaining_gap=gap;
   end
  end
 endtask
 initial begin
  sink=$fopen($sformatf("stream_out%0d.txt",E),"w");source=$fopen("stream_stim.txt","r");
  if(!source||!sink)$fatal(1,"Cannot open files");status=$fscanf(source,"%d\n",nframes);
  // Xilinx glbl holds DSP primitives in GSR for the first100ns of simulation.
  #120;
  // Cancel in-flight data and then reset while the output is backpressured.
  repeat(3)@(negedge clk);rst=0;iv=1;av=4;raw={11'd101,11'd100,11'd99,11'd98};orr=0;
  repeat(6)@(negedge clk);if(!ov)$fatal(1,"Reset prelude failed to fill output");
  rst=1;iv=0;repeat(2)@(negedge clk);rst=0;orr=1;
  repeat(5)begin @(negedge clk);if(ov)$fatal(1,"Canceled request escaped reset");end
  read_frame();running=1;
 end
 always @(negedge clk)if(running&&!done)begin
  orr=`STALL?((cycle%11!=4)&&(cycle%11!=5)&&(cycle%17!=3)):1;
  // Once valid is offered, preserve valid and every payload bit until acceptance.
  if(!source_held)begin
   iv=!exhausted&&(remaining_gap==0)&&(!`STALL||(cycle%13!=6));
   if(!exhausted)begin
   av=(length-index>=4)?4:(length-index);
   raw[10:0]=mem[index];raw[21:11]=av>=2?mem[index+1]:11'h7ff;
   raw[32:22]=av>=3?mem[index+2]:11'h400;
   raw[43:33]=av==4?mem[index+3]:11'h7ff;
   end else begin av=0;raw=0;iv=0;end
  end
 end
 always @(posedge clk)if(running&&!done)begin
  cycle=cycle+1;
  if(source_held)begin
   input_stalls=input_stalls+1;
   if(!iv||raw!==source_raw||av!==source_av||take!==source_take)
    $fatal(1,"Input changed during backpressure E%0d",E);
  end
  source_held=iv&&!ir;
  if(source_held)begin source_raw=raw;source_av=av;source_take=take;end
  if(held&&(!ov||answer!==hold_data||nout!==hold_count))$fatal(1,"Output changed during stall E%0d",E);
  if(held)output_stalls=output_stalls+1;
  held=ov&&!orr;if(held)begin hold_data=answer;hold_count=nout;end
  if(iv&&ir)begin
   if(take<1||take>av)$fatal(1,"Bad take count");
   if(tail-head>=30)$fatal(1,"Scoreboard overflow");
   qframe[tail%32]=frame;qstart[tail%32]=index;qn[tail%32]=take;qd[tail%32]=25;
   qclk[tail%32]=cycle;qstep[tail%32]=step;qmode[tail%32]=mode;tail=tail+1;
   accepted=accepted+1;neurons=neurons+take;narrow=narrow+mode;
   if(dut.identity_request)bypasses=bypasses+1;
   else issues=issues+1;
   if(first<0)first=cycle;
   index=index+take;if(index==length)read_frame();
  end
  if(ov&&orr)begin
   if(head==tail)$fatal(1,"Unexpected output");
   if(nout!=qn[head%32]||step-qstep[head%32]!=4)$fatal(1,"Count/pipeline latency E%0d",E);
   $fwrite(sink,"%0d %0d %0d %0d %011h %0d %0d %0d\n",qframe[head%32],qstart[head%32],nout,qd[head%32],answer,qclk[head%32],cycle,qmode[head%32]);
   retired=retired+1;head=head+1;last=cycle;
  end
  if(ir)step=step+1;
  if(remaining_gap>0)remaining_gap=remaining_gap-1;
  if(exhausted&&head==tail)begin
   if(accepted!=retired)$fatal(1,"Lost request");
   $display("STREAM E %0d REQUESTS %0d NEURONS %0d ISSUES %0d NARROW %0d BYPASS %0d CLOCKS %0d INPUT_STALLS %0d OUTPUT_STALLS %0d",E,accepted,neurons,issues,narrow,bypasses,last-first+1,input_stalls,output_stalls);
   $fclose(sink);$fclose(source);done=1;iv=0;
  end
  if(cycle>10000000)$fatal(1,"Timeout");
 end
endmodule
module tb_quad_leak;
 reg clk=0;always #2 clk=~clk;
 wire[4:0]done;
 stream_driver #(.E(0))a(clk,done[0]);stream_driver #(.E(1))b(clk,done[1]);
 stream_driver #(.E(2))c(clk,done[2]);stream_driver #(.E(3))d(clk,done[3]);
 stream_driver #(.E(4))e(clk,done[4]);
 initial begin wait(&done);$display("QUAD PASS");$finish;end
endmodule
