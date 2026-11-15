"""Easing, interpolation and formatting helpers for scene animation."""
from __future__ import annotations

import math


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if x < lo else hi if x > hi else x


def prog(t: float, start: float, dur: float) -> float:
    """Linear 0..1 progress of an animation starting at `start` lasting `dur`."""
    if dur <= 0:
        return 1.0 if t >= start else 0.0
    return clamp((t - start) / dur)


def ease_out(x: float) -> float:          # cubic
    x = clamp(x); return 1 - (1 - x) ** 3


def ease_in_out(x: float) -> float:
    x = clamp(x); return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def ease_out_back(x: float, s: float = 1.4) -> float:
    x = clamp(x); return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


def spring(x: float, damping: float = 7.0, freq: float = 2.2) -> float:
    x = clamp(x)
    return 1 - math.exp(-damping * x) * math.cos(freq * 2 * math.pi * x)


def lerp(a: float, b: float, x: float) -> float:
    return a + (b - a) * x


def appear(t: float, start: float, dur: float = 0.5) -> float:
    return ease_out(prog(t, start, dur))


def fade_out_tail(t: float, duration: float, tail: float = 0.35) -> float:
    """1 until the last `tail` seconds of a shot, then fades to 0 (soft cut)."""
    return clamp((duration - t) / tail) if tail > 0 else 1.0


def money(v: float, decimals: int = 0) -> str:
    sign = "-" if v < 0 else ""
    v = abs(v)
    if decimals:
        return f"{sign}${v:,.{decimals}f}"
    return f"{sign}${v:,.0f}"


def money_short(v: float) -> str:
    a = abs(v); s = "-" if v < 0 else ""
    if a >= 1e6:
        return f"{s}${a/1e6:.2f}M"
    if a >= 1e3:
        return f"{s}${a/1e3:.0f}K"
    return f"{s}${a:.0f}"


def fmt(v: float, kind: str = "money", decimals: int = 0) -> str:
    if kind == "money":
        return money(v, decimals)
    if kind == "pct":
        return f"{v:.{decimals}f}%"
    if kind == "years":
        return f"{v:.{decimals}f} yrs"
    return f"{v:,.{decimals}f}"
