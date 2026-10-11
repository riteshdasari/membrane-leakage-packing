`timescale 1ns/1ps
`ifndef SH
`define SH 1
`endif
`ifndef LEAK
`define LEAK 1
`endif
`ifndef HARD
`define HARD 0
`endif
module tb_exact_tile;
 reg clk=0;always #5 clk=~clk;
 reg rst=1;
 reg[4:0]valid=0,done=0;
 reg[1:0]cmd[5];reg[95:0]w[5];
 wire[4:0]ready;wire[23:0]sp[5];wire[383:0]state[5];
 integer cycles[5],events[5],busy[5];
 for(genvar g=0;g<5;g=g+1)begin:engines
  exact_tile #(.MODE(g),.SH(`SH),.LEAK(`LEAK),.HARD_RESET(`HARD)) dut(
   .clk(clk),.rst(rst),.valid(valid[g]),.cmd(cmd[g]),.w(w[g]),.ready(ready[g]),.spike(sp[g]),.state_debug(state[g]));
  always @(posedge clk)if(!rst&&!done[g])begin
   cycles[g]=cycles[g]+1;
   if(valid[g]&&ready[g]&&cmd[g]==1)events[g]=events[g]+1;
   if(!ready[g])busy[g]=busy[g]+1;
  end
 end
`ifdef TRACE
 always @(posedge clk)if(!rst&&cycles[0]<100)$display("TRACE valid=%b cmd0=%d ready=%b phase=%d accepted=%d",valid,cmd[0],ready,engines[0].dut.dsp.genblk1[0].genblk1.u.phase,engines[0].dut.dsp.accepted_cmd);
`endif
 task automatic issue(input integer idx,input integer c);
 begin
  valid[idx]=0;cmd[idx]=0;
  while(!ready[idx])@(negedge clk);
  valid[idx]=1;cmd[idx]=c;
  @(negedge clk);valid[idx]=0;cmd[idx]=0;
 end
 endtask
 task automatic run(input integer idx);
 integer fd,fo,fc,rv,t,e,j,k,tmp,steps;reg[95:0]nextw;
 begin
  fd=$fopen("stim.txt","r");fo=$fopen($sformatf("out%0d.txt",idx),"w");
  rv=$fscanf(fd,"%d",steps);
  for(t=0;t<steps;t=t+1)begin
   issue(idx,2);rv=$fscanf(fd,"%d",e);
   for(j=0;j<e;j=j+1)begin
    for(k=0;k<24;k=k+1)begin rv=$fscanf(fd,"%d",tmp);nextw[k*4+:4]=4'(tmp);end
    w[idx]=nextw;issue(idx,1);
   end
   issue(idx,3);while(!ready[idx])@(negedge clk);
   $fwrite(fo,"%d",t);
   for(k=0;k<24;k=k+1)$fwrite(fo," %d",$signed(state[idx][k*16+:16]));
   for(k=0;k<24;k=k+1)$fwrite(fo," %d",sp[idx][k]);
   $fwrite(fo,"\n");
  end
  done[idx]=1;
  fc=$fopen($sformatf("cycles%0d.txt",idx),"w");
  $fwrite(fc,"%d %d %d\n",cycles[idx],events[idx],busy[idx]);$fclose(fc);
  $fclose(fd);$fclose(fo);
 end
 endtask
 initial begin
  for(integer i=0;i<5;i=i+1)begin cmd[i]=0;w[i]=0;cycles[i]=0;events[i]=0;busy[i]=0;end
  repeat(20)@(negedge clk);rst=0;
  fork run(0);run(1);run(2);run(3);run(4);join
  $finish;
 end
 initial begin #50000000;$fatal(1,"timeout");end
endmodule
