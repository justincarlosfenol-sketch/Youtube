"""Render all channel brand assets into brand/assets/."""
from __future__ import annotations

from pathlib import Path

import skia

from . import brand as B

OUT = B.ROOT / "brand" / "assets"
NAME = "breakeven"
TAGLINE = "We run the numbers on life's expensive decisions."


def wordmark(c: skia.Canvas, x: float, baseline: float, size: float, ink: str, accent: str = B.EMBER) -> float:
    """Lowercase 'breakeven' in Inter Display Bold; the tittle-less word gets an
    accent rule under 'even' (the balance point). Returns width."""
    f = B.font("display_bold", size)
    w = B.draw_text(c, NAME, x, baseline, "display_bold", size, ink, tracking=-0.035)
    # accent underline beneath "even"
    pre = "break"
    pre_w = sum(f.measureText(ch) for ch in pre) + (-0.035 * size) * len(pre)
    even_w = w - pre_w
    y = baseline + size * 0.16
    c.drawLine(x + pre_w + size * 0.02, y, x + pre_w + even_w - size * 0.02, y, B.paint(accent, stroke=size * 0.07))
    return w


def lockup(bg: str, ink: str, path: Path, w: int = 2400, h: int = 800) -> Path:
    s = B.surface(w, h)
    c = s.getCanvas(); c.clear(B.color(bg))
    m = h * 0.56
    B.draw_mark(c, w * 0.08, (h - m) / 2, m, line_hex=ink, gap_hex=bg)
    wordmark(c, w * 0.08 + m * 1.12, h / 2 + h * 0.11, h * 0.30, ink)
    return B.save_png(s, path)


def avatar(path: Path, size: int = 800) -> Path:
    s = B.surface(size, size)
    c = s.getCanvas(); c.clear(B.color(B.INK))
    pad = size * 0.16
    B.draw_mark(c, pad, pad, size - 2 * pad, line_hex=B.PAPER)
    return B.save_png(s, path)


def watermark(path: Path, size: int = 150) -> Path:
    s = skia.Surface(size, size)
    c = s.getCanvas(); c.clear(skia.ColorTRANSPARENT)
    B.draw_mark(c, 0, 0, size, line_hex=B.PAPER, bg_hex=B.INK)
    return B.save_png(s, path)


def _grid(c, w, h, step, hex_, alpha):
    p = B.paint(hex_, alpha, stroke=1.5, cap_round=False)
    for x in range(0, w, step):
        c.drawLine(x, 0, x, h, p)
    for y in range(0, h, step):
        c.drawLine(0, y, w, y, p)


def banner(path: Path, w: int = 2560, h: int = 1440) -> Path:
    """YouTube banner. Safe area (all devices): 1546x423 centred."""
    s = B.surface(w, h)
    c = s.getCanvas(); c.clear(B.color(B.INK))
    _grid(c, w, h, 80, B.INK_3, 0.55)
    # two long racing curves across the full banner (visible on TV), crossing in the safe area
    import math
    def curve(fn, hex_, sw, alpha=1.0):
        p = skia.Path(); first = True
        for i in range(0, 401):
            x = w * i / 400
            y = fn(x / w)
            (p.moveTo if first else p.lineTo)(x, y); first = False
        c.drawPath(p, B.paint(hex_, alpha, stroke=sw))
    cy = h / 2
    # crossing at t~0.88: outside the mobile safe area, visible on desktop/TV
    lin = lambda t: cy + 330 - 612 * t                               # noqa: E731 steady climb
    crv = lambda t: cy - 60 - 160 * (1 - math.exp(-3 * t))           # noqa: E731 starts ahead, flattens
    curve(crv, B.TIDE, 7, 0.55)
    curve(lin, B.EMBER, 7, 0.55)
    # safe area content
    sa_w, sa_h = 1546, 423
    sx, sy = (w - sa_w) / 2, (h - sa_h) / 2
    panel = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(sx - 30, sy + 20, sa_w + 60, sa_h - 40), 28, 28)
    c.drawRRect(panel, B.paint(B.INK, 1.0))
    best = min(((abs(lin(t / 1000) - crv(t / 1000)), t / 1000) for t in range(1000)))
    X, Y = w * best[1], lin(best[1])
    c.drawCircle(X, Y, 22, B.paint(B.INK)); c.drawCircle(X, Y, 22, B.paint(B.GOLD, stroke=8))
    msize = 250
    B.draw_mark(c, sx + 40, sy + (sa_h - msize) / 2, msize, line_hex=B.PAPER)
    tx0 = sx + 40 + msize + 60
    wordmark(c, tx0, sy + 210, 150, B.PAPER)
    B.draw_text(c, TAGLINE, tx0 + 4, sy + 300, "serif_italic", 46, B.PAPER, 0.92)
    B.draw_text(c, "NEW MODEL EVERY TUESDAY", tx0 + 6, sy + 362, "mono_medium", 28, B.EMBER, tracking=0.12)
    return B.save_png(s, path)


def palette_sheet(path: Path) -> Path:
    sw = [("INK", B.INK), ("INK_2", B.INK_2), ("INK_3", B.INK_3), ("PAPER", B.PAPER), ("PAPER_2", B.PAPER_2),
          ("MUTED", B.MUTED), ("EMBER", B.EMBER), ("TIDE", B.TIDE), ("GOLD", B.GOLD), ("MINT", B.MINT), ("BRICK", B.BRICK)]
    W, H = 2200, 1300
    s = B.surface(W, H); c = s.getCanvas(); c.clear(B.color(B.PAPER))
    B.draw_text(c, "Breakeven — brand system", 80, 120, "display_bold", 64, B.INK)
    for i, (n, hx) in enumerate(sw):
        x = 80 + (i % 6) * 340; y = 190 + (i // 6) * 300
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, 300, 180), 18, 18), B.paint(hx))
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, 300, 180), 18, 18), B.paint(B.INK, 0.15, stroke=2))
        B.draw_text(c, n, x, y + 222, "mono_medium", 26, B.INK)
        B.draw_text(c, hx, x, y + 256, "mono", 24, B.MUTED)
    y = 860
    B.draw_text(c, "$2,243", 80, y + 140, "display_black", 170, B.INK)
    B.draw_text(c, "Inter Display Black — numbers", 80, y + 200, "mono", 24, B.MUTED)
    B.draw_text(c, "The fair fight", 900, y + 80, "serif", 84, B.INK)
    B.draw_text(c, "Fraunces — editorial accents", 900, y + 130, "mono", 24, B.MUTED)
    B.draw_text(c, "SOURCE: NAR, OCT 2026", 900, y + 210, "mono_medium", 34, B.EMBER, tracking=0.08)
    B.draw_text(c, "JetBrains Mono — data & sources", 900, y + 250, "mono", 24, B.MUTED)
    B.draw_mark(c, 1800, 900, 300, line_hex=B.PAPER, bg_hex=B.INK)
    return B.save_png(s, path)


def build_all() -> list[Path]:
    OUT.mkdir(parents=True, exist_ok=True)
    out = [
        lockup(B.INK, B.PAPER, OUT / "logo-horizontal-dark.png"),
        lockup(B.PAPER, B.INK, OUT / "logo-horizontal-light.png"),
        avatar(OUT / "avatar-800.png"),
        watermark(OUT / "watermark-150.png"),
        banner(OUT / "banner-2560x1440.png"),
        palette_sheet(OUT / "brand-sheet.png"),
    ]
    (OUT / "mark.svg").write_text(B.mark_svg())
    (OUT / "mark-light.svg").write_text(B.mark_svg(line_hex=B.INK, bg_hex=B.PAPER))
    out += [OUT / "mark.svg", OUT / "mark-light.svg"]
    return out


if __name__ == "__main__":
    for p in build_all():
        print(p)
