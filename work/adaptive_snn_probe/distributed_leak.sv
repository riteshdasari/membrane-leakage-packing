`timescale 1ns/1ps
// Strong constant-beta LUT alternatives; no DSP. Same one-compute-stage contract.
// E=0 uses ceil(231*U/256)=U-floor(25*U/256), 25=16+8+1.
// E=1 uses a constant 256-entry table with two read addresses.
module distributed_leak #(parameter E=0)(input wire clk,rst,valid,
 input wire[15:0]u_in,input wire[8:0]beta,output reg out_valid=0,
 output wire[15:0]u_out);
 reg[15:0]uq=0;reg vq=0;
 always @(posedge clk)begin
  if(rst)begin uq<=0;vq<=0;out_valid<=0;end
  else begin vq<=valid;out_valid<=vq;if(valid)uq<=u_in;end
 end
 (* rom_style="distributed" *) reg[7:0]rom[0:255];
 integer j,s,p;
 initial for(j=0;j<256;j=j+1)begin
  s=j<128?j:j-256;p=231*s;
  rom[j]=p>0?(p+255)/256:p/256;
 end
 for(genvar i=0;i<2;i=i+1)begin:lane
  wire signed[7:0]u=uq[i*8+:8];
  wire signed[12:0]x={{5{u[7]}},u};
  wire signed[12:0]p25=(x<<<4)+(x<<<3)+x;
  wire signed[12:0]y=x-(p25>>>8);
  reg[7:0]result=0;
  always @(posedge clk)begin
   if(rst)result<=0;else if(vq)result<=E==0?y:rom[uq[i*8+:8]];
  end
  assign u_out[i*8+:8]=result;
 end
endmodule
module top_leak_unused_dist_factored(input wire clk,rst,valid,input wire[15:0]u_in,input wire[8:0]beta,
 output wire out_valid,output wire[15:0]u_out);
 distributed_leak #(.E(0))u(.*);
endmodule
module top_leak_lut8_distributed(input wire clk,rst,valid,input wire[15:0]u_in,input wire[8:0]beta,
 output wire out_valid,output wire[15:0]u_out);
 distributed_leak #(.E(1))u(.*);
endmodule
