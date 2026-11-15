"""Scene base class, background and shared chrome."""
from __future__ import annotations

import skia

from .. import brand as B
from ..anim import appear, clamp

W, H = 1920, 1080
MARGIN = 120


class Scene:
    """A shot. `cues` maps names -> seconds from shot start. Subclasses implement draw_content."""

    name = "base"
    grid = False

    def __init__(self, params: dict, cues: dict[str, float], duration: float, meta: dict | None = None):
        self.p = params or {}
        self.cues = cues
        self.duration = duration
        self.meta = meta or {}
        self.setup()

    def setup(self) -> None:  # precompute
        pass

    def cue(self, name, default: float | None = None) -> float:
        if name is None:
            return default if default is not None else 0.0
        if isinstance(name, (int, float)):
            return float(name)
        if name in self.cues:
            return self.cues[name]
        if default is not None:
            return default
        raise KeyError(f"{self.name}: unknown cue '{name}' (have {sorted(self.cues)})")

    # --- drawing ------------------------------------------------------------
    def draw(self, c: skia.Canvas, t: float) -> None:
        background(c, grid=self.grid or self.p.get("grid", False))
        self.draw_content(c, t)
        chrome(c, t, self.meta.get("chapter_label"), self.p.get("source"), self.duration)

    def draw_content(self, c: skia.Canvas, t: float) -> None:
        raise NotImplementedError


_BG_SHADER = None


def background(c: skia.Canvas, grid: bool = False) -> None:
    global _BG_SHADER
    if _BG_SHADER is None:
        _BG_SHADER = skia.GradientShader.MakeRadial(
            skia.Point(W * 0.5, H * 0.42), W * 0.75,
            [B.color("#1A1E24"), B.color(B.INK)], [0.0, 1.0])
    p = skia.Paint(Shader=_BG_SHADER)
    c.drawRect(skia.Rect.MakeWH(W, H), p)
    if grid:
        gp = B.paint(B.INK_3, 0.35, stroke=1, cap_round=False)
        for x in range(0, W + 1, 80):
            c.drawLine(x, 0, x, H, gp)
        for y in range(0, H + 1, 80):
            c.drawLine(0, y, W, y, gp)


def chrome(c: skia.Canvas, t: float, chapter_label: str | None, source: str | None, duration: float) -> None:
    a = appear(t, 0.1, 0.6)
    if chapter_label:
        c.drawRect(skia.Rect.MakeXYWH(MARGIN, 74, 14, 14), B.paint(B.EMBER, a))
        B.draw_text(c, chapter_label.upper(), MARGIN + 30, 88, "mono_medium", 22, B.MUTED, a, tracking=0.14)
    B.draw_mark(c, W - MARGIN - 44, 58, 44, line_hex=B.PAPER, gap_hex=B.INK)
    if source:
        sa = appear(t, 0.6, 0.6)
        B.draw_text(c, "SOURCE  " + source.upper(), MARGIN, H - 64, "mono", 19, B.MUTED, sa * 0.95, tracking=0.06)


def wrap(text: str, role: str, size: float, max_w: float) -> list[str]:
    f = B.font(role, size)
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if f.measureText(trial.replace("*", "")) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    # keep *highlight* spans balanced across wrapped lines
    out, open_ = [], False
    for ln in lines:
        if open_:
            ln = "*" + ln
        if ln.count("*") % 2 == 1:
            ln += "*"; open_ = True
        else:
            open_ = False
        out.append(ln.replace("**", ""))
    return out


def draw_rich(c: skia.Canvas, line: str, x: float, y: float, role: str, size: float,
              base_hex: str, hi_hex: str, alpha: float = 1.0, align: str = "left") -> float:
    """Draw text where *words* in asterisks are highlighted."""
    f = B.font(role, size)
    parts, hi, buf = [], False, ""
    for ch in line:
        if ch == "*":
            if buf:
                parts.append((buf, hi))
            buf, hi = "", not hi
        else:
            buf += ch
    if buf:
        parts.append((buf, hi))
    total = sum(f.measureText(s) for s, _ in parts)
    xx = x - (total if align == "right" else total / 2 if align == "center" else 0)
    for s, h in parts:
        c.drawString(s, xx, y, f, B.paint(hi_hex if h else base_hex, alpha))
        xx += f.measureText(s)
    return total


def rrect(c: skia.Canvas, x, y, w, h, r, hex_, alpha=1.0, stroke=None):
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r),
                B.paint(hex_, alpha, stroke=stroke, cap_round=False))


def dashed_line(c, x0, y0, x1, y1, hex_, alpha=1.0, width=2.0, dash=(10, 10)):
    p = B.paint(hex_, alpha, stroke=width, cap_round=False)
    p.setPathEffect(skia.DashPathEffect.Make(list(dash), 0))
    c.drawLine(x0, y0, x1, y1, p)


def with_alpha(c: skia.Canvas, alpha: float):
    """Context manager-ish: returns save count; caller must c.restore()."""
    return c.saveLayerAlpha(None, int(clamp(alpha) * 255))
