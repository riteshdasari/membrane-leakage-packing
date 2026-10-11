`timescale 1ns/1ps
`ifndef STALL
 `define STALL 0
`endif
`ifndef CAPTURE_TRACE
 `define CAPTURE_TRACE 0
`endif
// Separate readers preserve the same group stream while prefix capacity changes.
// Arithmetic oracle below is ordinary signed integer addition, never residue math.
module restored_reference_driver #(parameter E=0)(input wire clk,output reg done=0);
 reg rst=1,iv=0,orr=1,running=0,trace_on=0;
 reg[87:0]raw_u=0,raw_i=0;reg[3:0]av=0;
 wire ir,ov,mode;wire[3:0]take,nout;wire[95:0]answer;
 generate if(E<6)begin:original
  guard_add_frontier #(.E(E))dut(.clk(clk),.rst(rst),.in_valid(iv),.out_ready(orr),
   .u_in(raw_u),.i_in(raw_i),.available(av),.in_ready(ir),.take(take),
   .out_valid(ov),.out_count(nout),.out_data(answer),.narrow_mode(mode));
 end else if(E<12)begin:f5
  guard_add_frontier_f5 #(.E(E-6))dut(.clk(clk),.rst(rst),.in_valid(iv),.out_ready(orr),
   .u_in(raw_u),.i_in(raw_i),.available(av),.in_ready(ir),.take(take),
   .out_valid(ov),.out_count(nout),.out_data(answer),.narrow_mode(mode));
 end else begin:static_narrow
  guard_add_static_narrow_eight dut(.clk(clk),.rst(rst),.in_valid(iv),.out_ready(orr),
   .u_in(raw_u),.i_in(raw_i),.available(av),.in_ready(ir),.take(take),
   .out_valid(ov),.out_count(nout),.out_data(answer),.narrow_mode(mode));
 end endgenerate
 integer source,sink,trace_sink=0,status,ngroups,group_id=-1,length=0,index=0,gap=0,remaining_gap=0,k;
 reg[10:0]mem_u[0:4095],mem_i[0:4095];
 integer head=0,tail=0,qgroup[0:31],qstart[0:31],qn[0:31],qclk[0:31],qstep[0:31];
 reg[95:0]qanswer[0:31];
 integer cycle=0,step=0,accepted=0,retired=0,neurons=0,first=-1,last=-1;
 integer input_stalls=0,output_stalls=0,latency_min=2147483647,latency_max=0;
 integer trace_index=0,first_trace=-1,last_trace=-1,reset_samples=0,prelude_samples=0;
 integer group_drains=0;
 reg exhausted=0,group_done=0,source_held=0,held=0;
 reg[87:0]held_u,held_i;reg[3:0]held_av,held_take;
 reg[95:0]hold_data;reg[3:0]hold_count;
 integer uu,ii,expected_take;
 reg[95:0]expected_answer;
 task read_group;
  begin
   group_id=group_id+1;
   if(group_id==ngroups)begin exhausted=1;index=0;length=0;end
   else begin
    status=$fscanf(source,"%d %d\n",length,gap);
    if(status!=2||length<1||length>4096||gap<0)$fatal(1,"Bad frontier group E%0d",E);
    for(k=0;k<length;k=k+1)begin
     status=$fscanf(source,"%h %h\n",mem_u[k],mem_i[k]);
     if(status!=2||mem_i[k][10:8]!={3{mem_i[k][7]}})$fatal(1,"Bad U11/I8 pair E%0d",E);
    end
    index=0;remaining_gap=gap;group_done=0;
   end
  end
 endtask
 initial begin
  sink=$fopen($sformatf("frontier_out%0d.txt",E),"w");source=$fopen("stream_stim.txt","r");
  if(!source||!sink)$fatal(1,"Cannot open frontier work files");
  if(`CAPTURE_TRACE)begin
   trace_sink=$fopen($sformatf("frontier_trace%0d.txt",E),"w");
   if(!trace_sink)$fatal(1,"Cannot open frontier trace");
  end
  status=$fscanf(source,"%d\n",ngroups);if(status!=1||ngroups<1)$fatal(1,"Bad frontier group count");
  #120;trace_on=1;
  repeat(3)@(negedge clk);rst=0;iv=1;av=8;orr=0;
  for(k=0;k<8;k=k+1)begin raw_u[11*k+:11]=96+k;raw_i[11*k+:11]=7+k;end
  repeat(7)@(negedge clk);if(!ov)$fatal(1,"Frontier blocked-output prelude failed E%0d",E);
  rst=1;iv=0;repeat(2)@(negedge clk);rst=0;orr=1;
  repeat(5)begin @(negedge clk);#0.001;if(ov)$fatal(1,"Reset-canceled frontier output escaped E%0d",E);end
  iv=1;av=8;raw_u={8{11'd127}};raw_i={8{11'd127}};
  repeat(2)@(negedge clk);rst=1;iv=0;
  repeat(2)@(negedge clk);rst=0;
  repeat(5)begin @(negedge clk);#0.001;if(ov)$fatal(1,"In-flight frontier output escaped reset E%0d",E);end
  read_group();#0.001;running=1;
 end
 always @(negedge clk)begin
  if(running&&!done)begin
   orr=`STALL?((cycle%11!=4)&&(cycle%11!=5)&&(cycle%17!=3)):1;
   if(!source_held)begin
    iv=!exhausted&&!group_done&&(remaining_gap==0)&&(!`STALL||(cycle%13!=6));
    if(!exhausted&&!group_done)begin
     av=(length-index>=8)?8:(length-index);
     for(k=0;k<8;k=k+1)begin
      raw_u[11*k+:11]=(k<av)?mem_u[index+k]:(k%2?11'h400:11'h7ff);
      raw_i[11*k+:11]=(k<av)?mem_i[index+k]:(k%2?11'h7ff:11'h400);
     end
    end else begin av=0;raw_u=0;raw_i=0;iv=0;end
   end
  end
  #0.020;
  if(trace_on&&!done)begin
   if(!running)prelude_samples=prelude_samples+1;
   if(rst)reset_samples=reset_samples+1;
   if(`CAPTURE_TRACE)begin
    $fwrite(trace_sink,"%0d %0d 0 %0d %0d %0d %0d %022h %022h %0d %0d %0d %0d %024h %0d %0d %0d %0d\n",
     trace_index,running,rst,iv,orr,av,raw_u,raw_i,ir,take,ov,nout,answer,mode,
     (ir===1'b1),(!rst&&iv&&ir&&av!=0),(!rst&&ov&&orr));
   end
   if(running&&iv&&ir&&av!=0&&first_trace<0)first_trace=trace_index;
   if(running&&ov&&orr)last_trace=trace_index;
   trace_index=trace_index+1;
  end
 end
 always @(posedge clk)if(running&&!done)begin
  cycle=cycle+1;
  if(ir!==!(ov&&!orr))$fatal(1,"Ready/advance contract E%0d",E);
  expected_take=(av<8)?av:8;
  if(E==0||E==6)expected_take=(av<6)?av:6;
  if(E==5||E==11)begin
   expected_take=(av<((E==11)?5:6))?av:((E==11)?5:6);
   for(integer lane=((E==11)?5:6);lane<8;lane=lane+1)begin
    uu=$signed(raw_u[11*lane+:11]);
    if(expected_take==lane&&av>lane&&uu>=-128&&uu<=127)expected_take=lane+1;
   end
  end
  if(take!==4'(expected_take)||mode!==(((E==5)&&(expected_take>6))||((E==11)&&(expected_take>5))))$fatal(1,"Frontier prefix/mode E%0d",E);
  if(E==12&&iv&&ir)begin
   for(integer lane=0;lane<av;lane=lane+1)begin
    uu=$signed(raw_u[11*lane+:11]);
    if(uu<-128||uu>127)$fatal(1,"Static comparator received wide U");
   end
  end
  if(source_held)begin
   input_stalls=input_stalls+1;
   if(!iv||raw_u!==held_u||raw_i!==held_i||av!==held_av||take!==held_take)$fatal(1,"Input changed during stall E%0d",E);
  end
  source_held=iv&&!ir;
  if(source_held)begin held_u=raw_u;held_i=raw_i;held_av=av;held_take=take;end
  if(held&&(!ov||answer!==hold_data||nout!==hold_count))$fatal(1,"Output changed while blocked E%0d",E);
  if(held)output_stalls=output_stalls+1;
  held=ov&&!orr;if(held)begin hold_data=answer;hold_count=nout;end
  if(iv&&ir&&av!=0)begin
   if(take<1||take>av||tail-head>=30)$fatal(1,"Bad frontier acceptance E%0d",E);
   expected_answer=0;
   for(k=0;k<take;k=k+1)begin
    uu=$signed(raw_u[11*k+:11]);ii=$signed(raw_i[11*k+:11]);
    expected_answer[12*k+:12]=12'(uu+ii);
   end
   qgroup[tail%32]=group_id;qstart[tail%32]=index;qn[tail%32]=take;
   qclk[tail%32]=cycle;qstep[tail%32]=step;qanswer[tail%32]=expected_answer;tail=tail+1;
   accepted=accepted+1;neurons=neurons+take;if(first<0)first=cycle;
   index=index+take;if(index==length)group_done=1;
  end
  if(ov&&orr)begin
   if(head==tail)$fatal(1,"Unexpected frontier output E%0d",E);
   if(nout!==4'(qn[head%32])||step-qstep[head%32]!=4)$fatal(1,"Frontier four-advance latency E%0d",E);
   if(answer!==qanswer[head%32])$fatal(1,"Frontier integer arithmetic/tail mismatch E%0d group%0d start%0d got%h expected%h",E,qgroup[head%32],qstart[head%32],answer,qanswer[head%32]);
   if(cycle-qclk[head%32]<4)$fatal(1,"Frontier physical latency below four");
   if(cycle-qclk[head%32]<latency_min)latency_min=cycle-qclk[head%32];
   if(cycle-qclk[head%32]>latency_max)latency_max=cycle-qclk[head%32];
   $fwrite(sink,"%0d %0d %0d %024h %0d %0d %0d\n",qgroup[head%32],qstart[head%32],nout,answer,qclk[head%32],cycle,step-qstep[head%32]);
   retired=retired+1;head=head+1;last=cycle;
  end
  if(ir)step=step+1;
  if(remaining_gap>0&&!iv)remaining_gap=remaining_gap-1;
  // Drain the current layer/timestep group before supplying the next group.
  if(group_done&&head==tail)begin group_drains=group_drains+1;read_group();end
  if(exhausted&&head==tail)begin
   if(accepted!=retired||group_drains!=ngroups)$fatal(1,"Lost frontier work");
   $display("FRONTIER E %0d REQUESTS %0d RETIREMENTS %0d NEURONS %0d CLOCKS %0d INPUT_STALLS %0d OUTPUT_STALLS %0d MIN_LATENCY %0d MAX_LATENCY %0d TRACE_ROWS %0d FIRST_ACCEPT_TRACE %0d LAST_RETIRE_TRACE %0d GROUP_DRAINS %0d RESET_SAMPLES %0d PRELUDE_SAMPLES %0d",E,accepted,retired,neurons,last-first+1,input_stalls,output_stalls,latency_min,latency_max,trace_index,first_trace,last_trace,group_drains,reset_samples,prelude_samples);
   $fclose(sink);$fclose(source);if(`CAPTURE_TRACE)$fclose(trace_sink);done=1;iv=0;
  end
  if(cycle>10000000)$fatal(1,"Frontier timeout E%0d",E);
 end
endmodule

`ifndef STATIC_COMPARATOR
 `define STATIC_COMPARATOR 0
`endif
module tb_restored_reference_compare;
 localparam ENGINES=12+`STATIC_COMPARATOR;
 reg clk=0;always #3 clk=~clk;
 wire[ENGINES-1:0]done;
 generate for(genvar e=0;e<ENGINES;e=e+1)begin:engines
  restored_reference_driver #(.E(e))driver(clk,done[e]);
 end endgenerate
 initial begin wait(&done);$display("RESTORED_REFERENCE_COMPARE PASS STALL %0d ENGINES %0d",`STALL,ENGINES);$finish;end
endmodule
