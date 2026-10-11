`timescale 1ns/1ps
module tb;
`ifdef NATIVE
localparam integer N=4,SLOT=12,GUARDED=0;
`else
localparam integer N=6,SLOT=8,GUARDED=1;
`endif
`ifndef SHIFT
`define SHIFT 1
`endif
reg clk=0;always #5 clk=~clk;
reg rst=1;reg[1:0]cmd=0;reg[N*4-1:0]w=0;
wire ready;wire[N-1:0]sp;wire[N*13-1:0]state;
`ifdef REUSE
reuse_neuron #(.N(N),.SLOT(SLOT),.SH(`SHIFT)) dut(.clk(clk),.rst(rst),.cmd(cmd),.w(w),.ready(ready),.spike(sp),.state_debug(state));
`else
`ifdef PIPE
shared_neuron_pipe #(.GUARDED(GUARDED),.N(N),.SLOT(SLOT),.SH(`SHIFT)) dut(.clk(clk),.rst(rst),.cmd(cmd),.w(w),.ready(ready),.spike(sp),.state_debug(state));
`else
shared_neuron #(.GUARDED(GUARDED),.N(N),.SLOT(SLOT),.SH(`SHIFT)) dut(.clk(clk),.rst(rst),.cmd(cmd),.w(w),.ready(ready),.spike(sp),.state_debug(state));
`endif
`endif
integer fd,fo,rv,t,e,j,k,tmp;
integer cycles=0,accepted_events=0,busy_cycles=0,fstats;
always @(posedge clk)if(!rst)begin
 cycles=cycles+1;if(ready&&cmd==1)accepted_events=accepted_events+1;if(!ready)busy_cycles=busy_cycles+1;
end
`ifdef TRACE
always @(posedge clk) if(t<1) $display("TRACE phase=%d sel=%d cmd=%d ready=%d narrow=%d mem0=%d sum=%d w0=%d",dut.phase,dut.sel,cmd,ready,dut.narrow,dut.mem[0],dut.sum,$signed(w[3:0]));
`endif
task issue(input integer c);
begin
 cmd=0;
 while(!ready)@(negedge clk);
 cmd=c;
 @(negedge clk);cmd=0;
end
endtask
initial begin
 fd=$fopen("stim.txt","r");fo=$fopen("out.txt","w");
 // UNISIM glbl holds GSR for 100 ns; release the design reset after that interval.
 repeat(20)@(negedge clk);rst=0;
 for(t=0;t<120;t=t+1)begin
  issue(2);
  rv=$fscanf(fd,"%d",e);
  for(j=0;j<e;j=j+1)begin
   for(k=0;k<6;k=k+1)begin rv=$fscanf(fd,"%d",tmp);if(k<N)w[k*4+:4]=4'(tmp);end
   issue(1);
  end
  issue(3);
  while(!ready)@(negedge clk);
  $fwrite(fo,"%d",t);
  for(k=0;k<N;k=k+1)$fwrite(fo," %d",$signed(state[k*13+:13]));
  for(k=0;k<N;k=k+1)$fwrite(fo," %d",sp[k]);
  $fwrite(fo,"\n");
 end
 fstats=$fopen("cycles.txt","w");$fwrite(fstats,"%d %d %d\n",cycles,accepted_events,busy_cycles);$fclose(fstats);
 $fclose(fd);$fclose(fo);$finish;
end
initial begin #10000000;$fatal(1,"timeout");end
endmodule
