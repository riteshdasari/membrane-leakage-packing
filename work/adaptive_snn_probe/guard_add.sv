`timescale 1ns/1ps
// Exact signed int11 membrane/current addition -> signed int12. This is an
// ordered arithmetic primitive, not a neuron, memory controller or spike model.
// E0: immutable ONE48 DSP, guarded six signed7 lanes or four signed11 lanes.
// E1: immutable FOUR12 DSP, four full-range lanes plus ordered zero-I copies.
// E2: FOUR12 DSP four lanes + two LUT lanes; E3: six full-range LUT lanes.
// available is in[0,6]. Binary unavailable input slots may be arbitrary;
// only valid operands affect selection, and unused output slots are zero.
// The source holds valid, available, U and I until acceptance. Valid is low in
// reset. Four advancing clocks separate acceptance from output handshake.
module guard_add #(parameter integer E=0)(
 input wire clk,rst,in_valid,out_ready,
 input wire[65:0]u_in,i_in,input wire[2:0]available,
 output wire in_ready,output wire[2:0]take,
 output reg out_valid=0,output reg[2:0]out_count=0,
 output reg[71:0]out_data=0,output wire narrow_mode);
 wire advance=!out_valid||out_ready;
 wire[10:0]u[0:5],i[0:5];wire[5:0]fit7;
 for(genvar l=0;l<6;l=l+1)begin:input_lane
  assign u[l]=u_in[11*l+:11];assign i[l]=i_in[11*l+:11];
  assign fit7[l]=(available<=l)||
                ((u[l][10:7]=={4{u[l][6]}})&&(i[l][10:7]=={4{i[l][6]}}));
 end
 wire copy5=(available>=5)&&(i[4]==0);
 wire copy6=copy5&&(available==6)&&(i[5]==0);
 wire fullcopy=(available==5&&copy5)||(available==6&&copy6);
 // Prefer the wide copy path when it consumes the entire presented window.
 // A partial fifth copy does not displace a useful six-lane narrow request.
 wire narrow=(E==0)&&(available>=5)&&!fullcopy&&(&fit7);
 assign narrow_mode=narrow;
 assign take=(available==0)?3'd0:
             ((E==2||E==3)?available:
              (narrow?available:(copy6?3'd6:(copy5?3'd5:(available>=4?3'd4:available)))));
 assign in_ready=advance;
 wire accept=in_valid&&advance&&(available!=0);
 reg v0=0,v1=0,v2=0,n0=0,n1=0,n2=0;
 reg[2:0]cnt0=0,cnt1=0,cnt2=0;
 reg[65:0]raw_u0=0,raw_i0=0;
 wire[71:0]answer;
 always @(posedge clk)begin
  if(rst)begin
   v0<=0;v1<=0;v2<=0;n0<=0;n1<=0;n2<=0;
   cnt0<=0;cnt1<=0;cnt2<=0;raw_u0<=0;raw_i0<=0;
   out_valid<=0;out_count<=0;out_data<=0;
  end else if(advance)begin
   v0<=accept;v1<=v0;v2<=v1;out_valid<=v2;
   // Every format isolates binary lane values, including ignored poisoned
   // tails. Final count masking hides unused sums without input datapath gates.
   if(accept)begin raw_u0<=u_in;raw_i0<=i_in;cnt0<=take;n0<=narrow;end
   if(v0)begin cnt1<=cnt0;n1<=n0;end
   if(v1)begin cnt2<=cnt1;n2<=n1;end
   if(v2)begin
    out_count<=cnt2;
    for(integer l=0;l<6;l=l+1)out_data[12*l+:12]<=cnt2>l?answer[12*l+:12]:12'd0;
   end
  end
 end
 generate if(E==0)begin:adaptive
  wire[47:0]narrow_u,narrow_i,wide_u,wide_i,p;
  wire[5:0]parity;
  reg[25:0]meta1=0,meta2=0;
  for(genvar l=0;l<6;l=l+1)begin:encode
   assign narrow_u[8*l+:8]={1'b0,raw_u0[11*l+:7]};
   assign narrow_i[8*l+:8]={1'b0,raw_i0[11*l+:7]};
   assign parity[l]=raw_u0[11*l+10]^raw_i0[11*l+10];
   if(l<4)begin:wide
    assign wide_u[12*l+:12]={1'b0,raw_u0[11*l+:11]};
    assign wide_i[12*l+:12]={1'b0,raw_i0[11*l+:11]};
   end
  end
  // The first four sign parities are common. The 22-bit union holds either
  // the two exact U11 copies or the last two narrow sign parities.
  wire[21:0]union0=n0?{20'd0,parity[5:4]}:raw_u0[65:44];
  always @(posedge clk)begin
   if(rst)begin meta1<=0;meta2<=0;end
   else if(advance)begin
    if(v0)meta1<={union0,parity[3:0]};
    if(v1)meta2<=meta1;
   end
  end
  guard_add_dsp #(.SIMD("ONE48"))d(
   .clk(clk),.rst(rst),.advance(advance),.operand_issue(v0),.sum_issue(v1),
   .ab(n0?narrow_u:wide_u),.c(n0?narrow_i:wide_i),.p(p));
  for(genvar l=0;l<6;l=l+1)begin:decode
   // Each unsigned field sum is below its field modulus, so ONE48 has no
   // interlane carry. XOR restores the true sum's signed result MSB.
   wire[7:0]small_sum={p[8*l+7]^meta2[l],p[8*l+:7]};
   wire[11:0]small_answer={{4{small_sum[7]}},small_sum};
   if(l<4)begin:wide
    wire[11:0]wide_answer={p[12*l+11]^meta2[l],p[12*l+:11]};
    assign answer[12*l+:12]=n2?small_answer:wide_answer;
   end else begin:copy
    wire[10:0]copied_u=meta2[4+11*(l-4)+:11];
    assign answer[12*l+:12]=n2?small_answer:{copied_u[10],copied_u};
   end
  end
 end else if(E==1)begin:native_copy
  wire[47:0]ab,c,p;reg[21:0]copy1=0,copy2=0;
  for(genvar l=0;l<4;l=l+1)begin:encode
   assign ab[12*l+:12]={raw_u0[11*l+10],raw_u0[11*l+:11]};
   assign c[12*l+:12]={raw_i0[11*l+10],raw_i0[11*l+:11]};
   assign answer[12*l+:12]=p[12*l+:12];
  end
  always @(posedge clk)begin
   if(rst)begin copy1<=0;copy2<=0;end
   else if(advance)begin if(v0)copy1<=raw_u0[65:44];if(v1)copy2<=copy1;end
  end
  for(genvar l=4;l<6;l=l+1)begin:copy
   wire[10:0]copied_u=copy2[11*(l-4)+:11];
   assign answer[12*l+:12]={copied_u[10],copied_u};
  end
  guard_add_dsp #(.SIMD("FOUR12"))d(
   .clk(clk),.rst(rst),.advance(advance),.operand_issue(v0),.sum_issue(v1),.ab(ab),.c(c),.p(p));
 end else if(E==2)begin:native_hybrid
  wire[47:0]ab,c,p;wire[23:0]extra;reg[23:0]sum1=0,sum2=0;
  for(genvar l=0;l<4;l=l+1)begin:encode
   assign ab[12*l+:12]={raw_u0[11*l+10],raw_u0[11*l+:11]};
   assign c[12*l+:12]={raw_i0[11*l+10],raw_i0[11*l+:11]};
   assign answer[12*l+:12]=p[12*l+:12];
  end
  for(genvar l=4;l<6;l=l+1)begin:lut
   wire signed[11:0]u12={raw_u0[11*l+10],raw_u0[11*l+:11]};
   wire signed[11:0]i12={raw_i0[11*l+10],raw_i0[11*l+:11]};
   (* use_dsp="no" *)wire signed[11:0]sum=u12+i12;
   assign extra[12*(l-4)+:12]=sum;
  end
  always @(posedge clk)begin
   if(rst)begin sum1<=0;sum2<=0;end
   else if(advance)begin if(v0)sum1<=extra;if(v1)sum2<=sum1;end
  end
  assign answer[71:48]=sum2;
  guard_add_dsp #(.SIMD("FOUR12"))d(
   .clk(clk),.rst(rst),.advance(advance),.operand_issue(v0),.sum_issue(v1),.ab(ab),.c(c),.p(p));
 end else begin:lut_all
  wire[71:0]sums;reg[71:0]sum1=0,sum2=0;
  for(genvar l=0;l<6;l=l+1)begin:lane
   wire signed[11:0]u12={raw_u0[11*l+10],raw_u0[11*l+:11]};
   wire signed[11:0]i12={raw_i0[11*l+10],raw_i0[11*l+:11]};
   (* use_dsp="no" *)wire signed[11:0]sum=u12+i12;
   assign sums[12*l+:12]=sum;
  end
  always @(posedge clk)begin
   if(rst)begin sum1<=0;sum2<=0;end
   else if(advance)begin if(v0)sum1<=sums;if(v1)sum2<=sum1;end
  end
  assign answer=sum2;
 end endgenerate
endmodule

// Installed AMD DSP48E1 model: OPMODE[1:0]=11 selects A:B,
// OPMODE[3:2]=00 selects zero, OPMODE[6:4]=011 selects C.
// Thus immutable 0110011 with ALUMODE0000 implements A:B+C.
module guard_add_dsp #(parameter SIMD="ONE48")(
 input wire clk,rst,advance,operand_issue,sum_issue,
 input wire[47:0]ab,c,output wire[47:0]p);
 DSP48E1 #(.USE_SIMD(SIMD),.USE_MULT("NONE"),.AREG(1),.ACASCREG(1),.BREG(1),.BCASCREG(1),
 .CREG(1),.DREG(0),.ADREG(0),.MREG(0),.PREG(1),.OPMODEREG(0),.ALUMODEREG(0),.CARRYINREG(0),
 .CARRYINSELREG(0),.INMODEREG(0))d(
 .CLK(clk),.A(ab[47:18]),.B(ab[17:0]),.C(c),.D(25'd0),.OPMODE(7'b0110011),.ALUMODE(4'b0000),
 .CARRYIN(1'b0),.CARRYINSEL(3'b000),.INMODE(5'b00000),.CEA1(1'b0),.CEA2(advance&&operand_issue),
 .CEB1(1'b0),.CEB2(advance&&operand_issue),.CEC(advance&&operand_issue),.CED(1'b0),.CEAD(1'b0),
 .CEM(1'b0),.CEP(advance&&sum_issue),.CECTRL(1'b0),.CEALUMODE(1'b0),
 .CECARRYIN(1'b0),.CEINMODE(1'b0),.RSTA(rst),.RSTB(rst),.RSTC(rst),.RSTD(1'b0),.RSTM(1'b0),
 .RSTP(rst),.RSTCTRL(1'b0),.RSTALUMODE(1'b0),.RSTALLCARRYIN(1'b0),.RSTINMODE(1'b0),
 .ACIN(30'd0),.BCIN(18'd0),.PCIN(48'd0),.CARRYCASCIN(1'b0),.MULTSIGNIN(1'b0),
 .P(p),.ACOUT(),.BCOUT(),.PCOUT(),.CARRYOUT(),.CARRYCASCOUT(),.MULTSIGNOUT(),
 .OVERFLOW(),.UNDERFLOW(),.PATTERNDETECT(),.PATTERNBDETECT());
endmodule
