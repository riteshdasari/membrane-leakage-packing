`timescale 1ns/1ps
// Six stored signed membranes; ceil((256-delta)*U/256), delta in [0,31].
// E=0: actual-U adaptive DSP (3 int5 or 2 full int11); E=1: fixed 2-lane DSP.
// E=2: factored/full multiplier LUT pair; E=3: six parallel LUT lanes.
// E=5: fixed pair ROM, constant coefficient only. MP=1 adds MREG/CREG.
// No external encoder, free monitor cycle, overflow truncation or exponent.
module adaptive_delta_leak #(parameter E=0,B=11,DC=25,MP=1)(
 input wire clk,rst,valid,input wire[6*B-1:0]u_in,input wire[4:0]delta,
 output wire ready,output reg out_valid=0,output reg[6*B-1:0]u_out=0,
 output wire issue_valid,output wire narrow_mode);
 reg busy=0,issuing=0,narrow_q=0;
 reg[6*B-1:0]uq=0;reg[4:0]dq=0;reg[1:0]count=0;
 wire[4:0]coef=DC<0?dq:DC;
 wire[4:0]input_coef=DC<0?delta:DC;
 wire[5:0]fits;
 for(genvar i=0;i<6;i=i+1)begin:monitor
  assign fits[i]=(u_in[i*B+5+:B-5]=={(B-5){u_in[i*B+4]}});
 end
 wire accept=valid&&ready;
 wire bypass=(u_in==0)||(input_coef==0);
 wire issue=busy&&issuing;
 assign ready=!busy;
 assign issue_valid=issue;
 assign narrow_mode=narrow_q;
 wire issue_last=(E==3)||(narrow_q?count==1:count==2);
 wire[2:0]position=narrow_q?(count==0?0:3):
                         (count==0?0:(count==1?2:4));
 reg signed[B-1:0]s0,s1,s2;
 always @* begin
  s0=uq[0+:B];s1=uq[B+:B];s2=uq[2*B+:B];
  if(narrow_q)begin
   if(count!=0)begin s0=uq[3*B+:B];s1=uq[4*B+:B];s2=uq[5*B+:B];end
  end else case(count)
   1:begin s0=uq[2*B+:B];s1=uq[3*B+:B];end
   2:begin s0=uq[4*B+:B];s1=uq[5*B+:B];end
  endcase
 end
 reg v0=0,v1=0,last0=0,last1=0;
 reg[2:0]pos0=0,pos1=0;
 wire result_valid=MP?v1:v0;
 wire result_last=MP?last1:last0;
 wire[2:0]result_pos=MP?pos1:pos0;
 reg[6*B-1:0]original0=0,original1=0;
 wire[6*B-1:0]original=MP?original1:original0;
 wire[6*B-1:0]computed;
 always @(posedge clk)begin
  if(rst)begin
   busy<=0;issuing<=0;narrow_q<=0;uq<=0;dq<=0;count<=0;
   v0<=0;v1<=0;last0<=0;last1<=0;pos0<=0;pos1<=0;
   original0<=0;original1<=0;out_valid<=0;u_out<=0;
  end else begin
   out_valid<=0;v0<=issue;v1<=v0;last0<=issue_last;last1<=last0;
   pos0<=position;pos1<=pos0;
   if(issue)begin
    if(E==3)original0<=uq;
    else original0<={{(3*B){1'b0}},s2,s1,s0};
    if(issue_last)issuing<=0;else count<=count+1;
   end
   if(v0)original1<=original0;
   if(accept)begin
    if(bypass)begin u_out<=u_in;out_valid<=1;end
    else begin
     uq<=u_in;if(DC<0)dq<=delta;
     narrow_q<=(E==0)&&(&fits);busy<=1;issuing<=1;count<=0;
    end
   end
   if(result_valid)begin
    if(E==3)u_out<=computed;
    else for(integer j=0;j<6;j=j+1)begin
     if(result_pos==j)u_out[j*B+:B]<=computed[0+:B];
     if(result_pos+1==j)u_out[j*B+:B]<=computed[B+:B];
     if(narrow_q&&result_pos+2==j)u_out[j*B+:B]<=computed[2*B+:B];
    end
    if(result_last)begin busy<=0;out_valid<=1;end
   end
  end
 end
 generate if(E==0||E==1)begin:dsp_path
  wire[7:0]r0=s0[7:0],r1=s1[7:0];
  wire[7:0]q0={~r0[7],r0[6:0]},q1={~r1[7],r1[6:0]};
  wire[4:0]n0={~s0[4],s0[3:0]},n1={~s1[4],s1[3:0]};
  wire[24:0]a_wide={1'b0,q1,8'b0,q0};
  wire[24:0]a_narrow={s2[4:0],5'b0,n1,5'b0,n0};
  wire[15:0]kw=16'd32768-({11'b0,coef}<<7);
  wire[9:0]kn=10'd512-({5'b0,coef}<<4);
  wire[47:0]cw={16'b0,kw,kw},cn={28'b0,kn,kn};
  wire[47:0]p;
  delta_dsp #(.MP(MP))d(.clk(clk),.rst(rst),.issue(issue),.delayed_issue(v0),
   .a(narrow_q?a_narrow:a_wide),.b({13'b0,coef}),.c(narrow_q?cn:cw),.p(p));
  for(genvar l=0;l<2;l=l+1)begin:high
   wire signed[B-1:0]u=l==0?s0:s1;
   wire signed[B-9:0]upper=u[B-1:8];
   wire signed[B-8:0]h={upper[B-9],upper}+$signed({{(B-8){1'b0}},u[7]});
   wire signed[5:0]dc={1'b0,coef};
   (* use_dsp="no" *) wire signed[B-2:0]hp=h*dc;
   reg signed[B-1:0]h0=0,h1=0;
   always @(posedge clk)begin
    if(rst)begin h0<=0;h1<=0;end
    else begin if(issue)h0<=hp;if(v0)h1<=h0;end
   end
   wire signed[B-1:0]hi=MP?h1:h0;
   wire signed[7:0]low_floor={~p[16*l+15],p[16*l+14-:7]};
   wire signed[1:0]small_floor={~p[10*l+9],p[10*l+8]};
   wire signed[B-1:0]orig=original[l*B+:B];
   wire signed[B-1:0]answer=narrow_q?orig-small_floor:orig-hi-low_floor;
   assign computed[l*B+:B]=answer;
  end
  wire signed[1:0]top_floor=p[29:28];
  wire signed[B-1:0]top_original=original[2*B+:B];
  assign computed[2*B+:B]=top_original-top_floor;
  assign computed[3*B+:3*B]=0;
 end else begin:lut_path
  localparam N=E==3?6:2;
  for(genvar l=0;l<N;l=l+1)begin:lane
   wire signed[B-1:0]u=E==3?uq[l*B+:B]:(l==0?s0:s1);
   reg signed[B-1:0]f0=0,f1=0;
   if(E==5)begin:rom_path
    (* rom_style="block" *) reg[B-1:0]rom[0:(1<<B)-1];
    integer t,z;
    initial for(t=0;t<(1<<B);t=t+1)begin
     z=t>=(1<<(B-1))?t-(1<<B):t;
     rom[t]=z-((DC*z)>>>8);
    end
    always @(posedge clk)begin
     if(rst)begin f0<=0;f1<=0;end
     else begin if(issue)f0<=rom[$unsigned(u)];if(v0)f1<=f0;end
    end
    assign computed[l*B+:B]=MP?f1:f0;
   end else begin:arithmetic
    wire signed[5:0]dc={1'b0,coef};
    wire signed[B+5:0]ux={{6{u[B-1]}},u};
    (* use_dsp="no" *) wire signed[B+5:0]product;
    if(DC==25)begin:factor25
     assign product=(ux<<<4)+(ux<<<3)+ux;
    end else begin:multiply
     assign product=u*dc;
    end
    always @(posedge clk)begin
     if(rst)begin f0<=0;f1<=0;end
     else begin if(issue)f0<=product>>>8;if(v0)f1<=f0;end
    end
    wire signed[B-1:0]orig=original[l*B+:B];
    wire signed[B-1:0]floor_value=MP?f1:f0;
    assign computed[l*B+:B]=orig-floor_value;
   end
  end
  if(N<6)assign computed[N*B+:(6-N)*B]=0;
 end endgenerate
endmodule

module delta_dsp #(parameter MP=1)(input wire clk,rst,issue,delayed_issue,
 input wire[24:0]a,input wire[17:0]b,input wire[47:0]c,output wire[47:0]p);
 DSP48E1 #(.USE_SIMD("ONE48"),.USE_MULT("MULTIPLY"),.AREG(0),.ACASCREG(0),.BREG(0),.BCASCREG(0),
 .CREG(MP),.DREG(0),.ADREG(0),.MREG(MP),.PREG(1),.OPMODEREG(0),.ALUMODEREG(0),.CARRYINREG(0),
 .CARRYINSELREG(0),.INMODEREG(0))d(
 .CLK(clk),.A({{5{a[24]}},a}),.B(b),.C(c),.D(25'd0),.OPMODE(7'b0110101),.ALUMODE(4'b0000),
 .CARRYIN(1'b0),.CARRYINSEL(3'b000),.INMODE(5'b00000),.CEA1(1'b0),.CEA2(1'b0),.CEB1(1'b0),.CEB2(1'b0),
 .CEC(issue),.CED(1'b0),.CEAD(1'b0),.CEM(issue),.CEP(MP?delayed_issue:issue),.CECTRL(1'b0),.CEALUMODE(1'b0),
 .CECARRYIN(1'b0),.CEINMODE(1'b0),.RSTA(1'b0),.RSTB(1'b0),.RSTC(rst),.RSTD(1'b0),.RSTM(rst),
 .RSTP(rst),.RSTCTRL(1'b0),.RSTALUMODE(1'b0),.RSTALLCARRYIN(1'b0),.RSTINMODE(1'b0),
 .ACIN(30'd0),.BCIN(18'd0),.PCIN(48'd0),.CARRYCASCIN(1'b0),.MULTSIGNIN(1'b0),
 .P(p),.ACOUT(),.BCOUT(),.PCOUT(),.CARRYOUT(),.CARRYCASCOUT(),.MULTSIGNOUT(),
 .OVERFLOW(),.UNDERFLOW(),.PATTERNDETECT(),.PATTERNBDETECT());
endmodule
`define DELTA_TOP(NAME,ENGINE,COEF,PIPE) \
module NAME(input wire clk,rst,valid,input wire[65:0]u_in,input wire[4:0]delta, \
 output wire ready,out_valid,output wire[65:0]u_out,output wire issue_valid,narrow_mode); \
 adaptive_delta_leak #(.E(ENGINE),.DC(COEF),.MP(PIPE))u(.*);endmodule
`DELTA_TOP(top_delta_adapt_const,0,25,1)
`DELTA_TOP(top_delta_fixed_const,1,25,1)
`DELTA_TOP(top_delta_lut2_const,2,25,1)
`DELTA_TOP(top_delta_lut6_const,3,25,1)
`DELTA_TOP(top_delta_rom2_const,5,25,1)
`DELTA_TOP(top_delta_adapt_prog,0,-1,1)
`DELTA_TOP(top_delta_fixed_prog,1,-1,1)
`DELTA_TOP(top_delta_lut2_prog,2,-1,1)
`DELTA_TOP(top_delta_lut6_prog,3,-1,1)
`DELTA_TOP(top_delta_adapt_fast_const,0,25,0)
`DELTA_TOP(top_delta_fixed_fast_const,1,25,0)
`DELTA_TOP(top_delta_lut2_fast_const,2,25,0)
`DELTA_TOP(top_delta_lut6_fast_const,3,25,0)
`DELTA_TOP(top_delta_adapt_fast_prog,0,-1,0)
`DELTA_TOP(top_delta_fixed_fast_prog,1,-1,0)
`DELTA_TOP(top_delta_lut2_fast_prog,2,-1,0)
`DELTA_TOP(top_delta_lut6_fast_prog,3,-1,0)
