`timescale 1ns/1ps
// N LIF neurons packed guard-bit-free into ONE DSP48E1 48-bit adder (USE_SIMD = ONE48).
// Invariant: P == sum_i (S_i + BIAS) * 2^(i*L)  (mod 2^48)   -- every value change is physical.
// Lane i field F_i = P[i*L +: L]. A carry crossing into lane i is detected from the 2 LSBs of F_i with a
// 2-bit reference, and counted in k[i-1]. Exact membrane: S_i = F_i - BIAS - k[i-1] + 2^L * k[i].
// k[i] = floor(prefix / 2^((i+1)L)) is a function of the true membranes -> bounded, never drifts.
// Every op adds/subtracts a word whose per-lane fields are one-sided in [0, 2^L) (pure wiring), so a
// lane receives at most one carry of -1/0/+1 per op -> mod-4 detection is exact. No stalls.
// Ops: 0 NOP, 1 ADD, 2 LEAKP, 5 LEAKPH, 6 LEAKN, 7 LEAKNH, 3 FIRE, 4 INIT.
//   ADD    : P += A:B + C, A:B = biased weights (w + 2^(WB-1)) per lane, C = -sum 2^(WB-1) 2^(iL)
//   LEAKP  : latch t = floor(S / 2^SH); P -= sum_{t>0} (t mod 2^L) 2^(iL)
//   LEAKPH : P -= sum_{t>0} (t div 2^L) 2^((i+1)L)      (lane i's high part, booked as a carry into i+1)
//   LEAKN  : P += sum_{t<0} (|t| mod 2^L) 2^(iL)
//   LEAKNH : P += sum_{t<0} (|t| div 2^L) 2^((i+1)L)
//   FIRE   : spike = S >= VTH; P -= sum spike * VTH 2^(iL)   (requires VTH < 2^L)
module pk_cluster #(
  parameter int L = 6, N = 7, KB = 5, WB = 4, SH = 1, VTH = 35
)(
  input  logic clk, rst,
  input  logic [2:0] op,
  input  logic [N*WB-1:0] w,
  output logic [N-1:0] spike,
  output logic [N*(L+KB+2)-1:0] dbg_s
);
  localparam int W    = L + KB + 2;
  localparam int BIAS = 1 << (L - 1);
  localparam int HB   = 1 << (WB - 1);
  localparam logic [47:0] BIASW = gen_word(BIAS);
  localparam logic [47:0] NEGHB = 48'd0 - gen_word(HB);
  initial assert ((N + 1) * L <= 48 && VTH < (1 << L)) else $fatal(1, "bad parameters");

  function automatic logic [47:0] gen_word(input int v);
    logic [47:0] x = '0;
    for (int i = 0; i < N; i++) x = x + (48'(v) << (i * L));
    return x;
  endfunction

  logic [47:0] P;
  logic signed [KB-1:0] k     [N];
  logic        [1:0]    ref_r [N+1];       // 1..N (N = spare region above the top lane)
  logic signed [W-1:0]  tl    [N];         // latched leak amounts

  // ---------------- carry detection on current P
  logic signed [2:0]  c    [N+1];
  logic signed [KB:0] keff [N];
  always_comb begin
    c[0] = '0;
    for (int i = 1; i <= N; i++) begin
      logic [1:0] d;
      d = P[i*L +: 2] - ref_r[i];
      c[i] = (d == 2'd1) ? 3'sd1 : (d == 2'd3) ? -3'sd1 : 3'sd0;
    end
    for (int i = 0; i < N; i++) keff[i] = k[i] + c[i+1];
  end

  // ---------------- exact membranes
  logic signed [W-1:0] s_ex [N];
  logic [N-1:0]        sp;
  logic signed [W-1:0] t    [N];
  always_comb begin
    for (int i = 0; i < N; i++) begin
      logic signed [W-1:0] f, kin, kout;
      f    = W'(P[i*L +: L]);
      kin  = (i == 0) ? '0 : W'(keff[i-1]);
      kout = W'(keff[i]);
      s_ex[i] = f - W'(BIAS) - kin + (kout <<< L);
      sp[i]   = (s_ex[i] >= W'(VTH));
      t[i]    = s_ex[i] >>> SH;
    end
  end

  // ---------------- per-lane one-sided amounts for this op
  logic [L-1:0] lo [N], hi [N];            // field at lane i, and high part placed at lane i+1
  always_comb begin
    for (int i = 0; i < N; i++) begin
      logic signed [W-1:0] m;
      lo[i] = '0; hi[i] = '0;
      case (op)
        3'd2: if (t[i] > 0)  lo[i] = t[i][L-1:0];
        3'd5: if (tl[i] > 0) hi[i] = L'(tl[i] >>> L);
        3'd6: if (tl[i] < 0) begin m = -tl[i]; lo[i] = m[L-1:0]; end
        3'd7: if (tl[i] < 0) begin m = -tl[i]; hi[i] = L'(m >>> L); end
        3'd3: if (sp[i])     lo[i] = L'(VTH);
        default: ;
      endcase
    end
  end

  // ---------------- DSP operands
  logic [47:0] ab_word, c_word;
  logic [6:0]  opmode;
  logic [3:0]  alumode;
  always_comb begin
    ab_word = '0; c_word = '0; opmode = 7'b010_00_00; alumode = 4'b0000;
    for (int i = 0; i < N; i++) begin
      c_word[i*L +: L]     = c_word[i*L +: L] | lo[i];
      c_word[(i+1)*L +: L] = c_word[(i+1)*L +: L] | hi[i];   // lo and hi never both nonzero in one op
    end
    case (op)
      3'd1: begin
        for (int i = 0; i < N; i++) ab_word[i*L +: WB] = {~w[i*WB + WB-1], w[i*WB +: WB-1]};
        c_word = NEGHB; opmode = 7'b010_11_11; alumode = 4'b0000;
      end
      3'd2, 3'd5, 3'd3: begin opmode = 7'b010_11_00; alumode = 4'b0011; end   // P - C
      3'd6, 3'd7:       begin opmode = 7'b010_11_00; alumode = 4'b0000; end   // P + C
      3'd4: begin c_word = BIASW; opmode = 7'b000_11_00; alumode = 4'b0000; end
      default: ;
    endcase
  end

  // ---------------- side state
  always_ff @(posedge clk) begin
    if (rst) begin
      for (int i = 0; i < N; i++) begin k[i] <= '0; tl[i] <= '0; end
      for (int i = 0; i <= N; i++) ref_r[i] <= '0;
      spike <= '0;
    end else if (op == 3'd4) begin
      for (int i = 0; i < N; i++) k[i] <= '0;
      for (int i = 1; i <= N; i++) ref_r[i] <= (i < N) ? 2'(BIAS) : 2'd0;
    end else begin
      for (int j = 1; j <= N; j++) begin
        logic [1:0] dl;                       // intended low-2 change of lane j's field
        logic signed [KB:0] kn;
        dl = '0;
        if (j < N) begin
          case (op)
            3'd1: dl = w[j*WB +: 2];
            3'd2, 3'd3: dl = 2'(-lo[j]);
            3'd6: dl = 2'(lo[j]);
            default: ;
          endcase
        end
        // high part of lane j-1 lands in lane j's field, booked as a carry out of lane j-1
        kn = keff[j-1];
        if (op == 3'd5) begin dl = dl - 2'(hi[j-1]); kn = keff[j-1] - (KB+1)'(hi[j-1]); end
        if (op == 3'd7) begin dl = dl + 2'(hi[j-1]); kn = keff[j-1] + (KB+1)'(hi[j-1]); end
        ref_r[j] <= ref_r[j] + 2'(c[j]) + dl;
        k[j-1]   <= KB'(kn);
      end
      if (op == 3'd2) for (int i = 0; i < N; i++) tl[i] <= t[i];
      if (op == 3'd3) spike <= sp;
    end
  end

  for (genvar i = 0; i < N; i++) begin : g_dbg
    assign dbg_s[i*W +: W] = s_ex[i];
  end

  DSP48E1 #(
    .USE_SIMD("ONE48"), .USE_MULT("NONE"), .USE_DPORT("FALSE"),
    .AREG(0), .ACASCREG(0), .BREG(0), .BCASCREG(0), .CREG(0), .DREG(0), .ADREG(0), .MREG(0),
    .PREG(1), .OPMODEREG(0), .ALUMODEREG(0), .CARRYINREG(0), .CARRYINSELREG(0), .INMODEREG(0),
    .A_INPUT("DIRECT"), .B_INPUT("DIRECT"), .USE_PATTERN_DETECT("NO_PATDET")
  ) dsp (
    .CLK(clk), .A(ab_word[47:18]), .B(ab_word[17:0]), .C(c_word), .D(25'd0),
    .OPMODE(opmode), .ALUMODE(alumode), .CARRYIN(1'b0), .CARRYINSEL(3'b000), .INMODE(5'b00000),
    .CEA1(1'b0), .CEA2(1'b0), .CEB1(1'b0), .CEB2(1'b0), .CEC(1'b0), .CED(1'b0), .CEAD(1'b0), .CEM(1'b0),
    .CEP(1'b1), .CECTRL(1'b0), .CEALUMODE(1'b0), .CECARRYIN(1'b0), .CEINMODE(1'b0),
    .RSTA(1'b0), .RSTB(1'b0), .RSTC(1'b0), .RSTD(1'b0), .RSTM(1'b0), .RSTP(rst), .RSTCTRL(1'b0),
    .RSTALUMODE(1'b0), .RSTALLCARRYIN(1'b0), .RSTINMODE(1'b0),
    .ACIN(30'd0), .BCIN(18'd0), .PCIN(48'd0), .CARRYCASCIN(1'b0), .MULTSIGNIN(1'b0),
    .P(P), .ACOUT(), .BCOUT(), .PCOUT(), .CARRYOUT(), .CARRYCASCOUT(), .MULTSIGNOUT(),
    .OVERFLOW(), .UNDERFLOW(), .PATTERNDETECT(), .PATTERNBDETECT()
  );
endmodule
