`timescale 1ns/1ps
// MATCHED TIMING FIXTURE ONLY; not a production ready/valid adapter.
// Identical raw-port launch/capture registers to the original guard-add trial.
// 138 launch FFs + 81 capture FFs = 219 preserved fixture FFs per baseline.
// Raw inputs and all core outputs register unconditionally. These registers
// expose arithmetic/classifier paths and do not add declared kernel latency.
module guard_add_i8_fixed_timing #(parameter E=2)(
 input wire clk,rst,in_valid,out_ready,
 input wire[65:0]u_in,i_in,input wire[2:0]available,
 output wire in_ready,out_valid,output wire[2:0]take,out_count,
 output wire[71:0]out_data,output wire narrow_mode);
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *) reg src_rst;
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *) reg src_in_valid;
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *) reg src_out_ready;
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *) reg[65:0]src_u;
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *) reg[65:0]src_i;
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *) reg[2:0]src_available;
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *) reg sink_in_ready;
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *) reg sink_out_valid;
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *) reg[2:0]sink_take;
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *) reg[2:0]sink_out_count;
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *) reg[71:0]sink_data;
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *) reg sink_narrow_mode;
 wire core_in_ready,core_out_valid,core_narrow_mode;
 wire[2:0]core_take,core_out_count;
 wire[71:0]core_data;
 // Keep the same preserved core/fixture boundary as the measured reference.
 // Mapping within the core remains enabled; crossing this boundary is restricted.
 (* KEEP_HIERARCHY="yes", DONT_TOUCH="yes" *)
 guard_add_i8_fixed #(.E(E)) core(
  .clk(clk),.rst(src_rst),.in_valid(src_in_valid),.out_ready(src_out_ready),
  .u_in(src_u),.i_in(src_i),.available(src_available),
  .in_ready(core_in_ready),.take(core_take),.out_valid(core_out_valid),
  .out_count(core_out_count),.out_data(core_data),.narrow_mode(core_narrow_mode));
 always @(posedge clk)begin
  src_rst<=rst;src_in_valid<=in_valid;src_out_ready<=out_ready;
  src_u<=u_in;src_i<=i_in;src_available<=available;
  sink_in_ready<=core_in_ready;sink_take<=core_take;
  sink_out_valid<=core_out_valid;sink_out_count<=core_out_count;
  sink_data<=core_data;sink_narrow_mode<=core_narrow_mode;
 end
 assign in_ready=sink_in_ready;assign take=sink_take;
 assign out_valid=sink_out_valid;assign out_count=sink_out_count;
 assign out_data=sink_data;assign narrow_mode=sink_narrow_mode;
endmodule
`define GUARD_ADD_I8_FIXED_TOP(NAME,ENGINE) \
module NAME(input wire clk,rst,in_valid,out_ready,input wire[65:0]u_in,i_in,input wire[2:0]available, \
 output wire in_ready,out_valid,output wire[2:0]take,out_count,output wire[71:0]out_data,output wire narrow_mode); \
 (* KEEP_HIERARCHY="yes", DONT_TOUCH="yes" *) guard_add_i8_fixed_timing #(.E(ENGINE))fixture(.*);endmodule
`GUARD_ADD_I8_FIXED_TOP(top_guard_add_i8_fixed_hybrid,2)
`GUARD_ADD_I8_FIXED_TOP(top_guard_add_i8_fixed_lut,3)
`undef GUARD_ADD_I8_FIXED_TOP
