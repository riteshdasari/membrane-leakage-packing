`timescale 1ns/1ps
// Shared exact checkpoint-coefficient control. Declared legal beta domain:
// 74..88 and153..170; every frozen GLIF channel/previous-spike value included.
// Full signed16 membrane domain. Two independent lanes, no DSPs.
module glif_mcm_lane(input wire signed[15:0]u,input wire[8:0]b,
 output wire[15:0]answer);
 wire mode=b[7];
 wire[4:0]delta=b[4:0]-(mode?5'd0:5'd16);
 wire[4:0]magnitude=delta[4]?(5'd0-delta):delta;
 wire signed[19:0]u20={{4{u[15]}},u};
 (* use_dsp="no" *)wire signed[19:0]m3=u20+(u20<<<1);
 (* use_dsp="no" *)wire signed[19:0]m5=u20+(u20<<<2);
 (* use_dsp="no" *)wire signed[19:0]m7=(u20<<<3)-u20;
 (* use_dsp="no" *)wire signed[19:0]m9=u20+(u20<<<3);
 reg signed[19:0]residual;
 always @* begin
  case(magnitude)
   0:residual=20'sd0;
   1:residual=u20;
   2:residual=u20<<<1;
   3:residual=m3;
   4:residual=u20<<<2;
   5:residual=m5;
   6:residual=m3<<<1;
   7:residual=m7;
   8:residual=u20<<<3;
   9:residual=m9;
   10:residual=m5<<<1;
   default:residual=20'sd0; // Caller declares the complete legal beta set.
  endcase
 end
 wire signed[24:0]m5wide={{5{m5[19]}},m5};
 wire signed[24:0]base=mode?(m5wide<<<5):(m5wide<<<4);
 wire signed[24:0]reswide={{5{residual[19]}},residual};
 (* use_dsp="no" *)wire signed[24:0]product=delta[4]?base-reswide:base+reswide;
 wire[15:0]floor_bits=product[23:8];
 (* use_dsp="no" *)wire[15:0]ceil_bits=floor_bits+{15'd0,(|product[7:0])};
 assign answer=ceil_bits;
endmodule

module sequential_leak16_glif_mcm(
 input wire clk,rst,in_valid,out_ready,input wire[31:0]u_in,
 input wire[17:0]beta_in,input wire[1:0]available,
 output wire in_ready,out_valid,output wire[1:0]take,out_count,
 output wire[31:0]out_data,output wire narrow_mode);
 assign take=available;
 reg v1=0,v2=0;reg[1:0]count1=0,count2=0;
 reg[31:0]u_q=0;reg[17:0]b_q=0;
 wire advance2=!v2||out_ready;
 assign in_ready=!rst&&(!v1||advance2);
 wire accept=in_valid&&in_ready&&(available!=0);
 wire issue=v1&&advance2&&!rst;
 always @(posedge clk)begin
  if(rst)begin v1<=0;v2<=0;count1<=0;count2<=0;u_q<=0;b_q<=0;end
  else begin
   if(advance2)begin v2<=v1;if(v1)count2<=count1;end
   if(in_ready)begin
    v1<=accept;
    if(accept)begin
     count1<=take;
     u_q<={take==2?u_in[31:16]:16'd0,u_in[15:0]};
     b_q<={take==2?beta_in[17:9]:9'd80,beta_in[8:0]};
    end
   end
  end
 end
 assign out_valid=v2;assign out_count=count2;assign narrow_mode=1'b0;
 wire[31:0]answer;
 for(genvar l=0;l<2;l=l+1)begin:lane
  wire[15:0]arithmetic;
  glif_mcm_lane mcm($signed(u_q[l*16+:16]),b_q[l*9+:9],arithmetic);
  reg[15:0]r=0;
  always @(posedge clk)if(rst)r<=0;else if(issue)r<=count1>l?arithmetic:16'd0;
  assign answer[l*16+:16]=r;
 end
 assign out_data={count2>1?answer[31:16]:16'd0,count2>0?answer[15:0]:16'd0};
endmodule
