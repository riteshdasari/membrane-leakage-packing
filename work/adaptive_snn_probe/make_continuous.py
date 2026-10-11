"""Generate the isolated THREE-ALWAYS trial; never run simulation or routing.

WHOLE sources are read-only templates. E5 keeps its existing full-range hybrid
arithmetic. E7 selects three bounded DSP lanes or two wide DSP lanes plus the
same LUT third lane; both always accept three available neurons.
"""
from pathlib import Path
import ast
import hashlib
import json

P = Path(__file__).resolve().parent
BASE = ['stream_pipeline_whole_leak.sv', 'tb_stream_pipeline_whole_leak.sv',
        'check_stream_pipeline_whole.py', 'check_stream_pipeline_whole_models.py',
        'stream_pipeline_whole_timing.sv', 'route_stream_pipeline_whole.tcl',
        'run_stream_pipeline_whole_route.py']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace(text, old, new, count=1):
    assert text.count(old) == count, ('Template changed', old, text.count(old))
    return text.replace(old, new)


def main():
    before = {name: sha(P / name) for name in BASE}
    assert before['stream_pipeline_whole_leak.sv'] == 'e78f42626f4739e0d62737c84db0ad134f8b2ecfa636d2b381104998241ec44d'
    outputs = {}

    core = (P / BASE[0]).read_text()
    core = core.replace('stream_pipeline_whole_leak', 'continuous_leak').replace('stream_pipeline_whole_dsp', 'continuous_dsp')
    core = replace(core, 'parameter E=0, DC=25', 'parameter E=7, DC=25')
    core = replace(core, 'E==0&&(coef<=25?fit7:fit6)', '(E==0||E==7)&&(coef<=25?fit7:fit6)')
    core = replace(core, 'wire always3=(E==3)||(E==4)||(E==5);', 'wire always3=(E==3)||(E==4)||(E==5)||(E==7);')
    core = replace(core, 'if(E==0||E==1||E==4||E==5||E==6)begin:dsp_path', 'if(E==0||E==1||E==4||E==5||E==6||E==7)begin:dsp_path')
    core = replace(core, 'if(E==5)begin:hybrid_lane', 'if(E==5||E==7)begin:hybrid_lane')
    original_registers = '''    always @(posedge clk)begin
     if(rst)begin m1<=0;r2<=0;end
     else if(enable)begin if(v0)m1<={u,quotient};if(v1)r2<=orig-quot;end
    end'''
    gated_registers = '''    // E7 suppresses only unused LUT-lane register writes. Combinational
    // quotient logic still exists; no power/toggle benefit is established.
    if(E==7)begin:adaptive_gate
     always @(posedge clk)begin
      if(rst)begin m1<=0;r2<=0;end
      else if(enable)begin
       if(v0&&!n0)m1<={u,quotient};
       if(v1&&!n1)r2<=orig-quot;
      end
     end
    end else begin:fixed_gate
''' + original_registers + '''
    end'''
    core = replace(core, original_registers, gated_registers)
    core = replace(core, '// E6 adaptive int6 triple. CW selects unsigned (0) or centered (1) wide lanes.',
                   '// E6 adaptive int6 triple; E7 always-three adaptive DSP/LUT placement.\n// CW selects unsigned (0) or centered (1) wide lanes; this trial instantiates CW0.')
    core = '// ISOLATED TRIAL: E5 unchanged hybrid; E7 THREE-ALWAYS membrane-aware\n// one-DSP routing: three narrow lanes, otherwise two wide lanes + LUT third.\n' + core
    outputs['continuous_leak.sv'] = core

    tb = (P / BASE[1]).read_text().replace('stream_pipeline_whole_leak', 'continuous_leak').replace('stream_driver', 'continuous_driver')
    monitor = ''' generate if(E==7)begin:gate_monitor
  reg[18:0]prior_m1;reg[10:0]prior_r2;
  reg m1_hold,r2_hold,saved_reset,m1_narrow,r2_narrow;
  integer m1_hold_checks=0,r2_hold_checks=0,m1_narrow_holds=0,r2_narrow_holds=0;
  // Sample CE/mode before NBA and compare state after NBA. Reset is exempt.
  always @(posedge clk)begin
   prior_m1=dut.dsp_path.adaptive_or_pair.hybrid_lane.m1;
   prior_r2=dut.dsp_path.adaptive_or_pair.hybrid_lane.r2;
   saved_reset=rst;
   m1_hold=!dut.enable||!dut.v0||dut.n0;
   r2_hold=!dut.enable||!dut.v1||dut.n1;
   m1_narrow=dut.enable&&dut.v0&&dut.n0;
   r2_narrow=dut.enable&&dut.v1&&dut.n1;
   #0.001;
   if(!saved_reset)begin
    if(m1_hold)begin
     m1_hold_checks=m1_hold_checks+1;
     if(dut.dsp_path.adaptive_or_pair.hybrid_lane.m1!==prior_m1)$fatal(1,"E7 LUT m1 changed while gated");
    end
    if(r2_hold)begin
     r2_hold_checks=r2_hold_checks+1;
     if(dut.dsp_path.adaptive_or_pair.hybrid_lane.r2!==prior_r2)$fatal(1,"E7 LUT r2 changed while gated");
    end
    if(m1_narrow)m1_narrow_holds=m1_narrow_holds+1;
    if(r2_narrow)r2_narrow_holds=r2_narrow_holds+1;
   end
  end
 end endgenerate
'''
    tb = replace(tb, 'endmodule\nmodule tb_continuous_leak;', monitor + 'endmodule\nmodule tb_continuous_leak;')
    start = tb.index(' wire[6:0]done;')
    tb = tb[:start] + ''' wire[1:0]done;
 continuous_driver #(.E(5))baseline(clk,done[0]);
 continuous_driver #(.E(7))adaptive(clk,done[1]);
 initial begin
  wait(&done);#0.01;
  $display("CONTINUOUS E7 GATE M1_HOLDS %0d R2_HOLDS %0d NARROW_M1 %0d NARROW_R2 %0d",
   adaptive.gate_monitor.m1_hold_checks,adaptive.gate_monitor.r2_hold_checks,
   adaptive.gate_monitor.m1_narrow_holds,adaptive.gate_monitor.r2_narrow_holds);
  $display("CONTINUOUS PASS");$finish;
 end
endmodule
'''
    outputs['tb_continuous_leak.sv'] = tb

    checker = (P / BASE[2]).read_text()
    checker = checker.replace('stream_pipeline_whole_leak', 'continuous_leak').replace('tb_stream_pipeline_whole_leak', 'tb_continuous_leak')
    checker = checker.replace('check_stream_pipeline_whole.py', 'check_continuous.py')
    checker = replace(checker, "'check_stream_pipeline.py', 'check_continuous.py']", "'check_stream_pipeline.py', 'check_continuous.py',\n                      'check_continuous_models.py', 'make_continuous.py']")
    checker = replace(checker, 'narrow = (e == 0 and (fit6 or (d <= 25 and fit7))) or (e == 6 and fit6)', 'assert e in (5,7)\n    narrow = e == 7 and (fit6 or (d <= 25 and fit7))')
    checker = replace(checker, 'take = 3 if n == 3 and (e in [3,4,5] or narrow or x[2] == 0) else min(2,n)', 'take = n')
    checker = checker.replace("tag.replace('stream_pipeline_whole','stream_pipeline',1)", "tag.replace('continuous','stream_pipeline_whole',1)")
    checker = checker.replace('matched_original_stimulus', 'matched_whole_stimulus').replace('Whole/default stimulus differs', 'Continuous/WHOLE stimulus differs')
    checker = replace(checker, "assert cw in (0,1), 'CW is unsigned(0) or centered(1) wide-residual encoding'", "assert cw == 0, 'This trial tests unsigned CW0 only'")
    checker = replace(checker, "assert 'STREAM PIPELINE WHOLE PASS' in z.stdout", "assert 'CONTINUOUS PASS' in z.stdout")
    checker = replace(checker, 'for e in range(7):', 'for e in (5,7):')
    checker = replace(checker, "assert row['narrow_requests'] == expected_narrow", '''assert row['narrow_requests'] == expected_narrow
        if e == 7:
            gates = re.search(r'CONTINUOUS E7 GATE M1_HOLDS (\\d+) R2_HOLDS (\\d+) NARROW_M1 (\\d+) NARROW_R2 (\\d+)',z.stdout)
            assert gates, z.stdout[-5000:]
            row.update(lut_m1_hold_checks=int(gates[1]),lut_r2_hold_checks=int(gates[2]),
                       lut_m1_narrow_holds=int(gates[3]),lut_r2_narrow_holds=int(gates[4]))
            assert row['lut_m1_hold_checks'] > 0 and row['lut_r2_hold_checks'] > 0
            if expected_narrow:
                assert row['lut_m1_narrow_holds'] > 0 and row['lut_r2_narrow_holds'] > 0''')
    checker = replace(checker, 'tested_engines=list(range(7))', 'tested_engines=[5,7]')
    checker = checker.replace("identity_policy='regular metadata; no third wide lane from identity alone'", "identity_policy='E5/E7 always consume three available neurons, including delta0 wide groups'")
    checker = checker.replace("assert cw in (0,1)", "assert cw == 0")
    checker = replace(checker, "prefix = 'stream_pipeline_whole_centered' if cw else 'stream_pipeline_whole'", "prefix = 'continuous'")
    checker = checker.replace('Independent integer oracle for whole unsigned products folded into DSP C.', 'Independent scalar ceiling oracle for E5 and THREE-ALWAYS adaptive E7.')
    checker = checker.replace('    # Encoded bypass keeps the regular pair/triple representation. Identity alone\n    # does not authorize a third wide membrane in engines with a pair fallback.', '    # Both engines consume the same three-output groups; only placement changes.')
    outputs['check_continuous.py'] = checker

    models = (P / BASE[3]).read_text().replace('from check_stream_pipeline_whole import simulate', 'from check_continuous import simulate')
    models = replace(models, 'assert cw in (0,1)', 'assert cw == 0')
    models = replace(models, "prefix = 'stream_pipeline_whole_centered' if cw else 'stream_pipeline_whole'", "prefix = 'continuous'")
    models = models.replace('STREAM PIPELINE WHOLE MODEL STATES/SPIKES PASS', 'CONTINUOUS MODEL STATES/SPIKES PASS')
    outputs['check_continuous_models.py'] = models

    fixture = (P / BASE[4]).read_text()
    fixture = fixture[:fixture.index('`PIPELINE_TIMING_TOP(top_')]
    fixture = fixture.replace('stream_pipeline_whole_timing', 'continuous_timing').replace('stream_pipeline_whole_leak', 'continuous_leak')
    fixture = replace(fixture, 'parameter E=0, DC=25', 'parameter E=7, DC=25')
    fixture = fixture.replace('PIPELINE_TIMING_TOP', 'CONTINUOUS_TIMING_TOP')
    fixture += '''`CONTINUOUS_TIMING_TOP(top_continuous_hybrid_const,5,25,0)
`CONTINUOUS_TIMING_TOP(top_continuous_hybrid_prog,5,-1,0)
`CONTINUOUS_TIMING_TOP(top_continuous_adaptive_const,7,25,0)
`CONTINUOUS_TIMING_TOP(top_continuous_adaptive_prog,7,-1,0)
`undef CONTINUOUS_TIMING_TOP
'''
    outputs['continuous_timing.sv'] = fixture

    tcl = (P / BASE[5]).read_text().replace('stream_pipeline_whole_leak.sv', 'continuous_leak.sv').replace('stream_pipeline_whole_timing.sv', 'continuous_timing.sv')
    tcl = replace(tcl, '^top_stream_pipeline_whole_[a-z0-9]+(_cw)?_(const|prog)$', '^top_continuous_(adaptive|hybrid)_(const|prog)$')
    tcl = replace(tcl, 'STREAM_PIPELINE_WHOLE_TIMING_ROUTED', 'CONTINUOUS_TIMING_ROUTED')
    outputs['route_continuous.tcl'] = tcl

    helper = (P / BASE[6]).read_text()
    helper = helper.replace('stream_pipeline_whole_leak.sv', 'continuous_leak.sv').replace('stream_pipeline_whole_timing.sv', 'continuous_timing.sv')
    helper = helper.replace('route_stream_pipeline_whole.tcl', 'route_continuous.tcl').replace('run_stream_pipeline_whole_route.py', 'run_continuous_route.py')
    helper = replace(helper, 'ENGINES = dict(adaptive=0, fixed2=1, lut2=2, lut3=3, fixed3=4, hybrid=5, adaptive6=6)', 'ENGINES = dict(adaptive=7, hybrid=5)')
    helper = replace(helper, "r'top_stream_pipeline_whole_([a-z0-9]+)(_cw)?_(const|prog)'", "r'top_continuous_(adaptive|hybrid)_(const|prog)'")
    helper = replace(helper, "prefix = 'stream_pipeline_whole'\n    stem = prefix + ('_centered_main' if match[2] else '_main')", "stem = 'continuous_main'")
    helper = replace(helper, "if match[3] == 'prog':", "if match[2] == 'prog':")
    helper = replace(helper, "checks = [stem + '_25_0_checks.json']", "checks = [stem + '_25_0_checks.json', 'continuous_models_checks.json', 'continuous_stress_checks.json']")
    helper = replace(helper, "assert data['frames'] > 0, name", "assert data['frames'] > 0 and data['acceptance_to_handshake_advances'] == 4, name\n        assert data['tested_engines'] == [5,7] and data['matched_whole_stimulus'] is True, name\n        assert hashlib.sha256((R/name.removesuffix('_checks.json')/'stream_stim.txt').read_bytes()).hexdigest() == data['stimulus_sha256'], name")
    helper = replace(helper, "assert row['mismatches'] == 0 and row['neurons'] > 0, (name, row)", "assert row['mismatches'] == 0 and row['neurons'] > 0, (name, row)\n        if name in ('continuous_models_checks.json','continuous_stress_checks.json'):\n            assert row['clocks'] == row['requests']+4, name\n        if name == 'continuous_models_checks.json':\n            assert row['state_mismatches'] == row['spike_mismatches'] == 0, name")
    helper = replace(helper, "ap.add_argument('--target', type=float, default=6.0)", "ap.add_argument('--target', type=float, default=None, help='Optional: must equal 6ns constant or 8ns programmed target.')")
    helper = replace(helper, 'assert args.target > 0 and args.min_free_gib >= 2.3', 'assert (args.target is None or args.target > 0) and args.min_free_gib >= 2.3')
    helper = replace(helper, 'for top in args.tops:\n        assert hashes()', "for top in args.tops:\n        target = 8.0 if top.endswith('_prog') else 6.0\n        assert args.target is None or args.target == target, ('Incorrect coefficient-cohort target',top,args.target)\n        assert hashes()")
    helper = helper.replace('target_ns=args.target', 'target_ns=target').replace('str(args.target)', 'str(target)').replace('parse_row(top, args.target,', 'parse_row(top, target,')
    helper = helper.replace('stream_pipeline_whole_hardware.json', 'continuous_hardware.json').replace('stream_pipeline_whole_tmp', 'continuous_tmp')
    outputs['run_continuous_route.py'] = helper

    for name, text in outputs.items():
        if name.endswith('.py'):
            ast.parse(text, filename=name)
        (P / name).write_text(text, newline='')
    assert {name: sha(P / name) for name in BASE} == before, 'Read-only templates changed'
    manifest = dict(scope='source generation only; no simulation/synthesis/route executed',
                    generator_sha256=sha(Path(__file__)), base_sha256=before,
                    generated_sha256={name: sha(P / name) for name in outputs},
                    engines={'5':'unchanged fixed DSP pair + LUT third',
                             '7':'actual-U narrow DSP triple; otherwise DSP pair + LUT third'},
                    coefficient_targets_ns={'constant25':6.0,'programmed':8.0},
                    limitations=['E7 register gating does not prove reduced combinational activity or power.',
                                 'No resource/timing/accuracy result exists until separate checks and routes pass.'])
    (P / 'results').mkdir(exist_ok=True)
    (P / 'results/continuous_generation.json').write_text(json.dumps(manifest, indent=2) + '\n', newline='')
    print('CONTINUOUS SOURCES GENERATED; NOT SIMULATED OR ROUTED', flush=True)
    for name in outputs:
        print(name, manifest['generated_sha256'][name], flush=True)


if __name__ == '__main__':
    main()
