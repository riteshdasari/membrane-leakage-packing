"""Prepare one in-situ causal CARRY4 probe. No vendor tool is launched."""
import hashlib
import json
import re
import shutil
from pathlib import Path

P = Path(__file__).resolve().parent
V = Path('C:/AMDDesignTools/2025.2/Vivado')
S = P.parent.parent / 'sequential_paper_trial'
W = P / 'shadow_context_v1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not W.exists(), 'Keep preparations immutable; use a new version.'
    W.mkdir()
    vendor = V / 'data/verilog/src/unisims/CARRY4.v'
    rv = S / 'hardware/export12_e2_a0/routed.v'
    sdf = S / 'hardware/export12_e2_a0/routed.sdf'
    trace = S / 'hardware/native_actual_s0_a3/trace2.txt'
    frozen = json.loads((P / 'internal_a0/provenance.json').read_text())
    for path in [rv, sdf, trace]:
        assert frozen[str(path.resolve())] == sha(path)
    shutil.copyfile(vendor, W / 'CARRY4_vendor.v')
    assert sha(vendor) == sha(P / 'CARRY4_vendor.v') == sha(W / 'CARRY4_vendor.v')
    isolated = (P / 'carry_original_paths.sdf').read_text()
    start = isolated.index('(CELL ')
    depth = 0
    for end in range(start, len(isolated)):
        depth += (isolated[end] == '(') - (isolated[end] == ')')
        if depth == 0:
            cell = isolated[start:end + 1]
            break
    paths = re.findall(r'\(IOPATH\s+([^\s]+)\s+([^\s]+)\s+\(([^)]+)\)\s+\(([^)]+)\)\)', cell)
    assert len(paths) == 12
    assert max(float(value) for path in paths for triple in path[2:] for value in triple.split(':')) == 579
    shadow_sdf = ('(DELAYFILE\n (SDFVERSION "3.0")\n (DESIGN "tb_sequential_energy_replay")\n'
                  ' (DIVIDER /)\n (TIMESCALE 1 ps)\n'
                  + cell.replace('(INSTANCE u)', '(INSTANCE shadow)') + '\n'
                  + cell.replace('(INSTANCE u)', '(INSTANCE canary)') + '\n)\n')
    (W / 'shadow_paths.sdf').write_text(shadow_sdf)
    target = r'dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 '
    baseline = (P / 'internal_a0/monitor.sv').read_text()
    assert baseline.count('endmodule') == 1
    probes = r'''
 // Diagnostic addition only: the routed DUT, replay and original model are unchanged.
 // Direct hierarchical port connections retain the live waveform, without
 // reconstructing same-timestamp #0 ordering from the earlier text dump.
 wire[3:0] shadow_co,shadow_o;
 CARRY4 shadow(.CI(TARGET.CI),.CYINIT(TARGET.CYINIT),
   .DI(TARGET.DI),.S(TARGET.S),.CO(shadow_co),.O(shadow_o));
 reg[3:0] canary_s=0;
 wire[3:0] canary_co,canary_o;
 CARRY4 canary(.CI(1'b0),.CYINIT(1'b0),.DI(4'b0),.S(canary_s),
   .CO(canary_co),.O(canary_o));
 initial $sdf_annotate("shadow_paths.sdf");
 initial begin
   #200.000; canary_s=1;
   #0.200;
   if(canary_o[0]!==1'b0)$fatal(1,"CAUSAL_CANARY_FAIL before228ps O%h",canary_o);
   #0.040;
   if(canary_o[0]!==1'b1)$fatal(1,"CAUSAL_CANARY_FAIL after228ps O%h",canary_o);
   $display("CAUSAL_CANARY_PASS S0_TO_O0_MAX228PS checks2");
 end
 integer observed_event_sequence=0;
 realtime original_last=0,shadow_last=0;
 task automatic event_line(input string scope_name,input string signal_name,
                           input integer bit_index,input reg value);
   if($realtime>=11098.000 && $realtime<=11106.100)begin
     observed_event_sequence=observed_event_sequence+1;
     $display("CAUSAL_EVENT SEQ%0d T%0.3f ROW%0d SCOPE%s SIGNAL%s BIT%0d VALUE%b",
       observed_event_sequence,$realtime,n,scope_name,signal_name,bit_index,value);
   end
 endtask
 always @(TARGET.S_in or TARGET.DI_in or TARGET.CI_in or TARGET.CYINIT_in or TARGET.CO_fb)
   original_last=$realtime;
 always @(shadow.S_in or shadow.DI_in or shadow.CI_in or shadow.CYINIT_in or shadow.CO_fb)
   shadow_last=$realtime;
 always @(TARGET.CI)event_line("original","CI_port",0,TARGET.CI);
 always @(TARGET.CYINIT)event_line("original","CYINIT_port",0,TARGET.CYINIT);
 always @(TARGET.CI_in)event_line("original","CI_in",0,TARGET.CI_in);
 always @(shadow.CI)event_line("shadow","CI_port",0,shadow.CI);
 always @(shadow.CYINIT)event_line("shadow","CYINIT_port",0,shadow.CYINIT);
 always @(shadow.CI_in)event_line("shadow","CI_in",0,shadow.CI_in);
 generate for(genvar bit_number=0;bit_number<4;bit_number=bit_number+1)begin:causal_bits
   always @(TARGET.S[bit_number])event_line("original","S_port",bit_number,TARGET.S[bit_number]);
   always @(TARGET.S_in[bit_number])event_line("original","S_in",bit_number,TARGET.S_in[bit_number]);
   always @(TARGET.DI[bit_number])event_line("original","DI_port",bit_number,TARGET.DI[bit_number]);
   always @(TARGET.CO[bit_number])event_line("original","CO",bit_number,TARGET.CO[bit_number]);
   always @(TARGET.CO_fb[bit_number])event_line("original","CO_fb",bit_number,TARGET.CO_fb[bit_number]);
   always @(TARGET.O[bit_number])event_line("original","O",bit_number,TARGET.O[bit_number]);
   always @(shadow.S[bit_number])event_line("shadow","S_port",bit_number,shadow.S[bit_number]);
   always @(shadow.S_in[bit_number])event_line("shadow","S_in",bit_number,shadow.S_in[bit_number]);
   always @(shadow.DI[bit_number])event_line("shadow","DI_port",bit_number,shadow.DI[bit_number]);
   always @(shadow.CO[bit_number])event_line("shadow","CO",bit_number,shadow.CO[bit_number]);
   always @(shadow.CO_fb[bit_number])event_line("shadow","CO_fb",bit_number,shadow.CO_fb[bit_number]);
   always @(shadow.O[bit_number])event_line("shadow","O",bit_number,shadow.O[bit_number]);
 end endgenerate
 task automatic snapshot(input string label_name);
   reg[3:0] expected_o,expected_co;
   reg carry;
   begin
     carry=TARGET.CI_in|TARGET.CYINIT_in;
     for(integer bit_number=0;bit_number<4;bit_number=bit_number+1)begin
       expected_o[bit_number]=TARGET.S_in[bit_number]^carry;
       expected_co[bit_number]=TARGET.S_in[bit_number]?carry:TARGET.DI_in[bit_number];
       carry=expected_co[bit_number];
     end
     $display("CAUSAL_SNAPSHOT %s T%0.3f ROW%0d ORIG_AGE%0.3f SHADOW_AGE%0.3f ORIG_S%h SHADOW_S%h ORIG_CI%b SHADOW_CI%b ORIG_DI%h SHADOW_DI%h ORIG_CO%h SHADOW_CO%h ORIG_FB%h SHADOW_FB%h ORIG_O%h SHADOW_O%h EXPECT_O%h EXPECT_CO%h D%b Q%b",
       label_name,$realtime,n,$realtime-original_last,$realtime-shadow_last,
       TARGET.S_in,shadow.S_in,TARGET.CI_in,shadow.CI_in,TARGET.DI_in,shadow.DI_in,
       TARGET.CO,shadow.CO,TARGET.CO_fb,shadow.CO_fb,TARGET.O,shadow.O,
       expected_o,expected_co,rd,rq);
   end
 endtask
 initial begin
   #11100.500; snapshot("after_last_glitch");
   #0.500; snapshot("plus500ps");
   #4.999; snapshot("before_capture");
   #0.002; snapshot("after_capture");
   $display("CAUSAL_PROBE_SNAPSHOTS_COMPLETE");
 end
 always @(posedge rc)if(n>=913&&n<=915)begin
   #0.001; snapshot("capture_edge_plus1ps");
 end
'''.replace('TARGET.', target + '.')
    (W / 'monitor_shadow.sv').write_text(baseline.replace('endmodule', probes + '\nendmodule'))
    (W / 'run.tcl').write_text('run 12000 ns\nquit\n')
    sources = [Path(__file__), vendor, rv, sdf, trace, P / 'carry_original_paths.sdf',
               P / 'internal_a0/monitor.sv', P / 'internal_a0/tool_3.log', P / 'internal_a0/tool_4.log',
               V / 'data/verilog/src/glbl.v', P.parent.parent / 'selective_energy_trial/run_selective_energy.py']
    generated = [W / 'CARRY4_vendor.v', W / 'monitor_shadow.sv', W / 'shadow_paths.sdf', W / 'run.tcl']
    result = {'status': 'prepared_not_run', 'diagnostic_only': True,
              'vendor_tools_launched': False, 'original_netlist_or_SDF_modified': False,
              'vendor_CARRY4_modified': False, 'timing_checks_disabled': False,
              'same_live_input_ports': True, 'maxdelay_ps': 579,
              'shadow_IOPATH_count': 12, 'canary_IOPATH_count': 12,
              'positive_timing_gate': 'S0_to_O0 unchanged at200ps, changed at240ps for original max228ps',
              'source_sha256': {str(path.resolve()): sha(path) for path in sources},
              'prepared_sha256': {str(path.resolve()): sha(path) for path in generated},
              'cautions': ['Passive per-bit print sequence is observer order, not an exact event-region dump.',
                           'Shadow hierarchical port connection can differ in aliasing or delta context.',
                           'Original row914 failure must reproduce before causal interpretation.',
                           'A changed outcome cannot be accepted as an original hardware fix.']}
    (W / 'preparation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if not k.endswith('sha256')}, indent=2))


if __name__ == '__main__':
    main()
