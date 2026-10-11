`timescale 1ns/1ps
// Exact ordered signed11 U+I -> signed12; same policy as original guard_add E0.
// V0: offset-binary fields, aligned wide permutation, raw input registers.
// V1: same fields/policy, but register encoded operands at acceptance.
// Original guard_add.sv supplies the unchanged guard_add_dsp primitive wrapper.
module guard_add_layout #(parameter integer V=0)(
 input wire clk,rst,in_valid,out_ready,
 input wire[65:0]u_in,i_in,input wire[2:0]available,
 output wire in_ready,output wire[2:0]take,
 output reg out_valid=0,output reg[2:0]out_count=0,
 output reg[71:0]out_data=0,output wire narrow_mode);
 wire advance=!out_valid||out_ready;
 wire[10:0]u[0:5],i[0:5];wire[5:0]fit7;
 for(genvar l=0;l<6;l=l+1)begin:input_lane
  assign u[l]=u_in[11*l+:11];assign i[l]=i_in[11*l+:11];
  assign fit7[l]=(available<=l)||
                ((u[l][10:7]=={4{u[l][6]}})&&(i[l][10:7]=={4{i[l][6]}}));
 end
 wire copy5=(available>=5)&&(i[4]==0);
 wire copy6=copy5&&(available==6)&&(i[5]==0);
 wire fullcopy=(available==5&&copy5)||(available==6&&copy6);
 wire narrow=(available>=5)&&!fullcopy&&(&fit7);
 assign narrow_mode=narrow;
 assign take=(available==0)?3'd0:
             (narrow?available:(copy6?3'd6:(copy5?3'd5:(available>=4?3'd4:available))));
 assign in_ready=advance;
 wire accept=in_valid&&advance&&(available!=0);
 reg v0=0,v1=0,v2=0,n0=0,n1=0,n2=0;
 reg[2:0]cnt0=0,cnt1=0,cnt2=0;
 wire[47:0]ab0,c0,p;
 wire[21:0]copy_source0;
 reg[21:0]copy1=0,copy2=0;
 wire[71:0]answer;
 always @(posedge clk)begin
  if(rst)begin
   v0<=0;v1<=0;v2<=0;n0<=0;n1<=0;n2<=0;
   cnt0<=0;cnt1<=0;cnt2<=0;
   copy1<=0;copy2<=0;
   out_valid<=0;out_count<=0;out_data<=0;
  end else if(advance)begin
   v0<=accept;v1<=v0;v2<=v1;out_valid<=v2;
   if(accept)begin cnt0<=take;n0<=narrow;end
   if(v0)begin cnt1<=cnt0;n1<=n0;copy1<=copy_source0;end
   if(v1)begin cnt2<=cnt1;n2<=n1;copy2<=copy1;end
   if(v2)begin
    out_count<=cnt2;
    for(integer l=0;l<6;l=l+1)out_data[12*l+:12]<=cnt2>l?answer[12*l+:12]:12'd0;
   end
  end
 end
 generate if(V==0)begin:raw_capture
  reg[65:0]raw_u0=0,raw_i0=0;
  always @(posedge clk)begin
   if(rst)begin raw_u0<=0;raw_i0<=0;end
   else if(advance&&accept)begin raw_u0<=u_in;raw_i0<=i_in;end
  end
  guard_add_layout_encode encode(.u(raw_u0),.i(raw_i0),.narrow(n0),.ab(ab0),.c(c0));
  assign copy_source0=raw_u0[65:44];
 end else begin:packed_capture
  wire[47:0]encoded_u,encoded_i;
  reg[47:0]packed_u0=0,packed_i0=0;
  reg[21:0]copy0=0;
  // The current decision encodes the current payload before acceptance.
  guard_add_layout_encode encode(.u(u_in),.i(i_in),.narrow(narrow),.ab(encoded_u),.c(encoded_i));
  always @(posedge clk)begin
   if(rst)begin packed_u0<=0;packed_i0<=0;copy0<=0;end
   else if(advance&&accept)begin
    packed_u0<=encoded_u;packed_i0<=encoded_i;copy0<=u_in[65:44];
   end
  end
  assign ab0=packed_u0;assign c0=packed_i0;assign copy_source0=copy0;
 end endgenerate
 guard_add_dsp #(.SIMD("ONE48"))d(
  .clk(clk),.rst(rst),.advance(advance),.operand_issue(v0),.sum_issue(v1),
  .ab(ab0),.c(c0),.p(p));
 for(genvar l=0;l<6;l=l+1)begin:decode
  // Offset-binary sum is U+I+2^K. Flipping field bit K recovers signed K+1.
  wire[7:0]small_sum={~p[8*l+7],p[8*l+:7]};
  wire[11:0]small_answer={{4{small_sum[7]}},small_sum};
  if(l<4)begin:wide
   localparam integer F=(l==2)?3:((l==3)?2:l);
   wire[11:0]wide_answer={~p[12*F+11],p[12*F+:11]};
   assign answer[12*l+:12]=n2?small_answer:wide_answer;
  end else begin:copy
   wire[10:0]copied_u=copy2[11*(l-4)+:11];
   assign answer[12*l+:12]=n2?small_answer:{copied_u[10],copied_u};
  end
 end
endmodule

// Two fields start at the same physical bit in both formats: logical 0 and 3.
// Wide physical order is 0,1,3,2. Narrow physical order remains 0,1,2,3,4,5.
// Each biased payload plus the zero guard isolates arbitrary binary tail data.
module guard_add_layout_encode(
 input wire[65:0]u,i,input wire narrow,output wire[47:0]ab,c);
 wire[47:0]small_u,small_i,wide_u,wide_i;
 for(genvar l=0;l<6;l=l+1)begin:narrow_field
  assign small_u[8*l+:8]={1'b0,~u[11*l+6],u[11*l+:6]};
  assign small_i[8*l+:8]={1'b0,~i[11*l+6],i[11*l+:6]};
 end
 for(genvar f=0;f<4;f=f+1)begin:wide
  localparam integer L=(f==2)?3:((f==3)?2:f);
  assign wide_u[12*f+:12]={1'b0,~u[11*L+10],u[11*L+:10]};
  assign wide_i[12*f+:12]={1'b0,~i[11*L+10],i[11*L+:10]};
 end
 assign ab=narrow?small_u:wide_u;
 assign c=narrow?small_i:wide_i;
endmodule
