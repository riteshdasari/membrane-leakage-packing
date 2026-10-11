`timescale 1ns/1ps
// Exact certified U in [-686,245] + signed8 I. Internal sum11, signextended output12.
// E0 adaptive DSP, E1 fixed8 DSP, E2 FOUR12+4 LUT, E3 LUT8,
// E4 the identical membrane prefix admission implemented using LUT arithmetic.
module certified_u11 #(parameter integer E=0)(
 input wire clk,rst,in_valid,out_ready,
 input wire[87:0]u_in,i_in,input wire[3:0]available,
 output wire in_ready,output wire[3:0]take,
 output wire out_valid,output wire[3:0]out_count,
 output wire[95:0]out_data,output wire narrow_mode);
 reg valid=0;reg[3:0]count=0;
 wire advance=!valid||out_ready;
 wire tail5_fits8=(u_in[11*5+8+:3]=={3{u_in[11*5+7]}});
 wire tail6_fits8=(u_in[11*6+8+:3]=={3{u_in[11*6+7]}});
 wire tail7_fits8=(u_in[11*7+8+:3]=={3{u_in[11*7+7]}});
 wire[3:0]prefix=(available<=5)?available:
  (!tail5_fits8?4'd5:((available<=6||!tail6_fits8)?4'd6:
   ((available>=8&&tail7_fits8)?4'd8:4'd7)));
 assign take=(E==0||E==4)?prefix:available;
 assign narrow_mode=(E==0||E==4)&&(take>5);
 assign in_ready=advance;assign out_valid=valid;assign out_count=count;
 wire accept=in_valid&&advance&&(available!=0);
 always @(posedge clk)begin
  if(rst)begin valid<=0;count<=0;end
  else if(advance)begin valid<=accept;if(accept)count<=take;end
 end
 wire[95:0]answer;
 generate for(genvar l=0;l<8;l=l+1)begin:zero_tail
  if(E==3||E==4||(E==2&&l>=4))assign out_data[12*l+:12]=answer[12*l+:12];
  else assign out_data[12*l+:12]=count>l?answer[12*l+:12]:12'd0;
 end endgenerate
 generate if(E==0||E==1)begin:residue8
  wire[47:0]ab,c,p;
  for(genvar l=0;l<8;l=l+1)begin:lane
   assign ab[6*l+:6]={1'b0,u_in[11*l+:5]};
   assign c[6*l+:6]={1'b0,i_in[11*l+:5]};
   if(E==0&&l>=5)begin:narrow
    wire signed[3:0]hu={u_in[11*l+7],u_in[11*l+5+:3]};
    wire signed[3:0]hi={i_in[11*l+7],i_in[11*l+5+:3]};
    (* use_dsp="no" *)wire signed[3:0]base=hu+hi;
    reg[3:0]base_reg=0;
    always @(posedge clk)if(rst)base_reg<=0;else if(accept)base_reg<=base;
    (* use_dsp="no" *)wire[3:0]high=base_reg+{3'd0,p[6*l+5]};
    wire[8:0]sum9={high,p[6*l+:5]};
    assign answer[12*l+:12]={{3{sum9[8]}},sum9};
   end else begin:full
    wire signed[5:0]hu=u_in[11*l+5+:6];
    wire signed[5:0]hi={{3{i_in[11*l+7]}},i_in[11*l+5+:3]};
    (* use_dsp="no" *)wire signed[5:0]base=hu+hi;
    reg[5:0]base_reg=0;
    always @(posedge clk)if(rst)base_reg<=0;else if(accept)base_reg<=base;
    (* use_dsp="no" *)wire[5:0]high=base_reg+{5'd0,p[6*l+5]};
    assign answer[12*l+:12]={high[5],high,p[6*l+:5]};
   end
  end
  certified_u11_dsp #(.SIMD("ONE48"))d(clk,rst,accept,ab,c,p);
 end else if(E==2)begin:hybrid
  wire[47:0]ab,c,p;
  for(genvar l=0;l<4;l=l+1)begin:dsp_lane
   assign ab[12*l+:12]={u_in[11*l+10],u_in[11*l+:11]};
   assign c[12*l+:12]={{4{i_in[11*l+7]}},i_in[11*l+:8]};
   assign answer[12*l+:12]=p[12*l+:12];
  end
  for(genvar l=4;l<8;l=l+1)begin:lut_lane
   wire signed[11:0]u12={u_in[11*l+10],u_in[11*l+:11]};
   wire signed[11:0]i12={{4{i_in[11*l+7]}},i_in[11*l+:8]};
   (* use_dsp="no" *)wire signed[11:0]sum=u12+i12;
   reg[10:0]sum_reg=0;
   always @(posedge clk)if(rst)sum_reg<=0;else if(accept)sum_reg<=take>l?sum[10:0]:11'd0;
   assign answer[12*l+:12]={sum_reg[10],sum_reg};
  end
  certified_u11_dsp #(.SIMD("FOUR12"))d(clk,rst,accept,ab,c,p);
 end else begin:lut_all
  for(genvar l=0;l<8;l=l+1)begin:lane
   if(E==4&&l>=5)begin:narrow
    wire signed[8:0]u9={u_in[11*l+7],u_in[11*l+:8]};
    wire signed[8:0]i9={i_in[11*l+7],i_in[11*l+:8]};
    (* use_dsp="no" *)wire signed[8:0]sum=u9+i9;
    reg[8:0]sum_reg=0;
    always @(posedge clk)if(rst)sum_reg<=0;else if(accept)sum_reg<=take>l?sum:9'd0;
    assign answer[12*l+:12]={{3{sum_reg[8]}},sum_reg};
   end else begin:full
    wire signed[11:0]u12={u_in[11*l+10],u_in[11*l+:11]};
    wire signed[11:0]i12={{4{i_in[11*l+7]}},i_in[11*l+:8]};
    (* use_dsp="no" *)wire signed[11:0]sum=u12+i12;
    reg[10:0]sum_reg=0;
    always @(posedge clk)if(rst)sum_reg<=0;else if(accept)sum_reg<=take>l?sum[10:0]:11'd0;
    assign answer[12*l+:12]={sum_reg[10],sum_reg};
   end
  end
 end endgenerate
endmodule

module certified_u11_dsp #(parameter SIMD="ONE48")(
 input wire clk,rst,issue,input wire[47:0]ab,c,output wire[47:0]p);
 DSP48E1 #(.USE_SIMD(SIMD),.USE_MULT("NONE"),.AREG(0),.ACASCREG(0),.BREG(0),.BCASCREG(0),
 .CREG(0),.DREG(0),.ADREG(0),.MREG(0),.PREG(1),.OPMODEREG(0),.ALUMODEREG(0),.CARRYINREG(0),
 .CARRYINSELREG(0),.INMODEREG(0))d(
 .CLK(clk),.A(ab[47:18]),.B(ab[17:0]),.C(c),.D(25'd0),.OPMODE(7'b0110011),.ALUMODE(4'b0000),
 .CARRYIN(1'b0),.CARRYINSEL(3'b000),.INMODE(5'b00000),.CEA1(1'b0),.CEA2(1'b0),
 .CEB1(1'b0),.CEB2(1'b0),.CEC(1'b0),.CED(1'b0),.CEAD(1'b0),.CEM(1'b0),.CEP(issue),
 .CECTRL(1'b0),.CEALUMODE(1'b0),.CECARRYIN(1'b0),.CEINMODE(1'b0),
 .RSTA(rst),.RSTB(rst),.RSTC(rst),.RSTD(1'b0),.RSTM(1'b0),.RSTP(rst),
 .RSTCTRL(1'b0),.RSTALUMODE(1'b0),.RSTALLCARRYIN(1'b0),.RSTINMODE(1'b0),
 .ACIN(30'd0),.BCIN(18'd0),.PCIN(48'd0),.CARRYCASCIN(1'b0),.MULTSIGNIN(1'b0),
 .P(p),.ACOUT(),.BCOUT(),.PCOUT(),.CARRYOUT(),.CARRYCASCOUT(),.MULTSIGNOUT(),
 .OVERFLOW(),.UNDERFLOW(),.PATTERNDETECT(),.PATTERNBDETECT());
endmodule
