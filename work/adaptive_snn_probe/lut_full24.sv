`timescale 1ns/1ps
// Strong baseline: direct 13-bit membrane arithmetic, without separate current storage.
module top_lut_full24(input wire clk,rst,input wire [2:0] op_i,input wire [95:0] w_i,
 output reg [23:0]sp_o);
 reg[2:0]op;reg[95:0]w;wire[23:0]sp;
 always @(posedge clk)begin op<=op_i;w<=w_i;sp_o<=sp;end
 lut_cluster #(.N(24),.WB(4),.B(13),.SH(1),.VTH(35)) u(.clk(clk),.rst(rst),.op(op),.w(w),.spike(sp),.dbg_s());
endmodule
