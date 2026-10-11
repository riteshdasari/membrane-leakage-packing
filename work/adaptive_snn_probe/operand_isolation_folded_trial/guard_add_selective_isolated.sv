`timescale 1ns/1ps
// Six immutable unsigned-residue DSP fields, with exact high-part recovery.
// Full domain: signed11 U + signed11 I -> signed12 U+I (V0/V1).
// Current8 domain: signed11 U + sign-extended signed8 I (V2/V3).
// V0 fixed six parallel high adders; V1 one shared high fallback corrector.
// V2 fixed six parallel high adders with a statically signed8 current;
// V3 one shared high fallback corrector with that same current8 contract.
// Shared variants use the exact fast union: both U/I signed8 OR
// (I signed8 AND residue carry == sign(I)). All other valid lanes use the
// full signed5 hU+hI+carry corrector. First correction occurs in the normal
// output stage; k bad lanes require max(k-1,0) extra globally frozen clocks.
// Partial outputs have out_valid=0; completed outputs honor backpressure.
// Lane-count/layout remain fixed, so this is adaptive EXACT CORRECTION,
// not variable lane-count DSP packing. Binary ignored tails may be arbitrary.
module guard_add_selective_isolated #(parameter integer V=3, parameter integer ISOLATE=1)(
 input wire clk,rst,in_valid,out_ready,
 input wire[65:0]u_in,i_in,input wire[2:0]available,
 output wire in_ready,output wire[2:0]take,
 output reg out_valid=0,output reg[2:0]out_count=0,
 output reg[71:0]out_data=0,output wire narrow_mode);
 localparam integer SHARED=(V==1||V==3);
 localparam integer CURRENT8=(V>=2);
 wire output_space=!out_valid||out_ready;
 reg busy=0;
 reg[5:0]pending_mask=0;
 reg v0=0,v1=0,v2=0;
 reg[2:0]cnt0=0,cnt1=0,cnt2=0;
 reg[41:0]residue_u0=0,residue_i0=0;
 reg[23:0]high_u0=0,high_u1=0,high_u2=0;
 wire[47:0]ab,c,p;
 wire[3:0]hu[0:5],hi[0:5];
 wire[71:0]parallel_answer,fast_answer;
 wire[5:0]bad_mask;
 wire[5:0]work_mask=busy?pending_mask:bad_mask;
 reg[2:0]selected_lane;
 reg[5:0]selected_mask;
 always @* begin
  selected_lane=0;selected_mask=0;
  if(work_mask[0])begin selected_lane=0;selected_mask=6'b000001;end
  else if(work_mask[1])begin selected_lane=1;selected_mask=6'b000010;end
  else if(work_mask[2])begin selected_lane=2;selected_mask=6'b000100;end
  else if(work_mask[3])begin selected_lane=3;selected_mask=6'b001000;end
  else if(work_mask[4])begin selected_lane=4;selected_mask=6'b010000;end
  else if(work_mask[5])begin selected_lane=5;selected_mask=6'b100000;end
 end
 wire[5:0]next_mask=work_mask&~selected_mask;
 wire remaining_any=|next_mask;
 wire multiple_bad=(|bad_mask)&&remaining_any;
 // When idle, freeze only for a pending output with at least two bad lanes.
 // When busy, preserve P/high2 and assemble one high result each physical
 // clock; the last correction advances and consumes v2 exactly once.
 wire advance=output_space&&(!SHARED||
                  (busy?!remaining_any:(!v2||!multiple_bad)));
 wire correction_step=SHARED&&output_space&&v2&&(|work_mask);
 assign in_ready=advance;
 assign take=available;
 assign narrow_mode=1'b0;
 wire accept=in_valid&&advance&&(available!=0);
 for(genvar l=0;l<6;l=l+1)begin:lane
  assign ab[8*l+:8]={1'b0,residue_u0[7*l+:7]};
  assign c[8*l+:8]={1'b0,residue_i0[7*l+:7]};
  assign hu[l]=high_u2[4*l+:4];
  wire u_fits8=(hu[l]==4'b0000)||(hu[l]==4'b1111);
  wire i_fits8=CURRENT8||(hi[l]==4'b0000)||(hi[l]==4'b1111);
  wire residue_carry=p[8*l+7];
  wire fast_small=u_fits8&&i_fits8;
  wire fast_copy=i_fits8&&(residue_carry==hi[l][0]);
  assign bad_mask[l]=(cnt2>l)&&!fast_small&&!fast_copy;
  wire signed[4:0]hu5={hu[l][3],hu[l]};
  wire signed[4:0]hi5={hi[l][3],hi[l]};
  wire signed[4:0]carry5={4'd0,residue_carry};
  (* use_dsp="no" *)wire signed[4:0]parallel_high=hu5+hi5+carry5;
  assign parallel_answer[12*l+:12]={parallel_high,p[8*l+:7]};
  // In the signed8/signed8 branch the exact high lies in [-2,1].
  wire signed[1:0]small_c={1'b0,residue_carry};
  wire signed[1:0]small_u={1'b0,hu[l][0]};
  wire signed[1:0]small_i={1'b0,hi[l][0]};
  (* use_dsp="no" *)wire signed[1:0]small_high=small_c-small_u-small_i;
  wire[4:0]fast_high=fast_small?{{3{small_high[1]}},small_high}:
                              (fast_copy?hu5:5'd0);
  assign fast_answer[12*l+:12]={fast_high,p[8*l+:7]};
 end
 // High U metadata is common to both operand-domain profiles.
 always @(posedge clk)begin
  if(rst)begin
   v0<=0;v1<=0;v2<=0;cnt0<=0;cnt1<=0;cnt2<=0;
   residue_u0<=0;residue_i0<=0;high_u0<=0;high_u1<=0;high_u2<=0;
  end else if(advance)begin
   v0<=accept;v1<=v0;v2<=v1;
   if(accept)begin
    cnt0<=take;
    for(integer l=0;l<6;l=l+1)begin
     residue_u0[7*l+:7]<=u_in[11*l+:7];
     residue_i0[7*l+:7]<=i_in[11*l+:7];
     high_u0[4*l+:4]<=u_in[11*l+7+:4];
    end
   end
   if(v0)begin cnt1<=cnt0;high_u1<=high_u0;end
   if(v1)begin cnt2<=cnt1;high_u2<=high_u1;end
  end
 end
 generate if(CURRENT8)begin:current8_metadata
  reg[5:0]sign_i0=0,sign_i1=0,sign_i2=0;
  for(genvar l=0;l<6;l=l+1)begin:lane
   // For the declared I8 domain, bits[10:7] are four copies of sign(I8).
   assign hi[l]={4{sign_i2[l]}};
  end
  always @(posedge clk)begin
   if(rst)begin sign_i0<=0;sign_i1<=0;sign_i2<=0;end
   else if(advance)begin
    if(accept)begin
     for(integer l=0;l<6;l=l+1)sign_i0[l]<=i_in[11*l+7];
    end
    if(v0)sign_i1<=sign_i0;
    if(v1)sign_i2<=sign_i1;
   end
  end
 end else begin:full_current_metadata
  reg[23:0]high_i0=0,high_i1=0,high_i2=0;
  for(genvar l=0;l<6;l=l+1)begin:lane
   assign hi[l]=high_i2[4*l+:4];
  end
  always @(posedge clk)begin
   if(rst)begin high_i0<=0;high_i1<=0;high_i2<=0;end
   else if(advance)begin
    if(accept)begin
     for(integer l=0;l<6;l=l+1)high_i0[4*l+:4]<=i_in[11*l+7+:4];
    end
    if(v0)high_i1<=high_i0;
    if(v1)high_i2<=high_i1;
   end
  end
 end endgenerate
 guard_add_dsp #(.SIMD("ONE48"))d(
  .clk(clk),.rst(rst),.advance(advance),.operand_issue(v0),.sum_issue(v1),
  .ab(ab),.c(c),.p(p));
 // Only one full-range high addition is reachable in shared variants.
 wire[3:0]selected_hu=hu[selected_lane];
 wire[3:0]selected_hi=hi[selected_lane];
 wire signed[4:0]selected_hu5={selected_hu[3],selected_hu};
 wire signed[4:0]selected_hi5={selected_hi[3],selected_hi};
 wire signed[4:0]selected_carry5={4'd0,p[8*selected_lane+7]};
 (* use_dsp="no" *)wire signed[4:0]corrected_high;
 generate if(CURRENT8&&SHARED)begin:current8_bad_correction
  // A selected bad lane failed the carry==sign(I8) fast-copy certificate,
  // so c!=sign(I8). Therefore hI+c is exactly +1 or -1. The shared
  // current8 fallback need not select or add the DSP carry separately.
  // Fold zero isolation into the existing one-hot lane selection.
  // selected_mask has one bit set for work, and is zero when no lane is bad.
  // This keeps a separate v2/any-work enable out of the selected HU adder.
  reg[3:0]masked_hu;
  reg masked_negative;
  always @* begin
   masked_hu=0;masked_negative=0;
   for(integer r=0;r<6;r=r+1)begin
    masked_hu=masked_hu|(hu[r]&{4{selected_mask[r]}});
    masked_negative=masked_negative|(hi[r][0]&selected_mask[r]);
   end
  end
  wire selected_any=|selected_mask;
  wire signed[4:0]adjustment=selected_hi[0]?5'b11111:5'b00001;
  wire signed[4:0]isolated_hu=ISOLATE?{masked_hu[3],masked_hu}:selected_hu5;
  wire signed[4:0]isolated_adjustment=ISOLATE?
   (selected_any?(masked_negative?5'b11111:5'b00001):5'd0):adjustment;
  assign corrected_high=isolated_hu+isolated_adjustment;
 end else begin:full_bad_correction
  assign corrected_high=selected_hu5+selected_hi5+selected_carry5;
 end endgenerate
 always @(posedge clk)begin
  if(rst)begin
   out_valid<=0;out_count<=0;out_data<=0;busy<=0;pending_mask<=0;
  end else if(output_space)begin
   if(SHARED)begin
    if(busy)begin
     // P/high2, count2, and the lane order stay frozen until the last lane.
     // Existing low bits and previously corrected high bits are retained.
     for(integer l=0;l<6;l=l+1)
      if(correction_step&&selected_mask[l])out_data[12*l+7+:5]<=corrected_high;
     pending_mask<=next_mask;
     busy<=remaining_any;
     out_valid<=!remaining_any;
     if(!remaining_any)out_count<=cnt2;
    end else if(v2)begin
     // Consume any prior ready output, then begin or finish the new output.
     // A partial assembly is never presented as a valid result.
     for(integer l=0;l<6;l=l+1)begin
      out_data[12*l+:12]<=cnt2>l?fast_answer[12*l+:12]:12'd0;
      if(correction_step&&selected_mask[l])out_data[12*l+7+:5]<=corrected_high;
     end
     out_count<=cnt2;
     pending_mask<=next_mask;
     busy<=multiple_bad;
     out_valid<=!multiple_bad;
    end else begin
     out_valid<=0;busy<=0;pending_mask<=0;
    end
   end else begin
    out_valid<=v2;busy<=0;pending_mask<=0;
    if(v2)begin
     out_count<=cnt2;
     for(integer l=0;l<6;l=l+1)
      out_data[12*l+:12]<=cnt2>l?parallel_answer[12*l+:12]:12'd0;
    end
   end
  end
 end
endmodule
