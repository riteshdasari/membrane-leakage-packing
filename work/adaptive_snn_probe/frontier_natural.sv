`timescale 1ns/1ps
// Same U13/I8 integer operation and ordered admission as the frozen trial.
// One advancing edge. DSP input registers are bypassed; P is registered.
// Metadata is registered alongside P; decoding and zero tails are combinational.
module frontier_natural #(parameter integer E=0)(
 input wire clk,rst,in_valid,out_ready,
 input wire[103:0]u_in,i_in,input wire[3:0]available,
 output wire in_ready,output wire[3:0]take,
 output wire out_valid,output wire[3:0]out_count,
 output wire[111:0]out_data,output wire narrow_mode);
 reg valid=0;reg[3:0]count=0;
 wire advance=!valid||out_ready;
 wire tail5_fits8=(u_in[13*5+8+:5]=={5{u_in[13*5+7]}});
 wire tail6_fits8=(u_in[13*6+8+:5]=={5{u_in[13*6+7]}});
 wire tail7_fits8=(u_in[13*7+8+:5]=={5{u_in[13*7+7]}});
 wire[3:0]prefix=(available<=5)?available:
  (!tail5_fits8?4'd5:((available<=6||!tail6_fits8)?4'd6:
   ((available>=8&&tail7_fits8)?4'd8:4'd7)));
 assign take=(E==0)?((available>6)?4'd6:available):((E==5)?prefix:available);
 assign narrow_mode=(E==5)&&(take>5);
 assign in_ready=advance;assign out_valid=valid;assign out_count=count;
 wire accept=in_valid&&advance&&(available!=0);
 always @(posedge clk)begin
  if(rst)begin valid<=0;count<=0;end
  else if(advance)begin valid<=accept;if(accept)count<=take;end
 end
 wire[111:0]answer;
 generate for(genvar l=0;l<8;l=l+1)begin:zero_tail
  if(E==4||(E==3&&l>=2))assign out_data[14*l+:14]=answer[14*l+:14];
  else assign out_data[14*l+:14]=count>l?answer[14*l+:14]:14'd0;
 end endgenerate
 generate if(E==0)begin:residue6
  wire[47:0]ab,c,p;
  for(genvar l=0;l<6;l=l+1)begin:lane
   assign ab[8*l+:8]={1'b0,u_in[13*l+:7]};
   assign c[8*l+:8]={1'b0,i_in[13*l+:7]};
   wire signed[6:0]hu={u_in[13*l+12],u_in[13*l+7+:6]};
   wire signed[6:0]hi={7{i_in[13*l+7]}};
   (* use_dsp="no" *)wire signed[6:0]base=hu+hi;
   reg[6:0]base_reg=0;
   always @(posedge clk)if(rst)base_reg<=0;else if(accept)base_reg<=base;
   (* use_dsp="no" *)wire[6:0]high=base_reg+{6'd0,p[8*l+7]};
   assign answer[14*l+:14]={high,p[8*l+:7]};
  end
  assign answer[111:84]=28'd0;
  frontier_direct_dsp #(.SIMD("ONE48"))d(clk,rst,accept,ab,c,p);
 end else if(E==1||E==2||E==5)begin:residue8
  wire[47:0]ab,c,p;
  for(genvar l=0;l<8;l=l+1)begin:lane
   assign ab[6*l+:6]={1'b0,u_in[13*l+:5]};
   assign c[6*l+:6]={1'b0,i_in[13*l+:5]};
   if(E==1)begin:late_high
    reg[7:0]hu=0;reg[2:0]hi=0;
    always @(posedge clk)begin
     if(rst)begin hu<=0;hi<=0;end
     else if(accept)begin hu<=u_in[13*l+5+:8];hi<=i_in[13*l+5+:3];end
    end
    wire signed[8:0]hu9={hu[7],hu};
    wire signed[8:0]hi9={{6{hi[2]}},hi};
    (* use_dsp="no" *)wire signed[8:0]high=hu9+hi9+{8'd0,p[6*l+5]};
    assign answer[14*l+:14]={high,p[6*l+:5]};
   end else if(E==5&&l>=5)begin:narrow
    wire signed[3:0]hu={u_in[13*l+7],u_in[13*l+5+:3]};
    wire signed[3:0]hi={i_in[13*l+7],i_in[13*l+5+:3]};
    (* use_dsp="no" *)wire signed[3:0]base=hu+hi;
    reg[3:0]base_reg=0;
    always @(posedge clk)if(rst)base_reg<=0;else if(accept)base_reg<=base;
    (* use_dsp="no" *)wire[3:0]high=base_reg+{3'd0,p[6*l+5]};
    wire[8:0]sum9={high,p[6*l+:5]};
    assign answer[14*l+:14]={{5{sum9[8]}},sum9};
   end else begin:full
    wire signed[8:0]hu={u_in[13*l+12],u_in[13*l+5+:8]};
    wire signed[8:0]hi={{6{i_in[13*l+7]}},i_in[13*l+5+:3]};
    (* use_dsp="no" *)wire signed[8:0]base=hu+hi;
    reg[8:0]base_reg=0;
    always @(posedge clk)if(rst)base_reg<=0;else if(accept)base_reg<=base;
    (* use_dsp="no" *)wire[8:0]high=base_reg+{8'd0,p[6*l+5]};
    assign answer[14*l+:14]={high,p[6*l+:5]};
   end
  end
  frontier_direct_dsp #(.SIMD("ONE48"))d(clk,rst,accept,ab,c,p);
 end else if(E==3)begin:hybrid
  wire[47:0]ab,c,p;
  for(genvar l=0;l<2;l=l+1)begin:dsp_lane
   assign ab[24*l+:24]={{11{u_in[13*l+12]}},u_in[13*l+:13]};
   assign c[24*l+:24]={{16{i_in[13*l+7]}},i_in[13*l+:8]};
   assign answer[14*l+:14]=p[24*l+:14];
  end
  for(genvar l=2;l<8;l=l+1)begin:lut_lane
   wire signed[13:0]u14={u_in[13*l+12],u_in[13*l+:13]};
   wire signed[13:0]i14={{6{i_in[13*l+7]}},i_in[13*l+:8]};
   (* use_dsp="no" *)wire signed[13:0]sum=u14+i14;
   reg[13:0]sum_reg=0;
   always @(posedge clk)if(rst)sum_reg<=0;else if(accept)sum_reg<=available>l?sum:14'd0;
   assign answer[14*l+:14]=sum_reg;
  end
  frontier_direct_dsp #(.SIMD("TWO24"))d(clk,rst,accept,ab,c,p);
 end else begin:lut_all
  for(genvar l=0;l<8;l=l+1)begin:lane
   wire signed[13:0]u14={u_in[13*l+12],u_in[13*l+:13]};
   wire signed[13:0]i14={{6{i_in[13*l+7]}},i_in[13*l+:8]};
   (* use_dsp="no" *)wire signed[13:0]sum=u14+i14;
   reg[13:0]sum_reg=0;
   always @(posedge clk)if(rst)sum_reg<=0;else if(accept)sum_reg<=available>l?sum:14'd0;
   assign answer[14*l+:14]=sum_reg;
  end
 end endgenerate
endmodule

module frontier_direct_dsp #(parameter SIMD="ONE48")(
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
