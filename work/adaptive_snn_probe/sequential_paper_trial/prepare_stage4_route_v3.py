"""Apply one common replay-matched fixture contract, reusing unchanged completed synthesis."""
from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent
tcl=(P/'route.tcl').read_text().replace('set_input_delay -clock clk -max 1.0','set_input_delay -clock clk -max 3.0').replace('set_input_delay -clock clk -min 0.1','set_input_delay -clock clk -min 3.0')
runner=(P/'run_stage4_route.py').read_text().replace('import hashlib,json,math,sys,time','import hashlib,json,math,sys,time,shutil')
runner=runner.replace("f'route_e{e}_a0'","f'route_e{e}_a2'").replace("P/'route.tcl'","P/'route_replay_phase3.tcl'")
runner=runner.replace("P/'stage4_native_acceptance_v4.json',ROOT/","P/'stage4_native_acceptance_v4.json',P/'stage4_route_v3_preparation.json',P/'route_replay_phase3.tcl',ROOT/")
runner=runner.replace("prep=read(P/'stage4_source_preparation.json');verify(prep['source_sha256'])","prep=read(P/'stage4_source_preparation.json');verify(prep['source_sha256']);verify(read(P/'stage4_route_v3_preparation.json')['source_sha256'])")
needle="    top=f'top_sequential_leak_e{e}'\n"
replacement=needle+'''    original=P/'hardware'/f'route_e{e}_a0'
    reused=(original/'synth/design.dcp').exists()and(original/'synth/provenance.txt').exists()
    if reused:
        original_sources=read(original/'source_provenance.json');verify(original_sources)
        for path in (P/'leak_core.sv',P/'leak_dsp.sv',P/'timing.sv'):
            assert original_sources[str(path)]==sha(path)
        origin=pins([original/'synth/design.dcp',original/'synth/provenance.txt',original/'source_provenance.json'])
        stamps.update(origin);write(wd/'checkpoint_origin.json',dict(status='completed_synthesis_reused',original_source_sha256=original_sources,original_artifact_sha256=origin,arithmetic_unchanged=True,fixture_constraints_reapplied_before_placement=True))
        stamps.update(pins([wd/'checkpoint_origin.json']))
'''
assert runner.count(needle)==1;runner=runner.replace(needle,replacement)
needle="    write(wd/'source_provenance.json',stamps)\n"
replacement=needle+'''    if reused:
        (wd/'synth').mkdir();shutil.copyfile(original/'synth/design.dcp',wd/'synth/design.dcp')
        (wd/'synth/provenance.txt').write_text(provenance+'\\n')
'''
runner=runner.replace(needle,replacement)
runner=runner.replace("provenance,'fresh',wd]","provenance,'resume'if reused else'fresh',wd]")
runner=runner.replace("latency_advancing_edges=2,part=","latency_advancing_edges=2,external_input_phase_ns=3.0,reused_completed_synthesis=reused,part=")
runner=runner.replace("'stage4_route_progress.json'","'stage4_route_progress_v3.json'").replace("'stage4_route_acceptance.json',state|","'stage4_route_acceptance_v3.json',state|")
# Reapply the changed phase even when opening a predecessor synthesis checkpoint.
needle='opt_design\n'
phase='''set replay_inputs [get_ports -filter {DIRECTION == IN && NAME != clk}]
set_input_delay -clock clk -max 3.0 $replay_inputs
set_input_delay -clock clk -min 3.0 $replay_inputs
set_output_delay -clock clk -max 1.0 [all_outputs]
set_output_delay -clock clk -min 0.1 [all_outputs]
opt_design
'''
assert tcl.count(needle)==1;tcl=tcl.replace(needle,phase)
for n,s in(('route_replay_phase3.tcl',tcl),('run_stage4_route_v3.py',runner)):
    p=P/n;assert not p.exists();p.write_text(s,encoding='utf-8',newline='\n')
paths=[P/n for n in ('prepare_stage4_route_v3.py','route_replay_phase3.tcl','run_stage4_route_v3.py','stage4_route_a0_superseded.json')]
p=P/'stage4_route_v3_preparation.json';assert not p.exists();p.write_text(json.dumps(dict(status='prepared',external_input_phase_ns=3.0,reason='Matched falling-edge input phase for all six registered OOC fixtures. Original failed/superseded files retained. Completed synthesis may be reused with exact source and checkpoint pins; placement and routing repeated.',source_sha256={str(x):hashlib.sha256(x.read_bytes()).hexdigest()for x in paths}),indent=2)+'\n')
