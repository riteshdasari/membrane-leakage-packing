`timescale 1ns/1ps
// Scalar quotient-only screen. Four advancing clocks accept -> handshake.
// ALT0: full signed product; ALT1: constant25 signed-digit expression;
// ALT2: U=256h+r, quotient=delta*h+floor(delta*r/256).
// ALT1 has the same generic multiplication as ALT0 for programmable delta.
// Every variant has raw capture -> quotient/original -> subtraction -> output.
module quotient_screen #(parameter ALT=0, DC=25)(
 input wire clk,rst,in_valid,out_ready,
 input wire signed[10:0]u_in,input wire[4:0]delta,
 output wire in_ready,output reg out_valid=0,
 output reg signed[10:0]u_out=0);
 wire advance=!out_valid||out_ready;
 wire accept=in_valid&&advance;
 assign in_ready=advance;
 reg v0=0,v1=0,v2=0;
 reg signed[10:0]u0=0,u1=0,r2=0;
 reg[4:0]d0=0;
 reg signed[7:0]q1=0;
 wire signed[7:0]quotient;
 generate if(ALT==2)begin:split
  wire signed[2:0]h=u0[10:8];
  wire[7:0]r=u0[7:0];
  wire signed[7:0]hx={{5{h[2]}},h};
  wire[12:0]rx={5'b0,r};
  wire signed[5:0]dc={1'b0,d0};
  (* use_dsp="no" *) wire signed[7:0]hp;
  (* use_dsp="no" *) wire[12:0]lp;
  if(DC==25)begin
   assign hp=(hx<<<4)+(hx<<<3)+hx;
   assign lp=(rx<<4)+(rx<<3)+rx;
  end else begin assign hp=h*dc;assign lp=r*d0;end
  assign quotient=hp+$signed({3'b0,lp[12:8]});
 end else begin:full
  wire signed[15:0]ux={{5{u0[10]}},u0};
  wire signed[5:0]dc={1'b0,d0};
  (* use_dsp="no" *) wire signed[15:0]p;
  if(DC==25&&ALT==1)assign p=(ux<<<5)-(ux<<<3)+ux;
  else if(DC==25)assign p=(ux<<<4)+(ux<<<3)+ux;
  else assign p=u0*dc;
  assign quotient=p[15:8];
 end endgenerate
 always @(posedge clk)begin
  if(rst)begin
   v0<=0;v1<=0;v2<=0;out_valid<=0;
   u0<=0;d0<=0;u1<=0;q1<=0;r2<=0;u_out<=0;
  end else if(advance)begin
   v0<=accept;v1<=v0;v2<=v1;out_valid<=v2;
   if(accept)begin u0<=u_in;d0<=DC<0?delta:DC;end
   if(v0)begin u1<=u0;q1<=quotient;end
   if(v1)r2<=u1-$signed({{3{q1[7]}},q1});
   if(v2)u_out<=r2;
  end
 end
endmodule
`define QS_TOP(NAME,VARIANT,COEF) \
module NAME(input wire clk,rst,in_valid,out_ready,input wire signed[10:0]u_in,input wire[4:0]delta, \
 output wire in_ready,out_valid,output wire signed[10:0]u_out); \
 quotient_screen #(.ALT(VARIANT),.DC(COEF))core(.*);endmodule
`QS_TOP(top_quotient_full_const,0,25)
`QS_TOP(top_quotient_digit_const,1,25)
`QS_TOP(top_quotient_split_const,2,25)
`QS_TOP(top_quotient_full_prog,0,-1)
`QS_TOP(top_quotient_digit_prog,1,-1)
`QS_TOP(top_quotient_split_prog,2,-1)
`undef QS_TOP
