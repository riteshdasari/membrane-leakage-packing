`timescale 1ns/1ps
// Guarded packed synaptic currents with a shared exact wide neuron update unit.
// Registers model the membrane bank. A real SRAM integration still needs its ports/timing modeled.
// cmd: 1 add event; 2 leak before timestep; 3 finish timestep and fire/reset.
module exact_checkpoint #(parameter integer GUARDED=1,N=6,SLOT=8,B=13,WB=4,SH=1,VTH=35,LEAK=1,HARD_RESET=0,STATIC=0)(
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
 function [47:0] bias_word; integer j; begin bias_word=0; for(j=0;j<N;j=j+1)bias_word=bias_word+(48'(1<<(SLOT-1))<<(j*SLOT));end endfunction
 localparam [47:0] BIASW=bias_word();
 generate if(GUARDED) begin
  packed_exact_acc #(.SLOT(SLOT),.N(N),.WB(WB),.MIDPOINT(0),.LATENCY(1),.SUPPRESS(STATIC)) a(.clk(clk),.rst(rst),.add(adding),.init(init),.w(w),.seed_word(BIASW),.sel(sel),.rd_s(narrow),.warning(warning),.accepted());
 end else begin
  wire signed [11:0] native;
  ff_acc #(.WB(WB)) a(.clk(clk),.rst(rst),.add(adding),.init(init),.w(w),.sel(sel),.rd_s(native));
  assign narrow=native; assign warning=1'b0;
 end endgenerate
 wire signed [B-1:0] old=mem[sel];
 wire signed [B-1:0] sum=old+{{(B-SLOT){narrow[SLOT-1]}},narrow};
 reg signed [B-1:0] sum_pending;
 reg [SW-1:0] store_sel; reg store_ending,valid_store;
 wire fire=sum_pending>=VTH;
 wire [SW-1:0] write_addr=valid_store?store_sel:sel;
 wire signed [B-1:0] write_data=valid_store?(store_ending?(fire?(HARD_RESET?0:sum_pending-VTH):sum_pending):sum_pending):(LEAK?(old-(old>>>SH)):old);
 integer i;
 always @(posedge clk) begin
  if(rst) begin valid_store<=0;sum_pending<=0;store_sel<=0;store_ending<=0;phase<=0;sel<=0;ending<=0;spike<=0; for(i=0;i<N;i=i+1)mem[i]<=0;end
  else begin
   valid_store<=0;
   if(valid_store||(phase==2))mem[write_addr]<=write_data;
   if(valid_store)begin
    if(store_ending)spike[store_sel]<=fire;
   end
   case(phase)
   0: begin phase<=1;sel<=0;end
   1: begin
    if(warning||(cmd==3)) begin phase<=3;sel<=0;ending<=cmd==3;end
    else if(cmd==2) begin phase<=2;sel<=0;spike<=0;end
   end
   2: begin if(sel==N-1)begin phase<=1;sel<=0;end else sel<=sel+1'b1;end
   3: begin
    sum_pending<=sum;store_sel<=sel;store_ending<=ending;valid_store<=1;
    if(sel==N-1)begin phase<=5;sel<=0;end else sel<=sel+1'b1;
   end
   5: phase<=4;
   4: phase<=1;
   default:phase<=0;
  endcase
  end
 end
 for(genvar g=0;g<N;g=g+1)assign state_debug[g*B+:B]=mem[g];
endmodule
