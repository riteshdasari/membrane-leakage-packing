`timescale 1ns/1ps
// Certified current tile kernel, not a complete accelerator. Ordered commands:
// 1 seed, 2 add two weight words, 3 commit current tile.
// Packed 6/8: full-word radix encoding. Native/LUT: raw int4 in low 96 bits.
// Supported variants are the four top modules below. CENTER is fixed per core.
// No output backpressure. Source must hold a stalled command stable.
// Bounds and full-word encoding are supplied offline; NO runtime overflow fallback.
module fixed_pair #(parameter SLOT=8, NATIVE=0, LUT=0, SH=1, LEAK=1, HARD=0,
 parameter CENTER=(SLOT==8 && !NATIVE && !LUT),
 parameter LANES=48/SLOT, GROUPS=24/LANES, WORDS=GROUPS*48)(
 input wire clk,rst,valid,input wire[1:0]cmd,
 input wire[WORDS-1:0]wa,wb,seed,
 input wire first,last,
 output wire ready,output reg out_valid,output reg[23:0]spike,
 output wire[383:0]state_debug
);
 reg[1:0]dcmd;reg df,dl;reg busy;
 reg[WORDS-1:0]a,b,c;
 // Six-bit seed = -L; retain it for exact Q - seed current recovery.
 reg[143:0]bias_q;
 wire[WORDS-1:0]packed_p;
 reg signed[15:0]mem[0:23],delta[0:23],sum_q[0:23];
 reg v1,v2,f1,l1,l2;
 assign ready=!rst && (cmd!=3 || !busy);
 always @(posedge clk)begin
  if(rst)begin dcmd<=0;df<=0;dl<=0;busy<=0;a<=0;b<=0;c<=0;end
  else begin
   dcmd<=(valid&&ready)?cmd:0;
   if(valid&&ready)begin
    df<=first;dl<=last;
    if(cmd==1)c<=seed;
    if(cmd==2)begin a<=wa;b<=wb;end
   end
   if(v2)busy<=0;
   if(valid&&ready&&cmd==3)busy<=1;
  end
 end
 generate if(!LUT)begin:dsp
  for(genvar g=0;g<GROUPS;g=g+1)begin
   wire[47:0]initial_word=NATIVE?48'd0:CENTER?48'h808080808080:c[g*48+:48];
   wire[47:0]av, bv;
   if(NATIVE)begin
    // Raw int4 weights only; sign extension is wiring, not expanded storage.
    for(genvar j=0;j<4;j=j+1)begin
     assign av[j*12+:12]={{8{a[(g*4+j)*4+3]}},a[(g*4+j)*4+:4]};
     assign bv[j*12+:12]={{8{b[(g*4+j)*4+3]}},b[(g*4+j)*4+:4]};
    end
   end else begin assign av=a[g*48+:48];assign bv=b[g*48+:48];end
   wire[47:0]cv=(dcmd==1)?initial_word:bv;
   DSP48E1 #(.USE_SIMD(NATIVE?"FOUR12":"ONE48"),.USE_MULT("NONE"),
   .AREG(0),.ACASCREG(0),.BREG(0),.BCASCREG(0),.CREG(0),.DREG(0),.ADREG(0),
   .MREG(0),.PREG(1),.OPMODEREG(0),.ALUMODEREG(0),.CARRYINREG(0),.CARRYINSELREG(0),.INMODEREG(0)) u(
    .CLK(clk),.A(av[47:18]),.B(av[17:0]),.C(cv),.D(25'd0),
    .OPMODE(dcmd==1?7'b000_11_00:dcmd==2?7'b010_11_11:7'b010_00_00),
    .ALUMODE(4'b0000),.CARRYIN(1'b0),.CARRYINSEL(3'b000),.INMODE(5'b0),
    .CEA1(1'b0),.CEA2(1'b0),.CEB1(1'b0),.CEB2(1'b0),.CEC(1'b0),.CED(1'b0),.CEAD(1'b0),
    .CEM(1'b0),.CEP(1'b1),.CECTRL(1'b0),.CEALUMODE(1'b0),.CECARRYIN(1'b0),.CEINMODE(1'b0),
    .RSTA(1'b0),.RSTB(1'b0),.RSTC(1'b0),.RSTD(1'b0),.RSTM(1'b0),.RSTP(rst),
    .RSTCTRL(1'b0),.RSTALUMODE(1'b0),.RSTALLCARRYIN(1'b0),.RSTINMODE(1'b0),
    .ACIN(30'd0),.BCIN(18'd0),.PCIN(48'd0),.CARRYCASCIN(1'b0),.MULTSIGNIN(1'b0),
    .P(packed_p[g*48+:48]),.ACOUT(),.BCOUT(),.PCOUT(),.CARRYOUT(),.CARRYCASCOUT(),
    .MULTSIGNOUT(),.OVERFLOW(),.UNDERFLOW(),.PATTERNDETECT(),.PATTERNBDETECT());
  end
 end endgenerate
 always @(posedge clk)begin
  if(rst)begin v1<=0;v2<=0;out_valid<=0;bias_q<=0;f1<=0;l1<=0;l2<=0;end
  else begin
   if(dcmd==1)bias_q<=c[143:0];
   v1<=dcmd==3;v2<=v1;out_valid<=v2;
   if(dcmd==3)begin f1<=df;l1<=dl;end
   if(v1)l2<=l1;
  end
 end
 for(genvar i=0;i<24;i=i+1)begin:neuron
  wire[15:0]q={{(16-SLOT){1'b0}},packed_p[(i/LANES)*48+(i%LANES)*SLOT+:SLOT]};
  wire signed[6:0]biased_delta=$signed({1'b0,q[5:0]})-$signed({1'b0,bias_q[i*6+:6]});
  wire signed[15:0]native_delta={{(16-SLOT){q[SLOT-1]}},q[SLOT-1:0]};
  wire signed[15:0]current_delta=NATIVE?native_delta:CENTER?($signed(q)-16'sd128):{{9{biased_delta[6]}},biased_delta};
  reg signed[7:0]cur;
  wire signed[3:0]da=a[i*4+:4],db=b[i*4+:4];
  always @(posedge clk)begin
   if(rst)begin mem[i]<=0;delta[i]<=0;sum_q[i]<=0;cur<=0;spike[i]<=0;end
   else begin
    if(LUT)begin
     if(dcmd==1)cur<=0;
     else if(dcmd==2)cur<=cur+{{4{da[3]}},da}+{{4{db[3]}},db};
    end
    if(dcmd==3)delta[i]<=LUT?{{8{cur[7]}},cur}:current_delta;
    if(v1)sum_q[i]<=(f1&&LEAK?(mem[i]-(mem[i]>>>SH)):mem[i])+delta[i];
    if(v2)begin
     mem[i]<=(l2&&sum_q[i]>=16'sd35)?(HARD?16'sd0:sum_q[i]-16'sd35):sum_q[i];
     spike[i]<=l2&&sum_q[i]>=16'sd35;
    end
   end
  end
  assign state_debug[i*16+:16]=mem[i];
 end
endmodule

// The same registered input / output protocol is used in simulation and routing.
`define PAIR_TOP(NAME,S,N,L) \
module NAME(input wire clk,rst,valid,input wire[1:0]cmd, \
 input wire[(24/(48/S))*48-1:0]wa,wb,seed,input wire first,last, \
 output wire ready,out_valid,output wire[23:0]spike,output wire[383:0]state_debug); \
 fixed_pair #(.SLOT(S),.NATIVE(N),.LUT(L)) u(.*); endmodule
`PAIR_TOP(top_pair6,6,0,0)
`PAIR_TOP(top_pair8,8,0,0)
`PAIR_TOP(top_pair12,12,1,0)
`PAIR_TOP(top_pairlut,8,0,1)
