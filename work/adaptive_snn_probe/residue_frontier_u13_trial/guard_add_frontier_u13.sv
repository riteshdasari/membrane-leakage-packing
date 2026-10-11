`timescale 1ns/1ps
// Exact signed13 U plus statically sign-extended signed8 I -> signed14.
// Four advancing-edge pipeline, global output freeze and ordered prefixes.
// E0: fixed6 radix128, E1: fixed8 late recovery, E2: fixed8 high precompute,
// E3: native TWO24 two DSP lanes plus six fabric lanes, E4: eight fabric lanes,
// E5: five full-U13 lanes plus three actual-U8-admitted narrow tail lanes.
// Original IF safety is certified for 32 timesteps, not unbounded integration.
module guard_add_frontier_u13 #(parameter integer E=0)(
 input wire clk,rst,in_valid,out_ready,
 input wire[103:0]u_in,i_in,input wire[3:0]available,
 output wire in_ready,output wire[3:0]take,
 output wire out_valid,output wire[3:0]out_count,
 output wire[111:0]out_data,output wire narrow_mode);
  reg result_valid=0;
  reg[3:0]result_count=0;
  reg[111:0]result_data=0;
  wire advance=!result_valid||out_ready;
  wire tail5_fits8=(u_in[13*5+8+:5]=={5{u_in[13*5+7]}});
  wire tail6_fits8=(u_in[13*6+8+:5]=={5{u_in[13*6+7]}});
  wire tail7_fits8=(u_in[13*7+8+:5]=={5{u_in[13*7+7]}});
  wire[3:0]adaptive_prefix=(available<=5)?available:
       (!tail5_fits8?4'd5:
        ((available<=6||!tail6_fits8)?4'd6:
         ((available>=8&&tail7_fits8)?4'd8:4'd7)));
  assign take=(E==0)?((available>6)?4'd6:available):((E==5)?adaptive_prefix:available);
  assign narrow_mode=(E==5)&&(take>5);
  assign in_ready=advance;
  assign out_valid=result_valid;
  assign out_count=result_count;
  assign out_data=result_data;
  wire accept=in_valid&&advance&&(available!=0);
  reg v0=0,v1=0,v2=0;
  reg[3:0]cnt0=0,cnt1=0,cnt2=0;
  wire[111:0]answer;
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
      result_data[14*l+:14]<=cnt2>l?answer[14*l+:14]:14'd0;
    end
   end
  end
  generate if(E==0)begin:residue_six
   reg[41:0]residue_u0=0,residue_i0=0;
   wire[47:0]ab,c,p;
   for(genvar l=0;l<6;l=l+1)begin:lane
    assign ab[8*l+:8]={1'b0,residue_u0[7*l+:7]};
    assign c[8*l+:8]={1'b0,residue_i0[7*l+:7]};
    wire[5:0]hu=u_in[13*l+7+:6];
    wire hi=i_in[13*l+7];
    wire signed[6:0]hu7={hu[5],hu};
    wire signed[6:0]hi7={7{hi}};
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
    wire signed[6:0]carry7={6'd0,p[8*l+7]};
    (* use_dsp="no" *)wire signed[6:0]high=$signed(base2)+carry7;
    assign answer[14*l+:14]={high,p[8*l+:7]};
   end
   assign answer[111:84]=28'd0;
   always @(posedge clk)begin
    if(rst)begin residue_u0<=0;residue_i0<=0;end
    else if(advance&&accept)begin
     for(integer l=0;l<6;l=l+1)begin
      residue_u0[7*l+:7]<=u_in[13*l+:7];
      residue_i0[7*l+:7]<=i_in[13*l+:7];
     end
    end
   end
   guard_add_dsp #(.SIMD("ONE48"))d(
    .clk(clk),.rst(rst),.advance(advance),.operand_issue(v0),.sum_issue(v1),
    .ab(ab),.c(c),.p(p));
  end else if(E==1||E==2||E==5)begin:residue_eight
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
      residue_u0[5*l+:5]<=u_in[13*l+:5];
      residue_i0[5*l+:5]<=i_in[13*l+:5];
     end
    end
   end
   guard_add_dsp #(.SIMD("ONE48"))d(
    .clk(clk),.rst(rst),.advance(advance),.operand_issue(v0),.sum_issue(v1),
    .ab(ab),.c(c),.p(p));
   if(E==1)begin:retained_metadata
    reg[63:0]high_u0=0,high_u1=0,high_u2=0;
    reg[23:0]high_i0=0,high_i1=0,high_i2=0;
    always @(posedge clk)begin
     if(rst)begin
      high_u0<=0;high_u1<=0;high_u2<=0;
      high_i0<=0;high_i1<=0;high_i2<=0;
     end else if(advance)begin
      if(accept)begin
       for(integer l=0;l<8;l=l+1)begin
        high_u0[8*l+:8]<=u_in[13*l+5+:8];
        high_i0[3*l+:3]<=i_in[13*l+5+:3];
       end
      end
      if(v0)begin high_u1<=high_u0;high_i1<=high_i0;end
      if(v1)begin high_u2<=high_u1;high_i2<=high_i1;end
     end
    end
    for(genvar l=0;l<8;l=l+1)begin:recover
     wire[7:0]hu=high_u2[8*l+:8];
     wire[2:0]hi=high_i2[3*l+:3];
     wire signed[8:0]hu9={hu[7],hu};
     wire signed[8:0]hi9={{6{hi[2]}},hi};
     wire signed[8:0]carry9={8'd0,p[6*l+5]};
     (* use_dsp="no" *)wire signed[8:0]high=hu9+hi9+carry9;
     assign answer[14*l+:14]={high,p[6*l+:5]};
    end
   end else begin:precomputed_metadata
    for(genvar l=0;l<8;l=l+1)begin:lane
     if(E==5&&l>=5)begin:narrow_tail
      // Only consumed if U is signed8; arbitrary unused U13 is hidden.
      wire[2:0]hu=u_in[13*l+5+:3];
      wire[2:0]hi=i_in[13*l+5+:3];
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
      assign answer[14*l+:14]={{5{sum9[8]}},sum9};
     end else begin:full_lane
      wire[7:0]hu=u_in[13*l+5+:8];
      wire[2:0]hi=i_in[13*l+5+:3];
      wire signed[8:0]hu9={hu[7],hu};
      wire signed[8:0]hi9={{6{hi[2]}},hi};
      (* use_dsp="no" *)wire signed[8:0]base=hu9+hi9;
      reg[8:0]base0=0,base1=0,base2=0;
      always @(posedge clk)begin
       if(rst)begin base0<=0;base1<=0;base2<=0;end
       else if(advance)begin
        if(accept)base0<=base;
        if(v0)base1<=base0;
        if(v1)base2<=base1;
       end
      end
      wire signed[8:0]carry9={8'd0,p[6*l+5]};
      (* use_dsp="no" *)wire signed[8:0]high=$signed(base2)+carry9;
      assign answer[14*l+:14]={high,p[6*l+:5]};
     end
    end
   end
  end else if(E==3)begin:native_hybrid
   reg[25:0]raw_u0=0;
   reg[15:0]raw_i0=0;
   reg[83:0]sum0=0,sum1=0,sum2=0;
   wire[83:0]extra;
   wire[47:0]ab,c,p;
   for(genvar l=0;l<2;l=l+1)begin:encode
    assign ab[24*l+:24]={{11{raw_u0[13*l+12]}},raw_u0[13*l+:13]};
    assign c[24*l+:24]={{16{raw_i0[8*l+7]}},raw_i0[8*l+:8]};
    assign answer[14*l+:14]=p[24*l+:14];
   end
   for(genvar l=2;l<8;l=l+1)begin:fabric_lane
    wire signed[13:0]u14={u_in[13*l+12],u_in[13*l+:13]};
    wire signed[13:0]i14={{6{i_in[13*l+7]}},i_in[13*l+:8]};
    (* use_dsp="no" *)wire signed[13:0]sum=u14+i14;
    assign extra[14*(l-2)+:14]=sum;
   end
   always @(posedge clk)begin
    if(rst)begin raw_u0<=0;raw_i0<=0;sum0<=0;sum1<=0;sum2<=0;end
    else if(advance)begin
     if(accept)begin
      raw_u0<=u_in[25:0];
      for(integer l=0;l<2;l=l+1)raw_i0[8*l+:8]<=i_in[13*l+:8];
      sum0<=extra;
     end
     if(v0)sum1<=sum0;
     if(v1)sum2<=sum1;
    end
   end
   assign answer[111:28]=sum2;
   guard_add_dsp #(.SIMD("TWO24"))d(
    .clk(clk),.rst(rst),.advance(advance),.operand_issue(v0),.sum_issue(v1),
    .ab(ab),.c(c),.p(p));
  end else begin:fabric_all
   wire[111:0]sums;
   reg[111:0]sum0=0,sum1=0,sum2=0;
   for(genvar l=0;l<8;l=l+1)begin:lane
    wire signed[13:0]u14={u_in[13*l+12],u_in[13*l+:13]};
    wire signed[13:0]i14={{6{i_in[13*l+7]}},i_in[13*l+:8]};
    (* use_dsp="no" *)wire signed[13:0]sum=u14+i14;
    assign sums[14*l+:14]=sum;
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
 endgenerate
endmodule
