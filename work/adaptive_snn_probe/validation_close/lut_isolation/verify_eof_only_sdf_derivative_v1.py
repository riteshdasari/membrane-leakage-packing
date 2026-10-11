"""Independently recheck an additive SDF certificate without modifying inputs."""
from pathlib import Path
import argparse
import hashlib
import json
import sys

sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent
sys.path.insert(0, str(P))
import sdf_structure_audit_v1 as audit


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify(certificate):
    certificate = Path(certificate).resolve()
    saved = json.loads(certificate.read_text(encoding='utf-8'))
    assert saved['status'] == 'pass_certified_additive_SDF_structure_derivative'
    assert saved['raw_source_modified'] is False
    assert saved['numerical_delays_modified'] is False
    assert saved['helper_sha256'] == sha(P / 'create_eof_only_sdf_derivative.py')
    assert saved['parser_sha256'] == sha(audit.__file__)
    source, target = [Path(saved[key]).resolve() for key in ['source', 'derivative']]
    assert source != target and source.is_file() and target.is_file()
    assert sha(source) == saved['source_sha256']
    assert sha(target) == saved['derivative_sha256']
    original, derivative = source.read_bytes(), target.read_bytes()
    count = saved['appended_closing_parentheses']
    assert count in (0, 3)
    suffix = ('\n' + ')' * count + '\n').encode() if count else b''
    assert suffix.hex() == saved['exact_appended_hex']
    assert derivative == original + suffix
    audit.self_check()
    source_check, source_text, repaired_text, source_root = audit.describe(source)
    derivative_check, derivative_text, _, derivative_root = audit.describe(target)
    assert source_check == saved['source_structural_audit']
    assert derivative_check == saved['derivative_structural_audit']
    assert derivative_text == repaired_text
    assert derivative_check['strict_structurally_balanced']
    if count:
        assert [n['expression'] for n in source_check['unclosed_expressions_at_EOF']] == ['DELAYFILE', 'CELL', 'DELAY']
        assert source_check['incomplete_cell_instances'] == ['']
    old_cells, new_cells = source_root.direct('CELL'), derivative_root.direct('CELL')
    assert len(old_cells) == len(new_cells) == source_check['direct_root_cell_count']
    for old, new in zip(old_cells, new_cells):
        assert audit.instance(old, repaired_text)[0] == audit.instance(new, derivative_text)[0]
        assert [(t.kind, t.text) for t in audit.leaves(old)] == [(t.kind, t.text) for t in audit.leaves(new)]
        assert repaired_text[old.start:old.end] == derivative_text[new.start:new.end]
    return dict(status='pass_independent_SDF_derivative_reverification',
                certificate=str(certificate), certificate_sha256=sha(certificate),
                source=str(source), source_sha256=sha(source),
                derivative=str(target), derivative_sha256=sha(target),
                appended_closing_parentheses=count,
                cell_count=len(old_cells), all_raw_bytes_tokens_paths_delays_checks_preserved=True,
                verifier_sha256=sha(__file__), simulation_or_energy_acceptance=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--certificate', required=True)
    args = ap.parse_args()
    print(json.dumps(verify(args.certificate), indent=2))


if __name__ == '__main__':
    main()
