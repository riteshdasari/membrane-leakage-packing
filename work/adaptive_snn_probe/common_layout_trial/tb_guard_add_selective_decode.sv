`timescale 1ns/1ps
`ifndef STALL
 `define STALL 0
`endif
`ifndef PROFILE
 `define PROFILE 0
`endif
// PROFILE0 tests full signed11 currents (coreV0/V1); PROFILE1 tests declared
// signed8 currents (coreV2/V3). V2/V3 below are local IDs for retimed E2/E3.
module guard_add_selective_decode_driver #(parameter V=0)(input wire clk,output reg done=0);
 reg rst=1,iv=0,orr=1;
 reg[65:0]raw_u=0,raw_i=0;reg[2:0]av=0;
 wire ir,ov,mode,advance_signal,correction_signal,busy_signal;
 wire[2:0]take,nout;wire[71:0]answer;
 generate if(V>=2)begin:retimed_reference
  guard_add_retime #(.E(V))dut(.clk(clk),.rst(rst),.in_valid(iv),.out_ready(orr),
   .u_in(raw_u),.i_in(raw_i),.available(av),.in_ready(ir),.take(take),
   .out_valid(ov),.out_count(nout),.out_data(answer),.narrow_mode(mode));
  assign advance_signal=dut.advance;
  assign correction_signal=1'b0;
  assign busy_signal=1'b0;
 end else begin:selective_variant
  guard_add_selective_decode #(.V(V+2*`PROFILE))dut(.clk(clk),.rst(rst),.in_valid(iv),.out_ready(orr),
   .u_in(raw_u),.i_in(raw_i),.available(av),.in_ready(ir),.take(take),
   .out_valid(ov),.out_count(nout),.out_data(answer),.narrow_mode(mode));
  assign advance_signal=dut.advance;
  assign correction_signal=dut.correction_step;
  assign busy_signal=dut.busy;
 end endgenerate
 integer source,sink,status,nframes,frame=-1,length,index,gap,remaining_gap=0,k;
 reg[10:0]mem_u[0:4095],mem_i[0:4095];
 integer head=0,tail=0,qframe[0:31],qstart[0:31],qn[0:31],qclk[0:31],qstep[0:31];
 integer cycle=0,step=0,accepted=0,retired=0,neurons=0,first=-1,last=-1;
 integer input_stalls=0,output_stalls=0,correction_freezes=0,correction_steps=0;
 integer correction_freeze_run=0,max_correction_freeze_run=0;
 integer latency_min=2147483647,latency_max=0;
 reg source_held=0;reg[65:0]source_u,source_i;reg[2:0]source_av,source_take;
 reg running=0,exhausted=0,held=0;reg[71:0]hold_data;reg[2:0]hold_count;
 task read_frame;
  begin
   frame=frame+1;
   if(frame==nframes)begin exhausted=1;index=0;length=0;end
   else begin
    status=$fscanf(source,"%d %d\n",length,gap);
    if(status!=2||length<1||length>4096||gap<0)$fatal(1,"Bad selective frame");
    for(k=0;k<length;k=k+1)begin
     status=$fscanf(source,"%h %h\n",mem_u[k],mem_i[k]);
     if(status!=2)$fatal(1,"Bad selective pair");
     if(`PROFILE && mem_i[k][10:8]!={3{mem_i[k][7]}})
      $fatal(1,"Current violates declared signed8 profile");
    end
    index=0;remaining_gap=gap;
   end
  end
 endtask
 initial begin
  sink=$fopen($sformatf("stream_out%0d.txt",V),"w");source=$fopen("stream_stim.txt","r");
  if(!source||!sink)$fatal(1,"Cannot open selective files");
  status=$fscanf(source,"%d\n",nframes);if(status!=1||nframes<1)$fatal(1,"Bad frame count");
  // Installed Xilinx primitive GSR remains asserted during initial100ns.
  #120;
  repeat(3)@(negedge clk);rst=0;iv=1;av=6;
  raw_u={11'd101,11'd100,11'd99,11'd98,11'd97,11'd96};
  raw_i={11'd12,11'd11,11'd10,11'd9,11'd8,11'd7};orr=0;
  repeat(6)@(negedge clk);if(!ov)$fatal(1,"Selective reset prelude failed to fill output");
  rst=1;iv=0;repeat(2)@(negedge clk);rst=0;orr=1;
  repeat(5)begin @(negedge clk);if(ov)$fatal(1,"Canceled selective output escaped reset");end
  // Cancel an adaptive six-exception correction partway through assembly.
  iv=1;av=6;raw_u={6{11'd1023}};raw_i={6{11'd127}};
  repeat(4)@(negedge clk);
  if(V==1&&!busy_signal)$fatal(1,"Selective busy-reset prelude never entered correction");
  rst=1;iv=0;repeat(2)@(negedge clk);rst=0;
  repeat(5)begin @(negedge clk);if(ov)$fatal(1,"Partial selective correction escaped reset");end
  read_frame();#0.001;running=1;
 end
 always @(negedge clk)if(running&&!done)begin
  orr=`STALL?((cycle%11!=4)&&(cycle%11!=5)&&(cycle%17!=3)):1;
  if(!source_held)begin
   iv=!exhausted&&(remaining_gap==0)&&(!`STALL||(cycle%13!=6));
   if(!exhausted)begin
    av=(length-index>=6)?6:(length-index);
    for(k=0;k<6;k=k+1)begin
     // Unavailable binary tails may violate the signed8 profile; masking must
     // prevent them from becoming correction jobs or influencing valid lanes.
     raw_u[11*k+:11]=(k<av)?mem_u[index+k]:(k%2?11'h400:11'h7ff);
     raw_i[11*k+:11]=(k<av)?mem_i[index+k]:(k%2?11'h7ff:11'h400);
    end
   end else begin av=0;raw_u=0;raw_i=0;iv=0;end
  end
 end
 always @(posedge clk)if(running&&!done)begin
  cycle=cycle+1;
  if(ir!==advance_signal)$fatal(1,"Ready/advance contract mismatch V%0d",V);
  if(source_held)begin
   input_stalls=input_stalls+1;
   if(!iv||raw_u!==source_u||raw_i!==source_i||av!==source_av||take!==source_take)
    $fatal(1,"Selective input changed during backpressure V%0d",V);
  end
  source_held=iv&&!ir;
  if(source_held)begin source_u=raw_u;source_i=raw_i;source_av=av;source_take=take;end
  if(held&&(!ov||answer!==hold_data||nout!==hold_count))$fatal(1,"Selective stalled output changed V%0d",V);
  if(held)output_stalls=output_stalls+1;
  held=ov&&!orr;if(held)begin hold_data=answer;hold_count=nout;end
  if(correction_signal)correction_steps=correction_steps+1;
  if(correction_signal&&!advance_signal)begin
   correction_freezes=correction_freezes+1;
   correction_freeze_run=correction_freeze_run+1;
   if(correction_freeze_run>max_correction_freeze_run)max_correction_freeze_run=correction_freeze_run;
  end else correction_freeze_run=0;
  if(iv&&ir)begin
   if(take<1||take>av||mode!==1'b0)$fatal(1,"Bad selective count/mode");
   if(tail-head>=30)$fatal(1,"Selective scoreboard overflow");
   qframe[tail%32]=frame;qstart[tail%32]=index;qn[tail%32]=take;
   qclk[tail%32]=cycle;qstep[tail%32]=step;tail=tail+1;
   accepted=accepted+1;neurons=neurons+take;
   if(first<0)first=cycle;
   index=index+take;if(index==length)read_frame();
  end
  if(ov&&orr)begin
   if(head==tail)$fatal(1,"Unexpected selective output V%0d",V);
   if(nout!=qn[head%32]||step-qstep[head%32]!=4)$fatal(1,"Selective count/advance latency V%0d",V);
   if(cycle-qclk[head%32]<4)$fatal(1,"Selective physical latency below four clocks");
   if(cycle-qclk[head%32]<latency_min)latency_min=cycle-qclk[head%32];
   if(cycle-qclk[head%32]>latency_max)latency_max=cycle-qclk[head%32];
   $fwrite(sink,"%0d %0d %0d 0 %018h %0d %0d 0\n",qframe[head%32],qstart[head%32],nout,
    answer,qclk[head%32],cycle);
   retired=retired+1;head=head+1;last=cycle;
  end
  if(advance_signal)step=step+1;
  if(remaining_gap>0&&!iv)remaining_gap=remaining_gap-1;
  if(exhausted&&head==tail)begin
   if(accepted!=retired)$fatal(1,"Lost selective request");
   $display("GUARD_ADD_SELECTIVE_DECODE V %0d REQUESTS %0d NEURONS %0d CLOCKS %0d INPUT_STALLS %0d OUTPUT_STALLS %0d CORRECTION_FREEZES %0d CORRECTION_STEPS %0d MAX_CORRECTION_FREEZE_RUN %0d MIN_LATENCY %0d MAX_LATENCY %0d",V,accepted,neurons,last-first+1,input_stalls,output_stalls,correction_freezes,correction_steps,max_correction_freeze_run,latency_min,latency_max);
   $fclose(sink);$fclose(source);done=1;iv=0;
  end
  if(cycle>10000000)$fatal(1,"Selective timeout V%0d",V);
 end
endmodule
module tb_guard_add_selective_decode;
 reg clk=0;always #2 clk=~clk;
 wire[3:0]done;
 guard_add_selective_decode_driver #(.V(0))fixed_reference(clk,done[0]);
 guard_add_selective_decode_driver #(.V(1))adaptive_variant(clk,done[1]);
 guard_add_selective_decode_driver #(.V(2))retimed_hybrid(clk,done[2]);
 guard_add_selective_decode_driver #(.V(3))retimed_lut(clk,done[3]);
 initial begin wait(&done);$display("GUARD_ADD_SELECTIVE_DECODE PASS");$finish;end
endmodule
