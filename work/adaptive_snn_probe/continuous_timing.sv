`timescale 1ns/1ps
// TIMING FIXTURE ONLY. This is deliberately not a production ready/valid wrapper.
// Raw inputs are launched unconditionally each clock, including reset and ready.
// Every core output is captured unconditionally each clock. The extra registers
// make the core's input arithmetic and combinational policy clock-to-clock paths.
// They must not be counted as core pipeline latency or as a working interface.
// 43 launch FFs + 40 capture FFs = 83 nominal fixture FFs for every engine/DC.
module continuous_timing #(parameter E=7, DC=25, CW=0)(
 input wire clk,rst,in_valid,out_ready,
 input wire[32:0]u_in,input wire[1:0]available,input wire[4:0]delta,
 output wire in_ready,out_valid,output wire[1:0]take,out_count,
 output wire[32:0]u_out,output wire triple_mode);
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *) reg src_rst;
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *) reg src_in_valid;
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *) reg src_out_ready;
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *) reg[32:0]src_u;
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *) reg[1:0]src_available;
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *) reg[4:0]src_delta;
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *) reg sink_in_ready;
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *) reg sink_out_valid;
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *) reg[1:0]sink_take;
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *) reg[1:0]sink_out_count;
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *) reg[32:0]sink_u;
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *) reg sink_triple_mode;
 wire core_in_ready,core_out_valid,core_triple_mode;
 wire[1:0]core_take,core_out_count;
 wire[32:0]core_u;
 // Hierarchical DONT_TOUCH prevents optimization across this boundary. Internal
 // core logic still maps normally; all engines receive the same boundary rule.
 (* KEEP_HIERARCHY="yes", DONT_TOUCH="yes" *)
 continuous_leak #(.E(E),.DC(DC),.CW(CW)) core(
  .clk(clk),.rst(src_rst),.in_valid(src_in_valid),.out_ready(src_out_ready),
  .u_in(src_u),.available(src_available),.delta(src_delta),
  .in_ready(core_in_ready),.take(core_take),.out_valid(core_out_valid),
  .out_count(core_out_count),.u_out(core_u),.triple_mode(core_triple_mode));
 always @(posedge clk)begin
  src_rst<=rst;src_in_valid<=in_valid;src_out_ready<=out_ready;
  src_u<=u_in;src_available<=available;src_delta<=delta;
  sink_in_ready<=core_in_ready;sink_take<=core_take;
  sink_out_valid<=core_out_valid;sink_out_count<=core_out_count;
  sink_u<=core_u;sink_triple_mode<=core_triple_mode;
 end
 assign in_ready=sink_in_ready;assign take=sink_take;
 assign out_valid=sink_out_valid;assign out_count=sink_out_count;
 assign u_out=sink_u;assign triple_mode=sink_triple_mode;
endmodule
`define CONTINUOUS_TIMING_TOP(NAME,ENGINE,COEF,CENTERED_WIDE) \
module NAME(input wire clk,rst,in_valid,out_ready,input wire[32:0]u_in,input wire[1:0]available,input wire[4:0]delta, \
 output wire in_ready,out_valid,output wire[1:0]take,out_count,output wire[32:0]u_out,output wire triple_mode); \
 (* KEEP_HIERARCHY="yes", DONT_TOUCH="yes" *) continuous_timing #(.E(ENGINE),.DC(COEF),.CW(CENTERED_WIDE))fixture(.*);endmodule
`CONTINUOUS_TIMING_TOP(top_continuous_hybrid_const,5,25,0)
`CONTINUOUS_TIMING_TOP(top_continuous_hybrid_prog,5,-1,0)
`CONTINUOUS_TIMING_TOP(top_continuous_adaptive_const,7,25,0)
`CONTINUOUS_TIMING_TOP(top_continuous_adaptive_prog,7,-1,0)
`undef CONTINUOUS_TIMING_TOP
