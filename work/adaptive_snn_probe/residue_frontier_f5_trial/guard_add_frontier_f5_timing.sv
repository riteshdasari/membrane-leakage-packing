`timescale 1ns/1ps
// MATCHED TIMING FIXTURE ONLY; unconditional raw launch and core capture FFs.
// Every engine retains 183 launch FFs and 107 capture FFs = 290 fixture FFs.
// This is not a production adapter and does not change declared kernel latency.
module guard_add_frontier_f5_timing #(parameter integer E=0)(
 input wire clk,rst,in_valid,out_ready,
 input wire[87:0]u_in,i_in,input wire[3:0]available,
 output wire in_ready,out_valid,output wire[3:0]take,out_count,
 output wire[95:0]out_data,output wire narrow_mode);
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *)reg src_rst;
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *)reg src_in_valid;
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *)reg src_out_ready;
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *)reg[87:0]src_u;
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *)reg[87:0]src_i;
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *)reg[3:0]src_available;
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *)reg sink_in_ready;
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *)reg sink_out_valid;
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *)reg[3:0]sink_take;
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *)reg[3:0]sink_out_count;
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *)reg[95:0]sink_data;
 (* DONT_TOUCH="yes", KEEP="yes", SHREG_EXTRACT="no" *)reg sink_narrow_mode;
 wire core_in_ready,core_out_valid,core_narrow_mode;
 wire[3:0]core_take,core_out_count;
 wire[95:0]core_data;
 (* KEEP_HIERARCHY="yes", DONT_TOUCH="yes" *)
 guard_add_frontier_f5 #(.E(E))core(
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
`define GUARD_ADD_FRONTIER_TOP(NAME,ENGINE) \
module NAME(input wire clk,rst,in_valid,out_ready,input wire[87:0]u_in,i_in,input wire[3:0]available, \
 output wire in_ready,out_valid,output wire[3:0]take,out_count,output wire[95:0]out_data,output wire narrow_mode); \
 (* KEEP_HIERARCHY="yes", DONT_TOUCH="yes" *)guard_add_frontier_f5_timing #(.E(ENGINE))fixture(.*);endmodule
`GUARD_ADD_FRONTIER_TOP(top_guard_add_frontier_f5_e0,0)
`GUARD_ADD_FRONTIER_TOP(top_guard_add_frontier_f5_e1,1)
`GUARD_ADD_FRONTIER_TOP(top_guard_add_frontier_f5_e2,2)
`GUARD_ADD_FRONTIER_TOP(top_guard_add_frontier_f5_e3,3)
`GUARD_ADD_FRONTIER_TOP(top_guard_add_frontier_f5_e4,4)
`GUARD_ADD_FRONTIER_TOP(top_guard_add_frontier_f5_e5,5)
`undef GUARD_ADD_FRONTIER_TOP
