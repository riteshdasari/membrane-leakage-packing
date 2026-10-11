`timescale 1ns/1ps
// TIMING FIXTURE ONLY. This is deliberately not a production ready/valid wrapper.
// Raw inputs are launched unconditionally each clock, including reset and ready.
// Every core output is captured unconditionally each clock. The extra registers
// make the core's input arithmetic and combinational policy clock-to-clock paths.
// They must not be counted as core pipeline latency or as a working interface.
// 50 launch FFs + 53 capture FFs = 103 fixture FFs for every engine.
module quad_timing #(parameter E=0)(
 input wire clk,rst,in_valid,out_ready,
 input wire[43:0]u_in,input wire[2:0]available,
 output wire in_ready,out_valid,output wire[2:0]take,out_count,
 output wire[43:0]u_out,output wire quad_mode);
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *) reg src_rst;
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *) reg src_in_valid;
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *) reg src_out_ready;
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *) reg[43:0]src_u;
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *) reg[2:0]src_available;
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *) reg sink_in_ready;
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *) reg sink_out_valid;
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *) reg[2:0]sink_take;
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *) reg[2:0]sink_out_count;
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *) reg[43:0]sink_u;
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *) reg sink_quad_mode;
 wire core_in_ready,core_out_valid,core_quad_mode;
 wire[2:0]core_take,core_out_count;
 wire[43:0]core_u;
 // Hierarchical DONT_TOUCH prevents optimization across this boundary. Internal
 // core logic still maps normally; all engines receive the same boundary rule.
 (* KEEP_HIERARCHY="yes", DONT_TOUCH="yes" *)
 quad_leak #(.E(E)) core(
  .clk(clk),.rst(src_rst),.in_valid(src_in_valid),.out_ready(src_out_ready),
  .u_in(src_u),.available(src_available),
  .in_ready(core_in_ready),.take(core_take),.out_valid(core_out_valid),
  .out_count(core_out_count),.u_out(core_u),.quad_mode(core_quad_mode));
 always @(posedge clk)begin
  src_rst<=rst;src_in_valid<=in_valid;src_out_ready<=out_ready;
  src_u<=u_in;src_available<=available;
  sink_in_ready<=core_in_ready;sink_take<=core_take;
  sink_out_valid<=core_out_valid;sink_out_count<=core_out_count;
  sink_u<=core_u;sink_quad_mode<=core_quad_mode;
 end
 assign in_ready=sink_in_ready;assign take=sink_take;
 assign out_valid=sink_out_valid;assign out_count=sink_out_count;
 assign u_out=sink_u;assign quad_mode=sink_quad_mode;
endmodule
`define QUAD_TOP(NAME,ENGINE) \
module NAME(input wire clk,rst,in_valid,out_ready,input wire[43:0]u_in,input wire[2:0]available, \
 output wire in_ready,out_valid,output wire[2:0]take,out_count,output wire[43:0]u_out,output wire quad_mode); \
 (* KEEP_HIERARCHY="yes", DONT_TOUCH="yes" *) quad_timing #(.E(ENGINE))fixture(.*);endmodule
`QUAD_TOP(top_quad_adaptive6,0)
`QUAD_TOP(top_quad_adaptive7,1)
`QUAD_TOP(top_quad_fixed3,2)
`QUAD_TOP(top_quad_fixed4,3)
`QUAD_TOP(top_quad_lut4,4)
`undef QUAD_TOP
