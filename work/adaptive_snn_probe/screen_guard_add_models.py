"""Supplied-window schedule and range screen for a new exact addition primitive.

Saved beta231 membranes are leaked before adding recorded current. This is not
RTL, memory, power, retraining or a full neuron-update timing measurement.
"""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import numpy as np

P = Path(__file__).resolve().parent
R = P / 'results'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def select(u, i, e):
    u, i = u[:6], i[:6]
    n = len(u)
    if e >= 2:
        return n, False
    wide = min(4, n)
    if n >= 5 and i[4] == 0:
        wide = 5
        if n == 6 and i[5] == 0:
            wide = 6
    narrow = e == 0 and n >= 5 and wide != n and all(-64 <= x <= 63 for x in u+i)
    return (n, True) if narrow else (wide, False)

def summarize(frames):
    rows = []
    for e in range(4):
        requests = narrow_requests = neurons = dsp_changes = lut_changes = copies = dsp_capacity = 0
        for u, i in frames:
            pos = 0
            while pos < len(u):
                count, narrow = select(u[pos:], i[pos:], e)
                requests += 1
                narrow_requests += narrow
                neurons += count
                dsp_n = 0 if e == 3 else (count if narrow else min(4, count))
                dsp_capacity += dsp_n
                changing = sum(v != 0 for v in i[pos:pos+count])
                active_dsp = sum(v != 0 for v in i[pos:pos+dsp_n])
                dsp_changes += active_dsp
                if e in (2, 3):
                    lut_changes += changing-active_dsp
                else:
                    copies += count-dsp_n
                pos += count
        rows.append(dict(engine=e, requests=requests, supplied_window_clocks=requests+4,
                         neurons=neurons, narrow_requests=narrow_requests,
                         changing_dsp_additions=dsp_changes, changing_lut_additions=lut_changes,
                         copied_neurons=copies, issued_dsp_lane_capacity=dsp_capacity,
                         changing_per_dsp_issue=dsp_changes/requests if e != 3 else None))
    return rows

def main():
    files = [R/'adaptive_delta_model_input.json', R/'adaptive_delta_model_25_1/expected.npz']
    pins = {str(p.relative_to(P)): sha(p) for p in files}
    ledger = json.loads(files[0].read_text())
    raw = np.load(files[1])['groups']
    frames = []
    u_lo, u_hi, i_lo, i_hi, s_lo, s_hi = 1024, -1024, 1024, -1024, 2048, -2048
    fitted = zeros = state_bad = spike_bad = 0
    for rec in ledger['ledger']:
        u = raw[rec['start']:rec['start']+rec['blocks']].reshape(-1)[:rec['neurons']].astype(np.int64)
        leaked = -np.floor_divide(-231*u, 256)
        current = np.array(rec['current'], dtype=np.int64)
        assert len(leaked) == len(current) and np.all((-1024 <= leaked) & (leaked <= 1023))
        assert np.all((-1024 <= current) & (current <= 1023))
        summed = leaked + current
        fired = summed >= rec['threshold']
        state = summed - fired*rec['threshold']
        state_bad += int(np.count_nonzero(state != rec['expected_state']))
        spike_bad += int(np.count_nonzero(fired != rec['expected_spikes']))
        fitted += int(np.count_nonzero((-64 <= leaked) & (leaked <= 63) & (-64 <= current) & (current <= 63)))
        zeros += int(np.count_nonzero(current == 0))
        u_lo, u_hi = min(u_lo, int(leaked.min())), max(u_hi, int(leaked.max()))
        i_lo, i_hi = min(i_lo, int(current.min())), max(i_hi, int(current.max()))
        s_lo, s_hi = min(s_lo, int(summed.min())), max(s_hi, int(summed.max()))
        frames.append((leaked.tolist(), current.tolist()))
    assert state_bad == spike_bad == 0 and len(frames) == 9216
    rows = summarize(frames)
    assert all(r['neurons'] == 635904 for r in rows)
    assert pins == {str(p.relative_to(P)): sha(p) for p in files}
    # Synthetic transitions supply preformed six-value windows; no arrival queue,
    # state dependency or source-memory service is simulated by this screen.
    synthetic = [([(-1)**k*12 for k in range(48)], [(-1)**k*3 for k in range(48)]),
                 ([(-1)**k*512 for k in range(48)], [(-1)**k*120 for k in range(48)]),
                 ([(-1)**k*700 for k in range(48)], [0]*48)]*16
    result = dict(created_utc=datetime.now(timezone.utc).isoformat(),
                  script_sha256=sha(Path(__file__)), model_input_sha256=pins,
                  operation='Addition of leaked signed11 membrane and recorded signed11 current, yielding signed12',
                  frames=len(frames), neurons=635904, eligible_scalar_pairs=fitted, zero_currents=zeros,
                  operand_ranges=dict(membrane=[u_lo,u_hi], current=[i_lo,i_hi], sum=[s_lo,s_hi]),
                  reference_state_mismatches=state_bad, reference_spike_mismatches=spike_bad,
                  models=rows, synthetic_transition_service=summarize(synthetic),
                  qualification='Changed beta231 reference, sampled144images/3seeds; this is not a trained-model preservation claim.',
                  limitations=['No RTL, timing, memory, power or burst arrival latency measured.',
                               'Only six-value ordered-window policies; generic gather/scatter zero compaction absent.',
                               'Fixed hybrid and LUT6 consume six every request and are necessary cost comparators.',
                               'Changing additions per issue are semantic counts, not measured DSP switching or efficiency.'])
    (R/'guard_add_workload_screen.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2), flush=True)

if __name__ == '__main__':
    main()
