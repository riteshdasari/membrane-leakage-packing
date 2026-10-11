`timescale 1ns/1ps
// Six-neuron primitive. ENGINE 0: persistent adaptive 8/16; 1: fixed16;
// 2: fixed8 current +16 membrane; 3: direct LUT16; 4: fixed8 persistent,
// requiring a separate proof that membrane and every prefix fit signed8.
// cmd 1 begin/leak, 2 two-weight add, 3 finish/reset. Wide persistent engines
// require two complete output-group passes (3+3 for 16 bits, 4+2 for 12 bits), including two finish
// commands. Source replays spike/weight input stream. No per-neuron queue/refill.
// Proven bounds of full-step current: LOW <= every prefix <= HIGH.
// Fixed-current engine separately requires signed8 current-prefix bounds.
module persistent_unit #(parameter ENGINE=0,SH=1,LEAK=1,HARD=0,LOW=-64,HIGH=56,TH=35,WIDE_BITS=16,STATE_BITS=16)(
 input wire clk,rst,valid,input wire[1:0]cmd,input wire[47:0]wa,wb,
 output wire ready,wide,half,output reg out_valid,output reg[5:0]spike,
 output wire[95:0]state_debug);
 reg boot=1,wide_q=0,half_q=0;
 localparam WL=48/WIDE_BITS,REST=6-WL;
 reg[(6-WL)*WIDE_BITS-1:0]side;
 localparam[47:0]WIDE_SEED={48/WIDE_BITS{1'b1,{WIDE_BITS-1{1'b0}}}};
 reg signed[STATE_BITS-1:0]mem[0:5];
 wire[47:0]p;
 wire signed[15:0]u[0:5],leaked[0:5],integrated[0:5],post[0:5];
 wire[5:0]fits,fire;
 wire take=valid&&ready;
 assign ready=!rst&&!boot;
 assign wide=wide_q;assign half=half_q;
 for(genvar i=0;i<6;i=i+1)begin:lane
  wire[7:0]q8=p[i*8+:8];
  wire[47:0]firstword=half_q?side:p,secondword=half_q?p:side;
  wire[WIDE_BITS-1:0]qwide=half_q?
   ((i<REST)?firstword[(i%WL)*WIDE_BITS+:WIDE_BITS]:
    (i<WL)?p[(i%WL)*WIDE_BITS+:WIDE_BITS]:p[(i%WL)*WIDE_BITS+:WIDE_BITS]):
   ((i<WL)?p[(i%WL)*WIDE_BITS+:WIDE_BITS]:secondword[(i%WL)*WIDE_BITS+:WIDE_BITS]);
  wire signed[7:0]narrow={~q8[7],q8[6:0]};
  wire signed[WIDE_BITS-1:0]signed_wide={~qwide[WIDE_BITS-1],qwide[WIDE_BITS-2:0]};
  wire signed[15:0]widened={{(16-WIDE_BITS){signed_wide[WIDE_BITS-1]}},signed_wide};
  assign u[i]=(ENGINE==2||ENGINE==3)?{{(16-STATE_BITS){mem[i][STATE_BITS-1]}},mem[i]}:wide_q?widened:{{8{narrow[7]}},narrow};
  assign leaked[i]=LEAK?(u[i]-(u[i]>>>SH)):u[i];
  assign fits[i]=(leaked[i]>=(-128-LOW))&&(leaked[i]<=(127-HIGH));
  wire signed[15:0]cur={{8{narrow[7]}},narrow};
  assign integrated[i]=(ENGINE==2)?(mem[i]+cur):u[i];
  assign fire[i]=integrated[i]>=TH;
  assign post[i]=fire[i]?(HARD?16'sd0:integrated[i]-TH):integrated[i];
  assign state_debug[i*16+:16]=u[i];
  if(ENGINE==2||ENGINE==3)begin
   wire signed[3:0]da=wa[i*4+:4],db=wb[i*4+:4];
   always @(posedge clk)begin
    if(rst)mem[i]<=0;
    else if(take)begin
     if(cmd==1)mem[i]<=leaked[i];
     else if(cmd==2&&ENGINE==3)mem[i]<=mem[i]+{{12{da[3]}},da}+{{12{db[3]}},db};
     else if(cmd==3)mem[i]<=post[i];
    end
   end
  end
 end
 wire choose_wide=(ENGINE==1)||((ENGINE==0)&&!(&fits));
 reg[47:0]seed8,seedfirst,seedsecond,finish8,finish16,nextword;
 always @*begin
  seed8=0;seedfirst=0;seedsecond=0;finish8=0;finish16=0;nextword=0;
  for(integer i=0;i<6;i=i+1)begin
   seed8[i*8+:8]={~leaked[i][7],leaked[i][6:0]};
   finish8[i*8+:8]={~post[i][7],post[i][6:0]};
   if(i<WL)seedfirst[i*WIDE_BITS+:WIDE_BITS]={~leaked[i][WIDE_BITS-1],leaked[i][WIDE_BITS-2:0]};
   else seedsecond[(i-WL)*WIDE_BITS+:WIDE_BITS]={~leaked[i][WIDE_BITS-1],leaked[i][WIDE_BITS-2:0]};
  end
  for(integer j=0;j<WL;j=j+1)begin
   if(j<REST)nextword[j*WIDE_BITS+:WIDE_BITS]=side[j*WIDE_BITS+:WIDE_BITS];
   else nextword[j*WIDE_BITS+:WIDE_BITS]={~post[j][WIDE_BITS-1],post[j][WIDE_BITS-2:0]};
   if(half_q)begin
    if(j+WL<6)finish16[j*WIDE_BITS+:WIDE_BITS]={~post[j+WL][WIDE_BITS-1],post[j+WL][WIDE_BITS-2:0]};
    else finish16[j*WIDE_BITS+:WIDE_BITS]={~u[j][WIDE_BITS-1],u[j][WIDE_BITS-2:0]};
   end else finish16[j*WIDE_BITS+:WIDE_BITS]={~post[j][WIDE_BITS-1],post[j][WIDE_BITS-2:0]};
  end
 end
 wire persistent=(ENGINE==0||ENGINE==1||ENGINE==4);
 wire init=boot||(take&&cmd==1)||(persistent&&take&&cmd==3);
 wire add=take&&cmd==2;
 wire[47:0]initial_word=(ENGINE==1)?WIDE_SEED:48'h808080808080;
 wire[47:0]seedword=boot?initial_word:(cmd==1)?((ENGINE==2)?48'h808080808080:choose_wide?seedfirst:seed8):
                    wide_q?(!half_q?nextword:finish16):finish8;
 always @(posedge clk)begin
  if(rst)begin boot<=1;wide_q<=ENGINE==1;half_q<=0;side<=WIDE_SEED;out_valid<=0;spike<=0;end
  else begin
   boot<=0;out_valid<=0;
   if(take)begin
    if(cmd==1)begin wide_q<=choose_wide;half_q<=0;side<=choose_wide?seedsecond:48'd0;spike<=0;end
    if(cmd==3)begin
     if(persistent&&wide_q&&!half_q)begin
      side<=finish16;half_q<=1;
      for(integer i=0;i<WL;i=i+1)spike[i]<=fire[i];
     end else begin
      out_valid<=1;
      if(persistent&&wide_q)for(integer i=WL;i<6;i=i+1)spike[i]<=fire[i];
      else spike<=fire;
     end
    end
   end
  end
 end
 generate if(ENGINE!=3)begin:dsp
 DSP48E1 #(.USE_SIMD("ONE48"),.USE_MULT("NONE"),.AREG(0),.ACASCREG(0),.BREG(0),.BCASCREG(0),
 .CREG(0),.DREG(0),.ADREG(0),.MREG(0),.PREG(1),.OPMODEREG(0),.ALUMODEREG(0),.CARRYINREG(0),
 .CARRYINSELREG(0),.INMODEREG(0)) dsp(
 .CLK(clk),.A(wa[47:18]),.B(wa[17:0]),.C(init?seedword:wb),.D(25'd0),
 .OPMODE(init?7'b000_11_00:add?7'b010_11_11:7'b010_00_00),.ALUMODE(4'b0000),
 .CARRYIN(1'b0),.CARRYINSEL(3'b000),.INMODE(5'b0),.CEA1(1'b0),.CEA2(1'b0),.CEB1(1'b0),.CEB2(1'b0),
 .CEC(1'b0),.CED(1'b0),.CEAD(1'b0),.CEM(1'b0),.CEP(1'b1),.CECTRL(1'b0),.CEALUMODE(1'b0),
 .CECARRYIN(1'b0),.CEINMODE(1'b0),.RSTA(1'b0),.RSTB(1'b0),.RSTC(1'b0),.RSTD(1'b0),.RSTM(1'b0),
 .RSTP(rst),.RSTCTRL(1'b0),.RSTALUMODE(1'b0),.RSTALLCARRYIN(1'b0),.RSTINMODE(1'b0),
 .ACIN(30'd0),.BCIN(18'd0),.PCIN(48'd0),.CARRYCASCIN(1'b0),.MULTSIGNIN(1'b0),
 .P(p),.ACOUT(),.BCOUT(),.PCOUT(),.CARRYOUT(),.CARRYCASCOUT(),.MULTSIGNOUT(),
 .OVERFLOW(),.UNDERFLOW(),.PATTERNDETECT(),.PATTERNBDETECT());
 end else assign p=0;endgenerate
endmodule

`define PERSIST_TOP(NAME,E) \
module NAME(input wire clk,rst,valid,input wire[1:0]cmd,input wire[47:0]wa,wb, \
 output wire ready,wide,half,out_valid,output wire[5:0]spike,output wire[95:0]state_debug); \
 persistent_unit #(.ENGINE(E))u(.*);endmodule
`PERSIST_TOP(top_persist_adaptive,0)
`PERSIST_TOP(top_persist_wide,1)
`PERSIST_TOP(top_persist_current,2)
`PERSIST_TOP(top_persist_lut,3)
`PERSIST_TOP(top_persist_narrow,4)

`define PERSIST_CONFIG_TOP(NAME,E,S,W) \
module NAME(input wire clk,rst,valid,input wire[1:0]cmd,input wire[47:0]wa,wb, \
 output wire ready,wide,half,out_valid,output wire[5:0]spike,output wire[95:0]state_debug); \
 persistent_unit #(.ENGINE(E),.SH(S),.WIDE_BITS(W))u(.*);endmodule
`PERSIST_CONFIG_TOP(top_persist_adaptive_s3,0,3,16)
`PERSIST_CONFIG_TOP(top_persist_wide_s3,1,3,16)
`PERSIST_CONFIG_TOP(top_persist_current_s3,2,3,16)
`PERSIST_CONFIG_TOP(top_persist_lut_s3,3,3,16)
`PERSIST_CONFIG_TOP(top_persist_adaptive12_s3,0,3,12)
`PERSIST_CONFIG_TOP(top_persist_fixed12_s3,1,3,12)
`PERSIST_CONFIG_TOP(top_persist_adaptive10_s3,0,3,10)
`PERSIST_CONFIG_TOP(top_persist_fixed10_s3,1,3,10)
`define PERSIST_SMALL_TOP(NAME,E) \
module NAME(input wire clk,rst,valid,input wire[1:0]cmd,input wire[47:0]wa,wb, \
 output wire ready,wide,half,out_valid,output wire[5:0]spike,output wire[95:0]state_debug); \
 persistent_unit #(.ENGINE(E),.SH(3),.STATE_BITS(10))u(.*);endmodule
`PERSIST_SMALL_TOP(top_persist_current10_s3,2)
`PERSIST_SMALL_TOP(top_persist_lut10_s3,3)
