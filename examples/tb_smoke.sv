`timescale 1ns/1ps
module tb_smoke;
 reg clk=0;always #5 clk=~clk;
 reg rst=1,in_valid=0,out_ready=1;reg[31:0]u_in=0;reg[17:0]beta_in=0;reg[1:0]available=0;
 wire in_ready,out_valid,narrow_mode;wire[1:0]take,out_count;wire[31:0]out_data;
 sequential_leak16 #(.E(5)) dut(clk,rst,in_valid,out_ready,u_in,beta_in,available,in_ready,out_valid,take,out_count,out_data,narrow_mode);
 integer u[0:4095],b[0:4095],expected[0:4095],position=0,retired=0,cycles=0,i,prod;
 reg[31:0]held;reg[1:0]held_count;reg holding=0;
 initial begin
  for(i=0;i<4096;i=i+1)begin
   if(i%8<4)begin u[i]=((i*31)%512)-256;b[i]=(i/2)%257;end
   else begin u[i]=((i*701)%65536)-32768;b[i]=(i*17)%257;end
   prod=u[i]*b[i];expected[i]=(prod+255)>>>8;
  end
  u[0]=-256;b[0]=1;u[1]=1;b[1]=1;expected[0]=-1;expected[1]=1;
  u[2]=381;b[2]=78;expected[2]=117;
  repeat(3)@(negedge clk);rst=0;
 end
 always @(negedge clk)if(!rst)begin
  out_ready=(cycles%7!=3)&&(cycles%7!=4);
  in_valid=position<4096;
  available=position<4095?2:(position<4096?1:0);
  if(position<4096)begin
   u_in[15:0]=u[position];beta_in[8:0]=b[position];
   u_in[31:16]=position<4095?u[position+1]:0;
   beta_in[17:9]=position<4095?b[position+1]:0;
  end
 end
 always @(posedge clk)if(!rst)begin
  cycles=cycles+1;
  if(holding && (!out_valid||out_data!==held||out_count!==held_count))$fatal(1,"Held output changed");
  if(out_valid&&out_ready)begin
   if(out_count<1||out_count>2)$fatal(1,"Bad count");
   if($signed(out_data[15:0])!=expected[retired])$fatal(1,"Lower mismatch %d",retired);
   if(out_count==2&&$signed(out_data[31:16])!=expected[retired+1])$fatal(1,"Upper mismatch %d",retired+1);
   retired=retired+out_count;
  end
  holding=out_valid&&!out_ready;held=out_data;held_count=out_count;
  if(in_valid&&in_ready)position=position+take;
  if(retired==4096)begin $display("PORTABLE RTL SMOKE PASS scalars=%0d cycles=%0d",retired,cycles);$finish;end
  if(cycles>20000)$fatal(1,"Timeout");
 end
endmodule
