`timescale 1ns/1ps
`ifndef DC
 `define DC 25
`endif
`ifndef STALL
 `define STALL 0
`endif
module tb_quotient_screen;
 reg clk=0;always #2 clk=~clk;
 reg rst=1,iv=0,orr=1;reg signed[10:0]u=0;reg[4:0]delta=0;
 wire[2:0]ir,ov;wire signed[10:0]a,b,c;
 quotient_screen #(.ALT(0),.DC(`DC))d0(clk,rst,iv,orr,u,delta,ir[0],ov[0],a);
 quotient_screen #(.ALT(1),.DC(`DC))d1(clk,rst,iv,orr,u,delta,ir[1],ov[1],b);
 quotient_screen #(.ALT(2),.DC(`DC))d2(clk,rst,iv,orr,u,delta,ir[2],ov[2],c);
 integer sink,cycle=0,step=0,next_case=0,head=0,tail=0;
 integer qc[0:31],qs[0:31],qclock[0:31];
 integer accepted=0,retired=0,first=-1,last=-1,input_stalls=0,output_stalls=0;
 integer case_id,x,d,prod,expected;
 reg running=0,source_held=0,output_held=0;
 reg signed[10:0]held_u;reg[4:0]held_delta;reg[32:0]held_output;
 initial begin
  sink=$fopen("quotient_out.txt","w");if(!sink)$fatal(1,"No output file");
  repeat(3)@(negedge clk);rst=0;iv=1;u=-33;delta=31;orr=0;
  repeat(6)@(negedge clk);if(ov!==3'b111)$fatal(1,"Reset prelude failed");
  rst=1;iv=0;repeat(2)@(negedge clk);rst=0;orr=1;
  repeat(5)begin @(negedge clk);if(ov!==3'b000)$fatal(1,"Canceled output escaped");end
  running=1;
 end
 always @(negedge clk)if(running)begin
  orr=`STALL?((cycle%11!=4)&&(cycle%11!=5)&&(cycle%17!=3)):1;
  if(!source_held)begin
   iv=next_case<65536&&(!`STALL||cycle%13!=6);
   u=-1024+(next_case%2048);delta=next_case/2048;
  end
 end
 always @(posedge clk)if(running)begin
  cycle=cycle+1;
  if(ir!=={3{ir[0]}}||ov!=={3{ov[0]}})$fatal(1,"Control differs");
  if(source_held)begin
   input_stalls=input_stalls+1;
   if(!iv||u!==held_u||delta!==held_delta)$fatal(1,"Source violated hold");
  end
  source_held=iv&&!ir[0];if(source_held)begin held_u=u;held_delta=delta;end
  if(output_held)begin
   output_stalls=output_stalls+1;
   if(!ov[0]||{c,b,a}!==held_output)$fatal(1,"Output violated hold");
  end
  output_held=ov[0]&&!orr;if(output_held)held_output={c,b,a};
  if(iv&&ir[0])begin
   if(tail-head>=30)$fatal(1,"Scoreboard overflow");
   qc[tail%32]=next_case;qs[tail%32]=step;qclock[tail%32]=cycle;tail=tail+1;
   next_case=next_case+1;accepted=accepted+1;if(first<0)first=cycle;
  end
  if(ov[0]&&orr)begin
   if(head==tail||step-qs[head%32]!=4)$fatal(1,"Order/latency failure");
   case_id=qc[head%32];x=-1024+(case_id%2048);d=`DC<0?case_id/2048:`DC;
   prod=x*d;expected=x-(prod>>>8);
   if($signed(a)!=expected||$signed(b)!=expected||$signed(c)!=expected)
    $fatal(1,"Arithmetic U%0d d%0d got%0d/%0d/%0d want%0d",x,d,$signed(a),$signed(b),$signed(c),expected);
   $fwrite(sink,"%0d %0d %03h %03h %03h %0d %0d\n",x,d,a,b,c,qclock[head%32],cycle);
   retired=retired+1;head=head+1;last=cycle;
  end
  if(ir[0])step=step+1;
  if(next_case==65536&&head==tail)begin
   if(accepted!=65536||retired!=65536)$fatal(1,"Lost requests");
   $display("QUOTIENT PASS REQUESTS %0d CLOCKS %0d INPUT_STALLS %0d OUTPUT_STALLS %0d",retired,last-first+1,input_stalls,output_stalls);
   $fclose(sink);$finish;
  end
  if(cycle>300000)$fatal(1,"Timeout");
 end
endmodule
