"""Independently decode retained E2 replay words and their source operands."""
from pathlib import Path
from collections import deque
import hashlib
import json
import re
import sys

sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent
S = P.parent.parent / 'sequential_paper_trial'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def signed(value, width):
    value &= (1 << width) - 1
    return value - (1 << width) if value & (1 << (width - 1)) else value


def decode(word):
    value = int(word, 16)
    return dict(in_ready=(value >> 30) & 1, take=(value >> 28) & 3,
                out_valid=(value >> 27) & 1, out_count=(value >> 25) & 3,
                data_hex=f'{(value >> 1) & 0xffffff:06x}', narrow_mode=value & 1,
                lane0_signed12=signed(value >> 1, 12), lane1_signed12=signed(value >> 13, 12))


def main():
    target = P / 'historical_discrepancy_fields_v1.json'
    assert not target.exists()
    paths = [P / 'internal_a0/tool_4.log',
             P / 'eof_repair_control_v2/run_raw_a0/tool_4.log',
             P / 'eof_repair_control_v2/run_balanced_a0/tool_4.log']
    findings = []
    for path in paths:
        text = path.read_text(errors='replace')
        found = re.findall(r'REPLAY mismatch E2 row(\d+) got([0-9a-fA-F]+) expected([0-9a-fA-F]+)', text)
        assert len(found) == 1
        row, got, expected = found[0]
        assert int(row) == 914
        g, e = decode(got), decode(expected)
        assert all(g[key] == e[key] for key in ['in_ready', 'take', 'out_valid', 'out_count', 'narrow_mode', 'lane1_signed12'])
        assert g['lane0_signed12'] == 509 and e['lane0_signed12'] == -3
        findings.append(dict(path=str(path.resolve()), log_sha256=sha(path), row=int(row), got_word=got, expected_word=expected,
                             got=g, expected=e, low_lane_signed_error=g['lane0_signed12'] - e['lane0_signed12']))
    trace = S / 'hardware/native_actual_s0_a3/trace2.txt'
    queue = deque()
    target_operation = None
    for index, line in enumerate(trace.read_text().splitlines()):
        f = line.split()
        assert len(f) == 15 and int(f[0]) == index
        _, rst, valid, ready, available, u, beta, ir, take, ov, nout, data, mode, accept, retire = [
            int(item, 16 if k in (5, 6, 11) else 10) for k, item in enumerate(f)]
        assert accept == int(valid and ir and available > 0)
        assert retire == int(ov and ready)
        if accept:
            assert not rst and 1 <= take <= available <= 2
            lanes = []
            expected_word = 0
            for lane in range(take):
                value = signed(u >> (12 * lane), 12)
                coefficient = (beta >> (9 * lane)) & 511
                assert coefficient <= 256
                result = -((-value * coefficient) // 256)
                expected_word |= (result & 4095) << (12 * lane)
                lanes.append(dict(U=value, beta=coefficient, scalar_ceil_leak=result))
            queue.append(dict(accept_row=index, take=take, expected_word=expected_word, lanes=lanes))
        if retire:
            assert queue
            operation = queue.popleft()
            assert operation['take'] == nout and operation['expected_word'] == data
            assert index - operation['accept_row'] == 2
            if index == 914:
                target_operation = operation | dict(retire_row=index, native_expected_data_hex=f'{data:06x}')
                break
    assert target_operation is not None
    assert target_operation['accept_row'] == 912
    assert target_operation['lanes'] == [dict(U=-6, beta=166, scalar_ceil_leak=-3),
                                         dict(U=193, beta=87, scalar_ceil_leak=66)]
    result = dict(status='pass_independent_historical_field_decode', same_discrepancy_in_all_three_contexts=True,
                  original_operand=target_operation, findings=findings,
                  low_lane_got=509, low_lane_expected=-3, low_lane_error=512,
                  high_lane_got_and_expected=66, all_control_fields_equal=True,
                  interpretation='The full packed replay word is not a scalar neuron value. Decoding its data/control fields reproduces the earlier509versus-3 discrepancy exactly. EOF structural completion does not resolve it.',
                  original_raw_evidence_modified=False, timing_acceptance=False,
                  source_sha256={str(p.resolve()):sha(p) for p in [Path(__file__), trace, P/'internal_a0/monitor.sv', *paths]})
    target.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
