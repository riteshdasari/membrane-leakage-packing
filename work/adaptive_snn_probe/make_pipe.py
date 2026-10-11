"""Generate a drain-pipelined variant without changing the already tested original."""
from pathlib import Path
p=Path(__file__).resolve().parent
s=(p/'shared_neuron.sv').read_text()
s=s.replace('shared_neuron','shared_neuron_pipe').replace('top_guard_shared','top_guard_pipe').replace('top_native_shared','top_native_pipe')
s=s.replace('.MIDPOINT(0)', '.MIDPOINT(0),.LATENCY(1)')
s=s.replace(' wire fire=sum>=VTH;', ''' reg signed [B-1:0] sum_pending;
 reg [SW-1:0] store_sel; reg store_ending,valid_store;
 wire fire=sum_pending>=VTH;
 wire [SW-1:0] write_addr=valid_store?store_sel:sel;
 wire signed [B-1:0] write_data=valid_store?(store_ending?(fire?sum_pending-VTH:sum_pending):sum_pending):(old-(old>>>SH));''')
s=s.replace('if(rst) begin phase<=0;', 'if(rst) begin valid_store<=0;sum_pending<=0;store_sel<=0;store_ending<=0;phase<=0;')
s=s.replace('  else case(phase)', '''  else begin
   valid_store<=0;
   if(valid_store||(phase==2))mem[write_addr]<=write_data;
   if(valid_store)begin
    if(store_ending)spike[store_sel]<=fire;
   end
   case(phase)''')
old='''    mem[sel]<=ending?(fire?sum-VTH:sum):sum;
    if(ending)spike[sel]<=fire;
    if(sel==N-1)begin phase<=4;sel<=0;end else sel<=sel+1'b1;'''
new='''    sum_pending<=sum;store_sel<=sel;store_ending<=ending;valid_store<=1;
    if(sel==N-1)begin phase<=5;sel<=0;end else sel<=sel+1'b1;'''
assert old in s
s=s.replace(old,new).replace('   4: phase<=1;', '   5: phase<=4;\n   4: phase<=1;').replace('  endcase\n end','  endcase\n  end\n end')
s=s.replace('2: begin mem[sel]<=old-(old>>>SH);', '2: begin')
(p/'shared_neuron_pipe.sv').write_text(s)
