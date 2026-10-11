`timescale 1ns/1ps
`ifndef STALL
 `define STALL 0
`endif
// Functional source drives on falling edges. Timing fixtures are separate.
module guard_add_driver #(parameter E=0)(input wire clk,output reg done=0);
 reg rst=1,iv=0,orr=1;
 reg[65:0]raw_u=0,raw_i=0;reg[2:0]av=0;
 wire ir,ov,mode;wire[2:0]take,nout;wire[71:0]answer;
 guard_add #(.E(E))dut(.clk(clk),.rst(rst),.in_valid(iv),.out_ready(orr),
  .u_in(raw_u),.i_in(raw_i),.available(av),.in_ready(ir),.take(take),
  .out_valid(ov),.out_count(nout),.out_data(answer),.narrow_mode(mode));
 integer source,sink,status,nframes,frame=-1,length,index,gap,remaining_gap=0,k;
 reg[10:0]mem_u[0:4095],mem_i[0:4095];
 integer head=0,tail=0,qframe[0:31],qstart[0:31],qn[0:31],qclk[0:31],qstep[0:31],qmode[0:31];
 integer cycle=0,step=0,accepted=0,retired=0,neurons=0,narrow=0,copies=0,first=-1,last=-1;
 integer input_stalls=0,output_stalls=0;
 reg source_held=0;reg[65:0]source_u,source_i;reg[2:0]source_av,source_take;
 reg running=0,exhausted=0,held=0;reg[71:0]hold_data;reg[2:0]hold_count;
 task read_frame;
  begin
   frame=frame+1;
   if(frame==nframes)begin exhausted=1;index=0;length=0;end
   else begin
    status=$fscanf(source,"%d %d\n",length,gap);
    if(status!=2||length<1||length>4096||gap<0)$fatal(1,"Bad add input frame");
    for(k=0;k<length;k=k+1)begin
     status=$fscanf(source,"%h %h\n",mem_u[k],mem_i[k]);
     if(status!=2)$fatal(1,"Bad add operand pair");
    end
    index=0;remaining_gap=gap;
   end
  end
 endtask
 initial begin
  sink=$fopen($sformatf("stream_out%0d.txt",E),"w");source=$fopen("stream_stim.txt","r");
  if(!source||!sink)$fatal(1,"Cannot open add files");
  status=$fscanf(source,"%d\n",nframes);if(status!=1||nframes<1)$fatal(1,"Bad frame count");
  // Xilinx primitive GSR is asserted during the initial100ns.
  #120;
  repeat(3)@(negedge clk);rst=0;iv=1;av=6;
  raw_u={11'd101,11'd100,11'd99,11'd98,11'd97,11'd96};
  raw_i={11'd12,11'd11,11'd10,11'd9,11'd8,11'd7};orr=0;
  repeat(6)@(negedge clk);if(!ov)$fatal(1,"Add reset prelude failed to fill output");
  rst=1;iv=0;repeat(2)@(negedge clk);rst=0;orr=1;
  repeat(5)begin @(negedge clk);if(ov)$fatal(1,"Canceled add request escaped reset");end
  read_frame();#0.001;running=1;
 end
 always @(negedge clk)if(running&&!done)begin
  orr=`STALL?((cycle%11!=4)&&(cycle%11!=5)&&(cycle%17!=3)):1;
  // Hold valid and the entire six-value payload until acceptance.
  if(!source_held)begin
   iv=!exhausted&&(remaining_gap==0)&&(!`STALL||(cycle%13!=6));
   if(!exhausted)begin
    av=(length-index>=6)?6:(length-index);
    for(k=0;k<6;k=k+1)begin
     // Poison unavailable tails; output tails must still be zero.
     raw_u[11*k+:11]=(k<av)?mem_u[index+k]:(k%2?11'h400:11'h7ff);
     raw_i[11*k+:11]=(k<av)?mem_i[index+k]:(k%2?11'h7ff:11'h400);
    end
   end else begin av=0;raw_u=0;raw_i=0;iv=0;end
  end
 end
 always @(posedge clk)if(running&&!done)begin
  cycle=cycle+1;
  if(source_held)begin
   input_stalls=input_stalls+1;
   if(!iv||raw_u!==source_u||raw_i!==source_i||av!==source_av||take!==source_take)
    $fatal(1,"Add input changed during backpressure E%0d",E);
  end
  source_held=iv&&!ir;
  if(source_held)begin source_u=raw_u;source_i=raw_i;source_av=av;source_take=take;end
  if(held&&(!ov||answer!==hold_data||nout!==hold_count))$fatal(1,"Add output changed during stall E%0d",E);
  if(held)output_stalls=output_stalls+1;
  held=ov&&!orr;if(held)begin hold_data=answer;hold_count=nout;end
  if(iv&&ir)begin
   if(take<1||take>av)$fatal(1,"Bad add take count");
   if(tail-head>=30)$fatal(1,"Add scoreboard overflow");
   qframe[tail%32]=frame;qstart[tail%32]=index;qn[tail%32]=take;
   qclk[tail%32]=cycle;qstep[tail%32]=step;qmode[tail%32]=mode;tail=tail+1;
   accepted=accepted+1;neurons=neurons+take;narrow=narrow+mode;
   if((E==0||E==1)&&!mode&&av>=5&&raw_i[44+:11]==0)copies=copies+1;
   if(first<0)first=cycle;
   index=index+take;if(index==length)read_frame();
  end
  if(ov&&orr)begin
   if(head==tail)$fatal(1,"Unexpected add output");
   if(nout!=qn[head%32]||step-qstep[head%32]!=4)$fatal(1,"Add count/pipeline latency E%0d",E);
   $fwrite(sink,"%0d %0d %0d 0 %018h %0d %0d %0d\n",qframe[head%32],qstart[head%32],nout,
    answer,qclk[head%32],cycle,qmode[head%32]);
   retired=retired+1;head=head+1;last=cycle;
  end
  if(ir)step=step+1;
  if(remaining_gap>0&&!iv)remaining_gap=remaining_gap-1;
  if(exhausted&&head==tail)begin
   if(accepted!=retired)$fatal(1,"Lost add request");
   $display("GUARD_ADD E %0d REQUESTS %0d NEURONS %0d NARROW %0d COPY %0d CLOCKS %0d INPUT_STALLS %0d OUTPUT_STALLS %0d",E,accepted,neurons,narrow,copies,last-first+1,input_stalls,output_stalls);
   $fclose(sink);$fclose(source);done=1;iv=0;
  end
  if(cycle>10000000)$fatal(1,"Add timeout");
 end
endmodule
module tb_guard_add;
 reg clk=0;always #2 clk=~clk;
 wire[3:0]done;
 guard_add_driver #(.E(0))a(clk,done[0]);guard_add_driver #(.E(1))b(clk,done[1]);
 guard_add_driver #(.E(2))c(clk,done[2]);guard_add_driver #(.E(3))d(clk,done[3]);
 initial begin wait(&done);$display("GUARD_ADD PASS");$finish;end
endmodule
