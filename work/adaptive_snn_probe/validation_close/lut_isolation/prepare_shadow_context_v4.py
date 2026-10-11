"""Prepare one combined-root causal probe, without launching vendor tools.

Every original routed CELL is copied with only its INSTANCE relocated beneath
the already-existing dut instance. In particular, top-cell INTERCONNECT paths
remain relative to that CELL's INSTANCE; they must not receive a second prefix.
"""
import ast
import hashlib
import json
import re
import shutil
from pathlib import Path

P = Path(__file__).resolve().parent
W = P / 'shadow_context_v4'
S = P.parent.parent / 'sequential_paper_trial'
V = Path('C:/AMDDesignTools/2025.2/Vivado')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def cells(text):
    """Retain exact CELL strings, observing quoted-string parentheses."""
    found = []
    offset = 0
    while True:
        match = re.search(r'\(CELL\s', text[offset:])
        if match is None:
            break
        start = offset + match.start()
        depth = 0
        quoted = False
        escaped = False
        for end in range(start, len(text)):
            char = text[end]
            if escaped:
                escaped = False
                continue
            if char == '\\':
                escaped = True
                continue
            if char == '"':
                quoted = not quoted
            if not quoted:
                depth += (char == '(') - (char == ')')
                if depth == 0:
                    found.append(text[start:end + 1])
                    offset = end + 1
                    break
        else:
            raise AssertionError('Unbalanced CELL')
    assert found
    return found


def instance(cell):
    matches = list(re.finditer(r'\(INSTANCE\s+([^)]*)\)', cell))
    assert len(matches) == 1
    return matches[0].group(1).strip()


def relocate(cell):
    prior = instance(cell)
    target = 'dut/' + prior if prior else 'dut'
    changed, count = re.subn(r'\(INSTANCE\s+([^)]*)\)', '(INSTANCE ' + target + ')', cell)
    assert count == 1
    # The inverse must recover the original entire cell byte-for-byte (after
    # universal newline decoding). This includes all paths and timing checks.
    match = re.search(r'\(INSTANCE\s+([^)]*)\)', cell)
    inverse, count = re.subn(r'\(INSTANCE\s+([^)]*)\)', lambda _: match.group(0), changed)
    assert count == 1 and inverse == cell
    return changed


def main():
    assert not W.exists(), 'Retain immutable preparations and attempts.'
    runners = [P / 'run_shadow_context_v4.py', P / 'run_shadow_context_v4_pulse100.py']
    assert not any(path.exists() for path in runners)
    previous = P / 'shadow_context_v2'
    prep = json.loads((previous / 'preparation.json').read_text())
    for section in ['source_sha256', 'prepared_sha256']:
        for name, stamp in prep[section].items():
            assert sha(name) == stamp, ('Changed earlier source', name)
    original_path = S / 'hardware/export12_e2_a0/routed.sdf'
    routed = original_path.read_text()
    old_cells = cells(routed)
    assert len(set(instance(cell) for cell in old_cells)) == len(old_cells)
    assert sum(instance(cell) == '' for cell in old_cells) == 1
    relocated = [relocate(cell) for cell in old_cells]
    added_cells = cells((previous / 'shadow_paths.sdf').read_text())
    assert [instance(cell) for cell in added_cells] == ['shadow', 'canary']
    original_target, = [cell for cell in old_cells
                        if instance(cell) == r'fixture/core/lut\.lane\[0\]\.r_reg\[11\]_i_4']
    target_without_instance = re.sub(r'\(INSTANCE\s+([^)]*)\)', '(INSTANCE)', original_target)
    for added in added_cells:
        assert re.sub(r'\(INSTANCE\s+([^)]*)\)', '(INSTANCE)', added) == target_without_instance
    prefix = routed[:routed.index(old_cells[0])]
    assert '(DIVIDER /)' in prefix and '(TIMESCALE 1ps)' in prefix
    prefix = prefix.replace('(DESIGN "top_sequential_leak_e2")', '(DESIGN "tb_sequential_energy_replay")')
    combined = prefix + '\n'.join(relocated + added_cells) + '\n)\n'
    assert cells(combined) == relocated + added_cells
    assert len(set(instance(cell) for cell in cells(combined))) == len(old_cells) + 2
    W.mkdir()
    (W / 'original_and_shadow_full.sdf').write_text(combined, newline='\n')
    shutil.copyfile(previous / 'CARRY4_vendor.v', W / 'CARRY4_vendor.v')
    assert sha(W / 'CARRY4_vendor.v') == sha(V / 'data/verilog/src/unisims/CARRY4.v')
    monitor = (previous / 'monitor_shadow.sv').read_text()
    old_annotation, = re.findall(r'^ initial \$sdf_annotate\([^\n]+\);$', monitor, re.M)
    monitor = monitor.replace(old_annotation + '\n', '')
    # Do not infer the observed vector assignment's transition time from a
    # single IOPATH. The known direct-path minimum is >50 ps and maximum579ps.
    old_canary = '''   #0.200;
   if(canary_o[0]!==1'b0)$fatal(1,"CAUSAL_CANARY_FAIL before228ps O%h",canary_o);
   #0.040;
   if(canary_o[0]!==1'b1)$fatal(1,"CAUSAL_CANARY_FAIL after228ps O%h",canary_o);
   $display("CAUSAL_CANARY_PASS S0_TO_O0_MAX228PS checks2");'''
    new_canary = '''   #0.050;
   if(canary_o[0]!==1'b0)$fatal(1,"CAUSAL_CANARY_FAIL before50ps O%h",canary_o);
   #0.550;
   if(canary_o!==4'h1 || canary_co!==4'h0)$fatal(1,"CAUSAL_CANARY_FAIL after600ps O%h CO%h",canary_o,canary_co);
   $display("CAUSAL_CANARY_PASS POSITIVE50PS_SETTLED600PS checks2");'''
    assert monitor.count(old_canary) == 1
    monitor = monitor.replace(old_canary, new_canary)
    assert '$sdf_annotate' not in monitor
    assert monitor.replace(new_canary, old_canary).replace(' initial begin\n   #200.000;', old_annotation + '\n initial begin\n   #200.000;') == (previous / 'monitor_shadow.sv').read_text()
    (W / 'monitor_shadow.sv').write_text(monitor, newline='\n')
    shutil.copyfile(previous / 'run.tcl', W / 'run.tcl')
    source = (P / 'run_shadow_context_v3.py').read_text()
    replacements = {
        "prepared = P / 'shadow_context_v2'": "prepared = P / 'shadow_context_v4'",
        "'shadow_paths.sdf'": "'original_and_shadow_full.sdf'",
        "'original_full_SDF_accepted': any('routed.sdf' in line for line in sdf_accepts)":
            "'original_full_SDF_source_equivalence': prep['all_original_cells_exact_except_INSTANCE'] and prep['original_cell_count'] > 0",
        "'shadow_and_canary_SDF_accepted': any('original_and_shadow_full.sdf' in line for line in sdf_accepts)":
            "'combined_full_SDF_accepted_at_TB_root': len(sdf_accepts) == 1 and 'original_and_shadow_full.sdf' in sdf_accepts[0] and 'root module \\\"tb_sequential_energy_replay\\\"' in sdf_accepts[0]",
        "'positive_228ps_timing_canary'": "'positive_50ps_settled_600ps_timing_canary'",
        "'original_netlist_or_SDF_modified': False, 'timing_checks_disabled': False":
            "'original_netlist_or_SDF_modified': False, 'combined_SDF_relocation_only': True, 'timing_checks_disabled': False",
    }
    for old, new in replacements.items():
        assert source.count(old) == 1, old
        source = source.replace(old, new)
    # Header keeps every snapshot/check and only changes root annotation and
    # canary gating. Explicit command-line annotation suppressed auto calls in
    # the retained cli_zero diagnostic; acceptance here still requires the
    # combined annotation record, no warning, and positive timing behavior.
    ast.parse(source)
    sources100 = source
    for option in ['pulse_r', 'pulse_int_r', 'pulse_e', 'pulse_int_e']:
        old = f"'-{option}', '0'"
        assert sources100.count(old) == 1
        sources100 = sources100.replace(old, f"'-{option}', '100'")
    ast.parse(sources100)
    for runner, content in zip(runners, [source, sources100]):
        runner.write_text(content, newline='\n')
    paths = [Path(__file__), *runners, P / 'run_shadow_context_v3.py',
             previous / 'preparation.json', previous / 'monitor_shadow.sv',
             previous / 'shadow_paths.sdf', original_path,
             S / 'hardware/export12_e2_a0/routed.v',
             S / 'hardware/native_actual_s0_a3/trace2.txt',
             V / 'data/verilog/src/unisims/CARRY4.v', V / 'data/verilog/src/glbl.v',
             P.parent.parent / 'selective_energy_trial/run_selective_energy.py']
    for directory in [P / 'shadow_context_v1/run_a0', previous / 'run_a0', previous / 'run_cli_zero_a0']:
        paths.extend(directory / name for name in ['diagnostic.json', 'tool_3.log', 'tool_4.log'])
    generated = [W / name for name in ['CARRY4_vendor.v', 'monitor_shadow.sv', 'original_and_shadow_full.sdf', 'run.tcl']]
    result = {
        'status': 'prepared_not_run', 'diagnostic_only': True, 'vendor_tools_launched': False,
        'original_cell_count': len(old_cells), 'combined_cell_count': len(old_cells) + 2,
        'all_original_cells_exact_except_INSTANCE': True,
        'all_original_numeric_delays_timing_checks_paths_PATHPULSE_unchanged': True,
        'original_top_INTERCONNECT_endpoints_remain_relative_to_dut_CELL': True,
        'shadow_and_canary_CELLs_exact_original_target_except_INSTANCE': True,
        'original_netlist_or_SDF_modified': False, 'vendor_CARRY4_modified': False,
        'timing_checks_disabled': False, 'positive_timing_gate': 'unchanged O0 at50ps, exact O1/CO0 at600ps',
        'maximum_added_IOPATH_ps': 579, 'same_live_input_ports': True,
        'annotation': 'One explicit xelab -sdfmax at tb_sequential_energy_replay, combined full SDF; no added procedural call.',
        'all_three_rejected_attempts_retained': True,
        'zero_100_runner_difference': 'Exactly four pulse percentage argument literals; source/monitor/SDF otherwise identical.',
        'source_sha256': {str(path.resolve()): sha(path) for path in paths},
        'prepared_sha256': {str(path.resolve()): sha(path) for path in generated},
        'cautions': ['Source equivalence is not simulator annotation acceptance.',
                     'A combined SDF success log and positive/settled timing canary are required before causal conclusions.',
                     'Shadow ports can differ in aliasing/delta context; observer sequence is not an exact event-region dump.',
                     'No result here accepts original failed LUT hardware or identifies a tool or hardware bug.'],
    }
    (W / 'preparation.json').write_text(json.dumps(result, indent=2) + '\n', newline='\n')
    print(json.dumps({key: value for key, value in result.items() if not key.endswith('sha256')}, indent=2))


if __name__ == '__main__':
    main()
