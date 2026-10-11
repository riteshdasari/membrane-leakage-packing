"""Append observation-only probes to the original full16 energy bench."""
from pathlib import Path
import hashlib, json, sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
W=P.parent.parent/'width16'
sys.path.insert(0,str(W));sys.path.insert(0,str(P.parent))
import certify_energy_export
import sdf_structure_audit_v1 as sdf


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    out=P/'signed16_probe_prepared'
    assert not out.exists()
    raw=W/'hardware/export_raw12_ottt_e2_ottt_stress_a0_e2'
    export=W/'hardware/export12_ottt_e2_ottt_stress_a0_e2'
    certified=certify_energy_export.verify(export)
    assert certified['status']=='pass_exact_derived_export_reproduction'
    vendor=P.parent/'CARRY4_vendor.v'
    installed=Path('C:/AMDDesignTools/2025.2/data/verilog/src/unisims/CARRY4.v')
    assert vendor.read_bytes()==installed.read_bytes()
    bench=W/'tb_energy16_12.sv'
    original=bench.read_bytes().decode()
    ending='endmodule\r\n' if original.endswith('endmodule\r\n') else 'endmodule\n'
    assert original.endswith(ending) and original.count('endmodule')==1
    addition=r'''
 // Observation only. Original DUT, SDF, comparison and complete input stream
 // remain unchanged; no force/release, altered clock or acceptance bypass.
 wire[3:0] probe_s=dut.fixture.core.\lut.lane[0].r_reg[15]_i_4 .S;
 wire[3:0] probe_di=dut.fixture.core.\lut.lane[0].r_reg[15]_i_4 .DI;
 wire probe_ci=dut.fixture.core.\lut.lane[0].r_reg[15]_i_4 .CI;
 wire probe_cy=dut.fixture.core.\lut.lane[0].r_reg[15]_i_4 .CYINIT;
 wire[3:0] probe_si=dut.fixture.core.\lut.lane[0].r_reg[15]_i_4 .S_in;
 wire[3:0] probe_dii=dut.fixture.core.\lut.lane[0].r_reg[15]_i_4 .DI_in;
 wire probe_cii=dut.fixture.core.\lut.lane[0].r_reg[15]_i_4 .CI_in;
 wire probe_cyi=dut.fixture.core.\lut.lane[0].r_reg[15]_i_4 .CYINIT_in;
 wire[3:0] probe_co=dut.fixture.core.\lut.lane[0].r_reg[15]_i_4 .CO;
 wire[3:0] probe_fb=dut.fixture.core.\lut.lane[0].r_reg[15]_i_4 .CO_fb;
 wire[3:0] probe_o=dut.fixture.core.\lut.lane[0].r_reg[15]_i_4 .O;
 wire[2:0] probe_parent_o=dut.fixture.core.p_0_in[23:21];
 wire probe_upstream_ci=dut.fixture.core.\lut.lane[0].r_reg[12]_i_2_n_0 ;
 wire probe_d14=dut.fixture.core.\lut.lane[0].r_reg[14] .D;
 wire probe_q14=dut.fixture.core.\lut.lane[0].r_reg[14] .Q;
 wire probe_c14=dut.fixture.core.\lut.lane[0].r_reg[14] .C;
 wire probe_ce14=dut.fixture.core.\lut.lane[0].r_reg[14] .CE;
 realtime probe_last_input=0;
 always @(probe_si or probe_dii or probe_cii or probe_cyi or probe_fb)
   probe_last_input=$realtime;
 task automatic probe_snapshot(input string label_name);
   reg[3:0] expected_o,expected_co;
   reg carry;
   begin
     carry=probe_cii|probe_cyi;
     for(integer k=0;k<4;k=k+1)begin
       expected_o[k]=probe_si[k]^carry;
       expected_co[k]=probe_si[k]?carry:probe_dii[k];
       carry=expected_co[k];
     end
     $display("FIXED16_SNAPSHOT %s T%0.3f ROW%0d AGE%0.3f S%h DI%h CI%b CY%b SI%h DII%h CII%b CYI%b CO%h FB%h O%h PARENT_O%h UPSTREAM_CI%b EXPECT_O%h EXPECT_CO%h D14%b Q14%b CLK%b CE%b",
       label_name,$realtime,n,$realtime-probe_last_input,probe_s,probe_di,probe_ci,probe_cy,
       probe_si,probe_dii,probe_cii,probe_cyi,probe_co,probe_fb,probe_o,probe_parent_o,
       probe_upstream_ci,expected_o,expected_co,probe_d14,probe_q14,probe_c14,probe_ce14);
   end
 endtask
 task automatic probe_event(input string signal_name,input integer bit_number,input reg value);
   if(n>=2172&&n<=2177)
     $display("FIXED16_EVENT T%0.3f ROW%0d SIGNAL%s BIT%0d VALUE%b",$realtime,n,signal_name,bit_number,value);
 endtask
 always @(probe_ci)probe_event("CI_port",0,probe_ci);
 always @(probe_cii)probe_event("CI_in",0,probe_cii);
 always @(probe_upstream_ci)probe_event("CI_upstream",0,probe_upstream_ci);
 always @(probe_cy)probe_event("CY_port",0,probe_cy);
 always @(probe_d14)probe_event("D14",0,probe_d14);
 always @(probe_q14)probe_event("Q14",0,probe_q14);
 generate for(genvar k=0;k<4;k=k+1)begin:probe_bits
   always @(probe_s[k])probe_event("S_port",k,probe_s[k]);
   always @(probe_si[k])probe_event("S_in",k,probe_si[k]);
   always @(probe_di[k])probe_event("DI_port",k,probe_di[k]);
   always @(probe_dii[k])probe_event("DI_in",k,probe_dii[k]);
   always @(probe_co[k])probe_event("CO",k,probe_co[k]);
   always @(probe_fb[k])probe_event("CO_fb",k,probe_fb[k]);
   always @(probe_o[k])probe_event("O",k,probe_o[k]);
 end endgenerate
 // Fixed known-row window includes settled inputs immediately before each
 // potential affected core capture and the first retained mismatch at2175.
 always @(posedge probe_c14)if(n>=2172&&n<=2177)begin
   #0.001;probe_snapshot("capture_plus1ps");
   #0.999;probe_snapshot("capture_plus1ns");
 end
 always @(negedge probe_c14)if(n>=2172&&n<=2177)begin
   #0.001;probe_snapshot("halfcycle_plus1ps");
 end
 initial begin
   #26208.000;probe_snapshot("window_begin");
   #29.999;probe_snapshot("before26238_capture");
   #0.002;probe_snapshot("after26238_capture");
   #11.998;probe_snapshot("before26250_capture");
   #0.002;probe_snapshot("after26250_capture");
   $display("FIXED16_PROBE_WINDOW_COMPLETE");
 end
'''
    # Exact byte prefix except the final endmodule. Source provenance also
    # certifies that no functional/testbench comparison text was altered.
    monitor=original[:-len(ending)]+addition+'\n'+ending
    assert monitor.replace(addition+'\n','',1)==original
    assert not any(token in addition for token in ['force ', 'release ', '$sdf_annotate', '$finish', '$fatal'])
    exported=(export/'routed.v').read_text()
    assert '.O({\\NLW_lut.lane[0].r_reg[15]_i_4_O_UNCONNECTED [3],p_0_in[23:21]})' in exported
    assert '.I2(p_0_in[22])' in exported
    record,_,_,_=sdf.describe(export/'routed.sdf')
    assert record['strict_structurally_balanced'] and record['direct_root_cell_count']==704
    out.mkdir()
    (out/'monitor.sv').write_bytes(monitor.encode())
    (out/'CARRY4_vendor.v').write_bytes(vendor.read_bytes())
    # Bounded duration does not shorten/rewrite the native full trace or weaken
    # its original fatal comparison. No SAIF collection is requested.
    (out/'run.tcl').write_text('run 26271 ns\nquit\n')
    sources=[Path(__file__),P/'run_signed16_probe.py',bench,vendor,installed,
      export/'routed.v',export/'routed.sdf',export/'provenance.json',export/'artifacts.json',
      export/'sdf_structure_certificate.json',export/'export_binding_certificate.json',
      raw/'routed.v',raw/'routed.sdf',W/'hardware/native_actual128_s0_a0/trace2.txt',
      W/'hardware/route12_e2_a1/hardware.json',W/'hardware/route12_e2_a1/design.dcp',
      P.parent/'sdf_structure_audit_v1.py',P.parent/'verify_eof_only_sdf_derivative_v1.py',
      W/'certify_energy_export.py']
    prep=dict(status='prepared_observation_only_signed16_probe_not_run',diagnostic_only=True,
      original_tb_prefix_and_all_comparisons_byte_preserved=True,original_export_and_SDF_unchanged=True,
      certified_export=certified,trace=str(sources[13].resolve()),full_trace_rows=7340,
      bounded_run_ns=26271,expected_first_retained_failure_row=2175,target_cell='dut.fixture.core.\\lut.lane[0].r_reg[15]_i_4 ',
      target_data_bit=14,cell_O_bit=1,parent_data_path='p_0_in[22] -> r[14]_i_1 -> r_reg[14].D',
      source_sha256={str(p.resolve()):sha(p) for p in sources},
      prepared_sha256={str(p.resolve()):sha(p) for p in out.iterdir() if p.is_file()},
      vendor_jobs_launched=False,hardware_energy_acceptance=False,
      event_limit='Observer order is not a simulator region/delta trace. Compare settled pin/internal/parent truth before assigning cause.')
    (out/'preparation.json').write_text(json.dumps(prep,indent=2)+'\n')
    print(json.dumps({k:v for k,v in prep.items() if k not in ['source_sha256','prepared_sha256','certified_export']},indent=2))


if __name__=='__main__':main()
