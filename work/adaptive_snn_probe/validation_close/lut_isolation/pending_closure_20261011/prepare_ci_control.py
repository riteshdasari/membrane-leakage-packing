"""Add a bounded carry-input pulse intervention to an immutable diagnostic copy."""
from pathlib import Path
import hashlib, json
P = Path(__file__).resolve().parent
old = P.parent / 'shadow_context_v5'
new = P / 'ci_control_prepared'
assert not new.exists(), 'Retain previous attempts'
new.mkdir()
for name in ['CARRY4_vendor.v','original_and_shadow_full.sdf','run.tcl']:
    (new/name).write_bytes((old/name).read_bytes())
bench = (old/'monitor_shadow.sv').read_text()
assert bench.count('endmodule') == 1
intervention = r'''
 // Bounded causal intervention only. This is never hardware/energy evidence.
 initial begin
   if($test$plusargs("MASK_CI"))begin
     #11098.000;
     $display("CI_INTERVENTION_BEGIN T%0.3f PRE_CI%b",$realtime,dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CI);
     force dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CI=1'b0;
     #9.000;
     release dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CI;
     $display("CI_INTERVENTION_END T%0.3f CI%b",$realtime,dut.fixture.core.\lut.lane[0].r_reg[11]_i_4 .CI);
   end
 end
'''
(new/'monitor_shadow.sv').write_text(bench.replace('endmodule',intervention+'\nendmodule'))
prep = json.loads((old/'preparation.json').read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
prep['prepared_sha256'] |= {str(p.resolve()):sha(p) for p in new.iterdir() if p.is_file()}
prep['source_sha256'][str(Path(__file__).resolve())]=sha(Path(__file__))
prep['new_bench_preserves_original_prefix_except_final_endmodule']=True
(new/'preparation.json').write_text(json.dumps(prep,indent=2)+'\n')
source=(P/'run_optimization_control.py').read_text()
assert source.count("prepared = ISO / 'shadow_context_v5'")==1
source=source.replace("prepared = ISO / 'shadow_context_v5'","prepared = P / 'ci_control_prepared'")
source=source.replace("ap.add_argument('--o0', action='store_true')","ap.add_argument('--o0', action='store_true')\n    ap.add_argument('--mask-ci', action='store_true')")
source=source.replace("wd = P / ('run_o0_' if a.o0 else 'run_default_') / a.attempt","wd = P / ('run_ci_mask_' if a.mask_ci else 'run_ci_unmasked_') / a.attempt")
source=source.replace("if a.o0:\n        cmds[3].insert(1, '--O0')","if a.o0:\n        cmds[3].insert(1, '--O0')\n    if a.mask_ci:\n        cmds[4].extend(['-testplusarg','MASK_CI'])")
source=source.replace("'disable_simulator_optimizations': a.o0, 'commands': cmds,","'disable_simulator_optimizations': a.o0, 'mask_ci': a.mask_ci, 'commands': cmds,")
(P/'run_ci_control.py').write_text(source)
print(json.dumps({'status':'prepared_only','prefix_preserved':True,'original_frozen':True,'force_window_ns':[11098,11107]},indent=2))
