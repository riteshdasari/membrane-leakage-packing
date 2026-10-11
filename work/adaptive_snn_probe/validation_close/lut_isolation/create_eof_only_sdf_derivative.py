"""Create an additive, certified SDF derivative; never overwrite raw exports.

The sole allowed defect is the observed three open terminal expressions:
DELAYFILE, the final empty-INSTANCE CELL, and that CELL's DELAY. The sole change
is three appended closing parentheses plus whitespace. A structurally complete
input is copied byte-identically to the separately named derivative. Any other
lexical/structural defect is rejected rather than heuristically repaired.
"""
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


def create(source, target, certificate):
    source, target, certificate = [Path(p).resolve() for p in (source, target, certificate)]
    assert source != target and source != certificate and target != certificate
    assert source.is_file() and not target.exists() and not certificate.exists()
    audit.self_check()
    record, text, repaired, root = audit.describe(source)
    count = record['EOF_only_added_closing_parentheses']
    if count:
        assert count == 3
        assert [entry['expression'] for entry in record['unclosed_expressions_at_EOF']] == ['DELAYFILE', 'CELL', 'DELAY']
        assert record['incomplete_cell_instances'] == ['']
        _, open_nodes, old_tokens = audit.parse(text, allow_eof=True)
        assert open_nodes[1] is root.direct('CELL')[-1] or open_nodes[1].start == root.direct('CELL')[-1].start
        assert open_nodes[2] in open_nodes[1].direct('DELAY')
        # Every CELL contains precisely one CELLTYPE, INSTANCE, and DELAY.
        # A malformed nonterminal cell or incomplete lexical token is rejected.
        assert record['complete_cell_count'] + 1 == record['direct_root_cell_count']
    else:
        _, _, old_tokens = audit.parse(text)
    original_bytes = source.read_bytes()
    assert original_bytes.decode('utf-8') == text
    appended = ('\n' + ')' * count + '\n').encode('utf-8') if count else b''
    output_bytes = original_bytes + appended
    assert output_bytes.decode('utf-8') == repaired
    roots, open_after, new_tokens = audit.parse(repaired)
    assert not open_after
    assert [(t.kind, t.text) for t in new_tokens[:len(old_tokens)]] == [(t.kind, t.text) for t in old_tokens]
    assert [t.kind for t in new_tokens[len(old_tokens):]] == [')'] * count
    # Assert preserved bytes and the exact changed suffix, not merely numerical
    # equivalence. All delay paths/checks, including PATHPULSE, remain identical.
    assert output_bytes[:len(original_bytes)] == original_bytes
    assert output_bytes[len(original_bytes):] == appended
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(output_bytes)
    verified, _, _, _ = audit.describe(target)
    assert verified['strict_structurally_balanced']
    assert verified['direct_root_cell_count'] == record['direct_root_cell_count']
    assert verified['cell_instances_sha256'] == record['cell_instances_sha256']
    assert sha(source) == record['source_sha256']
    result = dict(status='pass_certified_additive_SDF_structure_derivative',
                  source=str(source), source_sha256=record['source_sha256'],
                  derivative=str(target), derivative_sha256=sha(target),
                  exact_appended_hex=appended.hex(), appended_closing_parentheses=count,
                  raw_source_modified=False, numerical_delays_modified=False,
                  all_original_bytes_are_exact_prefix=True,
                  all_original_lexical_tokens_are_exact_prefix=True,
                  all_original_cell_paths_delays_timing_checks_PATHPULSE_unchanged=True,
                  source_structural_audit=record, derivative_structural_audit=verified,
                  helper_sha256=sha(__file__), parser_sha256=sha(audit.__file__),
                  vendor_tools_launched=False,
                  causal_replay_resolved=False,
                  limitation='This certifies an EOF-only syntax derivative, not SDF annotation, timing, replay, SAIF, energy, physical hardware, or the cause of any numerical discrepancy.')
    certificate.parent.mkdir(parents=True, exist_ok=True)
    certificate.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', required=True)
    ap.add_argument('--target', required=True)
    ap.add_argument('--certificate', required=True)
    args = ap.parse_args()
    print(json.dumps(create(args.source, args.target, args.certificate), indent=2))


if __name__ == '__main__':
    main()
