`timescale 1ns/1ps
// FireFly-style baseline: 4 LIF neurons in one DSP48E1 using SIMD FOUR12 (carry-isolated 12-bit lanes).
// Weights sign-extended to 12 bits by wiring. Same ops/semantics as pk_cluster (lanes wrap if > 12 b).
module ff_cluster #(
  parameter int WB = 4, SH = 1, VTH = 35
)(
  input  logic clk, rst,
  input  logic [2:0] op,                 // 0 NOP, 1 ADD, 2 LEAK, 3 FIRE, 4 INIT
  input  logic [4*WB-1:0] w,
  output logic [3:0] spike,
  output logic [4*12-1:0] dbg_s
);
  logic [47:0] P, ab_word, c_word;
  logic [6:0]  opmode;
  logic [3:0]  alumode, sp;
  logic signed [11:0] v [4];
  always_comb begin
    for (int i = 0; i < 4; i++) begin
      v[i]  = P[12*i +: 12];
      sp[i] = (v[i] >= 12'sd0 + VTH);
    end
    ab_word = '0; c_word = '0; opmode = 7'b010_00_00; alumode = 4'b0000;
    case (op)
      3'd1: begin
        for (int i = 0; i < 4; i++) ab_word[12*i +: 12] = {{(12-WB){w[i*WB+WB-1]}}, w[i*WB +: WB]};
        opmode = 7'b010_00_11; alumode = 4'b0000;
      end
      3'd2: begin
        for (int i = 0; i < 4; i++) c_word[12*i +: 12] = v[i] >>> SH;
        opmode = 7'b010_11_00; alumode = 4'b0011;
      end
      3'd3: begin
        for (int i = 0; i < 4; i++) c_word[12*i +: 12] = sp[i] ? 12'(VTH) : 12'd0;
        opmode = 7'b010_11_00; alumode = 4'b0011;
      end
      3'd4: begin opmode = 7'b000_00_00; alumode = 4'b0000; end   // P <= 0
      default: ;
    endcase
  end
  always_ff @(posedge clk) begin
    if (rst) spike <= '0; else if (op == 3'd3) spike <= sp;
  end
  for (genvar i = 0; i < 4; i++) begin : g_dbg
    assign dbg_s[12*i +: 12] = v[i];
  end
  DSP48E1 #(
    .USE_SIMD("FOUR12"), .USE_MULT("NONE"), .USE_DPORT("FALSE"),
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
