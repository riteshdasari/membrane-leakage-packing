`timescale 1ns/1ps
// Exact guarded current accumulation, NOT a complete neuron or SRAM controller.
// Each SLOT-bit offset-binary field reserves one bit of headroom.
// Drain and reinitialize after early warning, before accepting another update.
module guard_acc #(parameter integer SLOT=8, N=6, WB=4, MIDPOINT=1,LATENCY=0)(
 input wire clk,rst,add,init,
 input wire [N*WB-1:0] w,
 input wire [$clog2(N)-1:0] sel,
 output wire signed [SLOT-1:0] rd_s,
 output wire warning,accepted
);
 function [47:0] word_const(input integer v);
   integer i; begin word_const=0; for(i=0;i<N;i=i+1) word_const=word_const+(48'(v)<<(i*SLOT)); end
 endfunction
 localparam [47:0] BIASW=word_const(1<<(SLOT-1)), NEGHB=48'd0-word_const(1<<(WB-1));
 wire [47:0] P; reg [47:0] ab;
 wire [N-1:0] alarm;
 for(genvar i=0;i<N;i=i+1) begin
   if (MIDPOINT) assign alarm[i]=~(P[i*SLOT+SLOT-1]^P[i*SLOT+SLOT-2]);
   else if(LATENCY) assign alarm[i]=(~|P[i*SLOT+WB+:SLOT-WB])|(&P[i*SLOT+WB+:SLOT-WB]);
   else assign alarm[i]=(~|P[i*SLOT+WB-1+:SLOT-WB+1])|(&P[i*SLOT+WB-1+:SLOT-WB+1]);
 end
 if(LATENCY)begin
   reg warning_q;
   always @(posedge clk)if(rst||init)warning_q<=0;else warning_q<=|alarm;
   assign warning=warning_q;
 end else assign warning=|alarm;
 assign accepted=add&&!warning&&!init&&!rst;
 wire [SLOT-1:0] selected=P[sel*SLOT+:SLOT];
 assign rd_s={~selected[SLOT-1],selected[SLOT-2:0]};
 always @* begin
   ab=0;
   for(integer i=0;i<N;i=i+1) ab[i*SLOT+:WB]={~w[i*WB+WB-1],w[i*WB+:WB-1]};
 end
 DSP48E1 #(.USE_SIMD("ONE48"),.USE_MULT("NONE"),.AREG(0),.ACASCREG(0),.BREG(0),.BCASCREG(0),
 .CREG(0),.DREG(0),.ADREG(0),.MREG(0),.PREG(1),.OPMODEREG(0),.ALUMODEREG(0),.CARRYINREG(0),
 .CARRYINSELREG(0),.INMODEREG(0)) dsp(
 .CLK(clk),.A(ab[47:18]),.B(ab[17:0]),.C(init?BIASW:NEGHB),.D(25'd0),
 .OPMODE(init?7'b000_11_00:accepted?7'b010_11_11:7'b010_00_00),.ALUMODE(4'b0000),
 .CARRYIN(1'b0),.CARRYINSEL(3'b000),.INMODE(5'b0),.CEA1(1'b0),.CEA2(1'b0),.CEB1(1'b0),.CEB2(1'b0),
 .CEC(1'b0),.CED(1'b0),.CEAD(1'b0),.CEM(1'b0),.CEP(1'b1),.CECTRL(1'b0),.CEALUMODE(1'b0),
 .CECARRYIN(1'b0),.CEINMODE(1'b0),.RSTA(1'b0),.RSTB(1'b0),.RSTC(1'b0),.RSTD(1'b0),.RSTM(1'b0),
 .RSTP(rst),.RSTCTRL(1'b0),.RSTALUMODE(1'b0),.RSTALLCARRYIN(1'b0),.RSTINMODE(1'b0),
 .ACIN(30'd0),.BCIN(18'd0),.PCIN(48'd0),.CARRYCASCIN(1'b0),.MULTSIGNIN(1'b0),
 .P(P),.ACOUT(),.BCOUT(),.PCOUT(),.CARRYOUT(),.CARRYCASCOUT(),.MULTSIGNOUT(),
 .OVERFLOW(),.UNDERFLOW(),.PATTERNDETECT(),.PATTERNBDETECT());
endmodule

module top_margin_acc(input wire clk,rst,add_i,init_i,
 input wire [84*4-1:0] w_i,input wire [3:0] sel_i,
 output reg [14*8-1:0] rd_o,output reg [13:0] warn_o);
 reg add,init; reg [84*4-1:0] w; reg [2:0] sel;
 wire [14*8-1:0] rd; wire [13:0] warn;
 always @(posedge clk) begin add<=add_i;init<=init_i;w<=w_i;sel<=sel_i[2:0];rd_o<=rd;warn_o<=warn;end
 for(genvar g=0;g<14;g=g+1) begin
   guard_acc #(.MIDPOINT(0)) u(.clk(clk),.rst(rst),.add(add),.init(init),.w(w[g*24+:24]),.sel(sel),
     .rd_s(rd[g*8+:8]),.warning(warn[g]),.accepted());
 end
endmodule

module top_guard_acc(input wire clk,rst,add_i,init_i,
 input wire [84*4-1:0] w_i,input wire [3:0] sel_i,
 output reg [14*8-1:0] rd_o,output reg [13:0] warn_o);
 reg add,init; reg [84*4-1:0] w; reg [2:0] sel;
 wire [14*8-1:0] rd; wire [13:0] warn;
 always @(posedge clk) begin add<=add_i;init<=init_i;w<=w_i;sel<=sel_i[2:0];rd_o<=rd;warn_o<=warn;end
 for(genvar g=0;g<14;g=g+1) begin
   guard_acc u(.clk(clk),.rst(rst),.add(add),.init(init),.w(w[g*24+:24]),.sel(sel),
     .rd_s(rd[g*8+:8]),.warning(warn[g]),.accepted());
 end
endmodule
