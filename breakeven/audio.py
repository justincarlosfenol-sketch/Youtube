"""Original procedural score, sound design and final mix.

Everything here is synthesised from scratch with numpy, so we own 100% of the
audio. The score is an ambient pad + soft pluck arpeggio in D minor
(i-VI-III-VII), with an intensity curve that follows the edit (calmer under
dense explanation, lifting into the breakeven moment).
"""
from __future__ import annotations

import numpy as np
from scipy import signal

SR = 48_000
BPM = 84
PROGRESSION = [  # MIDI notes: Dm9, Bbmaj7, Fmaj7(add9), C6/9
    [50, 57, 60, 64, 65],
    [46, 53, 57, 60, 62],
    [41, 53, 57, 60, 67],
    [48, 55, 57, 62, 64],
]
_rng = np.random.default_rng(7)


def midi_hz(m: float) -> float:
    return 440.0 * 2 ** ((m - 69) / 12)


def _env(n: int, attack: float, release: float) -> np.ndarray:
    a, r = int(attack * SR), int(release * SR)
    e = np.ones(n, np.float32)
    if a:
        e[:a] = np.linspace(0, 1, a) ** 2
    if r:
        e[-r:] *= np.linspace(1, 0, r) ** 2
    return e


def _pad_note(f: float, n: int) -> np.ndarray:
    t = np.arange(n) / SR
    out = np.zeros(n, np.float32)
    for det in (-0.0025, 0.0, 0.0031):
        ff = f * (1 + det)
        for h, amp in ((1, 1.0), (2, 0.32), (3, 0.12), (4, 0.05), (5, 0.025)):
            out += amp * np.sin(2 * np.pi * ff * h * t + _rng.uniform(0, 6.28)).astype(np.float32)
    lfo = 0.85 + 0.15 * np.sin(2 * np.pi * 0.11 * t + _rng.uniform(0, 6.28))
    return out * lfo.astype(np.float32)


def _pluck(f: float, dur: float = 1.1) -> np.ndarray:
    n = int(dur * SR); t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 2 * f * t) + 0.08 * np.sin(2 * np.pi * 3 * f * t))
    return (x * np.exp(-t * 5.5) * _env(n, 0.004, 0.05)).astype(np.float32)


def _reverb(x: np.ndarray, seconds: float = 2.2, mix: float = 0.35) -> np.ndarray:
    n = int(seconds * SR)
    ir = _rng.standard_normal(n).astype(np.float32) * np.exp(-np.linspace(0, 7, n)).astype(np.float32)
    b, a = signal.butter(2, 4500 / (SR / 2), "low")
    ir = signal.lfilter(b, a, ir).astype(np.float32)
    ir /= np.sqrt((ir ** 2).sum()) + 1e-9
    wet = signal.oaconvolve(x, ir, mode="full")[: len(x)].astype(np.float32)
    return (1 - mix) * x + mix * wet


def score(duration: float, intensity: list[tuple[float, float]] | None = None, seed: int = 7) -> np.ndarray:
    """Mono music bed. intensity: [(time, 0..1)] breakpoints controlling pluck/brightness."""
    global _rng
    _rng = np.random.default_rng(seed)
    n = int(duration * SR) + SR
    out = np.zeros(n, np.float32)
    bar = 60 / BPM * 4
    chord_len = bar * 2
    t0, ci = 0.0, 0
    while t0 < duration + 1:
        chord = PROGRESSION[ci % len(PROGRESSION)]
        a, L = int(t0 * SR), int((chord_len + 2.5) * SR)
        seg = np.zeros(L, np.float32)
        for m in chord[1:]:
            seg += 0.16 * _pad_note(midi_hz(m), L)
        seg += 0.30 * _pad_note(midi_hz(chord[0] - 12), L) * 0.6  # sub
        seg *= _env(L, 1.6, 2.4)
        b = min(a + L, n)
        out[a:b] += seg[: b - a]
        t0 += chord_len; ci += 1
    # lowpass the pad for warmth
    bb, aa = signal.butter(2, 2400 / (SR / 2), "low")
    out = signal.lfilter(bb, aa, out).astype(np.float32)

    # pluck arpeggio (8th notes), gain follows intensity
    plucks = np.zeros(n, np.float32)
    step = 60 / BPM / 2
    k = 0
    tt = 0.0
    pattern = [0, 2, 1, 3, 2, 4, 1, 3]
    while tt < duration:
        chord = PROGRESSION[int(tt // chord_len) % len(PROGRESSION)]
        upper = sorted(chord[1:])
        note = upper[pattern[k % 8] % len(upper)] + 12
        p = _pluck(midi_hz(note)) * (0.9 if k % 2 == 0 else 0.6)
        a = int(tt * SR); b = min(a + len(p), n)
        plucks[a:b] += p[: b - a]
        tt += step; k += 1
    gain = _intensity_curve(n, intensity)
    out = out + 0.11 * plucks * gain
    out = _reverb(out, 2.6, 0.38)
    out *= _env(n, 1.5, 3.0)
    out /= np.abs(out).max() + 1e-9
    return out[: int(duration * SR)] * 0.5


def _intensity_curve(n: int, pts: list[tuple[float, float]] | None) -> np.ndarray:
    if not pts:
        return np.full(n, 0.6, np.float32)
    ts = np.array([p[0] for p in pts]) * SR
    vs = np.array([p[1] for p in pts])
    return np.interp(np.arange(n), ts, vs).astype(np.float32)


# ---- sound design ---------------------------------------------------------
def sfx(kind: str) -> np.ndarray:
    if kind == "whoosh":
        n = int(0.55 * SR); t = np.arange(n) / SR
        noise = _rng.standard_normal(n).astype(np.float32)
        out = np.zeros(n, np.float32)
        # sweep a bandpass upward
        chunks = 24
        for i in range(chunks):
            a, b = i * n // chunks, (i + 1) * n // chunks
            fc = 300 * (12 ** (i / chunks))
            bb, aa = signal.butter(2, [fc / (SR / 2), min(fc * 2.2, 20000) / (SR / 2)], "band")
            out[a:b] = signal.lfilter(bb, aa, noise[a:b])
        env = np.sin(np.pi * t / t[-1]) ** 2
        return (out * env * 0.5).astype(np.float32)
    if kind == "tick":
        n = int(0.09 * SR); t = np.arange(n) / SR
        return (0.35 * np.sin(2 * np.pi * 1650 * t) * np.exp(-t * 60)).astype(np.float32)
    if kind == "pop":
        n = int(0.18 * SR); t = np.arange(n) / SR
        f = 520 * np.exp(-t * 8)
        return (0.45 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 22)).astype(np.float32)
    if kind == "chime":  # the breakeven moment
        n = int(2.6 * SR); t = np.arange(n) / SR
        out = np.zeros(n, np.float32)
        for ratio, amp, dec in ((1, 1, 1.6), (2.76, 0.45, 2.4), (5.4, 0.22, 3.5), (8.93, 0.1, 5)):
            for f0 in (midi_hz(74), midi_hz(81)):
                out += amp * np.sin(2 * np.pi * f0 * ratio * t) * np.exp(-t * dec)
        return (0.16 * _reverb(out, 1.8, 0.3)).astype(np.float32)
    if kind == "riser":
        n = int(1.6 * SR); t = np.arange(n) / SR
        noise = _rng.standard_normal(n).astype(np.float32)
        bb, aa = signal.butter(2, 1800 / (SR / 2), "high")
        out = signal.lfilter(bb, aa, noise) * (t / t[-1]) ** 2.5
        return (0.12 * out).astype(np.float32)
    if kind == "thud":
        n = int(0.7 * SR); t = np.arange(n) / SR
        f = 90 * np.exp(-t * 3)
        return (0.6 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6)).astype(np.float32)
    raise KeyError(kind)


def resample(x: np.ndarray, sr_in: int, sr_out: int = SR) -> np.ndarray:
    if sr_in == sr_out:
        return x
    from math import gcd
    g = gcd(sr_in, sr_out)
    return signal.resample_poly(x, sr_out // g, sr_in // g).astype(np.float32)


def duck(music: np.ndarray, voice: np.ndarray, depth_db: float = 9.0) -> np.ndarray:
    """Sidechain-style ducking of music under narration."""
    env = np.abs(voice)
    win = int(0.25 * SR)
    env = np.convolve(env, np.ones(win) / win, mode="same")
    active = np.clip(env / (env.max() * 0.08 + 1e-9), 0, 1)
    # smooth attack/release
    b, a = signal.butter(1, 2.0 / (SR / 2))
    active = signal.filtfilt(b, a, active)
    gain = 10 ** (-depth_db * np.clip(active, 0, 1) / 20)
    return (music * gain).astype(np.float32)


def mix(voice: np.ndarray, music: np.ndarray, effects: np.ndarray, music_db: float = -20.0, sfx_db: float = -8.0) -> np.ndarray:
    n = max(len(voice), len(music), len(effects))
    pad = lambda x: np.pad(x, (0, n - len(x)))  # noqa: E731
    v, m, e = pad(voice), pad(music), pad(effects)
    m = duck(m, v)
    out = v + m * 10 ** (music_db / 20) + e * 10 ** (sfx_db / 20)
    peak = np.abs(out).max()
    if peak > 0.98:
        out *= 0.98 / peak
    return out.astype(np.float32)
