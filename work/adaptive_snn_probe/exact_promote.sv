`timescale 1ns/1ps
// Actual membrane in narrow DSP fields; group promotion is exact and permanent
// for this timestep. Wide fallback serializes one weight vector over N clocks.
module exact_promote #(parameter integer N=6,SLOT=8,B=16,WB=4,SH=1,VTH=35,LEAK=1,HARD_RESET=0)(
 input wire clk,rst,input wire [1:0] cmd,input wire [N*WB-1:0] w,
 output wire ready,output reg[N-1:0] spike,
 output wire[N*B-1:0] state_debug
);
 localparam integer SW=$clog2(N),MARGIN=(1<<WB),LO=-(1<<(SLOT-1))+MARGIN,HI=(1<<(SLOT-1))-MARGIN-1;
 localparam IDLE=0,LEAKING=1,SEED=2,NARROW=3,DRAIN=4,WIDE=5,WADD=6,FINISH=7;
 reg[3:0]phase;reg[SW-1:0]sel;reg finishing;
 reg signed[B-1:0]mem[N];reg[N*WB-1:0]held_w;
 wire signed[SLOT-1:0] narrow;wire warning;
 reg[47:0] seed_word;reg all_fit;
 integer i;
 always @*begin
  seed_word=0;all_fit=1;
  for(integer k=0;k<N;k=k+1)begin
   seed_word[k*SLOT+:SLOT]={~mem[k][SLOT-1],mem[k][SLOT-2:0]};
   if(mem[k]<LO||mem[k]>HI)all_fit=0;
  end
 end
 assign ready=(phase==IDLE)||(phase==WIDE)||((phase==NARROW)&&!warning);
 wire init=phase==SEED;
 packed_exact_acc #(.SLOT(SLOT),.N(N),.WB(WB),.MIDPOINT(0),.LATENCY(1)) a(
 .clk(clk),.rst(rst),.add((phase==NARROW)&&ready&&(cmd==1)),.init(init),
 .w(w),.seed_word(seed_word),.sel(sel),.rd_s(narrow),.warning(warning),.accepted());
 wire signed[B-1:0] old=mem[sel];
 wire signed[WB-1:0] delta=held_w[sel*WB+:WB];
 wire signed[B-1:0] updated=old+delta;
 wire fire=old>=VTH;
 reg signed[B-1:0] write_data;
 always @*begin
  write_data=old;
  case(phase)
   LEAKING:write_data=LEAK?(old-(old>>>SH)):old;
   DRAIN:write_data={{(B-SLOT){narrow[SLOT-1]}},narrow};
   WADD:write_data=updated;
   FINISH:write_data=fire?(HARD_RESET?0:old-VTH):old;
  endcase
 end
 always @(posedge clk)begin
  if(rst)begin phase<=IDLE;sel<=0;finishing<=0;held_w<=0;spike<=0;for(i=0;i<N;i=i+1)mem[i]<=0;end
  else begin
   if(phase==LEAKING||phase==DRAIN||phase==WADD||phase==FINISH)mem[sel]<=write_data;
   case(phase)
    IDLE:if(cmd==2)begin phase<=LEAKING;sel<=0;spike<=0;end
    LEAKING:if(sel==N-1)begin phase<=SEED;sel<=0;end else sel<=sel+1'b1;
    SEED:begin phase<=all_fit?NARROW:WIDE;sel<=0;end
    NARROW:if(warning||cmd==3)begin phase<=DRAIN;sel<=0;finishing<=cmd==3;end
    DRAIN:if(sel==N-1)begin phase<=finishing?FINISH:WIDE;sel<=0;end else sel<=sel+1'b1;
    WIDE:if(cmd==1)begin held_w<=w;phase<=WADD;sel<=0;end
         else if(cmd==3)begin phase<=FINISH;sel<=0;end
    WADD:if(sel==N-1)begin phase<=WIDE;sel<=0;end else sel<=sel+1'b1;
    FINISH:begin spike[sel]<=fire;if(sel==N-1)begin phase<=IDLE;sel<=0;end else sel<=sel+1'b1;end
    default:phase<=IDLE;
   endcase
  end
 end
 for(genvar g=0;g<N;g=g+1)assign state_debug[g*B+:B]=mem[g];
endmodule
