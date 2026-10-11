"""Prepare matched full-original replays; only balanced variant uses EOF repair.

No shadow cell, added canary, altered primitive, disabled timing check, traffic
decision, or numerical correction. Preparation performs no vendor launch.
"""
from pathlib import Path
import hashlib
import json
import sys

sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent
sys.path.insert(0, str(P))
from create_eof_only_sdf_derivative import create
from verify_eof_only_sdf_derivative_v1 import verify

S = P.parent.parent / 'sequential_paper_trial'
V = Path('C:/AMDDesignTools/2025.2/Vivado')
W = P / 'eof_repair_control_v1'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    assert not W.exists(), 'Retain immutable preparations and all attempts'
    old = P / 'internal_a0'
    stamps = json.loads((old / 'provenance.json').read_text())
    assert all(sha(path) == saved for path, saved in stamps.items())
    rv = S / 'hardware/export12_e2_a0/routed.v'
    sdf = S / 'hardware/export12_e2_a0/routed.sdf'
    trace = S / 'hardware/native_actual_s0_a3/trace2.txt'
    lines = trace.read_text().splitlines()
    for index, line in enumerate(lines):
        fields = line.split()
        assert len(fields) == 15 and int(fields[0]) == index
        assert not any('x' in token.lower() or 'z' in token.lower() for token in fields)
    assert len(lines) > 2836
    valid = sum(int(line.split()[9]) for line in lines)
    W.mkdir()
    cert = W / 'original_sdf_EOF_only_certificate.json'
    target = W / 'original_EOF_only_balanced.sdf'
    create(sdf, target, cert)
    verified = verify(cert)
    assert verified['appended_closing_parentheses'] == 3
    original_netlist = rv.read_bytes()
    old_path = str(sdf.resolve()).replace('\\', '/').encode()
    new_path = str(target.resolve()).replace('\\', '/').encode()
    assert original_netlist.count(old_path) == 1
    changed_netlist = original_netlist.replace(old_path, new_path)
    assert changed_netlist.replace(new_path, old_path) == original_netlist
    assert changed_netlist.count(b'$sdf_annotate(') == original_netlist.count(b'$sdf_annotate(') == 1
    (W / 'routed_raw.v').write_bytes(original_netlist)
    (W / 'routed_EOF_only_balanced.v').write_bytes(changed_netlist)
    (W / 'monitor.sv').write_bytes((old / 'monitor.sv').read_bytes())
    (W / 'CARRY4_vendor.v').write_bytes((old / 'CARRY4_vendor.v').read_bytes())
    assert sha(W / 'CARRY4_vendor.v') == sha(V / 'data/verilog/src/unisims/CARRY4.v')
    monitor = (W / 'monitor.sv').read_text()
    assert 'if(got!==expected[slot])' in monitor
    assert 'if(n>=2)compare_row((n-2)%4);' in monitor
    assert '$sdf_annotate' not in monitor and 'CARRY4 shadow' not in monitor
    assert 'CARRY4 canary' not in monitor and 'force ' not in monitor
    duration = (len(lines) + 2) * 12 + 200
    (W / 'run.tcl').write_text(f'run {duration} ns\nquit\n', newline='\n')
    sources = [Path(__file__), P / 'run_eof_repair_control_v1.py',
               P / 'create_eof_only_sdf_derivative.py', P / 'sdf_structure_audit_v1.py',
               P / 'verify_eof_only_sdf_derivative_v1.py',
               rv, sdf, trace, old / 'provenance.json', old / 'monitor.sv',
               old / 'CARRY4_vendor.v', old / 'run.tcl', old / 'diagnostic.json',
               old / 'tool_3.log', old / 'tool_4.log',
               V / 'data/verilog/src/unisims/CARRY4.v', V / 'data/verilog/src/glbl.v',
               P.parent.parent / 'selective_energy_trial/run_selective_energy.py']
    prepared = list(W.glob('*.*'))
    result = dict(status='prepared_matched_original_full_trace_EOF_only_control_not_run',
                  vendor_tools_launched=False, rows=len(lines), valid_rows=valid,
                  trace=str(trace.resolve()), duration_ns=duration,
                  certificate=str(cert.resolve()), certificate_reverification=verified,
                  complete_original_known_row_comparator_unchanged=True,
                  original_internal_monitor_byte_identical=True,
                  raw_netlist_byte_identical=True,
                  balanced_netlist_only_original_SDF_argument_changed=True,
                  all_original_delay_paths_checks_and_primitive_logic_unchanged=True,
                  matched_control_options='maxdelay; transport_int_delays; four explicit pulse limits0; all timing checks active',
                  no_shadow_or_added_canary=True,
                  original_raw_SDF_immutable=True,
                  source_sha256={str(p.resolve()): sha(p) for p in sources},
                  prepared_sha256={str(p.resolve()): sha(p) for p in prepared},
                  interpretations={
                      'both fail_same_row': 'EOF closure does not resolve the retained numerical discrepancy.',
                      'raw fails_balanced passes_all_rows': 'The EOF-only SDF derivative resolves this frozen simulation replay; this does not demonstrate physical FPGA correctness or a primitive implementation defect.',
                      'both pass': 'The original failure is not reproduced in this matched replay context; causal closure remains incomplete.',
                      'any annotation_or_timing_gate_fails': 'Reject the causal comparison rather than waive evidence.'})
    (W / 'preparation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if not k.endswith('sha256')}, indent=2))


if __name__ == '__main__':
    main()
