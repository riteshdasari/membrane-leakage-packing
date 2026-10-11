`timescale 1ns/1ps
// LUT-only baseline (FireFly-S / hls4ml style): N LIF neurons, each a B-bit fabric accumulator.
module lut_cluster #(
  parameter int N = 4, WB = 4, B = 11, SH = 1, VTH = 35
)(
  input  logic clk, rst,
  input  logic [2:0] op,
  input  logic [N*WB-1:0] w,
  output logic [N-1:0] spike,
  output logic [N*B-1:0] dbg_s
);
  logic signed [B-1:0] v [N];
  always_ff @(posedge clk) begin
    if (rst) begin
      for (int i = 0; i < N; i++) v[i] <= '0;
      spike <= '0;
    end else begin
      for (int i = 0; i < N; i++) begin
        case (op)
          3'd1: v[i] <= v[i] + B'($signed(w[i*WB +: WB]));
          3'd2: v[i] <= v[i] - (v[i] >>> SH);
          3'd3: v[i] <= (v[i] >= B'(VTH)) ? v[i] - B'(VTH) : v[i];
          3'd4: v[i] <= '0;
          default: ;
        endcase
      end
      if (op == 3'd3) for (int i = 0; i < N; i++) spike[i] <= (v[i] >= B'(VTH));
    end
  end
  for (genvar i = 0; i < N; i++) begin : g_dbg
    assign dbg_s[i*B +: B] = v[i];
  end
endmodule
