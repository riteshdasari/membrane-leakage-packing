`timescale 1ns/1ps
module tb_split_leak;
 reg clk=0;always #2 clk=~clk;
 reg rst=1,valid=0;reg[19:0]uin=0;reg[8:0]beta=0;
 wire[19:0]out[0:1];wire[1:0]ov;
 for(genvar e=0;e<2;e=e+1)begin:d
  split_leak #(.E(e),.BC(`BC))u(.clk(clk),.rst(rst),.valid(valid),.u_in(uin),.beta(beta),.out_valid(ov[e]),.u_out(out[e]));
 end
 integer fi,f0,f1,rows,i,v,b,rc;reg[19:0]raw;
 integer cycles=0,accepted=0,outputs=0;
 reg d0=0,d1=0;
 always @(posedge clk)begin
  if(!rst)begin cycles=cycles+1;if(valid)accepted=accepted+1;end
  #0.1;
  if(!rst)begin
   if(ov[0]!==ov[1])$fatal(1,"unequal valid latency");
   if(ov[0]!==d1)$fatal(1,"unexpected output latency");
   d1=d0;d0=valid;
   if(ov[0])begin $fdisplay(f0,"%h",out[0]);$fdisplay(f1,"%h",out[1]);outputs=outputs+1;end
  end
 end
 initial begin
  f0=$fopen("out0.txt","w");f1=$fopen("out1.txt","w");fi=$fopen("stim.txt","r");rc=$fscanf(fi,"%d",rows);
  repeat(50)@(negedge clk);rst=0;
  for(i=0;i<rows;i=i+1)begin
   rc=$fscanf(fi,"%d %d %h",v,b,raw);if(rc!=3)$fatal(1,"bad stimulus");
   @(negedge clk);valid=v;beta=b;uin=raw;
  end
  @(negedge clk);valid=0;repeat(4)@(negedge clk);
  if(accepted!=outputs)$fatal(1,"lost output");
  $fclose(f0);$fclose(f1);$display("SPLIT CYCLES %0d ACCEPTED %0d OUTPUTS %0d",cycles,accepted,outputs);$finish;
 end
 initial begin #3000000;$fatal(1,"timeout");end
endmodule
