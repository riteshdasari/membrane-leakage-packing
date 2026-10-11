`timescale 1ns/1ps
module tb_fixed_pair;
 reg clk=0;always #2 clk=~clk;
 reg rst=1,valid=0;reg[1:0]cmd=0;reg first=0,last=0;
 reg[383:0]lower=0;
 reg[287:0]wa[0:3],wb[0:3],seed[0:3];
 wire[3:0]ready,ov;wire[23:0]sp[0:3];wire[383:0]states[0:3];
 for(genvar m=0;m<4;m=m+1)begin:d
  localparam S=m==0?6:m==2?12:8;
  localparam W=24*S;
  fixed_pair #(.SLOT(S),.NATIVE(m==2),.LUT(m==3),.SH(`SH),.LEAK(`LEAK),.HARD(`HARD)) u(
   .clk(clk),.rst(rst),.valid(valid),.cmd(cmd),.first(first),.last(last),
   .wa(wa[m][W-1:0]),.wb(wb[m][W-1:0]),.seed(seed[m][W-1:0]),.ready(ready[m]),
   .out_valid(ov[m]),.spike(sp[m]),.state_debug(states[m]));
 end
 integer f,rc,n,k,gap,j,m,cycle=0,accepted=0,stalls=0,of[0:3];
 always @(posedge clk)begin
  if(!rst)begin cycle<=cycle+1;if(valid&&(&ready))accepted<=accepted+1;
   if(valid&&!(&ready))stalls<=stalls+1;end
  #0.1;
  for(integer a=0;a<4;a=a+1)if(ov[a])$fdisplay(of[a],"%h %h",states[a],sp[a]);
 end
 initial begin
  for(m=0;m<4;m=m+1)begin wa[m]=0;wb[m]=0;seed[m]=0;of[m]=$fopen($sformatf("out%0d.txt",m),"w");end
  // UNISIM glbl holds GSR for the first 100 ns.
  repeat(50)@(negedge clk);rst=0;
  f=$fopen("stim.txt","r");rc=$fscanf(f,"%d",n);
  for(k=0;k<n;k=k+1)begin
   @(negedge clk);valid=0;
   rc=$fscanf(f,"%d %d %b %b %h",gap,cmd,first,last,lower);
   if(rc!=5)$fatal(1,"Malformed command %0d",k);
   for(m=0;m<4;m=m+1)begin
    rc=$fscanf(f,"%h %h %h",wa[m],wb[m],seed[m]);
    if(rc!=3)$fatal(1,"Malformed payload %0d",k);
   end
   repeat(gap)@(negedge clk);
   valid=1;
   @(posedge clk);while(!(&ready))@(posedge clk);
  end
  @(negedge clk);valid=0;
  repeat(12)@(negedge clk);
  $display("COUNTS %0d %0d %0d",cycle,accepted,stalls);
  for(m=0;m<4;m=m+1)$fclose(of[m]);
  $finish;
 end
 initial begin #2000000;$fatal(1,"timeout");end
endmodule
