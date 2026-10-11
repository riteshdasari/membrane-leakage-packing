`timescale 1ns/1ps
// Same membrane-driven ordered5full+3narrow policy, isolated from DSP arithmetic.
// One advancing edge, exact signed13 U + signed8 I -> signed14.
module adaptive_natural_lut(input wire clk,rst,in_valid,out_ready,
 input wire[103:0]u_in,i_in,input wire[3:0]available,
 output wire in_ready,output wire[3:0]take,
 output wire out_valid,output wire[3:0]out_count,
 output wire[111:0]out_data,output wire narrow_mode);
 reg valid=0;reg[3:0]count=0;
 wire advance=!valid||out_ready;
 wire fits5=(u_in[13*5+8+:5]=={5{u_in[13*5+7]}});
 wire fits6=(u_in[13*6+8+:5]=={5{u_in[13*6+7]}});
 wire fits7=(u_in[13*7+8+:5]=={5{u_in[13*7+7]}});
 assign take=(available<=5)?available:
  (!fits5?4'd5:((available<=6||!fits6)?4'd6:
   ((available>=8&&fits7)?4'd8:4'd7)));
 assign narrow_mode=take>5;
 assign in_ready=advance;assign out_valid=valid;assign out_count=count;
 wire accept=in_valid&&advance&&(available!=0);
 always @(posedge clk)begin
  if(rst)begin valid<=0;count<=0;end
  else if(advance)begin valid<=accept;if(accept)count<=take;end
 end
 generate for(genvar l=0;l<8;l=l+1)begin:lane
  if(l<5)begin:full
   wire signed[13:0]u14={u_in[13*l+12],u_in[13*l+:13]};
   wire signed[13:0]i14={{6{i_in[13*l+7]}},i_in[13*l+:8]};
   (* use_dsp="no" *)wire signed[13:0]sum=u14+i14;
   reg[13:0]sum_reg=0;
   always @(posedge clk)if(rst)sum_reg<=0;else if(accept)sum_reg<=take>l?sum:14'd0;
   assign out_data[14*l+:14]=sum_reg;
  end else begin:narrow
   wire signed[8:0]u9={u_in[13*l+7],u_in[13*l+:8]};
   wire signed[8:0]i9={i_in[13*l+7],i_in[13*l+:8]};
   (* use_dsp="no" *)wire signed[8:0]sum=u9+i9;
   reg[8:0]sum_reg=0;
   always @(posedge clk)if(rst)sum_reg<=0;else if(accept)sum_reg<=take>l?sum:9'd0;
   assign out_data[14*l+:14]={{5{sum_reg[8]}},sum_reg};
  end
 end endgenerate
endmodule
