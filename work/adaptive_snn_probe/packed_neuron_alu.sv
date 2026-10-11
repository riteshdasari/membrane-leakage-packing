`timescale 1ns/1ps
// Fixed-format feasibility primitive, not an adaptive controller.
// ENGINE 0: DSP does accumulation, integer leak, and boundary reset.
// ENGINE 1: matched LUT state, five-bit pair pre-adder, leak and reset.
// All prefixes and persistent membrane must fit signed B bits.
module packed_neuron_alu #(parameter ENGINE=0,B=8,N=6,SH=1,LEAK=1,HARD=0,TH=35)(
 input wire clk,rst,valid,input wire[1:0]cmd,input wire[47:0]wa,wb,
 output wire ready,output reg out_valid,output reg[N-1:0]spike,
 output wire[N*16-1:0]state_debug);
 reg boot=1;
 wire take=valid&&ready;
 assign ready=!rst&&!boot;
 reg signed[B-1:0]mem[0:N-1];
 wire[47:0]p;
 wire[B-1:0]q[0:N-1];
 wire signed[B-1:0]u[0:N-1];
 wire[N-1:0]fire;
 localparam[B-1:0]BIAS=1<<(B-1);
 localparam[47:0]BIAS_WORD={N{BIAS}};
 localparam[B-1:0]K=BIAS>>SH;
 localparam[47:0]K_WORD={N{K}};
 wire[47:0]SHIFT_WORD,RESET_WORD;
 for(genvar i=0;i<N;i=i+1)begin:lane
  assign q[i]=p[i*B+:B];
  assign u[i]=ENGINE==0?{~q[i][B-1],q[i][B-2:0]}:mem[i];
  assign state_debug[i*16+:16]={{(16-B){u[i][B-1]}},u[i]};
  assign fire[i]=(ENGINE==0)?(q[i]>=(BIAS+TH)):(u[i]>=TH);
  assign SHIFT_WORD[i*B+:B]=q[i]>>SH;
  assign RESET_WORD[i*B+:B]=fire[i]?(HARD?{1'b0,q[i][B-2:0]}:TH):0;
  if(ENGINE==1)begin
   wire signed[3:0]a=wa[i*4+:4],b=wb[i*4+:4];
   wire signed[4:0]pair={a[3],a}+{b[3],b};
   always @(posedge clk)begin
    if(rst)mem[i]<=0;
    else if(take)case(cmd)
     1:if(LEAK)mem[i]<=mem[i]-(mem[i]>>>SH);
     2:mem[i]<=mem[i]+{{(B-5){pair[4]}},pair};
     3:if(fire[i])mem[i]<=HARD?0:mem[i]-TH;
    endcase
   end
  end
 end
 if(N*B<48)begin
  assign SHIFT_WORD[47:N*B]=0;
  assign RESET_WORD[47:N*B]=0;
 end
 always @(posedge clk)begin
  if(rst)begin boot<=1;out_valid<=0;spike<=0;end
  else begin
   boot<=0;out_valid<=take&&cmd==3;
   if(take&&cmd==3)spike<=fire;
  end
 end
 generate if(ENGINE==0)begin:dsp
 reg[47:0]ab,c;
 reg[6:0]op;
 reg[3:0]alu;
 always @*begin
  ab=0;c=0;op=7'b010_00_00;alu=0;
  if(boot)begin c=BIAS_WORD;op=7'b000_11_00;end
  else if(take)case(cmd)
   1:if(LEAK)begin
    // q' = q - (q >> SH) + (BIAS >> SH), lane by lane.
    // q >= q>>SH and each final q' fits its field, so no lane borrow/carry.
    ab=SHIFT_WORD;c=-K_WORD;op=7'b010_11_11;alu=4'b0011;
   end
   2:begin ab=wa;c=wb;op=7'b010_11_11;end
   3:begin ab=RESET_WORD;op=7'b010_00_11;alu=4'b0011;end
  endcase
 end
 DSP48E1 #(.USE_SIMD("ONE48"),.USE_MULT("NONE"),.AREG(0),.ACASCREG(0),.BREG(0),.BCASCREG(0),
 .CREG(0),.DREG(0),.ADREG(0),.MREG(0),.PREG(1),.OPMODEREG(0),.ALUMODEREG(0),.CARRYINREG(0),
 .CARRYINSELREG(0),.INMODEREG(0)) d(
 .CLK(clk),.A(ab[47:18]),.B(ab[17:0]),.C(c),.D(25'd0),.OPMODE(op),.ALUMODE(alu),
 .CARRYIN(1'b0),.CARRYINSEL(3'b000),.INMODE(5'b0),.CEA1(1'b0),.CEA2(1'b0),.CEB1(1'b0),.CEB2(1'b0),
 .CEC(1'b0),.CED(1'b0),.CEAD(1'b0),.CEM(1'b0),.CEP(1'b1),.CECTRL(1'b0),.CEALUMODE(1'b0),
 .CECARRYIN(1'b0),.CEINMODE(1'b0),.RSTA(1'b0),.RSTB(1'b0),.RSTC(1'b0),.RSTD(1'b0),.RSTM(1'b0),
 .RSTP(rst),.RSTCTRL(1'b0),.RSTALUMODE(1'b0),.RSTALLCARRYIN(1'b0),.RSTINMODE(1'b0),
 .ACIN(30'd0),.BCIN(18'd0),.PCIN(48'd0),.CARRYCASCIN(1'b0),.MULTSIGNIN(1'b0),
 .P(p),.ACOUT(),.BCOUT(),.PCOUT(),.CARRYOUT(),.CARRYCASCOUT(),.MULTSIGNOUT(),
 .OVERFLOW(),.UNDERFLOW(),.PATTERNDETECT(),.PATTERNBDETECT());
 end else assign p=0;endgenerate
endmodule

`define NEURON_TOP(NAME,E,W,L,S) \
module NAME(input wire clk,rst,valid,input wire[1:0]cmd,input wire[47:0]wa,wb, \
 output wire ready,out_valid,output wire[L-1:0]spike,output wire[L*16-1:0]state_debug); \
 packed_neuron_alu #(.ENGINE(E),.B(W),.N(L),.SH(S))u(.*);endmodule
`NEURON_TOP(top_neuron_dsp8,0,8,6,1)
`NEURON_TOP(top_neuron_lut8,1,8,6,1)
`NEURON_TOP(top_neuron_dsp10,0,10,4,3)
`NEURON_TOP(top_neuron_lut10,1,10,4,3)

`define NEURON_CURRENT_TOP(NAME,W,L,S) \
module NAME(input wire clk,rst,valid,input wire[1:0]cmd,input wire[47:0]wa,wb, \
 output wire ready,out_valid,output wire[L-1:0]spike,output wire[L*16-1:0]state_debug); \
 wire[95:0]sx;wire[5:0]spx; \
 persistent_unit #(.ENGINE(2),.STATE_BITS(W),.SH(S))u(.clk(clk),.rst(rst),.valid(valid),.cmd(cmd), \
 .wa({16'b0,wa[31:0]}),.wb({16'b0,wb[31:0]}),.ready(ready),.wide(),.half(),.out_valid(out_valid),.spike(spx),.state_debug(sx)); \
 assign spike=spx[L-1:0];assign state_debug=sx[L*16-1:0];endmodule
`NEURON_CURRENT_TOP(top_neuron_current10,10,4,3)
// Six-lane reference retains all six input fields.
module top_neuron_current8(input wire clk,rst,valid,input wire[1:0]cmd,input wire[47:0]wa,wb,
 output wire ready,out_valid,output wire[5:0]spike,output wire[95:0]state_debug);
 persistent_unit #(.ENGINE(2),.STATE_BITS(8),.SH(1))u(.clk(clk),.rst(rst),.valid(valid),.cmd(cmd),
 .wa(wa),.wb(wb),.ready(ready),.wide(),.half(),.out_valid(out_valid),.spike(spike),.state_debug(state_debug));
endmodule
