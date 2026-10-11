// ISOLATED TRIAL: E5 unchanged hybrid; E7 THREE-ALWAYS membrane-aware
// one-DSP routing: three narrow lanes, otherwise two wide lanes + LUT third.
// Whole wide-product C folding (CW0): P lane=32768+delta*U, original U
// metadata, final subtraction only. Exact for all int11 U and delta0..31.
// CW1 retains its centered residual C/pre arithmetic for optional comparison.
// Encoded bypass reconstruction: retain arithmetic-format metadata for every
// request and replace only decoded product-derived quotients/carry by zero.
// Pair policy consumes three only for narrow format or a real zero third lane;
// delta0 full-width pairs consume two. All-zero triples still consume three.
// Separate bounded repair: shared first-two pre-subtraction, exact constant bypass,
// and equivalent nested narrow selector. Original queue sources are unchanged.
// Strong LUT lane variants: STYLE1 signed-digit constant, STYLE2 split quotient.
`timescale 1ns/1ps
// Exact signed-int11 leakage: U-floor(delta*U/256). Four advancing clocks
// from input acceptance to output handshake. Common CE freezes all stages.
// E0: adaptive int7 (delta<=25) / int6 (all delta) triple, else wide pair.
// E1 DSP pair; E2 LUT pair; E3 LUT triple; E4 DSP triple; E5 DSP/LUT triple;
// E6 adaptive int6 triple; E7 always-three adaptive DSP/LUT placement.
// CW selects unsigned (0) or centered (1) wide lanes; this trial instantiates CW0.
module continuous_leak #(parameter E=7, DC=25, CW=0, STYLE=(DC==25?1:0))(
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
 wire fit6=(u0[10:6]=={5{u0[5]}})&&(u1[10:6]=={5{u1[5]}})&&(u2[10:6]=={5{u2[5]}});
 wire fit7=(u0[10:7]=={4{u0[6]}})&&(u1[10:7]=={4{u1[6]}})&&(u2[10:7]=={4{u2[6]}});
 wire narrow=(available==3)&&(((E==0||E==7)&&(coef<=25?fit7:fit6))||(E==6&&fit6));
 wire bypass=(coef==0)||(raw==0);
 wire always3=(E==3)||(E==4)||(E==5)||(E==7);
 wire thirdzero=(available==3)&&(u2==0);
 assign take=available==0?0:((available==3&&(always3||narrow||thirdzero))?3:(available>=2?2:1));
 assign in_ready=enable;
 assign triple_mode=narrow;
 wire accept=in_valid&&enable&&(available!=0);
 reg v0=0,v1=0,v2=0,b0=0,b1=0,b2=0,n0=0,n1=0,n2=0;
 reg[1:0]cnt0=0,cnt1=0,cnt2=0;
 reg[32:0]raw0=0;
 reg[4:0]coef0=0;
 localparam MW=(E==4&&DC!=25)?57:33;
 localparam NB=E==6?6:7;
 reg[MW-1:0]meta1=0,meta2=0;
 wire[MW-1:0]encoded;
 wire[32:0]answer;
 always @(posedge clk)begin
  if(rst)begin
   v0<=0;v1<=0;v2<=0;b0<=0;b1<=0;b2<=0;n0<=0;n1<=0;n2<=0;
   cnt0<=0;cnt1<=0;cnt2<=0;raw0<=0;coef0<=0;meta1<=0;meta2<=0;
   out_valid<=0;out_count<=0;u_out<=0;
  end else if(enable)begin
   v0<=accept;v1<=v0;v2<=v1;out_valid<=v2;
   if(accept)begin raw0<=raw;coef0<=coef;cnt0<=take;b0<=bypass;n0<=narrow;end
   if(v0)begin meta1<=encoded;cnt1<=cnt0;b1<=b0;n1<=n0;end
   if(v1)begin meta2<=meta1;cnt2<=cnt1;b2<=b1;n2<=n1;end
   if(v2)begin
    out_count<=cnt2;u_out[10:0]<=answer[10:0];
    u_out[21:11]<=cnt2>=2?answer[21:11]:0;
    u_out[32:22]<=cnt2==3?answer[32:22]:0;
   end
  end
 end
 generate if(E==0||E==1||E==4||E==5||E==6||E==7)begin:dsp_path
  wire[24:0]a;wire[47:0]c,p;
  wire[32:0]decoded;
  wire signed[5:0]dc0={1'b0,coef0};
  if(E!=4)begin:adaptive_or_pair
   wire[21:0]wide_meta;
   wire[31:0]whole_wide_c;
   wire[3*NB-1:0]narrow_meta;
   wire[8:0]frac;
   for(genvar l=0;l<3;l=l+1)begin:correction
    wire signed[10:0]u=raw0[11*l+:11];
    wire signed[1:0]h=E==6?$signed({u[5],u[5]}):$signed(u[6:5]);
    wire signed[6:0]hx={{5{h[1]}},h};
    (* use_dsp="no" *) wire signed[6:0]hp;
    if(DC==25)assign hp=(hx<<<4)+(hx<<<3)+hx;else assign hp=h*dc0;
    wire signed[3:0]q=hp[6:3];
    wire signed[NB-1:0]un=u[NB-1:0];
    assign narrow_meta[NB*l+:NB]=un-q;
    assign frac[3*l+:3]=hp[2:0];
    if(l<2)begin:wide
     wire signed[3:0]wh=CW==1?($signed({u[10],u[10:8]})+$signed({3'b0,u[7]})):$signed({u[10],u[10:8]});
     wire signed[7:0]wx={{4{wh[3]}},wh};
     (* use_dsp="no" *) wire signed[7:0]wp;
     if(DC==25)assign wp=(wx<<<4)+(wx<<<3)+wx;else assign wp=wh*dc0;
     // CW0 folds the entire high product into DSP C. Each field becomes
     // 32768+delta*U, so original U is the only wide metadata required.
     // CW1 retains centered-residual arithmetic and its wide pre-correction.
     assign whole_wide_c[16*l+:16]={~wp[7],wp[6:0],8'b0};
     assign wide_meta[11*l+:11]=CW==1?(u-wp):u;
    end
   end
   wire[7:0]q0=CW==1?{~u0[7],u0[6:0]}:u0[7:0];
   wire[7:0]q1=CW==1?{~u1[7],u1[6:0]}:u1[7:0];
   wire[24:0]aw={1'b0,q1,8'b0,q0};
   wire[15:0]kw=CW==1?16'd32768-({11'b0,coef0}<<7):16'd0;
   wire[47:0]cw=CW==1?{16'b0,kw,kw}:{16'b0,whole_wide_c};
   wire[24:0]an={~u2[4],u2[3:0],5'b0,u1[4:0],5'b0,u0[4:0]};
   wire[9:0]top=({5'b0,coef0}<<4)+({7'b0,frac[8:6]}<<5);
   wire[47:0]cn={18'b0,top,2'b0,frac[5:3],5'b0,2'b0,frac[2:0],5'b0};
   assign a=narrow?an:aw;
   assign c=n0?cn:cw;
   assign encoded=n0?{{(33-3*NB){1'b0}},narrow_meta}:{11'b0,wide_meta};
   wire[10:0]third;
   if(E==5||E==7)begin:hybrid_lane
    wire signed[10:0]u=raw0[32:22];
    wire signed[7:0]quotient;
    if(STYLE==2)begin:split_quotient
     wire signed[2:0]h=u[10:8];
     wire signed[7:0]hx={{5{h[2]}},h};
     wire[12:0]rx={5'b0,u[7:0]};
     (* use_dsp="no" *) wire signed[7:0]hp;
     (* use_dsp="no" *) wire[12:0]lp;
     if(DC==25)begin
      assign hp=(hx<<<4)+(hx<<<3)+hx;
      assign lp=(rx<<4)+(rx<<3)+rx;
     end else begin assign hp=h*$signed({1'b0,coef0});assign lp=u[7:0]*coef0;end
     assign quotient=hp+$signed({3'b0,lp[12:8]});
    end else begin:full_quotient
     wire signed[15:0]ux={{5{u[10]}},u};
     (* use_dsp="no" *) wire signed[15:0]prod;
     if(DC==25&&STYLE==1)assign prod=(ux<<<5)-(ux<<<3)+ux;
     else if(DC==25)assign prod=(ux<<<4)+(ux<<<3)+ux;
     else assign prod=u*dc0;
     assign quotient=prod[15:8];
    end
    reg[18:0]m1=0;reg[10:0]r2=0;
    wire signed[10:0]orig=m1[18:8];
    wire signed[10:0]quot={{3{m1[7]}},m1[7:0]};
    // E7 suppresses only unused LUT-lane register writes. Combinational
    // quotient logic still exists; no power/toggle benefit is established.
    if(E==7)begin:adaptive_gate
     always @(posedge clk)begin
      if(rst)begin m1<=0;r2<=0;end
      else if(enable)begin
       if(v0&&!n0)m1<={u,quotient};
       if(v1&&!n1)r2<=orig-quot;
      end
     end
    end else begin:fixed_gate
    always @(posedge clk)begin
     if(rst)begin m1<=0;r2<=0;end
     else if(enable)begin if(v0)m1<={u,quotient};if(v1)r2<=orig-quot;end
    end
    end
    assign third=r2;
   end else assign third=0;
   for(genvar l=0;l<3;l=l+1)begin:decode
    wire signed[NB-1:0]pre=meta2[NB*l+:NB];
    wire signed[NB-1:0]floor_n=b2?{NB{1'b0}}:{{(NB-2){1'b0}},p[10*l+8+:2]};
    wire signed[NB-1:0]res=pre-floor_n;
    wire[10:0]narrow_answer={{(11-NB){res[NB-1]}},res};
    if(l<2)begin:pair
     wire signed[7:0]whole_quotient={~p[16*l+15],p[16*l+8+:7]};
     wire signed[10:0]floor_w=b2?11'sd0:(CW==1?{{6{p[16*l+12]}},p[16*l+8+:5]}:{{3{whole_quotient[7]}},whole_quotient});
     wire signed[10:0]orig=meta2[11*l+:11];
     assign decoded[11*l+:11]=n2?narrow_answer:orig-floor_w;
    end else assign decoded[22+:11]=n2?narrow_answer:third;
   end
  end else if(DC==25)begin:fixed_folded_triple
   wire[29:0]fc;wire[32:0]fm;
   assign a={~u2[4],u2[3:0],5'b0,u1[4:0],5'b0,u0[4:0]};
   assign c={18'b0,fc};
   for(genvar l=0;l<3;l=l+1)begin:lane
    wire signed[10:0]u=raw0[11*l+:11];
    wire signed[5:0]h=u[10:5];
    wire signed[10:0]hx={{5{h[5]}},h};
    (* use_dsp="no" *) wire signed[10:0]hp=(hx<<<4)+(hx<<<3)+hx;
    assign fm[11*l+:11]=u-(hp>>>3);
    assign fc[10*l+:10]=({7'b0,hp[2:0]}<<5)+(l==2?10'd400:10'd0);
    wire signed[10:0]pre=meta2[11*l+:11];
    wire signed[10:0]f=b2?11'sd0:{9'b0,p[10*l+8+:2]};
    assign decoded[11*l+:11]=pre-f;
   end
   assign encoded=fm;
  end else begin:fixed_triple
   wire[9:0]k=10'd512-({5'b0,coef0}<<4);
   assign a={u2[4:0],5'b0,{~u1[4],u1[3:0]},5'b0,{~u0[4],u0[3:0]}};
   assign c={28'b0,k,k};
   wire[56:0]fm;
   for(genvar l=0;l<3;l=l+1)begin:lane
    wire signed[10:0]u=raw0[11*l+:11];
    wire signed[6:0]h=$signed({u[10],u[10:5]})+$signed({6'b0,u[4]});
    (* use_dsp="no" *) wire signed[12:0]hp=h*dc0;
    wire signed[12:0]hx={{6{h[6]}},h};
    wire signed[10:0]high=(hx<<<5)-(hp>>>3);
    assign fm[19*l+:19]={u[4:0],hp[2:0],high};
    wire signed[4:0]r=meta2[19*l+14+:5];
    wire[2:0]phi=meta2[19*l+11+:3];
    wire signed[10:0]hi=meta2[19*l+:11];
    wire[9:0]prod=p[10*l+:10];
    wire signed[1:0]f=b2?2'sd0:(l==2?prod[9:8]:{~prod[9],prod[8]});
    wire[3:0]carry_sum={1'b0,prod[7:5]}+{1'b0,phi};
    wire carry=b2?1'b0:carry_sum[3];
    wire signed[4:0]rem=r-f-$signed({4'b0,carry});
    assign decoded[11*l+:11]=hi+rem;
   end
   assign encoded=fm;
  end
  continuous_dsp d(.clk(clk),.rst(rst),.advance(enable),
   .issue(accept&&!bypass),.multiply_issue(v0&&!b0),.sum_issue(v1&&!b1),
   .a(a),.b({13'b0,coef}),.c(c),.p(p));
  assign answer=decoded;
 end else begin:lut_path
  localparam N=E==3?3:2;
  reg[19*N-1:0]m1=0;
  reg[32:0]r2=0;
  wire[19*N-1:0]next1;
  wire[32:0]next2;
  for(genvar l=0;l<N;l=l+1)begin:lane
   wire signed[10:0]u=raw0[11*l+:11];
   wire signed[5:0]dc={1'b0,coef0};
   wire signed[7:0]quotient;
    if(STYLE==2)begin:split_quotient
     wire signed[2:0]h=u[10:8];
     wire signed[7:0]hx={{5{h[2]}},h};
     wire[12:0]rx={5'b0,u[7:0]};
     (* use_dsp="no" *) wire signed[7:0]hp;
     (* use_dsp="no" *) wire[12:0]lp;
     if(DC==25)begin
      assign hp=(hx<<<4)+(hx<<<3)+hx;
      assign lp=(rx<<4)+(rx<<3)+rx;
     end else begin assign hp=h*$signed({1'b0,coef0});assign lp=u[7:0]*coef0;end
     assign quotient=hp+$signed({3'b0,lp[12:8]});
    end else begin:full_quotient
     wire signed[15:0]ux={{5{u[10]}},u};
     (* use_dsp="no" *) wire signed[15:0]prod;
     if(DC==25&&STYLE==1)assign prod=(ux<<<5)-(ux<<<3)+ux;
     else if(DC==25)assign prod=(ux<<<4)+(ux<<<3)+ux;
     else assign prod=u*dc;
     assign quotient=prod[15:8];
    end
   assign next1[19*l+:19]={u,quotient};
   wire signed[10:0]orig=m1[19*l+8+:11];
   wire signed[7:0]q=m1[19*l+:8];
   assign next2[11*l+:11]=orig-{{3{q[7]}},q};
  end
  if(N==2)assign next2[32:22]=0;
  assign encoded=0;assign answer=r2;
  always @(posedge clk)begin
   if(rst)begin m1<=0;r2<=0;end
   else if(enable)begin if(v0)m1<=next1;if(v1)r2<=next2;end
  end
 end endgenerate
endmodule

module continuous_dsp(input wire clk,rst,advance,issue,multiply_issue,sum_issue,
 input wire[24:0]a,input wire[17:0]b,input wire[47:0]c,output wire[47:0]p);
 DSP48E1 #(.USE_SIMD("ONE48"),.USE_MULT("MULTIPLY"),.AREG(1),.ACASCREG(1),.BREG(1),.BCASCREG(1),
 .CREG(1),.DREG(0),.ADREG(0),.MREG(1),.PREG(1),.OPMODEREG(0),.ALUMODEREG(0),.CARRYINREG(0),
 .CARRYINSELREG(0),.INMODEREG(0))d(
 .CLK(clk),.A({{5{a[24]}},a}),.B(b),.C(c),.D(25'd0),.OPMODE(7'b0110101),.ALUMODE(4'b0000),
 .CARRYIN(1'b0),.CARRYINSEL(3'b000),.INMODE(5'b00000),.CEA1(1'b0),.CEA2(advance&&issue),
 .CEB1(1'b0),.CEB2(advance&&issue),.CEC(advance&&multiply_issue),.CED(1'b0),.CEAD(1'b0),
 .CEM(advance&&multiply_issue),.CEP(advance&&sum_issue),.CECTRL(1'b0),.CEALUMODE(1'b0),
 .CECARRYIN(1'b0),.CEINMODE(1'b0),.RSTA(rst),.RSTB(rst),.RSTC(rst),.RSTD(1'b0),.RSTM(rst),
 .RSTP(rst),.RSTCTRL(1'b0),.RSTALUMODE(1'b0),.RSTALLCARRYIN(1'b0),.RSTINMODE(1'b0),
 .ACIN(30'd0),.BCIN(18'd0),.PCIN(48'd0),.CARRYCASCIN(1'b0),.MULTSIGNIN(1'b0),
 .P(p),.ACOUT(),.BCOUT(),.PCOUT(),.CARRYOUT(),.CARRYCASCOUT(),.MULTSIGNOUT(),
 .OVERFLOW(),.UNDERFLOW(),.PATTERNDETECT(),.PATTERNBDETECT());
endmodule
