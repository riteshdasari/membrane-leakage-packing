`timescale 1ns/1ps
// Isolated fixed-format feasibility gate, not adaptive packing or a full neuron.
// Contract: shared beta in [0,256], U_next=ceil(beta*U/256), two signed lanes.
// E=0: two 8-bit fields in one DSP; for wider B use two scalar DSPs.
// E=1: identical LUT arithmetic, with DSP inference explicitly disabled.
// E=2: two scalar DSPs, also for B=8. BC<0 makes beta programmable per request.
module packed_leak #(parameter E=0,B=8,BC=231)(
 input wire clk,rst,valid,input wire[2*B-1:0]u_in,input wire[8:0]beta,
 output reg out_valid=0,output wire[2*B-1:0]u_out);
 reg[2*B-1:0]u_q=0;
 reg[8:0]b_q=0;
 reg v_q=0;
 wire[8:0]coef=BC<0?b_q:BC;
 always @(posedge clk)begin
  if(rst)begin u_q<=0;b_q<=0;v_q<=0;out_valid<=0;end
  else begin
   v_q<=valid;out_valid<=v_q;
   if(valid)begin u_q<=u_in;if(BC<0)b_q<=beta;end
  end
 end
 generate if(E==0&&B==8)begin:packed_fields
  wire[7:0]q0={~u_q[7],u_q[6:0]},q1={~u_q[15],u_q[14:8]};
  wire[24:0]a={1'b0,q1,8'b0,q0};
  // K=128*(256-beta)+255; its field and each final product fit 16 bits.
  wire[15:0]k=16'd33023-({7'b0,coef}<<7);
  wire[47:0]c={16'b0,k,k};
  wire[47:0]p;
  leak_dsp d(.clk(clk),.rst(rst),.ce(v_q),.a(a),.b({9'b0,coef}),.c(c),.p(p));
  assign u_out={~p[31],p[30:24],~p[15],p[14:8]};
 end else if(E==1)begin:lut
  for(genvar i=0;i<2;i=i+1)begin:lane
   wire signed[B-1:0]u=u_q[i*B+:B];
   wire signed[9:0]cb={1'b0,coef};
   (* use_dsp="no" *) wire signed[B+9:0]product=u*cb;
   wire signed[B+9:0]rounded=product+255;
   reg[B-1:0]result=0;
   always @(posedge clk)begin
    if(rst)result<=0;else if(v_q)result<=rounded>>>8;
   end
   assign u_out[i*B+:B]=result;
  end
 end else begin:scalar
  for(genvar i=0;i<2;i=i+1)begin:lane
   wire signed[B-1:0]u=u_q[i*B+:B];
   wire[47:0]p;
   leak_dsp d(.clk(clk),.rst(rst),.ce(v_q),.a({{(25-B){u[B-1]}},u}),
    .b({9'b0,coef}),.c(48'd255),.p(p));
   assign u_out[i*B+:B]=p[B+7:8];
  end
 end endgenerate
endmodule

module leak_dsp(input wire clk,rst,ce,input wire[24:0]a,input wire[17:0]b,
 input wire[47:0]c,output wire[47:0]p);
 DSP48E1 #(.USE_SIMD("ONE48"),.USE_MULT("MULTIPLY"),.AREG(0),.ACASCREG(0),.BREG(0),.BCASCREG(0),
 .CREG(0),.DREG(0),.ADREG(0),.MREG(0),.PREG(1),.OPMODEREG(0),.ALUMODEREG(0),.CARRYINREG(0),
 .CARRYINSELREG(0),.INMODEREG(0))d(
 .CLK(clk),.A({{5{a[24]}},a}),.B(b),.C(c),.D(25'd0),.OPMODE(7'b0110101),.ALUMODE(4'b0000),
 .CARRYIN(1'b0),.CARRYINSEL(3'b000),.INMODE(5'b00000),.CEA1(1'b0),.CEA2(1'b0),.CEB1(1'b0),.CEB2(1'b0),
 .CEC(1'b0),.CED(1'b0),.CEAD(1'b0),.CEM(1'b0),.CEP(ce),.CECTRL(1'b0),.CEALUMODE(1'b0),
 .CECARRYIN(1'b0),.CEINMODE(1'b0),.RSTA(1'b0),.RSTB(1'b0),.RSTC(1'b0),.RSTD(1'b0),.RSTM(1'b0),
 .RSTP(rst),.RSTCTRL(1'b0),.RSTALUMODE(1'b0),.RSTALLCARRYIN(1'b0),.RSTINMODE(1'b0),
 .ACIN(30'd0),.BCIN(18'd0),.PCIN(48'd0),.CARRYCASCIN(1'b0),.MULTSIGNIN(1'b0),
 .P(p),.ACOUT(),.BCOUT(),.PCOUT(),.CARRYOUT(),.CARRYCASCOUT(),.MULTSIGNOUT(),
 .OVERFLOW(),.UNDERFLOW(),.PATTERNDETECT(),.PATTERNBDETECT());
endmodule

`define LEAK_TOP(NAME,ENGINE,BITS,COEF) \
module NAME(input wire clk,rst,valid,input wire[2*BITS-1:0]u_in,input wire[8:0]beta, \
 output wire out_valid,output wire[2*BITS-1:0]u_out); \
 packed_leak #(.E(ENGINE),.B(BITS),.BC(COEF))u(.*);endmodule
`LEAK_TOP(top_leak_pack8_const,0,8,231)
`LEAK_TOP(top_leak_lut8_const,1,8,231)
`LEAK_TOP(top_leak_scalar8_const,2,8,231)
`LEAK_TOP(top_leak_pack8_prog,0,8,-1)
`LEAK_TOP(top_leak_lut8_prog,1,8,-1)
`LEAK_TOP(top_leak_scalar8_prog,2,8,-1)
`LEAK_TOP(top_leak_scalar10_const,0,10,231)
`LEAK_TOP(top_leak_lut10_const,1,10,231)
`LEAK_TOP(top_leak_scalar10_prog,0,10,-1)
`LEAK_TOP(top_leak_lut10_prog,1,10,-1)
