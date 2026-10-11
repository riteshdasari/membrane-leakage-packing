"""Matched fixture timing repair: external stimulus changes at falling edge, +3 ns."""
from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent
old=(P/'route.tcl').read_text();start=old.index('set pre $trialout/synth');end=old.index('opt_design',start)
replacement='''# The synthesis checkpoint is unchanged; provenance and SHA are verified by runner.
set checkpoint [lindex $argv 5]
if {$checkpoint eq ""} {error "Missing pinned original synthesis checkpoint"}
open_checkpoint $checkpoint
if {[get_property PART [current_design]] ne "xc7a100tcsg324-1"} {error "Part mismatch"}
set ip [get_ports -filter {DIRECTION == IN && NAME != clk}]
# Exact declared external replay phase: falling edge, +3 ns from prior rising edge.
# This is a fixture integration contract, not an arbitrary board input budget.
set_input_delay -clock clk -max 3.0 $ip
set_input_delay -clock clk -min 3.0 $ip
set_output_delay -clock clk -max 1.0 [all_outputs]
set_output_delay -clock clk -min 0.1 [all_outputs]
'''
tcl=(old[:start]+replacement+old[end:]).replace('set_input_delay -clock clk -max 1.0 $inputs','set_input_delay -clock clk -max 3.0 $inputs').replace('set_input_delay -clock clk -min 0.1 $inputs','set_input_delay -clock clk -min 3.0 $inputs')
runner=(P/'run_stage4_route.py').read_text()
runner=runner.replace("f'route_e{e}_a0'","f'route_e{e}_a1'").replace("P/'route.tcl'","P/'route_phase3.tcl'")
runner=runner.replace("return prep['source_sha256']|pins(","return prep['source_sha256']|origins()|pins(")
pos=runner.index('def tool(')
runner=runner[:pos]+'''def origins():
    d=read(P/'stage4_route_acceptance.json');verify(d['artifact_sha256'])
    assert len(d['rows'])==6 and not d['failures']
    paths=[P/'stage4_route_acceptance.json',P/'stage4_phase3_preparation.json',P/'route_phase3.tcl']
    verify(read(P/'stage4_phase3_preparation.json')['source_sha256'])
    for name in d['rows']:
        p=Path(name);hw=read(p);verify(hw['source_sha256']);verify(hw['artifact_sha256'])
        paths.extend([p,p.parent/'synth/design.dcp',p.parent/'synth/provenance.txt'])
    return pins(paths)
'''+runner[pos:]
runner=runner.replace("'fresh',wd]","'fresh',wd,P/'hardware'/f'route_e{e}_a0/synth/design.dcp']")
runner=runner.replace("for folder in(wd,wd/'synth')","for folder in(wd,)")
runner=runner.replace("'stage4_route_progress.json'","'stage4_route_progress_v2.json'").replace("'stage4_route_acceptance.json',state|","'stage4_route_acceptance_v2.json',state|")
runner=runner.replace("latency_advancing_edges=2,part=","latency_advancing_edges=2,external_input_phase_ns=3.0,original_synthesis_checkpoint=str(P/'hardware'/f'route_e{e}_a0/synth/design.dcp'),part=")
runner=runner.replace('no board, complete-neuron or energy result','input phase fixed at 3 ns in common fixture; no board, complete-neuron or energy result')
for n,s in(('route_phase3.tcl',tcl),('run_stage4_route_v2.py',runner)):
    p=P/n;assert not p.exists();p.write_text(s,encoding='utf-8',newline='\n')
paths=[P/n for n in ('route.tcl','run_stage4_route.py','prepare_stage4_phase3.py','route_phase3.tcl','run_stage4_route_v2.py')]
value=dict(status='prepared',reason='Original raw-input 0.1 ns hold contract differs from replay falling-edge +3 ns stimulus; repair applies before placement to all engines without changing arithmetic, pipeline or disabling checks.',source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths})
p=P/'stage4_phase3_preparation.json';assert not p.exists();p.write_text(json.dumps(value,indent=2)+'\n')
