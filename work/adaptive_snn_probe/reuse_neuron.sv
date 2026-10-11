`timescale 1ns/1ps
// Reuse the SAME ONE48 DSP for packed currents and serialized wide neuron arithmetic.
// No wide fabric adder/subtractor. Packed currents are snapshotted before changing DSP role.
module reuse_neuron #(parameter integer N=6,SLOT=8,WB=4,B=13,SH=1,VTH=35)(
 input wire clk,rst,input wire[1:0]cmd,input wire[N*WB-1:0]w,
 output wire ready,output reg[N-1:0]spike,output wire[N*B-1:0]state_debug
);
 reg[3:0]phase;reg[$clog2(N)-1:0]sel;reg ending,warning_q;
 reg signed[B-1:0]mem[N];reg[47:0]snapshot;
 wire[47:0]P;reg[47:0]ab,cword;reg[6:0]opmode;reg[3:0]alumode;
 function[47:0]gen_word(input integer v);integer i;begin gen_word=0;for(i=0;i<N;i=i+1)gen_word=gen_word+(48'(v)<<(i*SLOT));end endfunction
 localparam[47:0]BIASW=gen_word(1<<(SLOT-1)),NEGHB=48'd0-gen_word(1<<(WB-1));
 wire[N-1:0]alarm;
 for(genvar i=0;i<N;i=i+1)assign alarm[i]=(~|P[i*SLOT+WB+:SLOT-WB])|(&P[i*SLOT+WB+:SLOT-WB]);
 wire[SLOT-1:0]field=snapshot[sel*SLOT+:SLOT];
 wire signed[SLOT-1:0]delta={~field[SLOT-1],field[SLOT-2:0]};
 wire signed[B-1:0]old=mem[sel];wire signed[B-1:0]result=P[B-1:0];
 wire fire=result>=VTH;
 assign ready=phase==1&&!warning_q;
 always @*begin
  ab=0;cword=0;opmode=7'b010_00_00;alumode=0;
  case(phase)
   0,8:begin cword=BIASW;opmode=7'b000_11_00;end
   1:if(ready&&cmd==1)begin
    for(integer i=0;i<N;i=i+1)ab[i*SLOT+:WB]={~w[i*WB+WB-1],w[i*WB+:WB-1]};
    cword=NEGHB;opmode=7'b010_11_11;
   end
   3:begin ab={{(48-B){old[B-1]}},old};cword={{(48-SLOT){delta[SLOT-1]}},delta};opmode=7'b000_11_11;end
   4:if(ending&&fire)begin cword=VTH;opmode=7'b010_11_00;alumode=4'b0011;end
   6:begin ab={{(48-B){old[B-1]}},old}>>>SH;cword={{(48-B){old[B-1]}},old};opmode=7'b011_00_11;alumode=4'b0011;end
   default:;
  endcase
 end
 integer i;
 always @(posedge clk)begin
  if(rst)begin phase<=0;sel<=0;ending<=0;warning_q<=0;snapshot<=0;spike<=0;for(i=0;i<N;i=i+1)mem[i]<=0;end
  else begin
   warning_q<=(phase==1)?(|alarm):1'b0;
   case(phase)
    0:phase<=1;
    1:begin
     if(warning_q||cmd==3)begin snapshot<=P;ending<=cmd==3;sel<=0;phase<=3;end
     else if(cmd==2)begin sel<=0;phase<=6;spike<=0;end
    end
    3:phase<=4;
    4:begin
     if(ending)spike[sel]<=fire;
     if(ending&&fire)phase<=5;
     else begin mem[sel]<=result;if(sel==N-1)begin phase<=8;sel<=0;end else begin sel<=sel+1'b1;phase<=3;end end
    end
    5:begin mem[sel]<=result;if(sel==N-1)begin phase<=8;sel<=0;end else begin sel<=sel+1'b1;phase<=3;end end
    6:phase<=7;
    7:begin mem[sel]<=result;if(sel==N-1)begin phase<=8;sel<=0;end else begin sel<=sel+1'b1;phase<=6;end end
    8:phase<=1;
    default:phase<=0;
   endcase
  end
 end
 for(genvar g=0;g<N;g=g+1)assign state_debug[g*B+:B]=mem[g];
 DSP48E1 #(.USE_SIMD("ONE48"),.USE_MULT("NONE"),.AREG(0),.ACASCREG(0),.BREG(0),.BCASCREG(0),
 .CREG(0),.DREG(0),.ADREG(0),.MREG(0),.PREG(1),.OPMODEREG(0),.ALUMODEREG(0),.CARRYINREG(0),
 .CARRYINSELREG(0),.INMODEREG(0)) dsp(
 .CLK(clk),.A(ab[47:18]),.B(ab[17:0]),.C(cword),.D(25'd0),.OPMODE(opmode),.ALUMODE(alumode),
 .CARRYIN(1'b0),.CARRYINSEL(3'b000),.INMODE(5'b0),.CEA1(1'b0),.CEA2(1'b0),.CEB1(1'b0),.CEB2(1'b0),
 .CEC(1'b0),.CED(1'b0),.CEAD(1'b0),.CEM(1'b0),.CEP(1'b1),.CECTRL(1'b0),.CEALUMODE(1'b0),
 .CECARRYIN(1'b0),.CEINMODE(1'b0),.RSTA(1'b0),.RSTB(1'b0),.RSTC(1'b0),.RSTD(1'b0),.RSTM(1'b0),
 .RSTP(rst),.RSTCTRL(1'b0),.RSTALUMODE(1'b0),.RSTALLCARRYIN(1'b0),.RSTINMODE(1'b0),
 .ACIN(30'd0),.BCIN(18'd0),.PCIN(48'd0),.CARRYCASCIN(1'b0),.MULTSIGNIN(1'b0),
 .P(P),.ACOUT(),.BCOUT(),.PCOUT(),.CARRYOUT(),.CARRYCASCOUT(),.MULTSIGNOUT(),
 .OVERFLOW(),.UNDERFLOW(),.PATTERNDETECT(),.PATTERNBDETECT());
endmodule
module top_reuse_shared(input wire clk,rst,input wire[1:0]cmd_i,input wire[95:0]w_i,
 output reg[23:0]sp_o,output reg[3:0]ready_o);
 reg[1:0]cmd;reg[95:0]w;wire[23:0]sp;wire[3:0]ready;
 always @(posedge clk)begin cmd<=cmd_i;w<=w_i;sp_o<=sp;ready_o<=ready;end
 for(genvar g=0;g<4;g=g+1)begin reuse_neuron u(.clk(clk),.rst(rst),.cmd(cmd),.w(w[g*24+:24]),.ready(ready[g]),.spike(sp[g*6+:6]),.state_debug());end
endmodule
