`timescale 1ns/1ps
module natural_lut(input wire clk,rst,in_valid,out_ready,
 input wire[103:0]u_in,i_in,input wire[3:0]available,
 output wire in_ready,output wire[3:0]take,
 output wire out_valid,output wire[3:0]out_count,
 output wire[111:0]out_data,output wire narrow_mode);
 reg valid=0;reg[3:0]count=0;reg[111:0]data=0;
 wire advance=!valid||out_ready;
 assign in_ready=advance;assign take=available;
 assign out_valid=valid;assign out_count=count;assign out_data=data;
 assign narrow_mode=1'b0;
 wire accept=in_valid&&advance&&(available!=0);
 wire[111:0]sums;
 generate for(genvar l=0;l<8;l=l+1)begin:lane
  wire signed[13:0]u14={u_in[13*l+12],u_in[13*l+:13]};
  wire signed[13:0]i14={{6{i_in[13*l+7]}},i_in[13*l+:8]};
  (* use_dsp="no" *)wire signed[13:0]sum=u14+i14;
  assign sums[14*l+:14]=sum;
 end endgenerate
 always @(posedge clk)begin
  if(rst)begin valid<=0;count<=0;data<=0;end
  else if(advance)begin
   valid<=accept;
   if(accept)begin count<=available;
    for(integer l=0;l<8;l=l+1)data[14*l+:14]<=available>l?sums[14*l+:14]:14'd0;
   end
  end
 end
endmodule
