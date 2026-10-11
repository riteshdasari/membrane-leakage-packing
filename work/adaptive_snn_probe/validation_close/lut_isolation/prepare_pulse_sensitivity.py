"""Prepare a separately pinned pulse-limit sensitivity runner; launch nothing."""
from pathlib import Path
import ast
import hashlib
import json

P = Path(__file__).resolve().parent
original = P / 'run_shadow_context_v2.py'
target = P / 'run_shadow_context_v2_pulse100.py'
assert not target.exists(), 'Keep diagnostic attempts immutable.'
before = original.read_text()
after = before
changes = []
for option in ('pulse_r', 'pulse_int_r', 'pulse_e', 'pulse_int_e'):
    old = f"'-{option}', '0'"
    new = f"'-{option}', '100'"
    assert after.count(old) == 1
    after = after.replace(old, new)
    changes.append((old, new))
assert "'-transport_int_delays'" in after
assert "'ROWS=950'" in after and 'positive_228ps_timing_canary' in after
assert "assert not any(item in argv" in after
restored = after
for old, new in changes:
    restored = restored.replace(new, old)
assert restored == before
assert ast.dump(ast.parse(restored)) == ast.dump(ast.parse(before))
ast.parse(after)
target.write_text(after, newline='\n')
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
record = dict(status='prepared_only', vendor_jobs_launched=False,
              original_runner_sha256=sha(original), new_runner_sha256=sha(target),
              source_sha256={str(original):sha(original),str(target):sha(target),
                             str(Path(__file__)):sha(__file__)},
              only_source_changes=changes, pulse_limits_percent=100,
              unchanged_transport_SDF_checks_rows_canary=True,
              scope='Sensitivity diagnostic only; cannot replace zero-limit replay acceptance.')
(P / 'pulse100_preparation.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
