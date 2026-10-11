`timescale 1ns/1ps
// Constant delta25 only: exact ceil(231*U/256), full signedint11 state/output.
// E0 quadfit6/triplefallback; E1 quadfit7/triplefallback; E2 fixed DSP triple;
// E3 full-range DSP quad; E4 signed-digit LUT quad. Ordered raw four-value window.
// Adaptive/fixed3 prefer the fourth-identity copy path when U3 is in[0,10].
// Four advancing clocks from acceptance through output handshake, common stall.
module quad_leak #(parameter E=0)(
 input wire clk,rst,in_valid,out_ready,input wire[43:0]u_in,
 input wire[2:0]available,output wire in_ready,output wire[2:0]take,
 output reg out_valid=0,output reg[2:0]out_count=0,
 output reg[43:0]u_out=0,output wire quad_mode);
 wire advance=!out_valid||out_ready;
 wire signed[10:0]u0=u_in[10:0];
 wire signed[10:0]u1=available>=2?$signed(u_in[21:11]):11'sd0;
 wire signed[10:0]u2=available>=3?$signed(u_in[32:22]):11'sd0;
 wire signed[10:0]u3=available==4?$signed(u_in[43:33]):11'sd0;
 wire[43:0]raw={u3,u2,u1,u0};
 wire fit6=(u0[10:6]=={5{u0[5]}})&&(u1[10:6]=={5{u1[5]}})&&
           (u2[10:6]=={5{u2[5]}})&&(u3[10:6]=={5{u3[5]}});
 wire fit7=(u0[10:7]=={4{u0[6]}})&&(u1[10:7]=={4{u1[6]}})&&
           (u2[10:7]=={4{u2[6]}})&&(u3[10:7]=={4{u3[6]}});
 wire copy4=(available==4)&&(u3>=0)&&(u3<=10);
 wire quad=(available!=0)&&((E==3)||(available==4&&!copy4&&((E==0&&fit6)||(E==1&&fit7))));
 assign quad_mode=quad;
 assign take=available==0?0:((available==4&&(E==4||quad||copy4))?4:(available>=3?3:available));
 assign in_ready=advance;
 wire accept=in_valid&&advance&&(available!=0);
 // Constant25 exact fixed points are U0..10. Every retained high quotient is
 // zero there, so masking extracted product corrections reconstructs U exactly.
 // Only consumed values matter; an unconsumed fourth cannot block bypass.
 wire identity_request=(u0>=0&&u0<=10)&&(take<2||(u1>=0&&u1<=10))&&
                       (take<3||(u2>=0&&u2<=10))&&(take<4||(u3>=0&&u3<=10));
 reg v0=0,v1=0,v2=0,b0=0,b1=0,b2=0,n0=0,n1=0,n2=0;
 reg[2:0]cnt0=0,cnt1=0,cnt2=0;reg[43:0]raw0=0;
 localparam NB=E==0?6:(E==1?7:11);
 localparam MW=4*(NB+6)>44?4*(NB+6):44;
 reg[MW-1:0]meta1=0,meta2=0;
 wire[MW-1:0]encoded;wire[43:0]answer;
 always @(posedge clk)begin
  if(rst)begin
   v0<=0;v1<=0;v2<=0;b0<=0;b1<=0;b2<=0;n0<=0;n1<=0;n2<=0;
   cnt0<=0;cnt1<=0;cnt2<=0;raw0<=0;meta1<=0;meta2<=0;
   out_valid<=0;out_count<=0;u_out<=0;
  end else if(advance)begin
   v0<=accept;v1<=v0;v2<=v1;out_valid<=v2;
   if(accept)begin raw0<=raw;cnt0<=take;b0<=identity_request;n0<=quad;end
   if(v0)begin meta1<=encoded;cnt1<=cnt0;b1<=b0;n1<=n0;end
   if(v1)begin meta2<=meta1;cnt2<=cnt1;b2<=b1;n2<=n1;end
   if(v2)begin out_count<=cnt2;
    u_out[10:0]<=answer[10:0];u_out[21:11]<=cnt2>=2?answer[21:11]:0;
    u_out[32:22]<=cnt2>=3?answer[32:22]:0;u_out[43:33]<=cnt2==4?answer[43:33]:0;
   end
  end
 end
 generate if(E!=4)begin:dsp_path
  wire[24:0]aq={2'b0,u3[1:0],5'b0,u2[1:0],5'b0,u1[1:0],5'b0,u0[1:0]};
  wire[24:0]at={~u2[4],u2[3:0],5'b0,u1[4:0],5'b0,u0[4:0]};
  // Fixed4 selects its format at elaboration, avoiding unreachable triple
  // datapaths whose irrelevance would otherwise depend on valid/mode history.
  wire[24:0]a=(E==3||quad)?aq:at;wire[47:0]p,c;
  wire[4*(NB+6)-1:0]qm;wire[32:0]tm;wire[29:0]tc;
  for(genvar l=0;l<4;l=l+1)begin:correction
   wire signed[10:0]u=raw0[11*l+:11];
   if(l<3&&E!=3)begin:shared
    // Adaptive modes select h before one high product and one full-state
    // subtraction. Fixed3 has only the compile-time full-range triple path.
    wire signed[5:0]h;
    if(E==2)begin:fixed_triple
     assign h=u[10:5];
    end else begin:adaptive
     wire signed[NB-3:0]narrow_h=u[NB-1:2];
     assign h=n0?{{(8-NB){narrow_h[NB-3]}},narrow_h}:u[10:5];
    end
    wire signed[10:0]hx={{5{h[5]}},h};
    (* use_dsp="no" *)wire signed[10:0]hp=(hx<<<4)+(hx<<<3)+hx;
    wire signed[10:0]high_quotient=(E==2)?(hp>>>3):(n0?(hp>>>6):(hp>>>3));
    wire signed[10:0]pre=u-high_quotient;
    assign qm[(NB+6)*l+:NB+6]={hp[5:0],pre[NB-1:0]};
    assign tm[11*l+:11]=pre;
    assign tc[10*l+:10]=({7'b0,hp[2:0]}<<5)+(l==2?10'd400:10'd0);
   end else begin:quad_only
    // The fourth adaptive lane and every full-range Fixed4 lane retain their
    // own R2 correction. Fixed4 never instantiates a triple correction.
    wire signed[NB-1:0]un=u[NB-1:0];
    wire signed[NB-3:0]h=un[NB-1:2];
    wire signed[13:0]hx={{(16-NB){h[NB-3]}},h};
    (* use_dsp="no" *)wire signed[13:0]hp=(hx<<<4)+(hx<<<3)+hx;
    wire signed[NB-1:0]pre=un-(hp>>>6);
    assign qm[(NB+6)*l+:NB+6]={hp[5:0],pre};
    if(l<3)begin:unused_triple
     assign tm[11*l+:11]=11'd0;assign tc[10*l+:10]=10'd0;
    end
   end
  end
  // A triple consumes four only through copy4, whose U3 is in[0,10].
  // Reconstruct its known-zero upper bits equally for E0/E1/E2.
  wire[43:0]triple_meta={cnt0==4?{7'b0,raw0[36:33]}:11'b0,tm};
  assign encoded=(E==3||n0)?{{(MW-4*(NB+6)){1'b0}},qm}:{{(MW-44){1'b0}},triple_meta};
  assign c=(E==3||n0)?48'd0:{18'b0,tc};
  quad_dsp d(.clk(clk),.rst(rst),.advance(advance),.issue(accept&&!identity_request),
   .multiply_issue(v0&&!b0),.sum_issue(v1&&!b1),.a(a),.c(c),.p(p));
  for(genvar l=0;l<4;l=l+1)begin:decode
   wire signed[NB-1:0]pre=meta2[(NB+6)*l+:NB];
   wire[5:0]phi=meta2[(NB+6)*l+NB+:6];wire[6:0]low_product=p[7*l+:7];
   wire[8:0]fraction_sum={1'b0,phi,2'b0}+{2'b0,low_product};
   wire correction=b2?1'b0:fraction_sum[8];
   wire signed[NB-1:0]result=pre-$signed({{(NB-1){1'b0}},correction});
   wire[10:0]quad_answer={{(11-NB){result[NB-1]}},result};
   if(l<3)begin:triple
    wire signed[10:0]tp=meta2[11*l+:11];
    wire signed[10:0]quot=b2?11'sd0:{9'b0,p[10*l+8+:2]};
    assign answer[11*l+:11]=(E==3||n2)?quad_answer:tp-quot;
   end else assign answer[33+:11]=(E==3||n2)?quad_answer:meta2[33+:11];
  end
 end else begin:lut_path
  reg[75:0]m1=0;reg[43:0]r2=0;wire[75:0]next1;wire[43:0]next2;
  for(genvar l=0;l<4;l=l+1)begin:lane
   wire signed[10:0]u=raw0[11*l+:11];wire signed[15:0]ux={{5{u[10]}},u};
   (* use_dsp="no" *)wire signed[15:0]prod=(ux<<<5)-(ux<<<3)+ux;
   assign next1[19*l+:19]={u,prod[15:8]};
   wire signed[10:0]orig=m1[19*l+8+:11];wire signed[7:0]q=m1[19*l+:8];
   assign next2[11*l+:11]=orig-$signed({{3{q[7]}},q});
  end
  always @(posedge clk)begin
   if(rst)begin m1<=0;r2<=0;end
   else if(advance)begin if(v0)m1<=next1;if(v1)r2<=next2;end
  end
  assign encoded=0;assign answer=r2;
 end endgenerate
endmodule

module quad_dsp(input wire clk,rst,advance,issue,multiply_issue,sum_issue,
 input wire[24:0]a,input wire[47:0]c,output wire[47:0]p);
 DSP48E1 #(.USE_SIMD("ONE48"),.USE_MULT("MULTIPLY"),.AREG(1),.ACASCREG(1),.BREG(1),.BCASCREG(1),
 .CREG(1),.DREG(0),.ADREG(0),.MREG(1),.PREG(1),.OPMODEREG(0),.ALUMODEREG(0),.CARRYINREG(0),
 .CARRYINSELREG(0),.INMODEREG(0))d(
 .CLK(clk),.A({{5{a[24]}},a}),.B(18'd25),.C(c),.D(25'd0),.OPMODE(7'b0110101),.ALUMODE(4'b0000),
 .CARRYIN(1'b0),.CARRYINSEL(3'b000),.INMODE(5'b00000),.CEA1(1'b0),.CEA2(advance&&issue),
 .CEB1(1'b0),.CEB2(advance&&issue),.CEC(advance&&multiply_issue),.CED(1'b0),.CEAD(1'b0),
 .CEM(advance&&multiply_issue),.CEP(advance&&sum_issue),.CECTRL(1'b0),.CEALUMODE(1'b0),
 .CECARRYIN(1'b0),.CEINMODE(1'b0),.RSTA(rst),.RSTB(rst),.RSTC(rst),.RSTD(1'b0),.RSTM(rst),
 .RSTP(rst),.RSTCTRL(1'b0),.RSTALUMODE(1'b0),.RSTALLCARRYIN(1'b0),.RSTINMODE(1'b0),
 .ACIN(30'd0),.BCIN(18'd0),.PCIN(48'd0),.CARRYCASCIN(1'b0),.MULTSIGNIN(1'b0),
 .P(p),.ACOUT(),.BCOUT(),.PCOUT(),.CARRYOUT(),.CARRYCASCOUT(),.MULTSIGNOUT(),
 .OVERFLOW(),.UNDERFLOW(),.PATTERNDETECT(),.PATTERNBDETECT());
endmodule
