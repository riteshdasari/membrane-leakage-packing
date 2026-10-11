"""Prepare one new matched U13 frontier; no tool jobs or frozen-file edits."""
from pathlib import Path
import hashlib
import json
import sys
sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent
F5 = P.parent/'residue_frontier_f5_trial'


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def once(source, old, new):
    assert source.count(old) == 1, (old, source.count(old))
    return source.replace(old, new)


def main():
    target = P/'guard_add_frontier_u13.sv'
    assert not target.exists(), 'Preserve prepared RTL'
    original = (F5/'guard_add_frontier_f5.sv').read_text()
    prefix = '''`timescale 1ns/1ps
// Exact signed13 U plus statically sign-extended signed8 I -> signed14.
// Four advancing-edge pipeline, global output freeze and ordered prefixes.
// E0: fixed6 radix128, E1: fixed8 late recovery, E2: fixed8 high precompute,
// E3: native TWO24 two DSP lanes plus six fabric lanes, E4: eight fabric lanes,
// E5: five full-U13 lanes plus three actual-U8-admitted narrow tail lanes.
// Original IF safety is certified for 32 timesteps, not unbounded integration.
module guard_add_frontier_u13 #(parameter integer E=0)(
 input wire clk,rst,in_valid,out_ready,
 input wire[103:0]u_in,i_in,input wire[3:0]available,
 output wire in_ready,output wire[3:0]take,
 output wire out_valid,output wire[3:0]out_count,
 output wire[111:0]out_data,output wire narrow_mode);
'''
    body = original.split('  reg result_valid=0;', 1)[1]
    body = '  reg result_valid=0;' + body
    body = once(body, ' end endgenerate\nendmodule', ' endgenerate\nendmodule')
    hybrid_at = body.index('  end else if(E==3)begin:native_hybrid')
    fabric_at = body.index('  end else begin:fabric_all', hybrid_at)
    before, fabric = body[:hybrid_at], body[fabric_at:]
    for old, new in (('[95:0]', '[111:0]'), ('11*', '13*'), ('12*', '14*'),
                     ('+:12', '+:14'), (":12'd0", ":14'd0")):
        before = before.replace(old, new)
        fabric = fabric.replace(old, new)
    before = once(before, 'assign take=(E==5)?adaptive_prefix:available;',
                  'assign take=(E==0)?((available>6)?4\'d6:available):((E==5)?adaptive_prefix:available);')
    for lane in (5,6,7):
        before = once(before, f'(u_in[13*{lane}+8+:3]=={{3{{u_in[13*{lane}+7]}}}})',
                      f'(u_in[13*{lane}+8+:5]=={{5{{u_in[13*{lane}+7]}}}})')
    before = once(before, '  if(E==1||E==2||E==5)begin:residue_eight',
                  '  generate if(E==0)begin:residue_six\n'+fixed_six()+
                  '  end else if(E==1||E==2||E==5)begin:residue_eight')
    # Exact, section-local widening. Residue widths/field positions stay fixed.
    a = before.index('   if(E==1)begin:retained_metadata')
    b = before.index('   end else begin:precomputed_metadata', a)
    retained = before[a:b]
    for old,new in (('reg[47:0]high_u','reg[63:0]high_u'),
                    ('high_u0[6*l+:6]<=u_in[13*l+5+:6]', 'high_u0[8*l+:8]<=u_in[13*l+5+:8]'),
                    ('wire[5:0]hu=high_u2[6*l+:6]', 'wire[7:0]hu=high_u2[8*l+:8]'),
                    ('signed[6:0]', 'signed[8:0]'), ('hu7', 'hu9'), ('hi7','hi9'),
                    ('carry7','carry9'), ('{hu[5],hu}', '{hu[7],hu}'),
                    ('{{4{hi[2]}},hi}', '{{6{hi[2]}},hi}'), ("{6'd0,p[6*l+5]}","{8'd0,p[6*l+5]}")):
        assert old in retained, old
        retained = retained.replace(old,new)
    before = before[:a]+retained+before[b:]
    before = once(before, '// Only consumed if U is signed8; arbitrary unused wide U is hidden.',
                  '// Only consumed if U is signed8; arbitrary unused U13 is hidden.')
    before = once(before, 'assign answer[14*l+:14]={{3{sum9[8]}},sum9};',
                  'assign answer[14*l+:14]={{5{sum9[8]}},sum9};')
    a = before.index('     end else begin:full_lane')
    full = before[a:]
    for old,new in (('wire[5:0]hu=u_in[13*l+5+:6]', 'wire[7:0]hu=u_in[13*l+5+:8]'),
                    ('signed[6:0]', 'signed[8:0]'), ('reg[6:0]', 'reg[8:0]'),
                    ('hu7','hu9'), ('hi7','hi9'), ('carry7','carry9'),
                    ('{hu[5],hu}', '{hu[7],hu}'), ('{{4{hi[2]}},hi}', '{{6{hi[2]}},hi}'),
                    ("{6'd0,p[6*l+5]}","{8'd0,p[6*l+5]}")):
        assert old in full,old
        full=full.replace(old,new)
    before=before[:a]+full
    for old,new in (('signed[11:0]', 'signed[13:0]'), ('u12','u14'),('i12','i14'),
                    ('{u_in[13*l+10],u_in[13*l+:11]}','{u_in[13*l+12],u_in[13*l+:13]}'),
                    ('{{4{i_in[13*l+7]}},i_in[13*l+:8]}','{{6{i_in[13*l+7]}},i_in[13*l+:8]}')):
        assert old in fabric,old
        fabric=fabric.replace(old,new)
    target.write_text(prefix+before+native_hybrid()+fabric)
    timing=(F5/'guard_add_frontier_f5_timing.sv').read_text()
    for old,new in (('guard_add_frontier_f5','guard_add_frontier_u13'),('[87:0]','[103:0]'),
                    ('[95:0]','[111:0]'),('183 launch FFs and 107 capture FFs = 290','215 launch FFs and 123 capture FFs = 338')):
        assert old in timing,old
        timing=timing.replace(old,new)
    (P/'guard_add_frontier_u13_timing.sv').write_text(timing)
    route=(P.parent/'residue_frontier_trial'/'route_frontier.tcl').read_text()
    route=route.replace('top_guard_add_frontier_e','top_guard_add_frontier_u13_e')
    route=once(route,' read_verilog -sv $here/../common_layout_trial/guard_add_selective.sv\n','')
    route=route.replace('guard_add_frontier.sv','guard_add_frontier_u13.sv').replace('guard_add_frontier_timing.sv','guard_add_frontier_u13_timing.sv')
    route=route.replace('183','215').replace('107','123')
    (P/'route_u13.tcl').write_text(route)
    (P/'export_u13.tcl').write_text((P.parent/'residue_frontier_trial'/'export_frontier.tcl').read_text())
    replay=(P.parent/'residue_frontier_trial'/'tb_frontier_route_replay.sv').read_text()
    replay=once(replay,' reg clk=0;always #3 clk=~clk;',
                ' reg clk=0;initial begin #6;forever #3 clk=~clk;end')
    for old,new in (('[87:0]','[103:0]'),('[95:0]','[111:0]'),('[106:0]','[122:0]'),
                    ('[106:101]','[122:117]'),('[100:97]','[116:113]'),
                    ('[96:1]','[112:1]'),('expected[slot][101]','expected[slot][117]'),
                    ('tb_frontier_route_replay','tb_frontier_u13_route_replay')):
        assert old in replay,old
        replay=replay.replace(old,new)
    (P/'tb_frontier_u13_route_replay.sv').write_text(replay)
    sources=[F5/'guard_add_frontier_f5.sv',F5/'guard_add_frontier_f5_timing.sv',
             P.parent/'residue_frontier_trial'/'route_frontier.tcl',
             P.parent/'residue_frontier_trial'/'export_frontier.tcl',
             P.parent/'residue_frontier_trial'/'tb_frontier_route_replay.sv',P.parent/'guard_add.sv']
    outputs=[target,P/'guard_add_frontier_u13_timing.sv',P/'route_u13.tcl',P/'export_u13.tcl',P/'tb_frontier_u13_route_replay.sv']
    (P/'rtl_preparation_manifest.json').write_text(json.dumps(dict(
        source_sha256={str(p):sha(p) for p in sources+[Path(__file__)]},
        prepared_sha256={str(p):sha(p) for p in outputs},
        scope='Preparation only; no compiler, route, replay or power execution'),indent=2)+'\n')
    print('U13 RTL PREPARED',flush=True)


def fixed_six():
    return '''   reg[41:0]residue_u0=0,residue_i0=0;
   wire[47:0]ab,c,p;
   for(genvar l=0;l<6;l=l+1)begin:lane
    assign ab[8*l+:8]={1'b0,residue_u0[7*l+:7]};
    assign c[8*l+:8]={1'b0,residue_i0[7*l+:7]};
    wire[5:0]hu=u_in[13*l+7+:6];
    wire hi=i_in[13*l+7];
    wire signed[6:0]hu7={hu[5],hu};
    wire signed[6:0]hi7={7{hi}};
    (* use_dsp="no" *)wire signed[6:0]base=hu7+hi7;
    reg[6:0]base0=0,base1=0,base2=0;
    always @(posedge clk)begin
     if(rst)begin base0<=0;base1<=0;base2<=0;end
     else if(advance)begin
      if(accept)base0<=base;
      if(v0)base1<=base0;
      if(v1)base2<=base1;
     end
    end
    wire signed[6:0]carry7={6'd0,p[8*l+7]};
    (* use_dsp="no" *)wire signed[6:0]high=$signed(base2)+carry7;
    assign answer[14*l+:14]={high,p[8*l+:7]};
   end
   assign answer[111:84]=28'd0;
   always @(posedge clk)begin
    if(rst)begin residue_u0<=0;residue_i0<=0;end
    else if(advance&&accept)begin
     for(integer l=0;l<6;l=l+1)begin
      residue_u0[7*l+:7]<=u_in[13*l+:7];
      residue_i0[7*l+:7]<=i_in[13*l+:7];
     end
    end
   end
   guard_add_dsp #(.SIMD("ONE48"))d(
    .clk(clk),.rst(rst),.advance(advance),.operand_issue(v0),.sum_issue(v1),
    .ab(ab),.c(c),.p(p));
'''


def native_hybrid():
    return '''  end else if(E==3)begin:native_hybrid
   reg[25:0]raw_u0=0;
   reg[15:0]raw_i0=0;
   reg[83:0]sum0=0,sum1=0,sum2=0;
   wire[83:0]extra;
   wire[47:0]ab,c,p;
   for(genvar l=0;l<2;l=l+1)begin:encode
    assign ab[24*l+:24]={{11{raw_u0[13*l+12]}},raw_u0[13*l+:13]};
    assign c[24*l+:24]={{16{raw_i0[8*l+7]}},raw_i0[8*l+:8]};
    assign answer[14*l+:14]=p[24*l+:14];
   end
   for(genvar l=2;l<8;l=l+1)begin:fabric_lane
    wire signed[13:0]u14={u_in[13*l+12],u_in[13*l+:13]};
    wire signed[13:0]i14={{6{i_in[13*l+7]}},i_in[13*l+:8]};
    (* use_dsp="no" *)wire signed[13:0]sum=u14+i14;
    assign extra[14*(l-2)+:14]=sum;
   end
   always @(posedge clk)begin
    if(rst)begin raw_u0<=0;raw_i0<=0;sum0<=0;sum1<=0;sum2<=0;end
    else if(advance)begin
     if(accept)begin
      raw_u0<=u_in[25:0];
      for(integer l=0;l<2;l=l+1)raw_i0[8*l+:8]<=i_in[13*l+:8];
      sum0<=extra;
     end
     if(v0)sum1<=sum0;
     if(v1)sum2<=sum1;
    end
   end
   assign answer[111:28]=sum2;
   guard_add_dsp #(.SIMD("TWO24"))d(
    .clk(clk),.rst(rst),.advance(advance),.operand_issue(v0),.sum_issue(v1),
    .ab(ab),.c(c),.p(p));
'''


if __name__=='__main__': main()
