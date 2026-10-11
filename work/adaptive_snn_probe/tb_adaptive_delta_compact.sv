`timescale 1ns/1ps
module delta_driver #(parameter E=0)(output reg done=0);
 reg clk=0;always #2 clk=~clk;
 reg rst=1,valid=0,active=0;reg[65:0]uin=0;reg[4:0]delta=0;
 wire ready,ov,iv,narrow;wire[65:0]out;
 adaptive_delta_compact #(.E(E),.DC(`DC),.MP(`MP))u(.clk(clk),.rst(rst),.valid(valid),
  .u_in(uin),.delta(delta),.ready(ready),.out_valid(ov),.u_out(out),.issue_valid(iv),.narrow_mode(narrow));
 integer fi,fo,rows,i,d,g,rc,j,sv;
 reg[65:0]raw;
 integer cycles=0,accepted=0,outputs=0,issues=0,due=-1,start_cycle=0,nslots=0,narrow_groups=0,bypasses=0;
 reg fit;
 always @(posedge clk)begin
  if(!rst&&active)begin
   cycles=cycles+1;if(iv)issues=issues+1;
   if(valid&&ready)begin
    if(due>=0)$fatal(1,"overlapping group");
    accepted=accepted+1;start_cycle=cycles;fit=1;
    for(j=0;j<6;j=j+1)begin sv=$signed(uin[j*11+:11]);if(sv< -16||sv>15)fit=0;end
    if(uin==0||(`DC<0?delta:`DC)==0)begin nslots=0;bypasses=bypasses+1;end
    else if(E==3)nslots=1;
    else if(E==0&&fit)begin nslots=2;narrow_groups=narrow_groups+1;end
    else nslots=3;
    due=cycles+(nslots==0?0:nslots+`MP+1);
   end
  end
  #0.1;
  if(!rst&&active)begin
   if(ov)begin
    if(due!=cycles)$fatal(1,"E%0d wrong latency due%0d now%0d",E,due,cycles);
    $fdisplay(fo,"%h %0d %0d",out,start_cycle,cycles);
    outputs=outputs+1;due=-1;
   end else if(due==cycles)$fatal(1,"E%0d missing output",E);
  end
 end
 initial begin
  fo=$fopen($sformatf("out%0d.txt",E),"w");fi=$fopen("stim.txt","r");rc=$fscanf(fi,"%d",rows);
  repeat(50)@(negedge clk);rst=0;uin={6{11'd777}};delta=25;valid=1;
  @(negedge clk);valid=0;
  // Cancel an in-flight group and verify that no stale valid emerges.
  @(negedge clk);rst=1;repeat(2)@(negedge clk);rst=0;
  repeat(5)begin @(negedge clk);if(ov)$fatal(1,"stale reset output");end
  active=1;
  for(i=0;i<rows;i=i+1)begin
   rc=$fscanf(fi,"%d %d %h",g,d,raw);if(rc!=3)$fatal(1,"bad stimulus");
   repeat(g)@(negedge clk);
   while(!ready)@(negedge clk);
   uin=raw;delta=d;valid=1;
   @(negedge clk);valid=0;
  end
  while(outputs<rows)@(negedge clk);
  if(accepted!=outputs)$fatal(1,"lost output");
  $fclose(fo);$fclose(fi);
  $display("DELTA E %0d CYCLES %0d ACCEPTED %0d OUTPUTS %0d ISSUES %0d NARROW %0d BYPASS %0d",E,cycles,accepted,outputs,issues,narrow_groups,bypasses);
  done=1;
 end
 initial begin #20000000;$fatal(1,"timeout E%0d",E);end
endmodule
module tb_adaptive_delta_compact;
 wire[4:0]done;
 delta_driver #(.E(0))a(done[0]);delta_driver #(.E(1))b(done[1]);
 delta_driver #(.E(2))c(done[2]);delta_driver #(.E(3))d(done[3]);
 if(`DC>=0)delta_driver #(.E(5))e(done[4]);else assign done[4]=1;
 initial begin wait(&done);$display("ADAPTIVE DELTA PASS");$finish;end
endmodule
