`timescale 1ns/1ps
// Fair fixed-baseline retiming trial: capture LUT sums at acceptance, rather
// than capturing their raw operands. Exact signed11 U+I -> signed12, same
// four advancing clocks and six-lane interface as original guard_add E2/E3.
// E2: fixed FOUR12 DSP for first four lanes plus two full-range LUT sums.
// E3: six full-range LUT sums. The DSP wrapper is reused unchanged.
module guard_add_retime #(parameter integer E=2)(
 input wire clk,rst,in_valid,out_ready,
 input wire[65:0]u_in,i_in,input wire[2:0]available,
 output wire in_ready,output wire[2:0]take,
 output reg out_valid=0,output reg[2:0]out_count=0,
 output reg[71:0]out_data=0,output wire narrow_mode);
 wire advance=!out_valid||out_ready;
 assign take=available;
 assign narrow_mode=1'b0;
 assign in_ready=advance;
 wire accept=in_valid&&advance&&(available!=0);
 reg v0=0,v1=0,v2=0;
 reg[2:0]cnt0=0,cnt1=0,cnt2=0;
 wire[71:0]answer;
 always @(posedge clk)begin
  if(rst)begin
   v0<=0;v1<=0;v2<=0;cnt0<=0;cnt1<=0;cnt2<=0;
   out_valid<=0;out_count<=0;out_data<=0;
  end else if(advance)begin
   v0<=accept;v1<=v0;v2<=v1;out_valid<=v2;
   if(accept)cnt0<=take;
   if(v0)cnt1<=cnt0;
   if(v1)cnt2<=cnt1;
   if(v2)begin
    out_count<=cnt2;
    for(integer l=0;l<6;l=l+1)
     out_data[12*l+:12]<=cnt2>l?answer[12*l+:12]:12'd0;
   end
  end
 end
 generate if(E==2)begin:hybrid
  reg[43:0]raw_u0=0,raw_i0=0;
  reg[23:0]sum0=0,sum1=0,sum2=0;
  wire[23:0]extra;
  wire[47:0]ab,c,p;
  for(genvar l=0;l<4;l=l+1)begin:encode
   assign ab[12*l+:12]={raw_u0[11*l+10],raw_u0[11*l+:11]};
   assign c[12*l+:12]={raw_i0[11*l+10],raw_i0[11*l+:11]};
   assign answer[12*l+:12]=p[12*l+:12];
  end
  for(genvar l=4;l<6;l=l+1)begin:lut
   wire signed[11:0]u12={u_in[11*l+10],u_in[11*l+:11]};
   wire signed[11:0]i12={i_in[11*l+10],i_in[11*l+:11]};
   (* use_dsp="no" *)wire signed[11:0]sum=u12+i12;
   assign extra[12*(l-4)+:12]=sum;
  end
  always @(posedge clk)begin
   if(rst)begin raw_u0<=0;raw_i0<=0;sum0<=0;sum1<=0;sum2<=0;end
   else if(advance)begin
    if(accept)begin raw_u0<=u_in[43:0];raw_i0<=i_in[43:0];sum0<=extra;end
    if(v0)sum1<=sum0;
    if(v1)sum2<=sum1;
   end
  end
  assign answer[71:48]=sum2;
  guard_add_dsp #(.SIMD("FOUR12"))d(
   .clk(clk),.rst(rst),.advance(advance),.operand_issue(v0),.sum_issue(v1),
   .ab(ab),.c(c),.p(p));
 end else begin:lut_all
  wire[71:0]sums;
  reg[71:0]sum0=0,sum1=0,sum2=0;
  for(genvar l=0;l<6;l=l+1)begin:lane
   wire signed[11:0]u12={u_in[11*l+10],u_in[11*l+:11]};
   wire signed[11:0]i12={i_in[11*l+10],i_in[11*l+:11]};
   (* use_dsp="no" *)wire signed[11:0]sum=u12+i12;
   assign sums[12*l+:12]=sum;
  end
  always @(posedge clk)begin
   if(rst)begin sum0<=0;sum1<=0;sum2<=0;end
   else if(advance)begin
    if(accept)sum0<=sums;
    if(v0)sum1<=sum0;
    if(v1)sum2<=sum1;
   end
  end
  assign answer=sum2;
 end endgenerate
endmodule
