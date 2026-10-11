"""Prepare isolated routing helpers for one exact provisional-high simplification.

Does not launch HDL tools or alter the frozen original selective cohort.
The independent decode verifier supplies nine functional source pins.
"""
from pathlib import Path
import hashlib
import ast

P = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    expected = {
        'guard_add_selective_timing.sv': 'd723a775f209968b58f658fab3b3f6367e627fab90a6048426ef7ed479c1b3c9',
        'route_guard_add_selective.tcl': 'a3bf48502d47127d286c37bb164bf3df7de1a623df3fefd5904e431a83dc2e3b',
        'run_guard_add_selective_route.py': 'f3c6f32cbffc7662970fa41b39bac5f0de00c1adacac7ed0d00477f6e2a02ae3',
    }
    assert all(sha(P/name) == stamp for name, stamp in expected.items())
    core = P/'guard_add_selective_decode.sv'
    assert core.is_file()
    for name in expected:
        body = (P/name).read_text()
        body = body.replace('guard_add_selective', 'guard_add_selective_decode')
        body = body.replace('GUARD_ADD_SELECTIVE', 'GUARD_ADD_SELECTIVE_DECODE')
        dest = name.replace('guard_add_selective', 'guard_add_selective_decode')
        if name.endswith('.py'):
            for old, new in [
                ("f'selective_{kind}", "f'selective_decode_{kind}"),
                ("f'selective_models", "f'selective_decode_models"),
                ("'selective_models", "'selective_decode_models"),
                ("'selective_snn_checks.json'", "'selective_decode_snn_checks.json'"),
                ("'selective_hardware.json'", "'selective_decode_hardware.json'"),
                ("'selective_tmp'", "'selective_decode_tmp'"),
                ("r'selective_(main|models)", "r'selective_decode_(main|models)"),
                ('for variant in range(4)}', 'for variant in (1, 3)}'),
            ]:
                body = body.replace(old, new)
            body = body.replace("'../baseline_retime_trial/guard_add_retime.sv']",
                                "'../baseline_retime_trial/guard_add_retime.sv', 'guard_add_selective.sv']")
            body = body.replace('b5c7d724d642b2310c4e447eabccaf965a3aa520aaf2e04c5f93accd5dbb9e48', sha(core))
            body = body.replace('import time\n', 'import time\nimport run_guard_add_selective_route as parent_route\n')
            needle = "    assert top in TOPS, ('Unknown matched selective-correction top', top)"
            assert needle in body
            body = body.replace(needle, needle + "\n    parent_sources = parent_route.hashes()\n    parent_checks = parent_route.functional('top_guard_add_selective_v0', parent_sources)\n    parent_functional = {key: parent_sources[key] for key in parent_route.FUNCTIONAL_SOURCES}")
            needle = "        suite_data[name] = data"
            assert needle in body
            body = body.replace(needle, """        parent_name = name.replace('selective_decode_', 'selective_', 1)
        parent_data = json.loads((R / parent_name).read_text())
        assert data['parent_source_hashes'] == parent_functional, name
        assert data['parent_check_file'] == str(Path('results') / parent_name), name
        assert data['parent_check_sha256'] == sha(R / parent_name), name
        assert data['outputs_byte_identical_to_parent'] is True, name
        assert data['parent_rows_identical'] is True, name
        assert data['rows'] == parent_data['rows'], name
        assert data['parent_output_hashes'] == {str(Path('results') / Path(parent_data['stimulus_file']).parent / f'stream_out{row["variant"]}.txt'): row['output_sha256'] for row in parent_data['rows']}, name
        suite_data[name] = data""")
            needle = "    evidence.update(policy_evidence(pin, model_pins))\n    return evidence"
            assert needle in body
            body = body.replace(needle, """    evidence.update(policy_evidence(pin, model_pins))
    parent_snn = json.loads((R / 'selective_snn_checks.json').read_text())
    assert data['parent_source_hashes'] == parent_functional
    assert data['parent_snn_check_file'] == str(Path('results') / 'selective_snn_checks.json')
    assert data['parent_snn_check_sha256'] == sha(R / 'selective_snn_checks.json')
    assert data['parent_output_hashes'] == parent_snn['output_hashes']
    assert data['parent_snn_rows_identical'] is True and data['rows'] == parent_snn['rows']
    evidence.update(parent_checks)
    evidence['run_guard_add_selective_route.py'] = sha(P / 'run_guard_add_selective_route.py')
    evidence.update(parent_functional)
    assert parent_route.hashes() == parent_sources, 'Frozen parent cohort changed'
    return evidence""")
            ast.parse(body)
        elif name.endswith('.tcl'):
            body = body.replace('_v[0-3]', '_v[13]')
        (P/dest).write_text(body, encoding='utf-8')
        print(dest, sha(P/dest))
    assert all(sha(P/name) == stamp for name, stamp in expected.items())


if __name__ == '__main__':
    main()
