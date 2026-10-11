`timescale 1ns/1ps
// Accumulate-only "event engines" (customization 1): per cycle each lane may add one signed weight.
// Leak/fire are NOT per lane here: a shared unit reads one lane per cycle through `sel` (rd_s).
// Same interface for all three designs so the per-lane cost of ACCUMULATION alone is comparable.

// ---- ours: guard-bit-free packed lanes, exact via carry counters, zero stalls
module pk_acc #(parameter int L = 6, N = 7, KB = 5, WB = 4)(
  input  logic clk, rst, add, init,
  input  logic [N*WB-1:0] w,
  input  logic [$clog2(N)-1:0] sel,
  output logic signed [L+KB+1:0] rd_s
);
  localparam int W = L + KB + 2, BIAS = 1 << (L - 1), HB = 1 << (WB - 1);
  function automatic logic [47:0] gen_word(input int v);
    logic [47:0] x = '0; for (int i = 0; i < N; i++) x = x + (48'(v) << (i * L)); return x;
  endfunction
  localparam logic [47:0] BIASW = gen_word(BIAS), NEGHB = 48'd0 - gen_word(HB);
  logic [47:0] P, ab;
  logic signed [KB-1:0] k [N];
  logic [1:0] ref_r [N+1];
  logic signed [2:0] c [N+1];
  always_comb begin
    c[0] = '0;
    for (int i = 1; i <= N; i++) begin
      logic [1:0] d; d = P[i*L +: 2] - ref_r[i];
      c[i] = (d == 2'd1) ? 3'sd1 : (d == 2'd3) ? -3'sd1 : 3'sd0;
    end
    ab = '0;
    for (int i = 0; i < N; i++) ab[i*L +: WB] = {~w[i*WB + WB-1], w[i*WB +: WB-1]};
  end
  always_ff @(posedge clk) begin
    if (rst || init) begin
      for (int i = 0; i < N; i++) k[i] <= '0;
      for (int i = 1; i <= N; i++) ref_r[i] <= (init && i < N) ? 2'(BIAS) : 2'd0;
    end else begin
      for (int j = 1; j <= N; j++) begin
        ref_r[j] <= ref_r[j] + 2'(c[j]) + ((add && j < N) ? w[j*WB +: 2] : 2'd0);
        k[j-1] <= k[j-1] + KB'(c[j]);
      end
    end
  end
  // shared readout: one lane per cycle
  always_comb begin
    logic signed [W-1:0] f, kin, kout;
    f = W'(P[sel*L +: L]);
    kin  = (sel == 0) ? '0 : W'(k[sel-1]);
    kout = W'(k[sel]);
    rd_s = f - W'(BIAS) - kin + (kout <<< L);
  end
  DSP48E1 #(.USE_SIMD("ONE48"), .USE_MULT("NONE"), .AREG(0), .ACASCREG(0), .BREG(0), .BCASCREG(0),
    .CREG(0), .DREG(0), .ADREG(0), .MREG(0), .PREG(1), .OPMODEREG(0), .ALUMODEREG(0), .CARRYINREG(0),
    .CARRYINSELREG(0), .INMODEREG(0)) dsp (
    .CLK(clk), .A(ab[47:18]), .B(ab[17:0]), .C(init ? BIASW : NEGHB), .D(25'd0),
    .OPMODE(init ? 7'b000_11_00 : add ? 7'b010_11_11 : 7'b010_00_00), .ALUMODE(4'b0000),
    .CARRYIN(1'b0), .CARRYINSEL(3'b000), .INMODE(5'b0), .CEA1(1'b0), .CEA2(1'b0), .CEB1(1'b0), .CEB2(1'b0),
    .CEC(1'b0), .CED(1'b0), .CEAD(1'b0), .CEM(1'b0), .CEP(1'b1), .CECTRL(1'b0), .CEALUMODE(1'b0),
    .CECARRYIN(1'b0), .CEINMODE(1'b0), .RSTA(1'b0), .RSTB(1'b0), .RSTC(1'b0), .RSTD(1'b0), .RSTM(1'b0),
    .RSTP(rst), .RSTCTRL(1'b0), .RSTALUMODE(1'b0), .RSTALLCARRYIN(1'b0), .RSTINMODE(1'b0),
    .ACIN(30'd0), .BCIN(18'd0), .PCIN(48'd0), .CARRYCASCIN(1'b0), .MULTSIGNIN(1'b0),
    .P(P), .ACOUT(), .BCOUT(), .PCOUT(), .CARRYOUT(), .CARRYCASCOUT(), .MULTSIGNOUT(),
    .OVERFLOW(), .UNDERFLOW(), .PATTERNDETECT(), .PATTERNBDETECT());
endmodule

// ---- FireFly-style: SIMD FOUR12, 4 lanes, weights sign-extended by wiring
module ff_acc #(parameter int WB = 4)(
  input  logic clk, rst, add, init,
  input  logic [4*WB-1:0] w,
  input  logic [1:0] sel,
  output logic signed [11:0] rd_s
);
  logic [47:0] P, ab;
  always_comb begin
    ab = '0;
    for (int i = 0; i < 4; i++) ab[12*i +: 12] = {{(12-WB){w[i*WB+WB-1]}}, w[i*WB +: WB]};
    rd_s = P[sel*12 +: 12];
  end
  DSP48E1 #(.USE_SIMD("FOUR12"), .USE_MULT("NONE"), .AREG(0), .ACASCREG(0), .BREG(0), .BCASCREG(0),
    .CREG(0), .DREG(0), .ADREG(0), .MREG(0), .PREG(1), .OPMODEREG(0), .ALUMODEREG(0), .CARRYINREG(0),
    .CARRYINSELREG(0), .INMODEREG(0)) dsp (
    .CLK(clk), .A(ab[47:18]), .B(ab[17:0]), .C(48'd0), .D(25'd0),
    .OPMODE(init ? 7'b000_00_00 : add ? 7'b010_00_11 : 7'b010_00_00), .ALUMODE(4'b0000),
    .CARRYIN(1'b0), .CARRYINSEL(3'b000), .INMODE(5'b0), .CEA1(1'b0), .CEA2(1'b0), .CEB1(1'b0), .CEB2(1'b0),
    .CEC(1'b0), .CED(1'b0), .CEAD(1'b0), .CEM(1'b0), .CEP(1'b1), .CECTRL(1'b0), .CEALUMODE(1'b0),
    .CECARRYIN(1'b0), .CEINMODE(1'b0), .RSTA(1'b0), .RSTB(1'b0), .RSTC(1'b0), .RSTD(1'b0), .RSTM(1'b0),
    .RSTP(rst), .RSTCTRL(1'b0), .RSTALUMODE(1'b0), .RSTALLCARRYIN(1'b0), .RSTINMODE(1'b0),
    .ACIN(30'd0), .BCIN(18'd0), .PCIN(48'd0), .CARRYCASCIN(1'b0), .MULTSIGNIN(1'b0),
    .P(P), .ACOUT(), .BCOUT(), .PCOUT(), .CARRYOUT(), .CARRYCASCOUT(), .MULTSIGNOUT(),
    .OVERFLOW(), .UNDERFLOW(), .PATTERNDETECT(), .PATTERNBDETECT());
endmodule

// ---- LUT-only accumulators
module lut_acc #(parameter int N = 4, WB = 4, B = 11)(
  input  logic clk, rst, add, init,
  input  logic [N*WB-1:0] w,
  input  logic [$clog2(N)-1:0] sel,
  output logic signed [B-1:0] rd_s
);
  logic signed [B-1:0] v [N];
  always_ff @(posedge clk)
    for (int i = 0; i < N; i++)
      if (rst || init) v[i] <= '0; else if (add) v[i] <= v[i] + B'($signed(w[i*WB +: WB]));
  assign rd_s = v[sel];
endmodule

// ---- 84-lane wrappers (lcm of 7, 4, 12) with registered I/O
module top_pk_acc (input logic clk, rst, add_i, init_i, input logic [84*4-1:0] w_i, input logic [3:0] sel_i,
                   output logic [12*13-1:0] rd_o);
  logic add, init; logic [84*4-1:0] w; logic [2:0] sel; logic [12*13-1:0] rd;
  always_ff @(posedge clk) begin add <= add_i; init <= init_i; w <= w_i; sel <= sel_i[2:0]; rd_o <= rd; end
  for (genvar g = 0; g < 12; g++) begin : g_c
    pk_acc #(.L(6), .N(7), .KB(5), .WB(4)) u (.clk, .rst, .add, .init, .w(w[g*28 +: 28]), .sel, .rd_s(rd[g*13 +: 13]));
  end
endmodule
module top_ff_acc (input logic clk, rst, add_i, init_i, input logic [84*4-1:0] w_i, input logic [3:0] sel_i,
                   output logic [21*12-1:0] rd_o);
  logic add, init; logic [84*4-1:0] w; logic [1:0] sel; logic [21*12-1:0] rd;
  always_ff @(posedge clk) begin add <= add_i; init <= init_i; w <= w_i; sel <= sel_i[1:0]; rd_o <= rd; end
  for (genvar g = 0; g < 21; g++) begin : g_c
    ff_acc #(.WB(4)) u (.clk, .rst, .add, .init, .w(w[g*16 +: 16]), .sel, .rd_s(rd[g*12 +: 12]));
  end
endmodule
module top_lut_acc (input logic clk, rst, add_i, init_i, input logic [84*4-1:0] w_i, input logic [3:0] sel_i,
                    output logic [21*11-1:0] rd_o);
  logic add, init; logic [84*4-1:0] w; logic [1:0] sel; logic [21*11-1:0] rd;
  always_ff @(posedge clk) begin add <= add_i; init <= init_i; w <= w_i; sel <= sel_i[1:0]; rd_o <= rd; end
  for (genvar g = 0; g < 21; g++) begin : g_c
    lut_acc #(.N(4), .WB(4), .B(11)) u (.clk, .rst, .add, .init, .w(w[g*16 +: 16]), .sel, .rd_s(rd[g*11 +: 11]));
  end
endmodule
