`timescale 1ns/1ps
// Same 43-launch/40-capture FF timing fixture as stream_pipeline_timing.sv.
// This is not a production ready/valid wrapper. Every input/output is sampled
// unconditionally; the strong core chooses the independently screened arithmetic.
module stream_pipeline_strong_timing #(parameter E=3, DC=25, CW=0)(
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
 (* KEEP_HIERARCHY="yes", DONT_TOUCH="yes" *)
 stream_pipeline_strong_leak #(.E(E),.DC(DC),.CW(CW)) core(
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
`define PIPELINE_STRONG_TIMING_TOP(NAME,ENGINE,COEF,CENTERED_WIDE) \
module NAME(input wire clk,rst,in_valid,out_ready,input wire[32:0]u_in,input wire[1:0]available,input wire[4:0]delta, \
 output wire in_ready,out_valid,output wire[1:0]take,out_count,output wire[32:0]u_out,output wire triple_mode); \
 (* KEEP_HIERARCHY="yes", DONT_TOUCH="yes" *) stream_pipeline_strong_timing #(.E(ENGINE),.DC(COEF),.CW(CENTERED_WIDE))fixture(.*);endmodule
`PIPELINE_STRONG_TIMING_TOP(top_stream_pipeline_lut3strong_const,3,25,0)
`PIPELINE_STRONG_TIMING_TOP(top_stream_pipeline_hybridstrong_const,5,25,0)
`PIPELINE_STRONG_TIMING_TOP(top_stream_pipeline_lut3strong_prog,3,-1,0)
`PIPELINE_STRONG_TIMING_TOP(top_stream_pipeline_hybridstrong_prog,5,-1,0)
`PIPELINE_STRONG_TIMING_TOP(top_stream_pipeline_hybridstrong_cw_const,5,25,1)
`PIPELINE_STRONG_TIMING_TOP(top_stream_pipeline_hybridstrong_cw_prog,5,-1,1)
`undef PIPELINE_STRONG_TIMING_TOP
