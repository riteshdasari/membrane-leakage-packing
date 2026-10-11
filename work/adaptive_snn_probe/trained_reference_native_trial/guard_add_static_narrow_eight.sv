`timescale 1ns/1ps
// Fixed eight-lane signed8 U + signed8 I -> exact signed12 results.
// Interface operands are sign-extended to signed11 for matched comparisons.
// Every consumed U and I must fit signed8; available is in [0,8]. This core
// performs no range detection. An upstream static certificate must justify U8.
// Unavailable lanes may be arbitrary; their result slots are masked to zero.
// Four advancing clocks separate input acceptance from output handshake.
// The output stall freezes the entire pipeline, including the ONE48 DSP.
module guard_add_static_narrow_eight(
 input wire clk,rst,in_valid,out_ready,
 input wire[87:0]u_in,i_in,input wire[3:0]available,
 output wire in_ready,output wire[3:0]take,
 output wire out_valid,output wire[3:0]out_count,
 output wire[95:0]out_data,output wire narrow_mode);
 reg result_valid=0;
 reg[3:0]result_count=0;
 reg[95:0]result_data=0;
 wire advance=!result_valid||out_ready;
 assign take=available;
 assign narrow_mode=1'b0;
 assign in_ready=advance;
 assign out_valid=result_valid;
 assign out_count=result_count;
 assign out_data=result_data;
 wire accept=in_valid&&advance&&(available!=0);
 reg v0=0,v1=0,v2=0;
 reg[3:0]cnt0=0,cnt1=0,cnt2=0;
 wire[95:0]answer;
 always @(posedge clk)begin
  if(rst)begin
   v0<=0;v1<=0;v2<=0;cnt0<=0;cnt1<=0;cnt2<=0;
   result_valid<=0;result_count<=0;result_data<=0;
  end else if(advance)begin
   v0<=accept;v1<=v0;v2<=v1;result_valid<=v2;
   if(accept)cnt0<=take;
   if(v0)cnt1<=cnt0;
   if(v1)cnt2<=cnt1;
   if(v2)begin
    result_count<=cnt2;
    for(integer l=0;l<8;l=l+1)
     result_data[12*l+:12]<=cnt2>l?answer[12*l+:12]:12'd0;
   end
  end
 end
 // Euclidean radix32 residues form eight independent unsigned six-bit sums.
 // Each residue is at most 31, so its sum is at most 62: no lane spill occurs.
 reg[39:0]residue_u0=0,residue_i0=0;
 wire[47:0]ab,c,p;
 for(genvar l=0;l<8;l=l+1)begin:encode
  assign ab[6*l+:6]={1'b0,residue_u0[5*l+:5]};
  assign c[6*l+:6]={1'b0,residue_i0[5*l+:5]};
 end
 always @(posedge clk)begin
  if(rst)begin residue_u0<=0;residue_i0<=0;end
  else if(advance&&accept)begin
   for(integer l=0;l<8;l=l+1)begin
    residue_u0[5*l+:5]<=u_in[11*l+:5];
    residue_i0[5*l+:5]<=i_in[11*l+:5];
   end
  end
 end
 guard_add_dsp #(.SIMD("ONE48"))d(
  .clk(clk),.rst(rst),.advance(advance),.operand_issue(v0),.sum_issue(v1),
  .ab(ab),.c(c),.p(p));
 for(genvar l=0;l<8;l=l+1)begin:lane
  wire[2:0]hu=u_in[11*l+5+:3];
  wire[2:0]hi=i_in[11*l+5+:3];
  wire signed[3:0]hu4={hu[2],hu};
  wire signed[3:0]hi4={hi[2],hi};
  (* use_dsp="no" *)wire signed[3:0]base=hu4+hi4;
  reg[3:0]base0=0,base1=0,base2=0;
  always @(posedge clk)begin
   if(rst)begin base0<=0;base1<=0;base2<=0;end
   else if(advance)begin
    if(accept)base0<=base;
    if(v0)base1<=base0;
    if(v1)base2<=base1;
   end
  end
  wire signed[3:0]carry4={3'd0,p[6*l+5]};
  (* use_dsp="no" *)wire signed[3:0]high=$signed(base2)+carry4;
  wire[8:0]sum9={high,p[6*l+:5]};
  assign answer[12*l+:12]={{3{sum9[8]}},sum9};
 end
endmodule
