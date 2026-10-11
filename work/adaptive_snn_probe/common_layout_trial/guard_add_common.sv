`timescale 1ns/1ps
// Exact signed int11 U + signed int11 I -> signed int12 for six ordered lanes.
// The ONE48 DSP has one immutable six-by-eight-bit unsigned-residue layout.
// U = 128*hU + rU, with hU signed4 and rU unsigned7 (likewise for I).
// Every DSP field computes rU+rI <=254, so no carry enters the next field.
// The field's bit7 is the carry c; {hU+hI+c, field[6:0]} is the exact result.
// V0: precompute signed5 hU+hI at acceptance, add the DSP carry at output.
// V1: retain the two signed4 highs, combine them with carry at output.
// This is a FIXED layout reference, not adaptive lane-count packing.
// Same ports and four advancing-clock contract as guard_add E2/E3. Binary
// unavailable tails are allowed; unused output lanes are masked to zero.
module guard_add_common #(parameter integer V=0)(
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
 reg[41:0]residue_u0=0,residue_i0=0;
 wire[47:0]ab,c,p;
 wire[71:0]answer;
 for(genvar l=0;l<6;l=l+1)begin:residue_encode
  assign ab[8*l+:8]={1'b0,residue_u0[7*l+:7]};
  assign c[8*l+:8]={1'b0,residue_i0[7*l+:7]};
 end
 always @(posedge clk)begin
  if(rst)begin
   v0<=0;v1<=0;v2<=0;cnt0<=0;cnt1<=0;cnt2<=0;
   residue_u0<=0;residue_i0<=0;
   out_valid<=0;out_count<=0;out_data<=0;
  end else if(advance)begin
   v0<=accept;v1<=v0;v2<=v1;out_valid<=v2;
   if(accept)begin
    cnt0<=take;
    for(integer l=0;l<6;l=l+1)begin
     residue_u0[7*l+:7]<=u_in[11*l+:7];
     residue_i0[7*l+:7]<=i_in[11*l+:7];
    end
   end
   if(v0)cnt1<=cnt0;
   if(v1)cnt2<=cnt1;
   if(v2)begin
    out_count<=cnt2;
    for(integer l=0;l<6;l=l+1)
     out_data[12*l+:12]<=cnt2>l?answer[12*l+:12]:12'd0;
   end
  end
 end
 guard_add_dsp #(.SIMD("ONE48"))d(
  .clk(clk),.rst(rst),.advance(advance),.operand_issue(v0),.sum_issue(v1),
  .ab(ab),.c(c),.p(p));
 generate if(V==0)begin:precomputed_high
  wire[29:0]high_sums;
  reg[29:0]high0=0,high1=0,high2=0;
  for(genvar l=0;l<6;l=l+1)begin:lane
   wire signed[4:0]hu={u_in[11*l+10],u_in[11*l+7+:4]};
   wire signed[4:0]hi={i_in[11*l+10],i_in[11*l+7+:4]};
   (* use_dsp="no" *)wire signed[4:0]sum=hu+hi;
   assign high_sums[5*l+:5]=sum;
   wire signed[4:0]stored_high=high2[5*l+:5];
   wire signed[4:0]carry={4'd0,p[8*l+7]};
   (* use_dsp="no" *)wire signed[4:0]corrected_high=stored_high+carry;
   assign answer[12*l+:12]={corrected_high,p[8*l+:7]};
  end
  always @(posedge clk)begin
   if(rst)begin high0<=0;high1<=0;high2<=0;end
   else if(advance)begin
    if(accept)high0<=high_sums;
    if(v0)high1<=high0;
    if(v1)high2<=high1;
   end
  end
 end else begin:combined_high
  reg[23:0]high_u0=0,high_i0=0,high_u1=0,high_i1=0,high_u2=0,high_i2=0;
  for(genvar l=0;l<6;l=l+1)begin:lane
   wire signed[4:0]hu={high_u2[4*l+3],high_u2[4*l+:4]};
   wire signed[4:0]hi={high_i2[4*l+3],high_i2[4*l+:4]};
   wire signed[4:0]carry={4'd0,p[8*l+7]};
   (* use_dsp="no" *)wire signed[4:0]corrected_high=hu+hi+carry;
   assign answer[12*l+:12]={corrected_high,p[8*l+:7]};
  end
  always @(posedge clk)begin
   if(rst)begin
    high_u0<=0;high_i0<=0;high_u1<=0;high_i1<=0;high_u2<=0;high_i2<=0;
   end else if(advance)begin
    if(accept)begin
     for(integer l=0;l<6;l=l+1)begin
      high_u0[4*l+:4]<=u_in[11*l+7+:4];
      high_i0[4*l+:4]<=i_in[11*l+7+:4];
     end
    end
    if(v0)begin high_u1<=high_u0;high_i1<=high_i0;end
    if(v1)begin high_u2<=high_u1;high_i2<=high_i1;end
   end
  end
 end endgenerate
endmodule
