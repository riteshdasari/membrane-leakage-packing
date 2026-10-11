`timescale 1ns/1ps
module tb_fixed_lut_leak;
 reg clk=0;always #2 clk=~clk;
 reg rst=1,valid=0;
 reg[2*`BITS-1:0]uin=0;reg[8:0]beta=0;
 wire[2*`BITS-1:0]out[0:1];wire[1:0]ov;
 for(genvar e=0;e<2;e=e+1)begin:d
  fixed_lut_leak #(.E(e))u(.clk(clk),.rst(rst),.valid(valid),.u_in(uin),.beta(beta),.out_valid(ov[e]),.u_out(out[e]));
 end
 integer inputfile,f[0:1],rows,i,j,v,b,rc;reg[2*`BITS-1:0]raw;
 integer cycles=0,accepted=0,outputs=0;
 always @(posedge clk)begin
  if(!rst)begin cycles=cycles+1;if(valid)accepted=accepted+1;end
  #0.1;
  if(!rst)begin
   if(ov!=={2{ov[0]}})$fatal(1,"unequal valid latency");
   for(j=0;j<2;j=j+1)if(ov[j])$fdisplay(f[j],"%h",out[j]);
   if(ov[0])outputs=outputs+1;
  end
 end
 initial begin
  for(i=0;i<2;i=i+1)f[i]=$fopen($sformatf("out%0d.txt",i),"w");
  inputfile=$fopen("stim.txt","r");rc=$fscanf(inputfile,"%d",rows);
  repeat(50)@(negedge clk);rst=0;
  for(i=0;i<rows;i=i+1)begin
   rc=$fscanf(inputfile,"%d %d %h",v,b,raw);if(rc!=3)$fatal(1,"bad stimulus");
   @(negedge clk);valid=v;beta=b;uin=raw;
  end
  @(negedge clk);valid=0;repeat(3)@(negedge clk);
  if(accepted!=outputs)$fatal(1,"lost output");
  for(i=0;i<2;i=i+1)$fclose(f[i]);
  $display("LEAK CYCLES %0d ACCEPTED %0d OUTPUTS %0d",cycles,accepted,outputs);$finish;
 end
 initial begin #2000000;$fatal(1,"timeout");end
endmodule
