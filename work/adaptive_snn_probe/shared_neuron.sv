`timescale 1ns/1ps
// Guarded packed synaptic currents with a shared exact wide neuron update unit.
// Registers model the membrane bank. A real SRAM integration still needs its ports/timing modeled.
// cmd: 1 add event; 2 leak before timestep; 3 finish timestep and fire/reset.
module shared_neuron #(parameter integer GUARDED=1,N=6,SLOT=8,B=13,WB=4,SH=1,VTH=35)(
 input wire clk,rst,input wire [1:0] cmd,input wire [N*WB-1:0] w,
 output wire ready,output reg [N-1:0] spike,
 output wire [N*B-1:0] state_debug
);
 localparam integer SW=$clog2(N);
 reg [2:0] phase; reg [SW-1:0] sel; reg ending;
 reg signed [B-1:0] mem[N];
 wire signed [SLOT-1:0] narrow;
 wire warning; wire init=(phase==0)||(phase==4);
 assign ready=(phase==1)&&!warning;
 wire adding=ready&&(cmd==1);
 generate if(GUARDED) begin
  guard_acc #(.SLOT(SLOT),.N(N),.WB(WB),.MIDPOINT(0)) a(.clk(clk),.rst(rst),.add(adding),.init(init),.w(w),.sel(sel),.rd_s(narrow),.warning(warning),.accepted());
 end else begin
  wire signed [11:0] native;
  ff_acc #(.WB(WB)) a(.clk(clk),.rst(rst),.add(adding),.init(init),.w(w),.sel(sel),.rd_s(native));
  assign narrow=native; assign warning=1'b0;
 end endgenerate
 wire signed [B-1:0] old=mem[sel];
 wire signed [B-1:0] sum=old+{{(B-SLOT){narrow[SLOT-1]}},narrow};
 wire fire=sum>=VTH;
 integer i;
 always @(posedge clk) begin
  if(rst) begin phase<=0;sel<=0;ending<=0;spike<=0; for(i=0;i<N;i=i+1)mem[i]<=0;end
  else case(phase)
   0: begin phase<=1;sel<=0;end
   1: begin
    if(warning||(cmd==3)) begin phase<=3;sel<=0;ending<=cmd==3;end
    else if(cmd==2) begin phase<=2;sel<=0;spike<=0;end
   end
   2: begin mem[sel]<=old-(old>>>SH); if(sel==N-1)begin phase<=1;sel<=0;end else sel<=sel+1'b1;end
   3: begin
    mem[sel]<=ending?(fire?sum-VTH:sum):sum;
    if(ending)spike[sel]<=fire;
    if(sel==N-1)begin phase<=4;sel<=0;end else sel<=sel+1'b1;
   end
   4: phase<=1;
   default:phase<=0;
  endcase
 end
 for(genvar g=0;g<N;g=g+1)assign state_debug[g*B+:B]=mem[g];
endmodule

module top_guard_shared(input wire clk,rst,input wire [1:0] cmd_i,input wire [24*4-1:0] w_i,
 output reg [23:0] sp_o,output reg [3:0] ready_o);
 reg [1:0] cmd;reg[95:0]w;wire[23:0]sp;wire[3:0]ready;
 always @(posedge clk)begin cmd<=cmd_i;w<=w_i;sp_o<=sp;ready_o<=ready;end
 for(genvar g=0;g<4;g=g+1)begin
 shared_neuron u(.clk(clk),.rst(rst),.cmd(cmd),.w(w[g*24+:24]),.ready(ready[g]),.spike(sp[g*6+:6]),.state_debug());end
endmodule
module top_native_shared(input wire clk,rst,input wire [1:0] cmd_i,input wire [24*4-1:0] w_i,
 output reg [23:0] sp_o,output reg [5:0] ready_o);
 reg [1:0]cmd;reg[95:0]w;wire[23:0]sp;wire[5:0]ready;
 always @(posedge clk)begin cmd<=cmd_i;w<=w_i;sp_o<=sp;ready_o<=ready;end
 for(genvar g=0;g<6;g=g+1)begin
 shared_neuron #(.GUARDED(0),.N(4),.SLOT(12)) u(.clk(clk),.rst(rst),.cmd(cmd),.w(w[g*16+:16]),.ready(ready[g]),.spike(sp[g*4+:4]),.state_debug());end
endmodule
