`timescale 1ns/1ps
`ifndef STALL
`define STALL 0
`endif
`ifndef CAPTURE
`define CAPTURE 0
`endif
`ifndef SHIFT_COHORT
`define SHIFT_COHORT 0
`endif
module tb_sequential_static9;
 localparam integer ENGINES=2;
 reg clk=0;always #3 clk=~clk;
 reg rst=1;reg[ENGINES-1:0]iv=0,oready=0;
 reg[31:0]u[0:ENGINES-1];reg[17:0]beta[0:ENGINES-1];reg[1:0]avail[0:ENGINES-1];
 wire[ENGINES-1:0]ir,ov,narrow;wire[1:0]take[0:ENGINES-1],count[0:ENGINES-1];wire[31:0]data[0:ENGINES-1];
 integer values[0:400000],coefs[0:400000],ends[0:400000];
 integer pos[0:ENGINES-1],retpos[0:ENGINES-1],head[0:ENGINES-1],tail[0:ENGINES-1],requests[0:ENGINES-1],retires[0:ENGINES-1];
 integer qt[0:ENGINES-1][0:7],qc[0:ENGINES-1][0:7],first[0:ENGINES-1],last[0:ENGINES-1],lo[0:ENGINES-1],hi[0:ENGINES-1];
 integer outfiles[0:ENGINES-1],tracefiles[0:ENGINES-1],holdsource[0:ENGINES-1],held[0:ENGINES-1];reg[31:0]helddata[0:ENGINES-1];reg[1:0]heldcount[0:ENGINES-1];
 integer fd,N,i,e,r,cycle,completed,t,expected,latency,acc,ret;
 generate for(genvar g=0;g<ENGINES;g=g+1)begin:duts
  if(g==0)begin:full16_reference
   sequential_leak16 #(.E(5),.B(16))dut(clk,rst,iv[g],oready[g],u[g],beta[g],avail[g],ir[g],ov[g],take[g],count[g],data[g],narrow[g]);
  end else begin:narrow_only_ablation
   sequential_leak_static9 #(.E(8),.B(16))dut(clk,rst,iv[g],oready[g],u[g],beta[g],avail[g],ir[g],ov[g],take[g],count[g],data[g],narrow[g]);
  end
 end endgenerate
 function automatic integer reference(input integer a,b);
  integer product;begin product=a*b;if(product>=0)reference=(product+255)/256;else reference=-((-product)/256);end
 endfunction
 initial begin
  fd=$fopen("stim.txt","r");if(!fd)$fatal(1,"Missing stimulus");r=$fscanf(fd,"%d\n",N);
  if(r!=1||N>400000||N<1)$fatal(1,"Invalid N");
  for(i=0;i<N;i=i+1)begin
   r=$fscanf(fd,"%d %d %d\n",values[i],coefs[i],ends[i]);
   if(r!=3||values[i]<-256||values[i]>255||coefs[i]<0||coefs[i]>256||ends[i]<=i||ends[i]>N)$fatal(1,"Invalid stimulus row %d",i);

  end
  $fclose(fd);
  for(e=0;e<ENGINES;e=e+1)begin
   u[e]=0;beta[e]=0;avail[e]=0;pos[e]=0;retpos[e]=0;head[e]=0;tail[e]=0;requests[e]=0;retires[e]=0;
   first[e]=-1;last[e]=-1;lo[e]=1000000;hi[e]=0;holdsource[e]=0;held[e]=0;
   outfiles[e]=$fopen($sformatf("out%0d.txt",e),"w");
   if(`CAPTURE)tracefiles[e]=$fopen($sformatf("trace%0d.txt",e),"w");
  end
  #121;
  begin:run_loop
   for(cycle=0;cycle<1000000;cycle=cycle+1)begin
    @(negedge clk);rst=cycle<3;
    for(e=0;e<ENGINES;e=e+1)begin
     oready[e]=!`STALL||(cycle%11<8);
     iv[e]=!rst&&(pos[e]<N)&&(holdsource[e]||!`STALL||(cycle%7!=5));
     avail[e]=(!rst&&pos[e]<N)?((ends[pos[e]]-pos[e]>=2)?2:1):0;
     u[e]=0;beta[e]=0;
     if(avail[e]>0)begin u[e][0+:16]=values[pos[e]];beta[e][0+:9]=coefs[pos[e]];end
     if(avail[e]>1)begin u[e][16+:16]=values[pos[e]+1];beta[e][9+:9]=coefs[pos[e]+1];end
    end
    @(posedge clk);completed=0;
    for(e=0;e<ENGINES;e=e+1)begin
     acc=iv[e]&&ir[e]&&avail[e]>0;ret=ov[e]&&oready[e];
     if(`CAPTURE)$fwrite(tracefiles[e],"%0d %0d %0d %0d %0d %08h %05h %0d %0d %0d %0d %08h %0d %0d %0d\n",cycle,rst,iv[e],oready[e],avail[e],u[e],beta[e],ir[e],take[e],ov[e],count[e],data[e],narrow[e],acc,ret);
     if(held[e]&&(ov[e]!==1'b1||data[e]!==helddata[e]||count[e]!==heldcount[e]))$fatal(1,"Output changed while held E%0d cycle%0d",e,cycle);
     held[e]=ov[e]&&!oready[e];helddata[e]=data[e];heldcount[e]=count[e];
     holdsource[e]=iv[e]&&!ir[e];
     if(acc)begin
      if(tail[e]-head[e]>=8)$fatal(1,"Scoreboard overflow");
      if(take[e]<1||take[e]>avail[e])$fatal(1,"Invalid take");
      qc[e][tail[e]%8]=take[e];qt[e][tail[e]%8]=cycle;tail[e]=tail[e]+1;
      pos[e]=pos[e]+take[e];requests[e]=requests[e]+1;if(first[e]<0)first[e]=cycle;
     end
     if(ret)begin
      if(head[e]>=tail[e]||count[e]!==qc[e][head[e]%8])$fatal(1,"Retirement count E%0d cycle%0d",e,cycle);
      t=count[e];expected=reference(values[retpos[e]],coefs[retpos[e]])&65535;
      if(t==2)expected=expected|((reference(values[retpos[e]+1],coefs[retpos[e]+1])&65535)<<16);
      if(data[e]!==expected[31:0])$fatal(1,"Numeric E%0d cycle%0d pos%0d got%h want%h",e,cycle,retpos[e],data[e],expected[31:0]);
      if(narrow[e]!==((e==0||e==1)&&t==2))$fatal(1,"Format metadata E%0d",e);
      latency=cycle-qt[e][head[e]%8];if(latency<2)$fatal(1,"Latency below2");
      if(latency<lo[e])lo[e]=latency;if(latency>hi[e])hi[e]=latency;
      $fwrite(outfiles[e],"%0d %0d %08h %0d\n",cycle,t,data[e],latency);
      retpos[e]=retpos[e]+t;head[e]=head[e]+1;retires[e]=retires[e]+1;last[e]=cycle;
     end
     if(retpos[e]==N&&pos[e]==N&&head[e]==tail[e])completed=completed+1;
    end
    if(completed==ENGINES)disable run_loop;
   end
  end
  for(e=0;e<ENGINES;e=e+1)begin
   if(retpos[e]!=N||pos[e]!=N||head[e]!=tail[e])$fatal(1,"Incomplete E%0d",e);
   $display("LEAK_NATIVE E %0d REQUESTS %0d RETIREMENTS %0d NEURONS %0d CLOCKS %0d MIN_LATENCY %0d MAX_LATENCY %0d FIRST %0d LAST %0d",e,requests[e],retires[e],retpos[e],last[e]-first[e]+1,lo[e],hi[e],first[e],last[e]);
   $fclose(outfiles[e]);if(`CAPTURE)$fclose(tracefiles[e]);
  end
  $display("LEAK_NATIVE PASS");#30;$finish;
 end
endmodule
