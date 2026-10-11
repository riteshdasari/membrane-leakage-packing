"""Create new timing runners with AMD's required transport/pulse settings.

The old runners and all old activity remain untouched. Arithmetic, routed
checkpoints, testbench comparisons, clock, stimulus and measured ROI do not
change. All accepted frontier energy will require this method uniformly.
"""
from pathlib import Path
import hashlib

P = Path(__file__).resolve().parent
F5 = P.parent / 'residue_frontier_f5_trial'
old = (P/'run_frontier_replay_startup_v2.py').read_text()
needle = "'-mt','off','-debug','all','-L','simprims_ver'"
replacement = ("'-mt','off','-debug','all','-maxdelay',"
               "'-transport_int_delays','-pulse_r','0','-pulse_int_r','0',"
               "'-L','simprims_ver'")
assert old.count(needle) == 1
new = old.replace(needle, replacement)
new = new.replace('"""Same routed replay with one phase-preserving startup clock delay, no waivers."""',
                  '"""Full routed slow/max replay with AMD-required transport/pulse settings."""')
new = new.replace('clock_startup_delay_ns=6,saif=stats,',
                  "clock_startup_delay_ns=6,timing_simulation_method='AMD transport, zero pulse rejection, slow/max',saif=stats,")
new = new.replace("default=1)", "default=2)")
new = new.replace('REPLAY STARTUP V2 COMPLETE', 'REPLAY TRANSPORT V3 COMPLETE')

for family in ('original', 'f5'):
    target = P if family == 'original' else F5
    source = new
    if family == 'f5':
        source = source.replace('import run_frontier as run', 'import run_frontier_f5 as run')
        start = source.index('def prepare_tb():')
        end = source.index('\n\n\ndef replay(', start)
        source = source[:start] + '''def prepare_tb():
    tb=P/'tb_frontier_route_replay.sv'
    text=tb.read_text()
    assert 'reg clk=0;initial begin #6;forever #3 clk=~clk;end' in text
    return tb
''' + source[end:]
        source = source.replace('choices=range(6)', 'choices=(5,)')
        source = source.replace("default=2)", "default=0)")
        source = source.replace("f'export_e{a.engine}_a0'", "f'export_e{a.engine}_a1'")
    dest = target/'run_frontier_replay_transport_v3.py'
    assert not dest.exists()
    dest.write_text(source)
    print(dest, hashlib.sha256(dest.read_bytes()).hexdigest())

note = P/'TIMING_SIMULATION_CORRECTION.md'
assert not note.exists()
note.write_text('''# Standalone timing simulation correction

The first frontier timing elaborations omitted AMD UG900's required
interconnect transport and zero pulse rejection options. Three a1 routed
replays reported valid-output mismatches, while E0/E1 and E4 completed; none
of those activities are accepted for a publication energy comparison.

The new v3 runners add `-transport_int_delays -pulse_r 0 -pulse_int_r 0`,
as directed by AMD, and explicitly select `-maxdelay` for the slow-corner SDF.
No timing checks, SDF annotation, warnings, assertions, trace rows or valid
results are disabled. All six original engines and the F5 sibling are repeated
with the same method. RTL, checkpoints, clock period/phase, full input trace,
sampling rule and activity interval remain unchanged. The archived runs,
including failed data comparisons and preliminary E0 power, remain available.

Source: AMD UG900, Running Standalone Timing Simulation:
https://docs.amd.com/api/khub/documents/58GdahXPIbol1YkpG7h4Rg/content
Options: https://docs.amd.com/r/2025.2-English/ug900-vivado-logic-simulation/xelab-xvhdl-and-xvlog-xsim-Command-Options

This correction also means previously archived selective/operand-isolation
activity estimates using the omitted switches are preliminary; do not reuse
their numeric energy comparison as final paper evidence without repeating
them. Their native arithmetic checks and routed resource/timing reports are
separate evidence and are not changed by simulator pulse handling.
''')
