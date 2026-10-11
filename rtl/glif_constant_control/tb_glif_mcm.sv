`timescale 1ns/1ps
`ifndef STALL
`define STALL 0
`endif
`ifndef EXHAUSTIVE
`define EXHAUSTIVE 0
`endif
`ifndef CAPTURE
`define CAPTURE 0
`endif
module tb_sequential_leak16_glif_mcm;
 reg clk=0;always #3 clk=~clk;
 reg rst=1,iv=0,oready=0;reg[31:0]u=0;reg[17:0]beta=0;reg[1:0]avail=0;
 wire ir,ov,narrow;wire[1:0]take,count;wire[31:0]data;
 sequential_leak16_glif_mcm dut(clk,rst,iv,oready,u,beta,avail,ir,ov,take,count,data,narrow);
 integer values[0:400000],coefs[0:400000],ends[0:400000],legal_beta[0:32];
 integer pos=0,retpos=0,head=0,tail=0,requests=0,retires=0;
 integer qt[0:7],qc[0:7],first=-1,last=-1,lo=1000000,hi=0;
 integer holdsource=0,held=0;reg[31:0]helddata;reg[1:0]heldcount;
 integer outfd,tracefd,fd,N,i,r,cycle,t,expected,latency,acc,ret;
 function automatic integer operand(input integer at);
  begin operand=`EXHAUSTIVE?((at%65536)-32768):values[at];end
 endfunction
 function automatic integer coefficient(input integer at);
  begin coefficient=`EXHAUSTIVE?legal_beta[at/65536]:coefs[at];end
 endfunction
 function automatic integer frame_end(input integer at);
  begin frame_end=`EXHAUSTIVE?((at/65536+1)*65536):ends[at];end
 endfunction
 function automatic integer reference(input integer a,b);
  integer product;begin product=a*b;if(product>=0)reference=(product+255)/256;else reference=-((-product)/256);end
 endfunction
 function automatic integer legal(input integer b);
  begin legal=(b>=74&&b<=88)||(b>=153&&b<=170);end
 endfunction
 initial begin
  legal_beta[0]=74;
  legal_beta[1]=75;
  legal_beta[2]=76;
  legal_beta[3]=77;
  legal_beta[4]=78;
  legal_beta[5]=79;
  legal_beta[6]=80;
  legal_beta[7]=81;
  legal_beta[8]=82;
  legal_beta[9]=83;
  legal_beta[10]=84;
  legal_beta[11]=85;
  legal_beta[12]=86;
  legal_beta[13]=87;
  legal_beta[14]=88;
  legal_beta[15]=153;
  legal_beta[16]=154;
  legal_beta[17]=155;
  legal_beta[18]=156;
  legal_beta[19]=157;
  legal_beta[20]=158;
  legal_beta[21]=159;
  legal_beta[22]=160;
  legal_beta[23]=161;
  legal_beta[24]=162;
  legal_beta[25]=163;
  legal_beta[26]=164;
  legal_beta[27]=165;
  legal_beta[28]=166;
  legal_beta[29]=167;
  legal_beta[30]=168;
  legal_beta[31]=169;
  legal_beta[32]=170;
  if(`EXHAUSTIVE)N=2162688;
  else begin
   fd=$fopen("stim.txt","r");if(!fd)$fatal(1,"Missing stimulus");r=$fscanf(fd,"%d\n",N);
   if(r!=1||N>400000||N<1)$fatal(1,"Invalid N");
   for(i=0;i<N;i=i+1)begin
    r=$fscanf(fd,"%d %d %d\n",values[i],coefs[i],ends[i]);
    if(r!=3||values[i]<-32768||values[i]>32767||!legal(coefs[i])||ends[i]<=i||ends[i]>N)$fatal(1,"Invalid row %0d",i);
   end
   $fclose(fd);
  end
  outfd=$fopen("out.txt","w");if(`CAPTURE)tracefd=$fopen("trace.txt","w");
  #121;
  begin:run_loop
   for(cycle=0;cycle<3000000;cycle=cycle+1)begin
    @(negedge clk);rst=cycle<3;
    oready=!`STALL||(cycle%11<8);
    iv=!rst&&(pos<N)&&(holdsource||!`STALL||(cycle%7!=5));
    avail=(!rst&&pos<N)?((frame_end(pos)-pos>=2)?2:1):0;
    u=0;beta=0;
    if(avail>0)begin u[15:0]=operand(pos);beta[8:0]=coefficient(pos);end
    if(avail>1)begin u[31:16]=operand(pos+1);beta[17:9]=coefficient(pos+1);end
    @(posedge clk);
    acc=iv&&ir&&avail>0;ret=ov&&oready;
    if(`CAPTURE)$fwrite(tracefd,"%0d %0d %0d %0d %0d %08h %05h %0d %0d %0d %0d %08h %0d %0d %0d\n",cycle,rst,iv,oready,avail,u,beta,ir,take,ov,count,data,narrow,acc,ret);
    if(held&&(ov!==1'b1||data!==helddata||count!==heldcount))$fatal(1,"Output changed while held at%0d",cycle);
    held=ov&&!oready;helddata=data;heldcount=count;holdsource=iv&&!ir;
    if(acc)begin
     if(tail-head>=8)$fatal(1,"Scoreboard overflow");
     if(take!==avail||take<1||take>2)$fatal(1,"Invalid fixed take");
     qc[tail%8]=take;qt[tail%8]=cycle;tail=tail+1;pos=pos+take;requests=requests+1;if(first<0)first=cycle;
    end
    if(ret)begin
     if(head>=tail||count!==qc[head%8])$fatal(1,"Retirement count cycle%0d",cycle);
     t=count;expected=reference(operand(retpos),coefficient(retpos))&65535;
     if(t==2)expected=expected|((reference(operand(retpos+1),coefficient(retpos+1))&65535)<<16);
     if(data!==expected[31:0])$fatal(1,"Numeric cycle%0d pos%0d got%h want%h",cycle,retpos,data,expected[31:0]);
     if(narrow!==1'b0)$fatal(1,"Unexpected adaptive metadata");
     latency=cycle-qt[head%8];if(latency<2)$fatal(1,"Latency below2");
     if(!`STALL&&latency!=2)$fatal(1,"Unstalled latency differs from2");
     if(latency<lo)lo=latency;if(latency>hi)hi=latency;
     $fwrite(outfd,"%0d %0d %08h %0d\n",cycle,t,data,latency);
     retpos=retpos+t;head=head+1;retires=retires+1;last=cycle;
    end
    if(retpos==N&&pos==N&&head==tail)disable run_loop;
   end
  end
  if(retpos!=N||pos!=N||head!=tail)$fatal(1,"Incomplete");
  $display("GLIF_MCM_NATIVE REQUESTS %0d RETIREMENTS %0d NEURONS %0d CLOCKS %0d MIN_LATENCY %0d MAX_LATENCY %0d FIRST %0d LAST %0d",requests,retires,retpos,last-first+1,lo,hi,first,last);
  $fclose(outfd);if(`CAPTURE)$fclose(tracefd);
  $display("GLIF_MCM_NATIVE PASS");#30;$finish;
 end
endmodule
