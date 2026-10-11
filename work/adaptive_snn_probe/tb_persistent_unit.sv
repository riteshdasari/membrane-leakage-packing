`timescale 1ns/1ps
module persist_driver #(parameter E=0,W=16)(input wire clk,output reg done=0);
 localparam WL=48/W;
 reg rst=1,valid=0;reg[1:0]cmd=0;reg[47:0]wa=0,wb=0;
 wire ready,wide,half,ov;wire[5:0]sp;wire[95:0]state;
 persistent_unit #(.ENGINE(E),.SH(`SH),.LEAK(`LEAK),.HARD(`HARD),.WIDE_BITS(W),.STATE_BITS(W==10?10:16))u(
 .clk(clk),.rst(rst),.valid(valid),.cmd(cmd),.wa(wa),.wb(wb),.ready(ready),.wide(wide),.half(half),.out_valid(ov),.spike(sp),.state_debug(state));
 integer f,rc,steps,k,i,j,pass,n,selected,cycles=0,narrow_steps=0,wide_steps=0,changes=0,prev=-1;
 reg[23:0]rawa[0:3],rawb[0:3];reg[47:0]worda,wordb;
 integer wi;
 task send(input[1:0]c,input[47:0]a,b);
  begin @(negedge clk);cmd=c;wa=a;wb=b;valid=1;@(posedge clk);while(!ready)@(posedge clk);end
 endtask
 always @(posedge clk)begin
  if(!rst&&!done)cycles=cycles+1;
  #0.1;if(ov)$fdisplay(f,"%h %h",state,sp);
 end
 initial begin
  f=$fopen($sformatf("out%0d_%0d.txt",E,W),"w");
  if((E==4&&(!`LEAK||`SH!=1))||(W<16&&!`LEAK))begin done=1;$fclose(f);end
  else begin
   rc=$fopen("stim.txt","r");i=$fscanf(rc,"%d",steps);
   repeat(50)@(negedge clk);rst=0;
   repeat(2)@(negedge clk);
   for(k=0;k<steps;k=k+1)begin
    i=$fscanf(rc,"%d",n);if(i!=1)$fatal(1,"bad step");
    for(j=0;j<n;j=j+1)begin i=$fscanf(rc,"%h %h",rawa[j],rawb[j]);if(i!=2)$fatal(1,"bad pair");end
    send(1,0,0);#0.2;
    selected=wide;
    if(selected)wide_steps=wide_steps+1;else narrow_steps=narrow_steps+1;
    if(prev>=0&&selected!=prev)changes=changes+1;prev=selected;
    for(pass=0;pass<(selected?2:1);pass=pass+1)begin
     for(j=0;j<n;j=j+1)begin
      worda=0;wordb=0;
      if(E==3)begin worda=rawa[j];wordb=rawb[j];end
      else for(integer lane=0;lane<(selected?WL:6);lane=lane+1)begin
       if(!selected||pass*WL+lane<6)begin
        wi=$signed(rawa[j][(selected?(pass*WL+lane):lane)*4+:4]);
        worda=worda+(48'(wi)<<((selected?W:8)*lane));
        wi=$signed(rawb[j][(selected?(pass*WL+lane):lane)*4+:4]);
        wordb=wordb+(48'(wi)<<((selected?W:8)*lane));
       end
      end
      send(2,worda,wordb);
     end
     send(3,0,0);
    end
   end
   @(negedge clk);valid=0;repeat(3)@(negedge clk);$fclose(f);
   $display("ENGINE %0d WIDTH %0d CYCLES %0d NARROW %0d WIDE %0d CHANGES %0d",E,W,cycles,narrow_steps,wide_steps,changes);
   done=1;
  end
 end
endmodule
module tb_persistent_unit;
 reg clk=0;always #2 clk=~clk;
 wire[10:0]done;
 for(genvar e=0;e<5;e=e+1)persist_driver #(.E(e))d(clk,done[e]);
 persist_driver #(.E(0),.W(12))a12(clk,done[5]);
 persist_driver #(.E(1),.W(12))f12(clk,done[6]);
 for(genvar e=0;e<4;e=e+1)persist_driver #(.E(e),.W(10))d10(clk,done[e+7]);
 initial begin wait(&done);#20;$finish;end
 initial begin #2000000;$fatal(1,"timeout");end
endmodule
