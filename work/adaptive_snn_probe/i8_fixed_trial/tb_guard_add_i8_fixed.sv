`timescale 1ns/1ps
`ifndef STALL
 `define STALL 0
`endif
// Local V0: new I8 hybrid E2. V1: new I8 all-LUT E3.
// V2: frozen exact-residue V2. V3: frozen full-I11 retimed hybrid E2.
// Only available currents must be sign-extended signed8; ignored binary tails
// are deliberately arbitrary. All variants have the same six-lane service.
module guard_add_i8_fixed_driver #(parameter V=0)(input wire clk,output reg done=0);
 reg rst=1,iv=0,orr=1;
 reg[65:0]raw_u=0,raw_i=0;reg[2:0]av=0;
 wire ir,ov,mode,advance_signal;wire[2:0]take,nout;wire[71:0]answer;
 generate if(V<2)begin:i8_variant
  guard_add_i8_fixed #(.E(V+2))dut(.clk(clk),.rst(rst),.in_valid(iv),.out_ready(orr),
   .u_in(raw_u),.i_in(raw_i),.available(av),.in_ready(ir),.take(take),
   .out_valid(ov),.out_count(nout),.out_data(answer),.narrow_mode(mode));
  assign advance_signal=dut.advance;
 end else if(V==2)begin:residue_reference
  guard_add_selective #(.V(2))dut(.clk(clk),.rst(rst),.in_valid(iv),.out_ready(orr),
   .u_in(raw_u),.i_in(raw_i),.available(av),.in_ready(ir),.take(take),
   .out_valid(ov),.out_count(nout),.out_data(answer),.narrow_mode(mode));
  assign advance_signal=dut.advance;
 end else begin:full_reference
  guard_add_retime #(.E(2))dut(.clk(clk),.rst(rst),.in_valid(iv),.out_ready(orr),
   .u_in(raw_u),.i_in(raw_i),.available(av),.in_ready(ir),.take(take),
   .out_valid(ov),.out_count(nout),.out_data(answer),.narrow_mode(mode));
  assign advance_signal=dut.advance;
 end endgenerate
 integer source,sink,status,nframes,frame=-1,length,index,gap,remaining_gap=0,k;
 reg[10:0]mem_u[0:4095],mem_i[0:4095];
 integer head=0,tail=0,qframe[0:31],qstart[0:31],qn[0:31],qclk[0:31],qstep[0:31];
 integer cycle=0,step=0,accepted=0,retired=0,neurons=0,first=-1,last=-1;
 integer input_stalls=0,output_stalls=0;
 integer latency_min=2147483647,latency_max=0;
 integer directed_cases=0,dc;
 reg source_held=0;reg[65:0]source_u,source_i;reg[2:0]source_av,source_take;
 reg running=0,exhausted=0,held=0;reg[71:0]hold_data;reg[2:0]hold_count;
 task read_frame;
  begin
   frame=frame+1;
   if(frame==nframes)begin exhausted=1;index=0;length=0;end
   else begin
    status=$fscanf(source,"%d %d\n",length,gap);
    if(status!=2||length<1||length>4096||gap<0)$fatal(1,"Bad I8 fixed frame");
    for(k=0;k<length;k=k+1)begin
     status=$fscanf(source,"%h %h\n",mem_u[k],mem_i[k]);
     if(status!=2)$fatal(1,"Bad I8 fixed pair");
     if(mem_i[k][10:8]!={3{mem_i[k][7]}})$fatal(1,"Current violates signed8 contract");
    end
    index=0;remaining_gap=gap;
   end
  end
 endtask
 // Explicit minimum/maximum currents and membrane values, every tail count,
 // and output backpressure before the archived stream starts at cycle zero.
 // Ordinary integer addition is the prelude oracle; no residue algebra used.
 task directed_boundary(input integer count,input integer rotate,input integer hold_cycles);
  integer lane,pair_index,a,b,h;
  reg[71:0]expected;
  begin
   @(negedge clk);iv=1;orr=0;av=count;expected=0;
   for(lane=0;lane<6;lane=lane+1)begin
    pair_index=(lane+rotate)%6;
    case(pair_index)
     0:begin a=-1024;b=-128;end
     1:begin a=-1024;b=127;end
     2:begin a=1023;b=-128;end
     3:begin a=1023;b=127;end
     4:begin a=-1;b=-128;end
     default:begin a=0;b=127;end
    endcase
    raw_u[11*lane+:11]=(lane<count)?(a&2047):(lane%2?11'h400:11'h7ff);
    raw_i[11*lane+:11]=(lane<count)?(b&2047):(lane%2?11'h7ff:11'h400);
    if(lane<count)expected[12*lane+:12]=(a+b)&4095;
   end
   @(posedge clk);if(!ir||take!=count||mode!==1'b0)$fatal(1,"Directed acceptance V%0d",V);
   @(negedge clk);iv=0;
   repeat(3)@(posedge clk);
   @(negedge clk);
   if(!ov||nout!=count||answer!==expected)$fatal(1,"Directed exact I8 boundary V%0d count%0d",V,count);
   for(h=0;h<hold_cycles;h=h+1)begin
    @(negedge clk);
    if(!ov||ir||nout!=count||answer!==expected)$fatal(1,"Directed held result V%0d",V);
   end
   orr=1;@(posedge clk);@(negedge clk);
   if(ov)$fatal(1,"Directed result duplicated V%0d",V);
   directed_cases=directed_cases+1;
  end
 endtask
 initial begin
  sink=$fopen($sformatf("stream_out%0d.txt",V),"w");source=$fopen("stream_stim.txt","r");
  if(!source||!sink)$fatal(1,"Cannot open I8 fixed files");
  status=$fscanf(source,"%d\n",nframes);if(status!=1||nframes<1)$fatal(1,"Bad frame count");
  // Installed Xilinx primitive GSR remains asserted during initial100ns.
  #120;
  repeat(3)@(negedge clk);rst=0;
  for(dc=1;dc<=6;dc=dc+1)directed_boundary(dc,0,3);
  for(dc=0;dc<6;dc=dc+1)directed_boundary(6,dc,0);
  // Empty offered windows accept no arithmetic work and cannot create output.
  @(negedge clk);iv=1;av=0;raw_u={6{11'h400}};raw_i={6{11'h7ff}};
  repeat(6)begin @(negedge clk);if(ov||take!=0)$fatal(1,"Empty I8 window produced output");end
  // Reset while a completed output is stalled.
  @(negedge clk);iv=1;av=6;orr=0;
  raw_u={11'd101,11'd100,11'd99,11'd98,11'd97,11'd96};
  raw_i={11'd12,11'd11,11'd10,11'd9,11'd8,11'd7};
  repeat(6)@(negedge clk);if(!ov)$fatal(1,"I8 reset prelude failed to fill output");
  rst=1;iv=0;repeat(2)@(negedge clk);rst=0;orr=1;
  repeat(5)begin @(negedge clk);if(ov)$fatal(1,"Canceled stalled I8 output escaped reset");end
  // Reset before a newly accepted result reaches the output stage.
  iv=1;av=6;raw_u={6{11'd1023}};raw_i={6{11'd127}};
  repeat(2)@(negedge clk);rst=1;iv=0;
  repeat(2)@(negedge clk);rst=0;
  repeat(5)begin @(negedge clk);if(ov)$fatal(1,"Canceled in-flight I8 result escaped reset");end
  read_frame();#0.001;running=1;
 end
 always @(negedge clk)if(running&&!done)begin
  orr=`STALL?((cycle%11!=4)&&(cycle%11!=5)&&(cycle%17!=3)):1;
  if(!source_held)begin
   iv=!exhausted&&(remaining_gap==0)&&(!`STALL||(cycle%13!=6));
   if(!exhausted)begin
    av=(length-index>=6)?6:(length-index);
    for(k=0;k<6;k=k+1)begin
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
    $fatal(1,"I8 fixed input changed during backpressure V%0d",V);
  end
  source_held=iv&&!ir;
  if(source_held)begin source_u=raw_u;source_i=raw_i;source_av=av;source_take=take;end
  if(held&&(!ov||answer!==hold_data||nout!==hold_count))$fatal(1,"I8 fixed stalled output changed V%0d",V);
  if(held)output_stalls=output_stalls+1;
  held=ov&&!orr;if(held)begin hold_data=answer;hold_count=nout;end
  if(iv&&ir)begin
   if(take<1||take>av||mode!==1'b0)$fatal(1,"Bad I8 fixed count/mode");
   for(k=0;k<av;k=k+1)
    if(raw_i[11*k+8+:3]!=={3{raw_i[11*k+7]}})$fatal(1,"Accepted current outside signed8");
   if(tail-head>=30)$fatal(1,"I8 fixed scoreboard overflow");
   qframe[tail%32]=frame;qstart[tail%32]=index;qn[tail%32]=take;
   qclk[tail%32]=cycle;qstep[tail%32]=step;tail=tail+1;
   accepted=accepted+1;neurons=neurons+take;
   if(first<0)first=cycle;
   index=index+take;if(index==length)read_frame();
  end
  if(ov&&orr)begin
   if(head==tail)$fatal(1,"Unexpected I8 fixed output V%0d",V);
   if(nout!=qn[head%32]||step-qstep[head%32]!=4)$fatal(1,"I8 fixed count/advance latency V%0d",V);
   if(cycle-qclk[head%32]<4)$fatal(1,"I8 fixed physical latency below four clocks");
   if(cycle-qclk[head%32]<latency_min)latency_min=cycle-qclk[head%32];
   if(cycle-qclk[head%32]>latency_max)latency_max=cycle-qclk[head%32];
   $fwrite(sink,"%0d %0d %0d 0 %018h %0d %0d 0\n",qframe[head%32],qstart[head%32],nout,
    answer,qclk[head%32],cycle);
   retired=retired+1;head=head+1;last=cycle;
  end
  if(advance_signal)step=step+1;
  if(remaining_gap>0&&!iv)remaining_gap=remaining_gap-1;
  if(exhausted&&head==tail)begin
   if(accepted!=retired)$fatal(1,"Lost I8 fixed request");
   $display("GUARD_ADD_I8_FIXED V %0d REQUESTS %0d NEURONS %0d CLOCKS %0d INPUT_STALLS %0d OUTPUT_STALLS %0d MIN_LATENCY %0d MAX_LATENCY %0d DIRECTED_CASES %0d",V,accepted,neurons,last-first+1,input_stalls,output_stalls,latency_min,latency_max,directed_cases);
   $fclose(sink);$fclose(source);done=1;iv=0;
  end
  if(cycle>10000000)$fatal(1,"I8 fixed timeout V%0d",V);
 end
endmodule
module tb_guard_add_i8_fixed;
 reg clk=0;always #2 clk=~clk;
 wire[3:0]done;
 guard_add_i8_fixed_driver #(.V(0))i8_hybrid(clk,done[0]);
 guard_add_i8_fixed_driver #(.V(1))i8_lut(clk,done[1]);
 guard_add_i8_fixed_driver #(.V(2))fixed_residue(clk,done[2]);
 guard_add_i8_fixed_driver #(.V(3))full_hybrid(clk,done[3]);
 initial begin wait(&done);$display("GUARD_ADD_I8_FIXED PASS");$finish;end
endmodule
