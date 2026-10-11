`timescale 1ns/1ps
// Common 24-neuron event interface. All groups consume a vector exactly once.
// MODE 0: current checkpoints; 1: actual membrane promotion;
// 2: native FOUR12; 3: static six-lane (requires proven signed8 current bound);
// 4: parallel LUT-only. Register banks and supplied weights, not an SRAM system.
module exact_tile #(parameter integer MODE=0,B=16,SH=1,LEAK=1,HARD_RESET=0,VTH=35)(
 input wire clk,rst,valid,input wire[1:0]cmd,input wire[95:0]w,
 output wire ready,output wire[23:0]spike,output wire[24*B-1:0]state_debug
);
 generate if(MODE==4)begin:lut
  reg signed[B-1:0]mem[24];reg[23:0]sp;
  assign ready=1'b1;assign spike=sp;
  for(genvar i=0;i<24;i=i+1)begin
   wire signed[3:0]delta=w[i*4+:4];
   always @(posedge clk)begin
    if(rst)begin mem[i]<=0;sp[i]<=0;end
    else if(valid)case(cmd)
     1:mem[i]<=mem[i]+delta;
     2:begin mem[i]<=LEAK?(mem[i]-(mem[i]>>>SH)):mem[i];sp[i]<=0;end
     3:begin sp[i]<=mem[i]>=VTH;if(mem[i]>=VTH)mem[i]<=HARD_RESET?0:mem[i]-VTH;end
    endcase
   end
   assign state_debug[i*B+:B]=mem[i];
  end
 end else begin:dsp
  localparam integer N=(MODE==2)?4:6,G=24/N,SLOT=(MODE==2)?12:8;
  wire[G-1:0]gr;wire[1:0]accepted_cmd=(valid&&ready)?cmd:2'b00;
  assign ready=&gr;
  for(genvar g=0;g<G;g=g+1)begin
   if(MODE==1)begin
    exact_promote #(.N(N),.SLOT(SLOT),.B(B),.SH(SH),.LEAK(LEAK),.HARD_RESET(HARD_RESET),.VTH(VTH)) u(
     .clk(clk),.rst(rst),.cmd(accepted_cmd),.w(w[g*N*4+:N*4]),.ready(gr[g]),
     .spike(spike[g*N+:N]),.state_debug(state_debug[g*N*B+:N*B]));
   end else begin
    exact_checkpoint #(.GUARDED(MODE!=2),.STATIC(MODE==3),.N(N),.SLOT(SLOT),.B(B),.SH(SH),.LEAK(LEAK),.HARD_RESET(HARD_RESET),.VTH(VTH)) u(
     .clk(clk),.rst(rst),.cmd(accepted_cmd),.w(w[g*N*4+:N*4]),.ready(gr[g]),
     .spike(spike[g*N+:N]),.state_debug(state_debug[g*N*B+:N*B]));
   end
  end
 end endgenerate
endmodule

// OOC timing shells below register ports without an elastic/skid buffer.
// Use exact_tile directly for the verified valid/ready protocol; these shells
// require aligned stimulus and must not be wired as host-ready interfaces.
module top_exact_checkpoint(input wire clk,rst,valid_i,input wire[1:0]cmd_i,input wire[95:0]w_i,output reg ready_o,output reg[23:0]sp_o);
 reg valid;reg[1:0]cmd;reg[95:0]w;wire ready;wire[23:0]sp;
 always @(posedge clk)begin valid<=valid_i;cmd<=cmd_i;w<=w_i;ready_o<=ready;sp_o<=sp;end
 exact_tile #(.MODE(0)) u(.clk(clk),.rst(rst),.valid(valid),.cmd(cmd),.w(w),.ready(ready),.spike(sp),.state_debug());
endmodule
module top_exact_promote(input wire clk,rst,valid_i,input wire[1:0]cmd_i,input wire[95:0]w_i,output reg ready_o,output reg[23:0]sp_o);
 reg valid;reg[1:0]cmd;reg[95:0]w;wire ready;wire[23:0]sp;
 always @(posedge clk)begin valid<=valid_i;cmd<=cmd_i;w<=w_i;ready_o<=ready;sp_o<=sp;end
 exact_tile #(.MODE(1)) u(.clk(clk),.rst(rst),.valid(valid),.cmd(cmd),.w(w),.ready(ready),.spike(sp),.state_debug());
endmodule
module top_exact_native(input wire clk,rst,valid_i,input wire[1:0]cmd_i,input wire[95:0]w_i,output reg ready_o,output reg[23:0]sp_o);
 reg valid;reg[1:0]cmd;reg[95:0]w;wire ready;wire[23:0]sp;
 always @(posedge clk)begin valid<=valid_i;cmd<=cmd_i;w<=w_i;ready_o<=ready;sp_o<=sp;end
 exact_tile #(.MODE(2)) u(.clk(clk),.rst(rst),.valid(valid),.cmd(cmd),.w(w),.ready(ready),.spike(sp),.state_debug());
endmodule
module top_exact_static(input wire clk,rst,valid_i,input wire[1:0]cmd_i,input wire[95:0]w_i,output reg ready_o,output reg[23:0]sp_o);
 reg valid;reg[1:0]cmd;reg[95:0]w;wire ready;wire[23:0]sp;
 always @(posedge clk)begin valid<=valid_i;cmd<=cmd_i;w<=w_i;ready_o<=ready;sp_o<=sp;end
 exact_tile #(.MODE(3)) u(.clk(clk),.rst(rst),.valid(valid),.cmd(cmd),.w(w),.ready(ready),.spike(sp),.state_debug());
endmodule
module top_exact_lut(input wire clk,rst,valid_i,input wire[1:0]cmd_i,input wire[95:0]w_i,output reg ready_o,output reg[23:0]sp_o);
 reg valid;reg[1:0]cmd;reg[95:0]w;wire ready;wire[23:0]sp;
 always @(posedge clk)begin valid<=valid_i;cmd<=cmd_i;w<=w_i;ready_o<=ready;sp_o<=sp;end
 exact_tile #(.MODE(4)) u(.clk(clk),.rst(rst),.valid(valid),.cmd(cmd),.w(w),.ready(ready),.spike(sp),.state_debug());
endmodule
