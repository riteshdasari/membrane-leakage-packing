`timescale 1ns/1ps
// E8 NARROW-DOMAIN ABLATION ONLY: signed9 U signextended on16-bitports.
// Exact ceil(beta*U/256), beta0..256. Noactualrangeadmission/full16support.
// E0 membrane9/precomp, E1 fixed split2, E2 LUT2, E3 scalarDSP2,
// E4 scalarDSP1, E5 membrane9/modulo2 post-correction reference.
// E6 model-specific exact shift2 control, legal only for beta128.
module sequential_leak_static9 #(parameter integer E=8,B=16)(
 input wire clk,rst,in_valid,out_ready,input wire[2*B-1:0]u_in,
 input wire[17:0]beta_in,input wire[1:0]available,
 output wire in_ready,out_valid,output wire[1:0]take,out_count,
 output wire[2*B-1:0]out_data,output wire narrow_mode);
 wire signed[B-1:0]raw0=u_in[0+:B],raw1=u_in[B+:B];
 wire[8:0]coef0=beta_in[0+:9],coef1=beta_in[9+:9];
 wire same=coef0==coef1;
 wire pair_ok=(available==2)&&same;
 assign take=available==0?0:((E==0||E==8)?(pair_ok?2:1):
    (E==1?((available==2&&same)?2:1):(E==4?1:available)));
 reg v1=0,v2=0;reg[1:0]count1=0,count2=0;
 reg[24:0]a_q=0;reg[2*B-1:0]u_q=0;reg[8:0]b0_q=0,b1_q=0;
 reg pack1=0,pack2=0,neg1=0,neg2=0,ref1=0,ref2=0;
 wire advance2=!v2||out_ready;
 assign in_ready=!rst&&(!v1||advance2);
 wire accept=in_valid&&in_ready&&(available!=0);
 wire issue=v1&&advance2&&!rst;
 wire prediction=(raw0<=-4)||((raw0==-3)&&(coef0>=86))||
    ((raw0==-2)&&(coef0>=128))||((raw0==-1)&&(coef0==256));
 wire[24:0]packed9={raw1[8:0],7'd0,~raw0[8],raw0[7:0]};
 wire[24:0]full_a={{16{raw0[8]}},raw0[8:0]}; // signed9-only scalar contract
 wire[24:0]split_a={1'b0,(take==2?raw1[7:0]:8'd0),8'd0,raw0[7:0]};
 always @(posedge clk)begin
  if(rst)begin
   v1<=0;v2<=0;count1<=0;count2<=0;a_q<=0;u_q<=0;b0_q<=0;b1_q<=0;
   pack1<=0;pack2<=0;neg1<=0;neg2<=0;ref1<=0;ref2<=0;
  end else begin
   if(advance2)begin
    v2<=v1;
    if(v1)begin count2<=count1;pack2<=pack1;neg2<=neg1;ref2<=ref1;end
   end
   if(in_ready)begin
    v1<=accept;
    if(accept)begin
     count1<=take;pack1<=pair_ok;neg1<=pair_ok&&prediction;
     ref1<=pair_ok&&((coef0[0]&raw1[0])^1'b1);
     b0_q<=coef0;b1_q<=take==2?coef1:9'd0;
     u_q<={(take==2?raw1:{B{1'b0}}),raw0};
     if(E==1)a_q<=split_a;
     else if(E==0||E==8)a_q<=pair_ok?packed9:full_a;
     else a_q<=full_a;
    end
   end
  end
 end
 assign out_valid=v2;assign out_count=count2;
 assign narrow_mode=(E==0||E==8)&&pack2;
 wire[2*B-1:0]answer;
 assign out_data={count2>1?answer[B+:B]:{B{1'b0}},
                  count2>0?answer[0+:B]:{B{1'b0}}};
 generate if(E==0||E==1||E==4||E==8)begin:one_dsp
  wire[7:0]neg_beta=8'd0-b0_q[7:0];
  wire c_flag=(E==0)?neg1:(b0_q==0);
  wire[47:0]packed_c={16'd0,8'd0,7'b1111111,c_flag,neg_beta,8'hff};
  wire[47:0]c=(E==1)?48'h000000ff00ff:
     ((E==0||E==8)&&pack1?packed_c:48'd255);
  wire[47:0]p;
  sequential_leak_dsp dsp(clk,rst,issue,a_q,{9'd0,b0_q},c,p);
  if(E==0)begin:pre
   wire[8:0]low9={neg2,p[15:8]};wire[8:0]high9=p[32:24];
   assign answer[0+:B]=pack2?{{(B-9){low9[8]}},low9}:p[B+7:8];
   assign answer[B+:B]=pack2?{{(B-9){high9[8]}},high9}:{B{1'b0}};
  end else if(E==8)begin:post
   wire spill=p[16]^ref2;
   wire[8:0]low9={spill,p[15:8]};
   (* use_dsp="no" *)wire[8:0]high9=p[32:24]+{8'd0,(spill&&(&p[23:16]))};
   assign answer[0+:B]=pack2?{{(B-9){low9[8]}},low9}:p[B+7:8];
   assign answer[B+:B]=pack2?{{(B-9){high9[8]}},high9}:{B{1'b0}};
  end else if(E==1)begin:split
   for(genvar l=0;l<2;l=l+1)begin:lane
    wire signed[B-9:0]h=u_q[l*B+8+:B-8];
    (* use_dsp="no" *)wire signed[B:0]product=h*$signed({1'b0,b0_q[7:0]});
    wire[B-1:0]hw={{8{h[B-9]}},h};
    wire[B-1:0]hp=b0_q[8]?(hw<<8):product[B-1:0];
    reg[B-1:0]high_q=0;
    always @(posedge clk)if(rst)high_q<=0;else if(issue)high_q<=count1>l?hp:{B{1'b0}};
    (* use_dsp="no" *)wire[B-1:0]s=high_q+{{(B-8){1'b0}},p[16*l+8+:8]};
    assign answer[l*B+:B]=s;
   end
  end else begin:scalar
   assign answer[0+:B]=p[B+7:8];assign answer[B+:B]={B{1'b0}};
  end
 end else if(E==2)begin:lut
  for(genvar l=0;l<2;l=l+1)begin:lane
   wire signed[B-1:0]u=u_q[l*B+:B];wire[8:0]b=l==0?b0_q:b1_q;
   (* use_dsp="no" *)wire signed[B+8:0]product=u*$signed({1'b0,b[7:0]});
   (* use_dsp="no" *)wire signed[B+8:0]rounded=product+255;
   reg[B-1:0]r=0;
   always @(posedge clk)if(rst)r<=0;else if(issue)r<=count1>l?(b[8]?u:(rounded>>>8)):{B{1'b0}};
   assign answer[l*B+:B]=r;
  end
 end else if(E==6)begin:shift128
  // Declared model-specific beta128 control: ceil(U/2), all signed16 values.
  // beta input is irrelevant to its arithmetic; caller must supply beta128.
  for(genvar l=0;l<2;l=l+1)begin:lane
   wire signed[B-1:0]u=u_q[l*B+:B];
   (* use_dsp="no" *)wire signed[B-1:0]half=u>>>1;
   (* use_dsp="no" *)wire signed[B-1:0]rounded_half=half+{{(B-1){1'b0}},u[0]};
   reg[B-1:0]r=0;
   always @(posedge clk)if(rst)r<=0;else if(issue)r<=count1>l?rounded_half:{B{1'b0}};
   assign answer[l*B+:B]=r;
  end
 end else begin:two_scalar
  for(genvar l=0;l<2;l=l+1)begin:lane
   wire signed[B-1:0]u=u_q[l*B+:B];wire[8:0]b=l==0?b0_q:b1_q;
   wire[47:0]p;
   sequential_leak_dsp dsp(clk,rst,issue,{{(25-B){u[B-1]}},u},{9'd0,b},48'd255,p);
   assign answer[l*B+:B]=p[B+7:8];
  end
 end endgenerate
endmodule
