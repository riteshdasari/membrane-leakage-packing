"""Prepare exact routed-CARRY4 timing diagnostics; never launches Vivado."""
from pathlib import Path
import hashlib
import json
import re
import shutil

P = Path(__file__).resolve().parent
V = Path('C:/AMDDesignTools/2025.2/Vivado')
S = P.parent.parent / 'sequential_paper_trial'
previous = P.parent / 'lut_diag_a2'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


sdf_source = S / 'hardware/export12_e2_a0/routed.sdf'
sdf = sdf_source.read_text()
instance = '(INSTANCE fixture/core/lut\\.lane\\[0\\]\\.r_reg\\[11\\]_i_4)'
i = sdf.index(instance)
a = list(re.finditer(r'\(CELL\s', sdf[:i]))[-1].start()
depth = 0
for j in range(a, len(sdf)):
    depth += (sdf[j] == '(') - (sdf[j] == ')')
    if depth == 0:
        cell = sdf[a:j + 1]
        break
else:
    raise AssertionError('unclosed SDF CELL')
assert '(CELLTYPE "CARRY4")' in cell
cell = cell.replace(instance, '(INSTANCE u)')
minimal_sdf = '''(DELAYFILE
  (SDFVERSION "3.0")
  (DESIGN "tb_minimal_carry")
  (DIVIDER /)
  (TIMESCALE 1 ps)
''' + cell + '\n)\n'
(P / 'carry_original_paths.sdf').write_text(minimal_sdf)
vendor = V / 'data/verilog/src/unisims/CARRY4.v'
shutil.copyfile(vendor, P / 'CARRY4_vendor.v')
assert sha(vendor) == sha(P / 'CARRY4_vendor.v')

pattern = re.compile(r'DBG T([0-9.]+) ROW(\d+) S([0-9a-f]+) DI([0-9a-f]+) CI([01]) CO([0-9a-f]+) O([0-9a-f]+)')
events = []
for line in (previous / 'tool_4.log').read_text().splitlines():
    m = pattern.match(line)
    if m and 910 <= int(m[2]) <= 914:
        t = round(float(m[1]) * 1000)
        pins = tuple(int(m[k], 16) for k in [3, 4, 5])
        if not events or pins != events[-1][1]:
            events.append((t, pins, int(m[2]), line))
assert events
origin = events[0][0]
commands = []
last = origin
for t, (sp, di, ci), row, line in events:
    commands.append(f'    #{t-last} S=4\'h{sp:x}; DI=4\'h{di:x}; CI=1\'b{ci}; // row{row} original {t} ps')
    last = t
commands += ['    #3000;', '    check("recorded row914 settled");']
trace_body = '\n'.join(commands)
tb = '''`timescale 1ps/1ps
module tb_minimal_carry;
  reg [3:0] S=0, DI=0;
  reg CI=0, CYINIT=0;
  wire [3:0] CO, O;
  CARRY4 u(.S(S),.DI(DI),.CI(CI),.CYINIT(CYINIT),.CO(CO),.O(O));
  integer fail_count=0;
  integer cases=0;
  integer i;
  integer widths[0:7];
  reg[3:0] expect_co,expect_o;
  reg c;
  task check(input string label);
    begin
      c=CI|CYINIT;
      for(i=0;i<4;i=i+1)begin
        expect_o[i]=S[i]^c;
        expect_co[i]=S[i]?c:DI[i];
        c=expect_co[i];
      end
      cases=cases+1;
      if(CO!==expect_co || O!==expect_o)begin
        fail_count=fail_count+1;
        $display("ISOLATED_FAILURE %s T%0t S%h DI%h CI%b CYINIT%b CO%h O%h EXPECT_CO%h EXPECT_O%h",label,$time,S,DI,CI,CYINIT,CO,O,expect_co,expect_o);
      end else $display("ISOLATED_PASS %s T%0t",label,$time);
    end
  endtask
  always @(S or DI or CI or CYINIT or CO or O)
    $display("M T%0t S%h DI%h CI%b CYINIT%b CO%h O%h",$time,S,DI,CI,CYINIT,CO,O);
  initial begin
`ifndef OMIT_SDF
    $sdf_annotate("carry_original_paths.sdf");
`endif
    #2000; S=7; #2000; check("stable setup");
    widths[0]=0; widths[1]=1; widths[2]=5; widths[3]=25;
    widths[4]=50; widths[5]=100; widths[6]=300; widths[7]=1000;
    for(integer w=0;w<8;w=w+1)begin
      S=0; CI=0; DI=0; #2000; S=7; #2000;
      CI=1; #(widths[w]) CI=0;
      #3000; check($sformatf("CI pulse width %0d ps",widths[w]));
    end
    S=0; CI=0; DI=0; #2000;
TRACE_BODY
    $display("ISOLATION_COMPLETE cases=%0d failures=%0d",cases,fail_count);
    $finish;
  end
endmodule
'''.replace('TRACE_BODY', trace_body)
(P / 'tb_minimal_carry.sv').write_text(tb)
(P / 'run.tcl').write_text('run all\nquit\n')
binding_log = (previous / 'tool_3.log').read_text()
assert 'Compiling module work.CARRY4' in binding_log
assert 'SDF backannotation was successful' in binding_log
evidence = {
    'status': 'prepared_not_run',
    'library_binding': 'lut_diag_a2/tool_3.log explicitly compiles work.CARRY4',
    'vendor_source_unmodified': sha(vendor) == sha(P / 'CARRY4_vendor.v'),
    'mapped_pins': {'CYINIT': 0, 'DI': 0},
    'recorded_events': len(events),
    'recorded_span_ps': events[-1][0] - origin,
    'recorded_last_inputs': events[-1][1],
    'recorded_trace_limit': 'Printed timestamps preserve 1 ps values but not event-region ordering; #0 separates observed same-time pin changes.',
    'SDF_limit': 'Only the exact original CARRY4 cell paths are isolated; upstream/interconnect paths are represented by recorded pin inputs.',
    'source_sha256': {str(p.resolve()): sha(p) for p in [Path(__file__), sdf_source, vendor, previous/'tool_3.log', previous/'tool_4.log']},
    'prepared_sha256': {str(p.resolve()): sha(p) for p in [P/'CARRY4_vendor.v', P/'carry_original_paths.sdf', P/'tb_minimal_carry.sv', P/'run.tcl']},
}
(P / 'preparation.json').write_text(json.dumps(evidence, indent=2)+'\n')
print(json.dumps({k: v for k,v in evidence.items() if not k.endswith('sha256')},indent=2))
