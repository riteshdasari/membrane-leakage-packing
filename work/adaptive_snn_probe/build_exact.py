"""Build isolated final candidates; preserve earlier experiment sources."""
from pathlib import Path
p=Path(__file__).resolve().parent
s=(p/'guard_acc.sv').read_text().split('\nmodule top_margin_acc')[0]
s=s.replace('module guard_acc #','module packed_exact_acc #')
s=s.replace('LATENCY=0)','LATENCY=0,SUPPRESS=0)')
s=s.replace('input wire [N*WB-1:0] w,','input wire [N*WB-1:0] w,\n input wire [47:0] seed_word,')
s=s.replace('assign warning=warning_q;','assign warning=SUPPRESS?1\'b0:warning_q;')
s=s.replace('assign warning=|alarm;','assign warning=SUPPRESS?1\'b0:|alarm;')
s=s.replace('.C(init?BIASW:NEGHB)','.C(init?seed_word:NEGHB)')
(p/'packed_exact_acc.sv').write_text(s)
s=(p/'shared_neuron_pipe.sv').read_text().split('\nmodule top_guard_pipe')[0]
s=s.replace('module shared_neuron_pipe #','module exact_checkpoint #')
s=s.replace('SH=1,VTH=35)','SH=1,VTH=35,LEAK=1,HARD_RESET=0,STATIC=0)')
s=s.replace('wire warning; wire init=',"wire warning; wire init=")
s=s.replace('guard_acc #(.SLOT(SLOT),.N(N),.WB(WB),.MIDPOINT(0),.LATENCY(1))',
 'packed_exact_acc #(.SLOT(SLOT),.N(N),.WB(WB),.MIDPOINT(0),.LATENCY(1),.SUPPRESS(STATIC))')
s=s.replace('.w(w),.sel(sel),.rd_s(narrow)',".w(w),.seed_word(BIASW),.sel(sel),.rd_s(narrow)",1)
s=s.replace('wire signed [B-1:0] old=mem[sel];',"localparam [47:0] BIASW={6{8'h80}};\n wire signed [B-1:0] old=mem[sel];")
# Generic bias constant, rather than assuming the default lane layout.
s=s.replace("localparam [47:0] BIASW={6{8'h80}};", "function [47:0] bias_word; integer j; begin bias_word=0; for(j=0;j<N;j=j+1)bias_word=bias_word+(48'(1<<(SLOT-1))<<(j*SLOT));end endfunction\n localparam [47:0] BIASW=bias_word();")
start=s.index(' function [47:0] bias_word;')
end=s.index(' wire signed [B-1:0] old=mem[sel];',start)
const=s[start:end]
s=s[:start]+s[end:]
s=s.replace(' generate if(GUARDED) begin',const+' generate if(GUARDED) begin')
s=s.replace('fire?sum_pending-VTH:sum_pending','fire?(HARD_RESET?0:sum_pending-VTH):sum_pending')
s=s.replace('(old-(old>>>SH))','(LEAK?(old-(old>>>SH)):old)')
(p/'exact_checkpoint.sv').write_text(s)
