`timescale 1ns/1ps
// Strong fixed full-range baseline: U=256*h+r, r signed int8.
// ceil(beta*U/256)=beta*h+ceil(beta*r/256). Always exact over signed int10.
// Two registered compute stages after accepting inputs, one pair per clock.
// E=0 packs both low residues in one DSP and corrects high bits in fabric.
// E=1 implements the same complete int10 operation in LUTs, two stages.
module split_leak #(parameter E=0,BC=231)(input wire clk,rst,valid,
 input wire[19:0]u_in,input wire[8:0]beta,output reg out_valid=0,
 output reg[19:0]u_out=0);
 reg v0=0,v1=0;
 reg[19:0]uq=0;reg[8:0]bq=0;
 wire[8:0]coef=BC<0?bq:BC;
 always @(posedge clk)begin
  if(rst)begin uq<=0;bq<=0;v0<=0;v1<=0;out_valid<=0;end
  else begin
   v0<=valid;v1<=v0;out_valid<=v1;
   if(valid)begin uq<=u_in;if(BC<0)bq<=beta;end
  end
 end
 generate if(E==0)begin:split
  wire[15:0]low_in={u_in[17:10],u_in[7:0]};
  wire[15:0]low_out;
  wire low_valid;
  packed_leak #(.E(0),.B(8),.BC(BC))low(.clk(clk),.rst(rst),.valid(valid),
   .u_in(low_in),.beta(beta),.out_valid(low_valid),.u_out(low_out));
  for(genvar i=0;i<2;i=i+1)begin:lane
   wire signed[2:0]top={{1{uq[i*10+9]}},uq[i*10+8+:2]};
   wire signed[2:0]h=top+$signed({2'b0,uq[i*10+7]});
   wire signed[9:0]cb={1'b0,coef};
   (* use_dsp="no" *) wire signed[12:0]hi_product=h*cb;
   reg signed[10:0]hi_q=0;
   wire signed[7:0]r=low_out[i*8+:8];
   wire signed[10:0]sum=hi_q+{{3{r[7]}},r};
   always @(posedge clk)begin
    if(rst)begin hi_q<=0;u_out[i*10+:10]<=0;end
    else begin
     if(v0)hi_q<=hi_product;
     if(v1)u_out[i*10+:10]<=sum;
    end
   end
  end
 end else begin:lut
  for(genvar i=0;i<2;i=i+1)begin:lane
   wire signed[9:0]u=uq[i*10+:10],cb={1'b0,coef};
   (* use_dsp="no" *) wire signed[19:0]p=u*cb;
   reg signed[17:0]product_q=0;
   wire signed[17:0]rounded=product_q+255;
   always @(posedge clk)begin
    if(rst)begin product_q<=0;u_out[i*10+:10]<=0;end
    else begin
     if(v0)product_q<=p;
     if(v1)u_out[i*10+:10]<=rounded>>>8;
    end
   end
  end
 end endgenerate
endmodule
`define SPLIT_TOP(NAME,ENGINE,COEF) \
module NAME(input wire clk,rst,valid,input wire[19:0]u_in,input wire[8:0]beta, \
 output wire out_valid,output wire[19:0]u_out); \
 split_leak #(.E(ENGINE),.BC(COEF))u(.*);endmodule
`SPLIT_TOP(top_leak_split10_const,0,231)
`SPLIT_TOP(top_leak_lut10_pipe_const,1,231)
`SPLIT_TOP(top_leak_split10_prog,0,-1)
`SPLIT_TOP(top_leak_lut10_pipe_prog,1,-1)
