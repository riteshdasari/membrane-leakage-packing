"""Does overflow-driven block-DPS help when SNN membranes live in narrow packed DSP lanes?

Real data, no download: sklearn's bundled 8x8 handwritten digits (1797 samples, copied to ./data).
Pipeline: train a 64-128-10 ReLU MLP in numpy -> int8 weights -> rate-coded LIF SNN (ANN->SNN
conversion, soft reset, T timesteps, Poisson input spikes). Each neuron's membrane is held in an
L-bit signed lane (like a DSP48E2 SIMD lane). Every synaptic add is simulated one at a time, in input
order, exactly as a lane would see it.

Lane policies:
  wide       : unbounded integer lane (reference = what enough guard bits give you)
  wrap       : plain L-bit two's-complement lane (what DSP SIMD lanes do natively); weights/threshold
               pre-scaled by 2^-k, k calibrated
  sat        : L-bit lane + per-add overflow detect + clamp (needs fabric logic, like DPS); k calibrated
  dps_mono   : block-DPS, one shared exponent per group of G lanes (G=4 = one DSP48E2 FOUR12).
               On any lane overflow: all lanes of the group shift right 1 (rounded), e += 1.
               No calibration: e starts at the finest exponent that still represents V_th.
  dps_bi     : dps_mono + shift-left at end of each timestep when every lane's top two bits are equal
               (never below the starting exponent, otherwise V_th would not fit)
Rounding: 'trunc' (floor / arithmetic shift) or 'rha' (round half away from zero) for all shifts.
"""
import os, gzip, sys
os.environ.setdefault("OMP_NUM_THREADS", "2")
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
rng = np.random.default_rng(0)
T = 32
E_BITS = 4          # stored exponent bits per DPS group
E_MAX_STEPS = 2 ** E_BITS - 1


# ---------------------------------------------------------------- data + ANN
def load():
    d = np.loadtxt(gzip.open(os.path.join(HERE, "data", "digits.csv.gz")), delimiter=",")
    x, y = d[:, :64] / 16.0, d[:, 64].astype(int)
    p = rng.permutation(len(y))
    x, y = x[p], y[p]
    return (x[:1077], y[:1077]), (x[1077:1437], y[1077:1437]), (x[1437:], y[1437:])  # train / calib / test


def train_mlp(x, y, h=128, epochs=300, lr=3e-3):
    w1 = rng.normal(0, np.sqrt(2 / 64), (64, h)); w2 = rng.normal(0, np.sqrt(2 / h), (h, 10))
    ps = [w1, w2]; m = [np.zeros_like(p) for p in ps]; v = [np.zeros_like(p) for p in ps]
    Y = np.eye(10)[y]; t = 0
    for ep in range(epochs):
        for i in np.array_split(rng.permutation(len(y)), 9):
            a1 = np.maximum(x[i] @ ps[0], 0); z = a1 @ ps[1]
            pz = np.exp(z - z.max(1, keepdims=True)); pz /= pz.sum(1, keepdims=True)
            g2 = (pz - Y[i]) / len(i)
            gw2 = a1.T @ g2; gw1 = x[i].T @ ((g2 @ ps[1].T) * (a1 > 0))
            t += 1
            for k, g in enumerate((gw1, gw2)):
                g = g + 1e-4 * ps[k]
                m[k] = 0.9 * m[k] + 0.1 * g; v[k] = 0.999 * v[k] + 0.001 * g * g
                ps[k] -= lr * (m[k] / (1 - 0.9 ** t)) / (np.sqrt(v[k] / (1 - 0.999 ** t)) + 1e-8)
    return ps


# ---------------------------------------------------------------- lane arithmetic
def rnd(x, mode):
    return np.floor(x) if mode == "trunc" else np.sign(x) * np.floor(np.abs(x) + 0.5)


class Lanes:
    """Membranes of one layer for a batch: shape (B, N), one L-bit lane each."""

    def __init__(self, policy, L, mode, B, N, vth_int, k=0, G=4):
        self.p, self.L, self.mode, self.G = policy, L, mode, G
        self.MAX, self.MIN = 2 ** (L - 1) - 1, -(2 ** (L - 1))
        self.vth_int = vth_int
        self.u = np.zeros((B, N))
        if policy in ("dps_mono", "dps_bi"):
            # finest exponent at which V_th still fits in the lane
            self.e0 = max(0, int(np.ceil(np.log2(vth_int / self.MAX)))) if policy != "wide" else 0
            self.e = np.full((B, -(-N // G)), self.e0, dtype=np.int64)
        else:
            self.k = k
        self.events = 0; self.adds = 0

    def scale(self):
        """per-lane power-of-two scale, shape (B, N)"""
        if self.p in ("dps_mono", "dps_bi"):
            return np.repeat(2.0 ** self.e, self.G, axis=1)[:, :self.u.shape[1]]
        return np.full(self.u.shape, 2.0 ** self.k) if self.p != "wide" else np.ones(self.u.shape)

    def leak(self, beta_shift):
        # beta = 1 - 2^-beta_shift (shift-based leak); beta_shift = None -> IF neuron (no leak)
        if beta_shift is None:
            return
        if self.p == "wide":
            self.u = self.u * (1 - 2.0 ** -beta_shift); return
        self.u = self.u - rnd(self.u / 2 ** beta_shift, self.mode)

    def add(self, w_row, active):
        """add synaptic weight row w_row (N,) to samples where active (B,) is True"""
        if not active.any():
            return
        a = active[:, None]
        if self.p == "wide":
            self.u = self.u + a * w_row[None]; return
        if self.p in ("wrap", "sat"):
            w = w_row[None] * a                  # row already pre-scaled offline by 2^-k (see run_snn)
        else:
            w = rnd(w_row[None] / self.scale(), self.mode) * a
        s = self.u + w
        self.adds += int(a.sum()) * s.shape[1]
        ovf = (s > self.MAX) | (s < self.MIN)
        if self.p == "wrap":
            self.events += int(ovf.sum())
            self.u = np.mod(s - self.MIN, 2 ** self.L) + self.MIN
        elif self.p == "sat":
            self.events += int(ovf.sum())
            self.u = np.clip(s, self.MIN, self.MAX)
        else:
            B, N = s.shape
            gov = self.gany(ovf, False).any(-1) & (self.e < self.e0 + E_MAX_STEPS)
            self.events += int(gov.sum())
            sh = self.expand(gov)
            s = np.where(sh, rnd(s / 2, self.mode), s)   # adder has 1 extra bit: shift the true sum
            self.e = self.e + gov
            self.u = np.clip(s, self.MIN, self.MAX)       # only reachable when exponent is exhausted

    def add_bulk(self, I, spikes):
        s = self.u + I
        self.adds += int(spikes.sum()) * s.shape[1]
        self.events += int(((s > self.MAX) | (s < self.MIN)).sum())   # counts net wraps per step
        self.u = np.mod(s - self.MIN, 2 ** self.L) + self.MIN

    def fire(self):
        vth = self.vth_int / self.scale()
        if self.p != "wide":
            vth = rnd(vth, "rha")
        spk = self.u >= vth
        self.u = self.u - spk * vth
        return spk

    def maybe_shift_left(self):
        if self.p != "dps_bi":
            return
        B, N = self.u.shape
        half = 2 ** (self.L - 2)
        ok = self.gany((self.u < half) & (self.u >= -half), True).all(-1) & (self.e > self.e0)
        self.u = np.where(self.expand(ok), self.u * 2, self.u)
        self.e = self.e - ok

    def gany(self, m, fill):
        """reduce lane mask (B, N) to group mask with any/all; pads N up to a multiple of G"""
        B, N = m.shape; pad = (-N) % self.G
        if pad: m = np.concatenate([m, np.full((B, pad), fill)], 1)
        return m.reshape(B, -1, self.G)

    def expand(self, g):
        return np.repeat(g, self.G, axis=1)[:, :self.u.shape[1]]

    def membrane_real(self):
        return self.u * self.scale()


def run_snn(wi, vth, x, policy, L, mode, beta_shift, ks=(0, 0), G=4, seed=1, stats=None):
    """wi: int8 weight matrices; vth: integer thresholds per layer. Returns predictions."""
    r = np.random.default_rng(seed)
    B = len(x)
    lay = [Lanes(policy, L, mode, B, wi[0].shape[1], vth[0], ks[0], G),
           Lanes(policy, L, mode, B, wi[1].shape[1], vth[1], ks[1], G)]
    if policy in ("wrap", "sat"):   # static pre-scaling of weights is done once, offline
        wi = [rnd(w / 2.0 ** k, mode) for w, k in zip(wi, ks)]
    cnt = np.zeros((B, 10))
    maxabs = [0.0, 0.0]
    for t in range(T):
        s_in = r.random(x.shape) < x
        spikes = s_in
        for li, (w, ln) in enumerate(zip(wi, lay)):
            ln.leak(beta_shift)
            if policy == "wrap":
                # two's-complement wrap is modular: adding one-by-one == adding the sum, then wrapping
                ln.add_bulk(spikes.astype(float) @ w, spikes)
            else:
                for j in range(w.shape[0]):
                    ln.add(w[j], spikes[:, j])
            maxabs[li] = max(maxabs[li], np.abs(ln.membrane_real()).max())
            spikes = ln.fire()
            ln.maybe_shift_left()
        cnt += spikes
    if stats is not None:
        stats["maxabs"] = maxabs
        stats["events"] = sum(l.events for l in lay); stats["adds"] = sum(l.adds for l in lay)
        if policy.startswith("dps"):
            stats["e_mean"] = [float((l.e - l.e0).mean()) for l in lay]
    score = cnt + 1e-6 * lay[1].membrane_real()
    return score.argmax(1)


def main():
    (xtr, ytr), (xca, yca), (xte, yte) = load()
    w1, w2 = train_mlp(xtr, ytr)
    ann_acc = np.mean((np.maximum(xte @ w1, 0) @ w2).argmax(1) == yte)
    # int8 per-layer weights
    s1, s2 = np.abs(w1).max() / 127, np.abs(w2).max() / 127
    wi = [np.round(w1 / s1), np.round(w2 / s2)]
    a1 = np.maximum(xca @ w1, 0)
    log = [f"ANN test acc = {ann_acc:.4f}  (train {len(ytr)}, calib {len(yca)}, test {len(yte)}), T={T}"]

    for beta_shift, bname in ((1, "LIF beta=0.5"), (None, "IF (beta=1)"), (3, "LIF beta=0.875")):
        # threshold balancing: V_th = factor * p99 of ANN activation, factor tuned on calib set (FP lanes)
        best = None
        for f in (0.05, 0.1, 0.2, 0.35, 0.5, 0.75, 1.0):
            v = [f * np.percentile(a1, 99) / s1, f * np.percentile(a1 @ w2, 99) / s2]
            acc = np.mean(run_snn(wi, v, xca, "wide", 0, "rha", beta_shift) == yca)
            if best is None or acc > best[0]: best = (acc, v, f)
        vth = best[1]
        st = {}
        ref_te = run_snn(wi, vth, xte, "wide", 0, "rha", beta_shift, stats=st)
        ref_acc = np.mean(ref_te == yte)
        bits_needed = [int(np.ceil(np.log2(m + 1))) + 1 for m in st["maxabs"]]
        log.append(f"\n== {bname}: Vth factor {best[2]}, Vth_int=({vth[0]:.0f},{vth[1]:.0f}); wide-lane SNN test acc={ref_acc:.4f}; "
                   f"max|u| -> lane bits for zero overflow (guard-bit design) = {bits_needed}")
        print(log[-1], flush=True)
        for L in (10, 8, 6):
            for policy in ("wrap", "sat", "dps_mono", "dps_bi"):
                for mode in ("trunc", "rha"):
                    if policy in ("wrap", "sat"):
                        # calibrate static pre-shift k per layer (joint small grid) on calib set
                        kfit = [max(0, int(np.ceil(np.log2(v / (2 ** (L - 1) - 1))))) for v in vth]
                        # coordinate descent over per-layer shifts k = kfit + {0..3}
                        ks = [kfit[0], kfit[1] + 1]
                        for li in (0, 1):
                            bestk = None
                            for d in range(0, 4):
                                kk = list(ks); kk[li] = kfit[li] + d
                                acc = np.mean(run_snn(wi, vth, xca[:180], policy, L, mode, beta_shift, tuple(kk)) == yca[:180])
                                if bestk is None or acc > bestk[0]: bestk = (acc, kk)
                            ks = bestk[1]
                        ks = tuple(ks)
                    else:
                        ks = (0, 0)
                    st = {}
                    pred = run_snn(wi, vth, xte, policy, L, mode, beta_shift, ks, stats=st)
                    acc = np.mean(pred == yte); agree = np.mean(pred == ref_te)
                    bpn = L + (E_BITS / 4 if policy.startswith("dps") else 0)
                    extra = f" k={ks}" if policy in ("wrap", "sat") else f" mean e-steps={np.round(st.get('e_mean', [0, 0]), 2).tolist()}"
                    log.append(f"  L={L:2d} ({bpn:5.2f} b/neuron) {policy:8s} {mode:5s}: acc={acc:.4f} agree-with-wide={agree:.4f} "
                               f"ovf-events/add={st['events'] / max(st['adds'], 1):.2e}{extra}")
                    print(log[-1], flush=True)
    txt = "\n".join(log)
    print(txt)
    open(os.path.join(HERE, "dsp_lane_results.txt"), "w").write(txt + "\n")


if __name__ == "__main__":
    main()




