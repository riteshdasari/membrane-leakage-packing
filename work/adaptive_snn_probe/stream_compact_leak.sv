`timescale 1ns/1ps
// Raw ordered window; consume/return 1..3 real neurons. Exact int11 leakage.
// E0: absolute-int5 OR equal-upper-bits shared offset, else fixed wide pair.
// E1: fixed wide DSP pair. E2: LUT pair. E3: LUT triple.
// E4: fixed full-range DSP triple, with three independent high corrections.
// E5: fixed DSP pair plus one exact LUT lane. E6: direct signed-int5 triple.
// DC=-1 allows a new shared delta[0..31] on every accepted request.
// All engines consume three when the third is zero or the operation is identity.
// All data/metadata and DSP stages freeze on output backpressure.
module stream_compact_leak #(parameter E=0,DC=25)(
 input wire clk,rst,in_valid,out_ready,
 input wire[32:0]u_in,input wire[1:0]available,input wire[4:0]delta,
 output wire in_ready,output wire[1:0]take,
 output reg out_valid=0,output reg[1:0]out_count=0,
 output reg[32:0]u_out=0,output wire triple_mode);
 wire enable=!out_valid||out_ready;
 wire[4:0]coef=DC<0?delta:DC;
 wire signed[10:0]u0=u_in[10:0];
 wire signed[10:0]u1=available>=2?$signed(u_in[21:11]):11'sd0;
 wire signed[10:0]u2=available==3?$signed(u_in[32:22]):11'sd0;
 wire[32:0]raw={u2,u1,u0};
 wire absfit=(u0[10:5]=={6{u0[4]}})&&(u1[10:5]=={6{u1[4]}})&&(u2[10:5]=={6{u2[4]}});
 wire coherent=(u0[10:5]==u1[10:5])&&(u0[10:5]==u2[10:5]);
 wire narrow=(available==3)&&((E==0&&(absfit||coherent))||(E==6&&absfit));
 wire bypass=(coef==0)||(raw==0);
 wire always3=(E==3)||(E==4)||(E==5);
 wire thirdzero=(available==3)&&(u2==0);
 assign take=available==0?0:((available==3&&(always3||narrow||bypass||thirdzero))?3:(available>=2?2:1));
 assign in_ready=enable;
 assign triple_mode=narrow;
 wire accept=in_valid&&in_ready&&(available!=0);
 reg v0=0,v1=0,b0=0,b1=0,n0=0,n1=0;
 reg[1:0]cnt0=0,cnt1=0;
 localparam MW=E==4?57:33;
 reg[MW-1:0]meta0=0,meta1=0;
 wire[MW-1:0]encoded;
 wire[32:0]answer;
 always @(posedge clk)begin
  if(rst)begin v0<=0;v1<=0;b0<=0;b1<=0;n0<=0;n1<=0;
   cnt0<=0;cnt1<=0;meta0<=0;meta1<=0;out_valid<=0;out_count<=0;u_out<=0;end
  else if(enable)begin
   v0<=accept;v1<=v0;out_valid<=v1;
   if(accept)begin meta0<=encoded;cnt0<=take;b0<=bypass;n0<=narrow;end
   if(v0)begin meta1<=meta0;cnt1<=cnt0;b1<=b0;n1<=n0;end
   if(v1)begin out_count<=cnt1;
    u_out[10:0]<=answer[10:0];u_out[21:11]<=cnt1>=2?answer[21:11]:0;
    u_out[32:22]<=cnt1==3?answer[32:22]:0;
   end
  end
 end
 generate if(E==0||E==1||E==4||E==5||E==6)begin:dsp_path
  wire[24:0]a;wire[47:0]c,p;
  wire[32:0]decoded;
  wire[4:0]res0=absfit?{~u0[4],u0[3:0]}:u0[4:0];
  wire[4:0]res1=absfit?{~u1[4],u1[3:0]}:u1[4:0];
  wire[4:0]res2=absfit?{~u2[4],u2[3:0]}:u2[4:0];
  // The shared base is -16 for absolute int5, else floor(U0/32)*32.
  wire signed[10:0]base=absfit?-11'sd16:$signed({u0[10:5],5'b0});
  wire signed[6:0]bh=base[10:4];
  wire signed[5:0]dc={1'b0,coef};
  (* use_dsp="no" *) wire signed[12:0]z;
  wire signed[12:0]bx={{6{bh[6]}},bh};
  if(DC==25)assign z=(bx<<<4)+(bx<<<3)+bx;else assign z=bh*dc;
  wire signed[10:0]base_leak=base-(z>>>4);
  wire[32:0]nmeta={3'b0,res2,res1,res0,z[3:0],base_leak};
  wire[21:0]wide_meta;
  for(genvar l=0;l<2;l=l+1)begin:wide_pre
   wire signed[10:0]u=l==0?u0:u1;
   wire signed[3:0]h=$signed({u[10],u[10:8]})+$signed({3'b0,u[7]});
   (* use_dsp="no" *) wire signed[7:0]hp=h*dc;
   assign wide_meta[l*11+:11]=u-hp;
  end
  wire[7:0]q0={~u0[7],u0[6:0]},q1={~u1[7],u1[6:0]};
  wire[24:0]aw={1'b0,q1,8'b0,q0};
  wire[15:0]kw=16'd32768-({11'b0,coef}<<7);
  wire[47:0]cw={16'b0,kw,kw};
  // Unsigned residuals; top signed residual is centered for the signed25 multiplier.
  wire[24:0]an={~res2[4],res2[3:0],5'b0,res1,5'b0,res0};
  wire[47:0]cn={19'b0,coef,24'b0}; // (16*delta)<<20
  if(E!=4)begin:adaptive_or_pair
   wire[24:0]direct_a={u2[4:0],5'b0,{~u1[4],u1[3:0]},5'b0,{~u0[4],u0[3:0]}};
   wire[9:0]direct_k=10'd512-({5'b0,coef}<<4);
   wire[47:0]direct_c={28'b0,direct_k,direct_k};
   assign a=narrow?(E==6?direct_a:an):aw;
   assign c=narrow?(E==6?direct_c:cn):cw;
   wire signed[16:0]hybrid_x={{6{u2[10]}},u2};
   (* use_dsp="no" *) wire signed[16:0]hybrid_product;
   if(DC==25)assign hybrid_product=(hybrid_x<<<4)+(hybrid_x<<<3)+hybrid_x;
   else assign hybrid_product=u2*dc;
   wire[10:0]hybrid_leak=u2-(hybrid_product>>>8);
   wire[32:0]direct_meta={18'b0,u2[4:0],u1[4:0],u0[4:0]};
   assign encoded=bypass?raw:(narrow?(E==6?direct_meta:nmeta):{E==5?hybrid_leak:11'b0,wide_meta});
   // Shared upper increment; each lane needs only its low five-bit carry.
   wire[5:0]upper=meta1[10:5],upper_next=upper+6'd1;
   for(genvar l=0;l<3;l=l+1)begin:decode
    wire[4:0]r=meta1[15+5*l+:5];
    wire[9:0]prod=p[10*l+:10];
    wire[4:0]carry_sum={1'b0,prod[7:4]}+{1'b0,meta1[14:11]};
    wire[4:0]rem_leak=r-{3'b0,prod[9:8]}-carry_sum[4];
    wire signed[10:0]h=meta1[10:0];
    wire signed[10:0]residual_leak={6'b0,rem_leak};
    wire[5:0]low_sum={1'b0,meta1[4:0]}+{1'b0,rem_leak};
    wire[10:0]shared_answer={low_sum[5]?upper_next:upper,low_sum[4:0]};
    wire signed[4:0]direct_u=meta1[5*l+:5];
    wire signed[1:0]direct_floor=l==2?prod[9:8]:{~prod[9],prod[8]};
    wire signed[4:0]direct_result=direct_u-direct_floor;
    wire signed[10:0]narrow_answer=E==6?{{6{direct_result[4]}},direct_result}:shared_answer;
    if(l<2)begin:pair
     wire signed[4:0]floor_low=p[16*l+12-:5];
     wire signed[10:0]orig=meta1[11*l+:11];
     assign decoded[11*l+:11]=n1?narrow_answer:orig-floor_low;
    end else assign decoded[22+:11]=n1?narrow_answer:(E==5?meta1[32:22]:0);
   end
  end else begin:fixed_triple
   wire[4:0]qf0={~u0[4],u0[3:0]},qf1={~u1[4],u1[3:0]};
   wire[9:0]kf=10'd512-({5'b0,coef}<<4);
   assign a={u2[4:0],5'b0,qf1,5'b0,qf0};assign c={28'b0,kf,kf};
   wire[56:0]fm;
   for(genvar l=0;l<3;l=l+1)begin:lane
    wire signed[10:0]u=l==0?u0:(l==1?u1:u2);
    wire signed[6:0]h=$signed({u[10],u[10:5]})+$signed({6'b0,u[4]});
    (* use_dsp="no" *) wire signed[12:0]hp;
    wire signed[12:0]hx={{6{h[6]}},h};
    if(DC==25)assign hp=(hx<<<4)+(hx<<<3)+hx;else assign hp=h*dc;
    wire signed[12:0]wide_base=hx<<<5;
    wire signed[10:0]high_leak=wide_base-(hp>>>3);
    assign fm[19*l+:19]={u[4:0],hp[2:0],high_leak};
    wire signed[4:0]r=meta1[19*l+14+:5];
    wire[2:0]frac=meta1[19*l+11+:3];
    wire signed[10:0]high=meta1[19*l+:11];
    wire[9:0]prod=p[10*l+:10];
    wire signed[1:0]f=l==2?prod[9:8]:{~prod[9],prod[8]};
    wire[3:0]carry_sum={1'b0,prod[7:5]}+{1'b0,frac};
    wire signed[4:0]rem_leak=r-f-$signed({4'b0,carry_sum[3]});
    assign decoded[11*l+:11]=high+rem_leak;
   end
   assign encoded=bypass?{24'b0,raw}:fm;
  end
  stream_compact_dsp d(.clk(clk),.rst(rst),.issue(accept&&!bypass),.advance(enable),
   .delayed_issue(v0&&!b0),.a(a),.b({13'b0,coef}),.c(c),.p(p));
  assign answer=b1?meta1[32:0]:decoded;
 end else begin:lut_path
  localparam N=E==3?3:2;
  reg[32:0]f0=0,f1=0;
  wire[32:0]next;
  for(genvar l=0;l<N;l=l+1)begin:lane
   wire signed[10:0]u=l==0?u0:(l==1?u1:u2);
   wire signed[5:0]dc={1'b0,coef};
   wire signed[16:0]ux={{6{u[10]}},u};
   (* use_dsp="no" *) wire signed[16:0]p;
   if(DC==25)assign p=(ux<<<4)+(ux<<<3)+ux;else assign p=u*dc;
   assign next[11*l+:11]=u-(p>>>8);
  end
  if(N==2)assign next[22+:11]=0;
  always @(posedge clk)begin
   if(rst)begin f0<=0;f1<=0;end
   else if(enable)begin if(accept)f0<=bypass?raw:next;if(v0)f1<=f0;end
  end
  assign encoded=0;assign answer=f1;
 end endgenerate
endmodule

module stream_compact_dsp(input wire clk,rst,issue,advance,delayed_issue,
 input wire[24:0]a,input wire[17:0]b,input wire[47:0]c,output wire[47:0]p);
 DSP48E1 #(.USE_SIMD("ONE48"),.USE_MULT("MULTIPLY"),.AREG(0),.ACASCREG(0),.BREG(0),.BCASCREG(0),
 .CREG(1),.DREG(0),.ADREG(0),.MREG(1),.PREG(1),.OPMODEREG(0),.ALUMODEREG(0),.CARRYINREG(0),
 .CARRYINSELREG(0),.INMODEREG(0))d(
 .CLK(clk),.A({{5{a[24]}},a}),.B(b),.C(c),.D(25'd0),.OPMODE(7'b0110101),.ALUMODE(4'b0000),
 .CARRYIN(1'b0),.CARRYINSEL(3'b000),.INMODE(5'b00000),.CEA1(1'b0),.CEA2(1'b0),.CEB1(1'b0),.CEB2(1'b0),
 .CEC(issue),.CED(1'b0),.CEAD(1'b0),.CEM(issue),.CEP(advance&&delayed_issue),.CECTRL(1'b0),.CEALUMODE(1'b0),
 .CECARRYIN(1'b0),.CEINMODE(1'b0),.RSTA(1'b0),.RSTB(1'b0),.RSTC(rst),.RSTD(1'b0),.RSTM(rst),
 .RSTP(rst),.RSTCTRL(1'b0),.RSTALUMODE(1'b0),.RSTALLCARRYIN(1'b0),.RSTINMODE(1'b0),
 .ACIN(30'd0),.BCIN(18'd0),.PCIN(48'd0),.CARRYCASCIN(1'b0),.MULTSIGNIN(1'b0),
 .P(p),.ACOUT(),.BCOUT(),.PCOUT(),.CARRYOUT(),.CARRYCASCOUT(),.MULTSIGNOUT(),
 .OVERFLOW(),.UNDERFLOW(),.PATTERNDETECT(),.PATTERNBDETECT());
endmodule
`define STREAM_TOP(NAME,ENGINE,COEF) \
module NAME(input wire clk,rst,in_valid,out_ready,input wire[32:0]u_in,input wire[1:0]available,input wire[4:0]delta, \
 output wire in_ready,out_valid,output wire[1:0]take,out_count,output wire[32:0]u_out,output wire triple_mode); \
 stream_compact_leak #(.E(ENGINE),.DC(COEF))u(.*);endmodule
`STREAM_TOP(top_stream_compact_offset_const,0,25)
`STREAM_TOP(top_stream_compact_fixed2_const,1,25)
`STREAM_TOP(top_stream_compact_lut2_const,2,25)
`STREAM_TOP(top_stream_compact_lut3_const,3,25)
`STREAM_TOP(top_stream_compact_fixed3_const,4,25)
`STREAM_TOP(top_stream_compact_absolute_const,6,25)
`STREAM_TOP(top_stream_compact_offset_prog,0,-1)
`STREAM_TOP(top_stream_compact_fixed2_prog,1,-1)
`STREAM_TOP(top_stream_compact_lut3_prog,3,-1)
`STREAM_TOP(top_stream_compact_fixed3_prog,4,-1)

`STREAM_TOP(top_stream_compact_hybrid_const,5,25)
`STREAM_TOP(top_stream_compact_hybrid_prog,5,-1)
`STREAM_TOP(top_stream_compact_absolute_prog,6,-1)
