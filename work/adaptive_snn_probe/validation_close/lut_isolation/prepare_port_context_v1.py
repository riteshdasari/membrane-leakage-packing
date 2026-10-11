"""Prepare one output-port shape control, retaining the frozen full replay.

No vendor process is launched. The third live-input CARRY4 differs from the
existing flat shadow only in the O connection's concatenated sliced-net shape.
It retains the same vendor source, input port events, CO wire, and twelve SDF
IOPATH records. This control can test sufficiency of this shape in this local
context; it cannot identify an exact simulator delta region or repair hardware.
"""
from pathlib import Path
import ast
import hashlib
import json
import sys

sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent
sys.path.insert(0, str(P))
import sdf_structure_audit_v1 as parser
from verify_eof_only_sdf_derivative_v1 import verify
W = P / 'port_context_v1'
PREVIOUS = P / 'shadow_context_v5'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    assert not W.exists(), 'Retain all preparations and runs'
    prep = json.loads((PREVIOUS / 'preparation.json').read_text())
    for key in ['source_sha256', 'prepared_sha256']:
        assert all(sha(path) == pin for path, pin in prep[key].items())
    verify(prep['original_SDF_structure_derivative']['certificate'])
    old_monitor = (PREVIOUS / 'monitor_shadow.sv').read_bytes().decode()
    assert old_monitor.endswith('endmodule\n')
    addition = r'''
 // One targeted control: live identical inputs, concatenated sliced-net O.
 wire alias_unused_o3;
 wire[19:0] alias_product;
 wire[3:0] alias_co;
 CARRY4 alias_shadow(.CI(dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CI),.CYINIT(dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CYINIT),
   .DI(dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .DI),.S(dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .S),
   .CO(alias_co),.O({alias_unused_o3,alias_product[19:17]}));
 wire[3:0] alias_o={alias_unused_o3,alias_product[19:17]};
 realtime alias_last=0;
 always @(alias_shadow.S_in or alias_shadow.DI_in or alias_shadow.CI_in or alias_shadow.CYINIT_in or alias_shadow.CO_fb)
   alias_last=$realtime;
 task automatic port_snapshot(input string label_name);
   reg[3:0] expected_o,expected_co;
   reg carry;
   begin
     carry=dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CI_in|dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CYINIT_in;
     for(integer bit_number=0;bit_number<4;bit_number=bit_number+1)begin
       expected_o[bit_number]=dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .S_in[bit_number]^carry;
       expected_co[bit_number]=dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .S_in[bit_number]?carry:dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .DI_in[bit_number];
       carry=expected_co[bit_number];
     end
     $display("PORT_CONTEXT_SNAPSHOT %s T%0.3f ROW%0d ORIG_AGE%0.3f FLAT_AGE%0.3f ALIAS_AGE%0.3f ORIG_S%h FLAT_S%h ALIAS_S%h ORIG_CI%b FLAT_CI%b ALIAS_CI%b ORIG_CY%b FLAT_CY%b ALIAS_CY%b ORIG_DI%h FLAT_DI%h ALIAS_DI%h ORIG_O%h FLAT_O%h ALIAS_O%h ORIG_CO%h FLAT_CO%h ALIAS_CO%h EXPECT_O%h EXPECT_CO%h",
       label_name,$realtime,n,$realtime-original_last,$realtime-shadow_last,$realtime-alias_last,
       dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .S_in,shadow.S_in,alias_shadow.S_in,
       dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CI_in,shadow.CI_in,alias_shadow.CI_in,
       dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CYINIT_in,shadow.CYINIT_in,alias_shadow.CYINIT_in,
       dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .DI_in,shadow.DI_in,alias_shadow.DI_in,
       dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .O,shadow.O,alias_shadow.O,
       dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CO,shadow.CO,alias_shadow.CO,
       expected_o,expected_co);
   end
 endtask
 initial begin
   #11100.500; port_snapshot("after_last_glitch");
   #0.500; port_snapshot("plus500ps");
   #4.999; port_snapshot("before_capture");
   #0.002; port_snapshot("after_capture");
   $display("PORT_CONTEXT_PROBE_SNAPSHOTS_COMPLETE");
 end
 always @(posedge rc)if(n>=913&&n<=915)begin
   #0.001; port_snapshot("capture_edge_plus1ps");
 end
'''
    monitor = old_monitor[:-len('endmodule\n')] + addition + '\nendmodule\n'
    assert monitor.replace(addition + '\n', '', 1) == old_monitor
    assert '$sdf_annotate' not in monitor
    assert 'if(got!==expected[slot])' in monitor
    sdf = (PREVIOUS / 'original_and_shadow_full.sdf').read_bytes().decode()
    roots, opened, _ = parser.parse(sdf)
    assert len(roots) == 1 and not opened
    cells = roots[0].direct('CELL')
    assert len(cells) == 556
    flat, = [c for c in cells if parser.instance(c, sdf)[0] == 'shadow']
    _, instance = parser.instance(flat, sdf)
    added_cell = sdf[flat.start:instance.start] + '(INSTANCE alias_shadow)' + sdf[instance.end:flat.end]
    # Appending inside the existing DELAYFILE leaves all 556 CELL byte strings
    # unchanged, including every original INTERCONNECT endpoint and timing check.
    close = roots[0].end - 1
    assert sdf[close] == ')'
    combined = sdf[:close] + added_cell + '\n' + sdf[close:]
    new_roots, opened, _ = parser.parse(combined)
    assert not opened and len(new_roots) == 1
    new_cells = new_roots[0].direct('CELL')
    assert len(new_cells) == 557
    assert all(sdf[a.start:a.end] == combined[b.start:b.end] for a, b in zip(cells, new_cells))
    assert parser.instance(new_cells[-1], combined)[0] == 'alias_shadow'
    W.mkdir()
    (W / 'monitor_shadow.sv').write_bytes(monitor.encode())
    (W / 'original_and_shadow_full.sdf').write_bytes(combined.encode())
    for name in ['CARRY4_vendor.v', 'run.tcl']:
        (W / name).write_bytes((PREVIOUS / name).read_bytes())
    runner = P / 'run_port_context_v1.py'
    ast.parse(runner.read_text())
    result = dict(status='prepared_single_output_port_shape_control_not_run',
                  vendor_tools_launched=False, diagnostic_only=True,
                  original_SDF_structure_derivative=prep['original_SDF_structure_derivative'],
                  previous_combined_cells=556, combined_cells=557,
                  every_previous_CELL_byte_identical=True, known_row_comparator_unchanged=True,
                  full_trace_rows=prep['full_trace_rows'], valid_rows=prep['valid_rows'],
                  duration_ns=prep['duration_ns'], trace=prep['trace'],
                  targeted_difference='Flat shadow O wire versus same live-input shadow O concatenation {unusedbit,sliced_net[19:17]}; inputs, CO, vendor source and twelve IOPATHs are identical.',
                  source_sha256={**prep['source_sha256'], **prep['prepared_sha256'],
                     **{str(p.resolve()):sha(p) for p in [Path(__file__), runner, PREVIOUS/'preparation.json']}},
                  prepared_sha256={str(p.resolve()):sha(p) for p in W.glob('*.*')},
                  caveats=['Source preparation is not successful vendor elaboration or timing replay.',
                    'Added monitoring may change context; the original row914 failure and flat-shadow correctness must both reproduce before interpreting this control.',
                    'The concatenation is a local sufficiency test, not a reproduction of all original net topology.',
                    'Observers are not an exact simulator region or delta trace.',
                    'No passing shadow substitutes for the failed original full replay or authorizes hardware/energy acceptance.'])
    (W / 'preparation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['source_sha256','prepared_sha256']}, indent=2))


if __name__ == '__main__':
    main()
