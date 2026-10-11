`timescale 1ns/1ps
// 28-neuron wrappers with registered inputs/outputs (same interface for all three designs).
module top_pk (input logic clk, rst, input logic [2:0] op_i, input logic [28*4-1:0] w_i, output logic [27:0] spike_o);
  logic [2:0] op; logic [28*4-1:0] w; logic [27:0] sp;
  always_ff @(posedge clk) begin op <= op_i; w <= w_i; spike_o <= sp; end
  for (genvar g = 0; g < 4; g++) begin : g_c
    pk_cluster #(.L(6), .N(7), .KB(5), .WB(4), .SH(1), .VTH(35)) u (.clk, .rst, .op, .w(w[g*28 +: 28]), .spike(sp[g*7 +: 7]), .dbg_s());
  end
endmodule

module top_ff (input logic clk, rst, input logic [2:0] op_i, input logic [28*4-1:0] w_i, output logic [27:0] spike_o);
  logic [2:0] op; logic [28*4-1:0] w; logic [27:0] sp;
  always_ff @(posedge clk) begin op <= op_i; w <= w_i; spike_o <= sp; end
  for (genvar g = 0; g < 7; g++) begin : g_c
    ff_cluster #(.WB(4), .SH(1), .VTH(35)) u (.clk, .rst, .op, .w(w[g*16 +: 16]), .spike(sp[g*4 +: 4]), .dbg_s());
  end
endmodule

module top_lut (input logic clk, rst, input logic [2:0] op_i, input logic [28*4-1:0] w_i, output logic [27:0] spike_o);
  logic [2:0] op; logic [28*4-1:0] w; logic [27:0] sp;
  always_ff @(posedge clk) begin op <= op_i; w <= w_i; spike_o <= sp; end
  lut_cluster #(.N(28), .WB(4), .B(11), .SH(1), .VTH(35)) u (.clk, .rst, .op, .w, .spike(sp), .dbg_s());
endmodule
