"""Brand tokens and drawing primitives shared by every renderer.

"Ink & Paper": videos are ink-dark with paper-cream type; thumbnails are
paper-cream with ink type (they pop against YouTube's dark UI). Two signal
colours always mean "Choice A" (Ember) vs "Choice B" (Tide): orange vs
blue-teal stays distinguishable under the common colour-vision deficiencies.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import skia

ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / "brand" / "fonts"

# ---- colour tokens -------------------------------------------------------
INK = "#121417"        # video background, thumbnail type
INK_2 = "#1C2026"      # raised panels on ink
INK_3 = "#2A3038"      # gridlines / hairlines on ink
PAPER = "#F3EEE4"      # thumbnail background, video type
PAPER_2 = "#E4DDD0"    # panels on paper
MUTED = "#8C93A0"      # secondary text on ink
EMBER = "#FF5C39"      # Choice A / brand accent
TIDE = "#38B6CC"       # Choice B
GOLD = "#F5B700"       # the breakeven moment (used sparingly)
MINT = "#5CCB8A"       # positive delta
BRICK = "#E5484D"      # negative delta

PALETTE = {k: v for k, v in globals().items() if k.isupper() and isinstance(v, str) and v.startswith("#")}

# ---- typography ----------------------------------------------------------
TYPE = {
    "display_black": "InterDisplay-Black.otf",   # big numbers, thumbnails
    "display_bold": "InterDisplay-Bold.otf",     # headlines
    "display_semi": "InterDisplay-SemiBold.otf",
    "body": "Inter-Regular.otf",
    "body_medium": "Inter-Medium.otf",
    "body_semi": "Inter-SemiBold.otf",
    "serif": "Fraunces-600-normal.ttf",          # editorial accents, chapter titles
    "serif_italic": "Fraunces-400-italic.ttf",
    "serif_black": "Fraunces-900-normal.ttf",
    "mono": "JetBrainsMono-Regular.ttf",         # sources, data labels
    "mono_medium": "JetBrainsMono-Medium.ttf",
}


def color(hex_: str, alpha: float = 1.0) -> int:
    h = hex_.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return skia.Color(r, g, b, max(0, min(255, int(round(alpha * 255)))))


@lru_cache(maxsize=None)
def typeface(role: str) -> skia.Typeface:
    tf = skia.Typeface.MakeFromFile(str(FONTS / TYPE[role]))
    if tf is None:
        raise FileNotFoundError(FONTS / TYPE[role])
    return tf


@lru_cache(maxsize=4096)
def font(role: str, size: float) -> skia.Font:
    f = skia.Font(typeface(role), size)
    f.setSubpixel(True)
    f.setEdging(skia.Font.Edging.kSubpixelAntiAlias)
    return f


def paint(hex_: str, alpha: float = 1.0, stroke: float | None = None, cap_round: bool = True) -> skia.Paint:
    p = skia.Paint(AntiAlias=True, Color=color(hex_, alpha))
    if stroke is not None:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(stroke)
        if cap_round:
            p.setStrokeCap(skia.Paint.kRound_Cap)
            p.setStrokeJoin(skia.Paint.kRound_Join)
    return p


def text_width(s: str, f: skia.Font) -> float:
    return f.measureText(s)


def draw_text(c: skia.Canvas, s: str, x: float, y: float, role: str, size: float, hex_: str,
              alpha: float = 1.0, align: str = "left", tracking: float = 0.0) -> float:
    """Draw text with baseline at y. Returns rendered width."""
    f = font(role, size)
    p = paint(hex_, alpha)
    if tracking:
        w = sum(f.measureText(ch) for ch in s) + tracking * size * (len(s) - 1)
        xx = x - (w if align == "right" else w / 2 if align == "center" else 0)
        for ch in s:
            c.drawString(ch, xx, y, f, p)
            xx += f.measureText(ch) + tracking * size
        return w
    w = f.measureText(s)
    xx = x - (w if align == "right" else w / 2 if align == "center" else 0)
    c.drawString(s, xx, y, f, p)
    return w


def cap_height(role: str, size: float) -> float:
    return font(role, size).getMetrics().fCapHeight


# ---- the mark --------------------------------------------------------------
# Two paths race across a square: the straight Ember line climbs steadily,
# the Paper curve starts ahead and flattens. They cross once: the breakeven.
MARK_A = ((0.17, 0.76), (0.83, 0.20))                      # straight line (overtaker)
MARK_B = ((0.17, 0.44), (0.50, 0.30), (0.83, 0.36))        # curve: starts ahead, flattens
MARK_BASE = ((0.17, 0.86), (0.83, 0.86))                   # chart baseline
MARK_X = (0.46, 0.515)                                      # approx. crossing


def _mark_cross() -> tuple[float, float]:
    """Numerically find where line A meets curve B (unit coordinates)."""
    (x0, y0), (x1, y1) = MARK_A
    p0, p1, p2 = MARK_B
    best = (1e9, 0.5, 0.5)
    for i in range(2001):
        t = i / 2000
        bx = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0]
        by = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]
        ay = y0 + (y1 - y0) * (bx - x0) / (x1 - x0)
        if abs(ay - by) < best[0]:
            best = (abs(ay - by), bx, by)
    return best[1], best[2]


def draw_mark(c: skia.Canvas, x: float, y: float, size: float, line_hex: str = PAPER,
              accent_hex: str = EMBER, bg_hex: str | None = None, progress: float = 1.0,
              gap_hex: str = INK) -> None:
    """Draw the Breakeven mark in the square (x, y, size). progress animates 0..1."""
    if bg_hex:
        c.drawCircle(x + size / 2, y + size / 2, size / 2, paint(bg_hex))
    sw = size * 0.085
    P = lambda u, v: (x + u * size, y + v * size)  # noqa: E731
    p0, p1, p2 = MARK_B
    curve = skia.Path()
    curve.moveTo(*P(*p0)); curve.quadTo(*P(*p1), *P(*p2))
    line = skia.Path()
    line.moveTo(*P(*MARK_A[0])); line.lineTo(*P(*MARK_A[1]))
    bx0, bx1 = P(*MARK_BASE[0]), P(*MARK_BASE[1])
    c.drawLine(bx0[0], bx0[1], bx0[0] + (bx1[0] - bx0[0]) * min(1, progress * 1.5), bx1[1],
               paint(line_hex, 0.45, stroke=sw * 0.55))
    for path, hx in ((curve, line_hex), (line, accent_hex)):
        if progress < 1:
            meas = skia.PathMeasure(path, False)
            seg = skia.Path()
            meas.getSegment(0, meas.getLength() * max(progress, 0.001), seg, True)
            path = seg
        c.drawPath(path, paint(hx, stroke=sw))
    if progress >= 0.85:
        a = min(1.0, (progress - 0.85) / 0.15)
        cx, cy = P(*_mark_cross())
        c.drawCircle(cx, cy, size * 0.075 * a, paint(bg_hex or gap_hex))
        c.drawCircle(cx, cy, size * 0.075 * a, paint(GOLD, stroke=size * 0.04))


def mark_svg(size: int = 512, line_hex: str = PAPER, accent_hex: str = EMBER, bg_hex: str | None = INK) -> str:
    s = size
    sw = s * 0.085
    p0, p1, p2 = MARK_B
    cx, cy = _mark_cross()
    bg = f'<circle cx="{s/2}" cy="{s/2}" r="{s/2}" fill="{bg_hex}"/>' if bg_hex else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {s} {s}" width="{s}" height="{s}">{bg}'
            f'<path d="M{p0[0]*s:.1f},{p0[1]*s:.1f} Q{p1[0]*s:.1f},{p1[1]*s:.1f} {p2[0]*s:.1f},{p2[1]*s:.1f}" '
            f'fill="none" stroke="{line_hex}" stroke-width="{sw:.1f}" stroke-linecap="round"/>'
            f'<line x1="{MARK_A[0][0]*s:.1f}" y1="{MARK_A[0][1]*s:.1f}" x2="{MARK_A[1][0]*s:.1f}" y2="{MARK_A[1][1]*s:.1f}" '
            f'stroke="{accent_hex}" stroke-width="{sw:.1f}" stroke-linecap="round"/>'
            f'<line x1="{MARK_BASE[0][0]*s:.1f}" y1="{MARK_BASE[0][1]*s:.1f}" x2="{MARK_BASE[1][0]*s:.1f}" y2="{MARK_BASE[1][1]*s:.1f}" '
            f'stroke="{line_hex}" stroke-opacity="0.45" stroke-width="{sw*0.55:.1f}" stroke-linecap="round"/>'
            f'<circle cx="{cx*s:.1f}" cy="{cy*s:.1f}" r="{s*0.075:.1f}" fill="{bg_hex or INK}" stroke="{GOLD}" stroke-width="{s*0.04:.1f}"/>'
            f'</svg>')


def surface(w: int, h: int) -> skia.Surface:
    return skia.Surface(w, h)


def save_png(surf: skia.Surface, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    surf.makeImageSnapshot().save(str(path), skia.kPNG)
    return path


def save_jpg(surf: skia.Surface, path: Path, quality: int = 92) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = surf.makeImageSnapshot().encodeToData(skia.kJPEG, quality)
    path.write_bytes(bytes(data))
    return path
