"""Procedural background music for the full video.

lofi (calm)  ->  energetic build (part 5)  ->  cinematic / inspirational (finale)
Pure numpy/scipy synthesis, no samples. Output: stereo float32 array at SR.
"""
import numpy as np
from scipy.signal import butter, sosfilt

SR = 44100
rng = np.random.default_rng(7)

def note(m):  # midi -> Hz
    return 440.0 * 2 ** ((m - 69) / 12)

def lp(x, fc, order=2):
    return sosfilt(butter(order, fc, "low", fs=SR, output="sos"), x, axis=0)

def hp(x, fc, order=2):
    return sosfilt(butter(order, fc, "high", fs=SR, output="sos"), x, axis=0)

def bp(x, lo, hi):
    return sosfilt(butter(2, [lo, hi], "band", fs=SR, output="sos"), x, axis=0)

def tt(d):
    return np.arange(int(d * SR)) / SR

def add_wrap(buf, sig, idx):
    n = len(buf); idx %= n
    end = idx + len(sig)
    if end <= n:
        buf[idx:end] += sig
    else:
        k = n - idx
        buf[idx:] += sig[:k]
        rest = sig[k:]
        while len(rest):
            m = min(len(rest), n)
            buf[:m] += rest[:m]; rest = rest[m:]

# ---------- instruments ----------
def rhodes(f, d=2.5):
    t = tt(d)
    s = np.sin(2*np.pi*f*t) + 0.45*np.sin(4*np.pi*f*t)*np.exp(-t*5) + 0.12*np.sin(6*np.pi*f*t)*np.exp(-t*8)
    return s * np.exp(-t*2.2) * (1 - np.exp(-t*80))

def pluck(f, d=0.5):
    t = tt(d)
    s = 2*((f*t) % 1) - 1
    s = lp(s, 2200)
    return s * np.exp(-t*9) * (1 - np.exp(-t*200))

def piano(f, d=3.0):
    t = tt(d)
    s = np.sin(2*np.pi*f*t) + 0.5*np.sin(4*np.pi*f*t)*np.exp(-t*4) + 0.25*np.sin(6*np.pi*f*t)*np.exp(-t*7)
    return s * np.exp(-t*1.6) * (1 - np.exp(-t*150))

def kick(d=0.35):
    t = tt(d)
    f = 45 + 90*np.exp(-t*28)
    return np.sin(2*np.pi*np.cumsum(f)/SR) * np.exp(-t*9)

def snare(d=0.25):
    t = tt(d)
    return (bp(rng.standard_normal(len(t)), 1500, 7000) * 0.8 + np.sin(2*np.pi*190*t)*0.3) * np.exp(-t*20)

def clap(d=0.25):
    t = tt(d)
    return bp(rng.standard_normal(len(t)), 1000, 6000) * np.exp(-t*18)

def hat(d=0.08, open_=False):
    t = tt(0.3 if open_ else d)
    return hp(rng.standard_normal(len(t)), 7000) * np.exp(-t*(14 if open_ else 70))

def bass_sine(f, d):
    t = tt(d)
    return (np.sin(2*np.pi*f*t) + 0.2*np.sin(4*np.pi*f*t)) * np.minimum(1, np.minimum(t*40, (d-t)*30+0.0))

def saw_pad(f, d, det=0.004, cutoff=1400):
    t = tt(d)
    out = np.zeros((len(t), 2))
    for k, dt in enumerate((-det, 0, det)):
        ff = f * (1 + dt)
        s = 2*(((ff*t) + rng.random()) % 1) - 1
        pan = (k - 1) * 0.5
        out[:, 0] += s * (1 - max(pan, 0)); out[:, 1] += s * (1 + min(pan, 0))
    return lp(out, cutoff) / 3

def stereo(x, pan=0.0):
    return np.stack([x * (1 - max(pan, 0)), x * (1 + min(pan, 0))], axis=1)

def echo(x, delay=0.375, fb=0.35, n=4, lpf=3000):
    out = x.copy()
    for i in range(1, n + 1):
        k = int(delay * SR * i)
        out[k:] += lp(x[:-k], lpf) * (fb ** i)
    return out

# ---------- sections ----------
CH_LOFI = [[45, 52, 55, 59, 60, 64], [41, 48, 52, 55, 57, 60], [48, 52, 55, 59, 64], [43, 50, 55, 59, 64]]  # Am9 Fmaj7 Cmaj7 G6

def lofi_loop(bpm=76, bars_per_chord=2):
    beat = 60 / bpm
    bar = 4 * beat
    n_bars = 4 * bars_per_chord
    L = int(n_bars * bar * SR)
    buf = np.zeros((L, 2))
    for b in range(n_bars):
        ch = CH_LOFI[b // bars_per_chord]
        t0 = b * bar
        # rhodes comp: beat 1 and the "and" of 2 (swung)
        for off, vel in ((0, 1.0), (1.65 * beat, 0.7)):
            for j, m in enumerate(ch[1:]):
                s = rhodes(note(m + 12), 2.2) * vel * 0.16
                add_wrap(buf, stereo(s, (j - 2) * 0.12), int((t0 + off + j * 0.018) * SR))
        # bass
        add_wrap(buf, stereo(bass_sine(note(ch[0]), beat * 1.8) * 0.5), int(t0 * SR))
        if b % 2 == 1:
            add_wrap(buf, stereo(bass_sine(note(ch[0] + 7), beat * 0.9) * 0.4), int((t0 + 2.5 * beat) * SR))
        # drums
        add_wrap(buf, stereo(kick() * 0.7), int(t0 * SR))
        add_wrap(buf, stereo(kick() * 0.5), int((t0 + 2.5 * beat) * SR))
        add_wrap(buf, stereo(snare() * 0.3), int((t0 + 1 * beat) * SR))
        add_wrap(buf, stereo(snare() * 0.3), int((t0 + 3 * beat) * SR))
        for e in range(8):
            sw = 0.12 * beat if e % 2 else 0
            add_wrap(buf, stereo(hat() * (0.07 if e % 2 else 0.05), 0.3), int((t0 + e * beat / 2 + sw) * SR))
    # vinyl crackle
    crack = np.zeros(L)
    for _ in range(int(L / SR * 18)):
        i = rng.integers(0, L - 50); crack[i:i + 20] += rng.standard_normal(20) * rng.random() * 0.05
    buf += stereo(hp(crack, 1500))
    buf += stereo(lp(rng.standard_normal(L), 4000) * 0.004)
    return lp(buf, 5200)

def energetic_loop(bpm=104):
    beat = 60 / bpm; bar = 4 * beat
    prog = [(45, [57, 60, 64]), (41, [57, 60, 65]), (48, [55, 60, 64]), (43, [55, 59, 62])]
    L = int(4 * bar * SR)
    buf = np.zeros((L, 2))
    for b, (root, tri) in enumerate(prog):
        t0 = b * bar
        for k in range(4):
            add_wrap(buf, stereo(kick() * 0.9), int((t0 + k * beat) * SR))
            add_wrap(buf, stereo(hat(open_=True) * 0.10, -0.2), int((t0 + k * beat + beat / 2) * SR))
        for k in (1, 3):
            add_wrap(buf, stereo(clap() * 0.35), int((t0 + k * beat) * SR))
        for e in range(16):
            add_wrap(buf, stereo(hat() * 0.045, 0.3), int((t0 + e * beat / 4) * SR))
        for e in range(8):
            add_wrap(buf, stereo(bass_sine(note(root), beat * 0.45) * 0.55), int((t0 + e * beat / 2) * SR))
        arp = tri + [tri[0] + 12, tri[1] + 12, tri[2] + 12, tri[1] + 12, tri[0] + 12]
        for e in range(8):
            m = arp[(e * 3) % len(arp)] + 12
            add_wrap(buf, stereo(pluck(note(m), 0.5) * 0.17, -0.3 if e % 2 else 0.3), int((t0 + e * beat / 2) * SR))
        pad = saw_pad(note(tri[0] + 12), bar + 0.4, cutoff=1100) * 0.12
        add_wrap(buf, pad, int(t0 * SR))
        add_wrap(buf, saw_pad(note(tri[2] + 12), bar + 0.4, cutoff=1100) * 0.10, int(t0 * SR))
    return buf

def cinematic(total, bpm=84):
    # C - G - Am - F, hopeful; each chord 4 bars... use 7 s per chord
    prog = [(36, [60, 64, 67, 72]), (31, [59, 62, 67, 71]), (33, [57, 60, 64, 69]), (29, [57, 60, 65, 69])]
    seg = 7.0
    L = int(total * SR)
    buf = np.zeros((L, 2))
    n = int(total // seg) + 1
    beat = 60 / bpm
    for k in range(n):
        root, tri = prog[k % 4]
        t0 = k * seg
        d = seg + 2.5
        for m in tri:
            p = saw_pad(note(m - 12), d, det=0.006, cutoff=1500) * 0.16
            e = np.minimum(1, tt(d) / 2.5) * np.minimum(1, (d - tt(d)) / 2.5)
            i0 = int(t0 * SR)
            if i0 < L: buf[i0:min(L, i0 + len(p))] += (p * e[:, None])[:min(L, i0 + len(p)) - i0]
        # strings-ish octave doubling
        for m in (tri[0] + 12, tri[2] + 12):
            p = saw_pad(note(m), d, det=0.008, cutoff=2400) * 0.07
            e = np.minimum(1, tt(d) / 3.0) * np.minimum(1, (d - tt(d)) / 2.5)
            i0 = int(t0 * SR)
            if i0 < L: buf[i0:min(L, i0 + len(p))] += (p * e[:, None])[:min(L, i0 + len(p)) - i0]
        # deep root + boom
        b = bass_sine(note(root), d) * 0.35
        i0 = int(t0 * SR)
        if i0 < L: buf[i0:min(L, i0 + len(b))] += stereo(b)[:min(L, i0 + len(b)) - i0]
        # piano arpeggio (eighths) with echo
        pn = np.zeros((int((seg + 4) * SR), 2))
        order = [0, 1, 2, 3, 2, 1, 2, 3]
        for e_ in range(int(seg / (beat / 2))):
            m = tri[order[e_ % 8]] + 12
            i1 = int(e_ * beat / 2 * SR); s = stereo(piano(note(m), 2.5) * 0.12, (e_ % 4 - 1.5) * 0.2)
            pn[i1:i1 + len(s)] += s[:len(pn) - i1]
        pn = echo(pn, 60 / bpm * 0.75, 0.4, 3)
        if i0 < L: buf[i0:min(L, i0 + len(pn))] += pn[:min(L, i0 + len(pn)) - i0]
    # slow crescendo
    g = np.linspace(0.65, 1.0, L) ** 1.2
    return lp(buf * g[:, None], 7000)

def norm(x, peak=0.8):
    return x * (peak / (np.max(np.abs(x)) + 1e-9))

def tile(loop, total):
    reps = int(total * SR // len(loop)) + 1
    return np.tile(loop, (reps, 1))[: int(total * SR)]

def fade_env(n, fin, fout):
    e = np.ones(n)
    a, b = int(fin * SR), int(fout * SR)
    if a: e[:a] = np.linspace(0, 1, a)
    if b: e[-b:] = np.minimum(e[-b:], np.linspace(1, 0, b))
    return e

def build(total, t_energy, t_cinema):
    """total seconds; energetic build starts t_energy; cinematic finale starts t_cinema."""
    N = int(total * SR)
    out = np.zeros((N, 2))
    lofi = norm(tile(lofi_loop(), total), 0.8)
    # lofi until a few s after energy start
    end1 = int((t_energy + 22) * SR)
    out[:end1] += (lofi[:end1] * fade_env(end1, 3, 5)[:, None])
    # energetic
    e_len = (t_cinema + 3) - (t_energy + 16)
    en = norm(tile(energetic_loop(), e_len), 0.8)
    ramp = np.concatenate([np.linspace(0.35, 1.0, int(18 * SR)), np.ones(max(0, len(en) - int(18 * SR)))])[:len(en)]
    en = en * ramp[:, None] * fade_env(len(en), 5, 4)[:, None]
    s = int((t_energy + 16) * SR); out[s:s + len(en)] += en[:N - s]
    # cinematic
    c_len = total - (t_cinema - 1)
    ci = norm(cinematic(c_len), 0.85)
    ci = ci * fade_env(len(ci), 4, 6)[:, None]
    s = int((t_cinema - 1) * SR); out[s:s + len(ci)] += ci[:N - s]
    return norm(out, 0.9).astype(np.float32)
