`timescale 1ns/1ps
module neuron_driver #(parameter E=0,B=8,N=6)(input wire clk,output reg done=0);
 reg rst=1,valid=0;reg[1:0]cmd=0;reg[47:0]wa=0,wb=0;
 wire ready,ov;wire[N-1:0]sp;wire[N*16-1:0]state;
 generate if(E<2)begin
 packed_neuron_alu #(.ENGINE(E),.B(B),.N(N),.SH(`SH),.LEAK(`LEAK),.HARD(`HARD),.TH(17))u(
 .clk(clk),.rst(rst),.valid(valid),.cmd(cmd),.wa(wa),.wb(wb),.ready(ready),.out_valid(ov),.spike(sp),.state_debug(state));
 end else begin
 wire[95:0]sx;wire[5:0]spx;
 persistent_unit #(.ENGINE(2),.STATE_BITS(B),.SH(`SH),.LEAK(`LEAK),.HARD(`HARD),.TH(17))u(
 .clk(clk),.rst(rst),.valid(valid),.cmd(cmd),.wa(wa),.wb(wb),.ready(ready),.wide(),.half(),.out_valid(ov),.spike(spx),.state_debug(sx));
 assign state=sx[N*16-1:0];assign sp=spx[N-1:0];
 end endgenerate
 integer f,s,k,j,i,n,steps,rc,cycles=0,wi;
 reg[23:0]a[0:63],b[0:63];reg[47:0]pa,pb;
 task send(input[1:0]co,input[47:0]aa,bb);
  begin @(negedge clk);valid=1;cmd=co;wa=aa;wb=bb;@(posedge clk);while(!ready)@(posedge clk);end
 endtask
 always @(posedge clk)begin
  if(!rst&&!done)cycles=cycles+1;
  #0.1;if(ov)$fdisplay(f,"%h %h",state,sp);
 end
 initial begin
  f=$fopen($sformatf("out%0d.txt",E),"w");rc=$fopen("stim.txt","r");i=$fscanf(rc,"%d",steps);
  repeat(50)@(negedge clk);rst=0;repeat(2)@(negedge clk);
  for(k=0;k<steps;k=k+1)begin
   if(k>0&&k%32==0)begin @(negedge clk);rst=1;valid=0;repeat(2)@(negedge clk);rst=0;repeat(2)@(negedge clk);end
   i=$fscanf(rc,"%d",n);if(i!=1)$fatal(1,"bad step");
   for(j=0;j<n;j=j+1)begin i=$fscanf(rc,"%h %h",a[j],b[j]);if(i!=2)$fatal(1,"bad pair");end
   send(1,0,0);
   for(j=0;j<n;j=j+1)begin
    pa=0;pb=0;
    if(E==1)begin pa=a[j];pb=b[j];end
    else for(integer lane=0;lane<N;lane=lane+1)begin
     wi=$signed(a[j][lane*4+:4]);pa=pa+(48'(wi)<<(lane*(E==2?8:B)));
     wi=$signed(b[j][lane*4+:4]);pb=pb+(48'(wi)<<(lane*(E==2?8:B)));
    end
    send(2,pa,pb);
   end
   send(3,0,0);
  end
  @(negedge clk);valid=0;repeat(3)@(negedge clk);$fclose(f);
  $display("ENGINE %0d CYCLES %0d",E,cycles);done=1;
 end
endmodule
module tb_packed_neuron_alu;
 reg clk=0;always #2 clk=~clk;
 wire[2:0]done;
 for(genvar e=0;e<3;e=e+1)neuron_driver #(.E(e),.B(`BITS),.N(`LANES))d(clk,done[e]);
 initial begin wait(&done);#20;$finish;end
 initial begin #10000000;$fatal(1,"timeout");end
endmodule
