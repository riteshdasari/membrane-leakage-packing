`timescale 1ns/1ps
// Portable simulation ONLY. The FPGA implementation uses rtl/leak_dsp.sv.
module sequential_leak_dsp(input wire clk,rst,ce,input wire[24:0]a,input wire[17:0]b,
 input wire[47:0]c,output reg[47:0]p=0);
 wire signed[24:0]sa=a;wire signed[17:0]sb=b;wire signed[47:0]sc=c;
 always @(posedge clk)if(rst)p<=0;else if(ce)p<=sa*sb+sc;
endmodule
