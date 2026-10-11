`timescale 1ns/1ps
// Ordered exact signed11 U + sign-extended signed8 I -> signed12 results.
// All engines have one four-advancing-edge pipeline and a global output freeze.
// E0: frozen six-field selective V2, adapted to the common eight-value window.
// E1: eight radix32 residue fields; retain high operands for late recovery.
// E2: same eight fields; precompute high bases at acceptance.
// E3: four native FOUR12 DSP sums plus four captured fabric sums.
// E4: eight captured fabric sums.
// E5: common radix32 layout; five full-range lanes and three exact signed8-U lanes.
// E5 consumes a longer ordered prefix only when the actual tail U fits signed8.
// No consumed operand is requantized, and no exception stalls or layout mux exist.
module guard_add_frontier_f5 #(parameter integer E=0)(
 input wire clk,rst,in_valid,out_ready,
 input wire[87:0]u_in,i_in,input wire[3:0]available,
 output wire in_ready,output wire[3:0]take,
 output wire out_valid,output wire[3:0]out_count,
 output wire[95:0]out_data,output wire narrow_mode);
 generate if(E==0)begin:frozen_six
  wire[2:0]six_take,six_count;
  wire[71:0]six_data;
  wire six_mode;
  wire[3:0]prefix=(available>6)?4'd6:available;
  guard_add_selective #(.V(2)) reference_core(
   .clk(clk),.rst(rst),.in_valid(in_valid),.out_ready(out_ready),
   .u_in(u_in[65:0]),.i_in(i_in[65:0]),.available(prefix[2:0]),
   .in_ready(in_ready),.take(six_take),.out_valid(out_valid),
   .out_count(six_count),.out_data(six_data),.narrow_mode(six_mode));
  assign take={1'b0,six_take};
  assign out_count={1'b0,six_count};
  assign out_data={24'd0,six_data};
  assign narrow_mode=six_mode;
 end else begin:eight_window
  reg result_valid=0;
  reg[3:0]result_count=0;
  reg[95:0]result_data=0;
  wire advance=!result_valid||out_ready;
  wire tail5_fits8=(u_in[11*5+8+:3]=={3{u_in[11*5+7]}});
  wire tail6_fits8=(u_in[11*6+8+:3]=={3{u_in[11*6+7]}});
  wire tail7_fits8=(u_in[11*7+8+:3]=={3{u_in[11*7+7]}});
  wire[3:0]adaptive_prefix=(available<=5)?available:
       (!tail5_fits8?4'd5:
        ((available<=6||!tail6_fits8)?4'd6:
         ((available>=8&&tail7_fits8)?4'd8:4'd7)));
  assign take=(E==5)?adaptive_prefix:available;
  assign narrow_mode=(E==5)&&(take>5);
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
  if(E==1||E==2||E==5)begin:residue_eight
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
   if(E==1)begin:retained_metadata
    reg[47:0]high_u0=0,high_u1=0,high_u2=0;
    reg[23:0]high_i0=0,high_i1=0,high_i2=0;
    always @(posedge clk)begin
     if(rst)begin
      high_u0<=0;high_u1<=0;high_u2<=0;
      high_i0<=0;high_i1<=0;high_i2<=0;
     end else if(advance)begin
      if(accept)begin
       for(integer l=0;l<8;l=l+1)begin
        high_u0[6*l+:6]<=u_in[11*l+5+:6];
        high_i0[3*l+:3]<=i_in[11*l+5+:3];
       end
      end
      if(v0)begin high_u1<=high_u0;high_i1<=high_i0;end
      if(v1)begin high_u2<=high_u1;high_i2<=high_i1;end
     end
    end
    for(genvar l=0;l<8;l=l+1)begin:recover
     wire[5:0]hu=high_u2[6*l+:6];
     wire[2:0]hi=high_i2[3*l+:3];
     wire signed[6:0]hu7={hu[5],hu};
     wire signed[6:0]hi7={{4{hi[2]}},hi};
     wire signed[6:0]carry7={6'd0,p[6*l+5]};
     (* use_dsp="no" *)wire signed[6:0]high=hu7+hi7+carry7;
     assign answer[12*l+:12]={high,p[6*l+:5]};
    end
   end else begin:precomputed_metadata
    for(genvar l=0;l<8;l=l+1)begin:lane
     if(E==5&&l>=5)begin:narrow_tail
      // Only consumed if U is signed8; arbitrary unused wide U is hidden.
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
     end else begin:full_lane
      wire[5:0]hu=u_in[11*l+5+:6];
      wire[2:0]hi=i_in[11*l+5+:3];
      wire signed[6:0]hu7={hu[5],hu};
      wire signed[6:0]hi7={{4{hi[2]}},hi};
      (* use_dsp="no" *)wire signed[6:0]base=hu7+hi7;
      reg[6:0]base0=0,base1=0,base2=0;
      always @(posedge clk)begin
       if(rst)begin base0<=0;base1<=0;base2<=0;end
       else if(advance)begin
        if(accept)base0<=base;
        if(v0)base1<=base0;
        if(v1)base2<=base1;
       end
      end
      wire signed[6:0]carry7={6'd0,p[6*l+5]};
      (* use_dsp="no" *)wire signed[6:0]high=$signed(base2)+carry7;
      assign answer[12*l+:12]={high,p[6*l+:5]};
     end
    end
   end
  end else if(E==3)begin:native_hybrid
   reg[43:0]raw_u0=0;
   reg[31:0]raw_i0=0;
   reg[47:0]sum0=0,sum1=0,sum2=0;
   wire[47:0]extra,ab,c,p;
   for(genvar l=0;l<4;l=l+1)begin:encode
    assign ab[12*l+:12]={raw_u0[11*l+10],raw_u0[11*l+:11]};
    assign c[12*l+:12]={{4{raw_i0[8*l+7]}},raw_i0[8*l+:8]};
    assign answer[12*l+:12]=p[12*l+:12];
   end
   for(genvar l=4;l<8;l=l+1)begin:fabric_lane
    wire signed[11:0]u12={u_in[11*l+10],u_in[11*l+:11]};
    wire signed[11:0]i12={{4{i_in[11*l+7]}},i_in[11*l+:8]};
    (* use_dsp="no" *)wire signed[11:0]sum=u12+i12;
    assign extra[12*(l-4)+:12]=sum;
   end
   always @(posedge clk)begin
    if(rst)begin raw_u0<=0;raw_i0<=0;sum0<=0;sum1<=0;sum2<=0;end
    else if(advance)begin
     if(accept)begin
      raw_u0<=u_in[43:0];
      for(integer l=0;l<4;l=l+1)raw_i0[8*l+:8]<=i_in[11*l+:8];
      sum0<=extra;
     end
     if(v0)sum1<=sum0;
     if(v1)sum2<=sum1;
    end
   end
   assign answer[95:48]=sum2;
   guard_add_dsp #(.SIMD("FOUR12"))d(
    .clk(clk),.rst(rst),.advance(advance),.operand_issue(v0),.sum_issue(v1),
    .ab(ab),.c(c),.p(p));
  end else begin:fabric_all
   wire[95:0]sums;
   reg[95:0]sum0=0,sum1=0,sum2=0;
   for(genvar l=0;l<8;l=l+1)begin:lane
    wire signed[11:0]u12={u_in[11*l+10],u_in[11*l+:11]};
    wire signed[11:0]i12={{4{i_in[11*l+7]}},i_in[11*l+:8]};
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
  end
 end endgenerate
endmodule
