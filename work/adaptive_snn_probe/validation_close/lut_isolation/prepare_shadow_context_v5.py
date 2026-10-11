"""Prepare a single balanced combined-root live-shadow diagnostic, no launch.

An explicit EOF-only syntax derivative is the source. Original CELL bodies,
paths, numeric delays and timing checks are retained; only INSTANCE regions
are relocated underneath dut. Original top-cell INTERCONNECT endpoints retain
their original paths relative to that CELL. Both pulse controls share one SDF,
monitor, vendor primitive, trace, canary and runner.
"""
from pathlib import Path
import ast
import hashlib
import json
import re
import sys

sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent
sys.path.insert(0, str(P))
import sdf_structure_audit_v1 as audit
from verify_eof_only_sdf_derivative_v1 import verify
W = P / 'shadow_context_v5'
PREVIOUS = P / 'shadow_context_v2'
S = P.parent.parent / 'sequential_paper_trial'
V = Path('C:/AMDDesignTools/2025.2/Vivado')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def cell_without_instance(text, cell):
    _, inst = audit.instance(cell, text)
    return text[cell.start:inst.start] + '(INSTANCE)' + text[inst.end:cell.end]


def relocated(text, cell):
    old, inst = audit.instance(cell, text)
    target = 'dut/' + old if old else 'dut'
    original = text[cell.start:cell.end]
    before = text[cell.start:inst.start]
    after = text[inst.end:cell.end]
    modified = before + '(INSTANCE ' + target + ')' + after
    assert before + text[inst.start:inst.end] + after == original
    return modified, dict(original=old, combined=target,
                          original_cell_text_sha256=hashlib.sha256(original.encode()).hexdigest(),
                          combined_cell_text_sha256=hashlib.sha256(modified.encode()).hexdigest(),
                          exact_original_before_and_after_INSTANCE_preserved=True)


def main():
    assert not W.exists(), 'Retain every earlier preparation'
    prior = json.loads((PREVIOUS / 'preparation.json').read_text())
    for section in ['source_sha256', 'prepared_sha256']:
        assert all(sha(name) == stamp for name, stamp in prior[section].items())
    original_cert = P / 'eof_repair_control_v2/original_sdf_EOF_only_certificate.json'
    verified = verify(original_cert)
    assert verified['appended_closing_parentheses'] == 3
    original = Path(verified['source'])
    balanced = Path(verified['derivative'])
    text = balanced.read_bytes().decode('utf-8')
    roots, opened, _ = audit.parse(text)
    assert not opened and len(roots) == 1
    root = roots[0]
    old_cells = root.direct('CELL')
    relocated_records = [relocated(text, cell) for cell in old_cells]
    copied, mappings = zip(*relocated_records)
    added_text = (PREVIOUS / 'shadow_paths.sdf').read_bytes().decode('utf-8')
    added_roots, opened, _ = audit.parse(added_text)
    assert not opened and len(added_roots) == 1
    added_cells = added_roots[0].direct('CELL')
    assert [audit.instance(cell, added_text)[0] for cell in added_cells] == ['shadow', 'canary']
    target, = [cell for cell in old_cells if audit.instance(cell, text)[0] ==
               r'fixture/core/lut\.lane\[0\]\.r_reg\[11\]_i_4']
    for cell in added_cells:
        assert cell_without_instance(added_text, cell) == cell_without_instance(text, target)
    # The original header has one DESIGN value. All other original metadata,
    # divider, timescale and the original first CELL position are retained.
    prefix = text[:old_cells[0].start]
    old_design = '(DESIGN "top_sequential_leak_e2")'
    assert prefix.count(old_design) == 1
    prefix = prefix.replace(old_design, '(DESIGN "tb_sequential_energy_replay")')
    combined = prefix + '\n'.join([*copied, *[added_text[c.start:c.end] for c in added_cells]]) + '\n)\n'
    combined_roots, opened, _ = audit.parse(combined)
    assert not opened and len(combined_roots) == 1
    all_cells = combined_roots[0].direct('CELL')
    assert len(all_cells) == len(old_cells) + 2
    names = [audit.instance(c, combined)[0] for c in all_cells]
    assert len(set(names)) == len(names)
    for old, new in zip(old_cells, all_cells):
        assert cell_without_instance(text, old) == cell_without_instance(combined, new)
    W.mkdir()
    (W / 'original_and_shadow_full.sdf').write_bytes(combined.encode())
    (W / 'CARRY4_vendor.v').write_bytes((PREVIOUS / 'CARRY4_vendor.v').read_bytes())
    assert sha(W / 'CARRY4_vendor.v') == sha(V / 'data/verilog/src/unisims/CARRY4.v')
    monitor = (PREVIOUS / 'monitor_shadow.sv').read_text()
    annotation, = re.findall(r'^ initial \$sdf_annotate\([^\n]+\);$', monitor, re.M)
    without_annotation = monitor.replace(annotation + '\n', '')
    old_canary = '''   #0.200;
   if(canary_o[0]!==1'b0)$fatal(1,"CAUSAL_CANARY_FAIL before228ps O%h",canary_o);
   #0.040;
   if(canary_o[0]!==1'b1)$fatal(1,"CAUSAL_CANARY_FAIL after228ps O%h",canary_o);
   $display("CAUSAL_CANARY_PASS S0_TO_O0_MAX228PS checks2");'''
    new_canary = '''   #0.050;
   if(canary_o!==4'h0 || canary_co!==4'h0)$fatal(1,"CAUSAL_CANARY_FAIL before50ps O%h CO%h",canary_o,canary_co);
   #0.550;
   if(canary_o!==4'h1 || canary_co!==4'h0)$fatal(1,"CAUSAL_CANARY_FAIL after600ps O%h CO%h",canary_o,canary_co);
   $display("CAUSAL_CANARY_PASS POSITIVE50PS_SETTLED600PS checks2");'''
    assert without_annotation.count(old_canary) == 1
    changed = without_annotation.replace(old_canary, new_canary)
    assert changed.replace(new_canary, old_canary) == without_annotation
    assert '$sdf_annotate' not in changed
    assert 'if(got!==expected[slot])' in changed
    (W / 'monitor_shadow.sv').write_text(changed, newline='\n')
    trace = S / 'hardware/native_actual_s0_a3/trace2.txt'
    trace_lines = trace.read_text().splitlines()
    rows = len(trace_lines)
    valid = sum(int(line.split()[9]) for line in trace_lines)
    duration = (rows + 2) * 12 + 200
    (W / 'run.tcl').write_text(f'run {duration} ns\nquit\n', newline='\n')
    runner = P / 'run_shadow_context_v5.py'
    ast.parse(runner.read_text())
    paths = [Path(__file__), runner, P / 'sdf_structure_audit_v1.py',
             P / 'verify_eof_only_sdf_derivative_v1.py',
             P / 'create_eof_only_sdf_derivative.py', P / 'run_shadow_context_v3.py',
             PREVIOUS / 'preparation.json', PREVIOUS / 'monitor_shadow.sv',
             PREVIOUS / 'shadow_paths.sdf', original, balanced, original_cert,
             S / 'hardware/export12_e2_a0/routed.v', trace,
             V / 'data/verilog/src/unisims/CARRY4.v', V / 'data/verilog/src/glbl.v',
             P.parent.parent / 'selective_energy_trial/run_selective_energy.py']
    for folder in [P / 'shadow_context_v1/run_a0', PREVIOUS / 'run_a0', PREVIOUS / 'run_cli_zero_a0']:
        paths.extend(folder / name for name in ['diagnostic.json', 'tool_3.log', 'tool_4.log'])
    result = dict(status='prepared_balanced_combined_root_shadow_and_pulse_control_not_run',
                  vendor_tools_launched=False, diagnostic_only=True,
                  original_cell_count=len(old_cells), combined_cell_count=len(all_cells),
                  original_SDF_structure_derivative=verified,
                  original_cells_byte_identical_except_INSTANCE_after_explicit_EOF_completion=True,
                  numeric_delays_timing_checks_PATHPULSE_and_all_endpoint_paths_unchanged=True,
                  original_top_CELL_instance='dut', original_top_INTERCONNECT_endpoints_unchanged=True,
                  shadow_and_canary_cells_exact_original_target_except_INSTANCE=True,
                  combined_single_annotation='Explicit xelab -sdfmax at tb_sequential_energy_replay',
                  maximum_added_IOPATH_ps=579,
                  canary_gate='ExactO0/CO0 at50ps, exactO1/CO0 at600ps',
                  same_live_original_cell_port_events=True,
                  known_row_comparator_unchanged=True, full_trace_rows=rows, valid_rows=valid,
                  trace=str(trace.resolve()), duration_ns=duration,
                  pulse_controls='One immutable runner; four explicit limits are all0 or all100. Same transport interconnect option and all other inputs/checks.',
                  source_sha256={str(p.resolve()): sha(p) for p in paths},
                  prepared_sha256={str(p.resolve()): sha(p) for p in W.glob('*.*')},
                  instance_mapping=mappings,
                  caveats=['Preparation is not successful simulator annotation.',
                           'Global -sdfmax suppresses the routed netlist annotation call; combined SDF must itself include every original CELL.',
                           'Per-pin observer order is not an exact event-region/delta dump.',
                           'The one-change no-shadow full-original EOF test is the primary causal control.',
                           'Pulse100 passing alone cannot replace original failed zero-limit evidence.',
                           'A syntax defect does not itself establish the cause of a settled arithmetic discrepancy.'])
    (W / 'preparation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ['source_sha256', 'prepared_sha256', 'instance_mapping']}, indent=2))


if __name__ == '__main__':
    main()
