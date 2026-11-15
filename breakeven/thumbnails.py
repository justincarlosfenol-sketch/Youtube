"""Thumbnail templates (1280x720, paper background).

Grammar: ONE number, ONE object, ONE tension device; max ~4 words of text.
Driven by videos/<slug>/thumbnails.yaml. Also writes a mobile-size preview
sheet so legibility at 168x94 can be checked before choosing.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import skia
import yaml

from . import brand as B

TW, TH = 1280, 720


def _hex(v, default=B.INK):
    if not v:
        return default
    return v if v.startswith("#") else getattr(B, v.upper())


def house(c: skia.Canvas, x: float, y: float, s: float, fill: str, roof: str, door: str = B.PAPER):
    """Geometric house icon, bottom-left at (x, y+s), size s."""
    body = skia.Path()
    body.addRect(skia.Rect.MakeXYWH(x + s * 0.12, y + s * 0.45, s * 0.76, s * 0.55))
    c.drawPath(body, B.paint(fill))
    r = skia.Path(); r.moveTo(x, y + s * 0.5); r.lineTo(x + s / 2, y + s * 0.05); r.lineTo(x + s, y + s * 0.5); r.close()
    c.drawPath(r, B.paint(roof))
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x + s * 0.42, y + s * 0.68, s * 0.16, s * 0.32), 6, 6), B.paint(door))
    c.drawRect(skia.Rect.MakeXYWH(x + s * 0.22, y + s * 0.56, s * 0.13, s * 0.12), B.paint(door))
    c.drawRect(skia.Rect.MakeXYWH(x + s * 0.65, y + s * 0.56, s * 0.13, s * 0.12), B.paint(door))


def _frame(c):
    c.clear(B.color(B.PAPER))
    # faint graph-paper texture for brand recognition
    p = B.paint(B.PAPER_2, 1, stroke=2, cap_round=False)
    for x in range(0, TW + 1, 64):
        c.drawLine(x, 0, x, TH, p)
    for y in range(0, TH + 1, 64):
        c.drawLine(0, y, TW, y, p)


def _badge(c):
    B.draw_mark(c, TW - 112, 26, 82, line_hex=B.INK, gap_hex=B.PAPER)


def tpl_number(c, spec):
    _frame(c)
    # crossing lines behind
    lw = 22
    c.drawLine(520, 470, 1130, 470 - 610 * 410 / 720, B.paint(B.EMBER, 0.95, stroke=lw))
    pth = skia.Path(); pth.moveTo(560, 268); pth.quadTo(900, 222, 1240, 268)
    c.drawPath(pth, B.paint(B.TIDE, 0.95, stroke=lw))
    house(c, 770, 400, 290, B.INK, B.EMBER)
    # crossing ring (numerically located)
    best = min((abs((470 - (x - 520) * 410 / 720) - (268 - 2 * (1 - (x - 560) / 680) * ((x - 560) / 680) * 46)), x)
               for x in range(560, 1240))
    cx = best[1]; cy = 470 - (cx - 520) * 410 / 720
    c.drawCircle(cx, cy, 46, B.paint(B.PAPER)); c.drawCircle(cx, cy, 46, B.paint(B.GOLD, stroke=18))
    size = spec.get("size", 250)
    B.draw_text(c, spec["number"], 60, 330, "display_black", size, _hex(spec.get("number_color"), B.INK), tracking=-0.04)
    if spec.get("unit"):
        B.draw_text(c, spec["unit"], 70, 450, "display_black", 120, _hex(spec.get("unit_color"), B.EMBER), tracking=-0.02)
    if spec.get("caption"):
        w = B.text_width(spec["caption"], B.font("display_black", 58)) + 56
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(56, 515, w, 100), 14, 14), B.paint(B.INK))
        B.draw_text(c, spec["caption"], 84, 585, "display_black", 58, B.PAPER)
    _badge(c)


def tpl_versus(c, spec):
    _frame(c)
    L, R = spec["left"], spec["right"]
    for side, x0 in ((L, 0), (R, TW / 2)):
        col = _hex(side.get("color"))
        c.drawRect(skia.Rect.MakeXYWH(x0 + 30, 30, TW / 2 - 60, TH - 60), B.paint(col, 0.10))
        B.draw_text(c, side["label"].upper(), x0 + TW / 4, 175, "display_bold", 58, col, align="center", tracking=0.02)
        B.draw_text(c, side["value"], x0 + TW / 4 + (-12 if x0 == 0 else 12), 390, "display_black", 138, B.INK, align="center", tracking=-0.04)
    c.drawCircle(TW / 2, 340, 54, B.paint(B.GOLD))
    B.draw_text(c, spec.get("operator", "="), TW / 2, 372, "display_black", 90, B.INK, align="center")
    if spec.get("caption"):
        f = B.font("display_black", 70)
        w = f.measureText(spec["caption"]) + 70
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(TW / 2 - w / 2, 505, w, 115), 14, 14), B.paint(B.INK))
        B.draw_text(c, spec["caption"], TW / 2, 588, "display_black", 70, B.PAPER, align="center")
    _badge(c)


def tpl_chart(c, spec):
    _frame(c)
    x = np.asarray(spec["x"], float); a = np.asarray(spec["a"], float); b = np.asarray(spec["b"], float)
    xmax = spec.get("x_max", x[-1]); m = x <= xmax
    x, a, b = x[m], a[m], b[m]
    ymin, ymax = min(a.min(), b.min()), max(a.max(), b.max())
    X0, X1, Y0, Y1 = 90, 1190, 150, 640
    X = lambda v: X0 + v / xmax * (X1 - X0)  # noqa: E731
    Y = lambda v: Y1 - (v - ymin) / (ymax - ymin) * (Y1 - Y0)  # noqa: E731
    for arr, col in ((b, B.TIDE), (a, B.EMBER)):
        p = skia.Path(); p.moveTo(X(x[0]), Y(arr[0]))
        for xx, yy in zip(x[1:], arr[1:]):
            p.lineTo(X(xx), Y(yy))
        c.drawPath(p, B.paint(col, stroke=20))
    bx = spec["cross_x"]; by = float(np.interp(bx, x, a))
    c.drawLine(X(bx), Y0 - 20, X(bx), Y1 + 20, B.paint(B.INK, 0.5, stroke=6))
    c.drawCircle(X(bx), Y(by), 44, B.paint(B.PAPER)); c.drawCircle(X(bx), Y(by), 44, B.paint(B.GOLD, stroke=18))
    B.draw_text(c, spec.get("left_text", ""), X(bx) - 30, 150, "display_black", 92, B.TIDE, align="right")
    B.draw_text(c, spec.get("right_text", ""), X(bx) + 40, 610, "display_black", 92, B.EMBER)
    B.draw_text(c, spec["number"], X(bx) + 70, Y(by) + 40, "display_black", 120, B.INK)
    _badge(c)


TEMPLATES = {"number": tpl_number, "versus": tpl_versus, "chart": tpl_chart}


def _bind(obj, data):
    from .production import _bind as bind
    return bind(obj, data)


def render_all(video_dir: Path) -> list[Path]:
    import json
    video_dir = Path(video_dir).resolve()
    spec = yaml.safe_load((video_dir / "thumbnails.yaml").read_text())
    data = json.loads((video_dir / "data.json").read_text()) if (video_dir / "data.json").exists() else {}
    spec = _bind(spec, data)
    out = video_dir / "output" / "thumbnails"; out.mkdir(parents=True, exist_ok=True)
    paths = []
    for th in spec["thumbnails"]:
        surf = skia.Surface(TW, TH)
        TEMPLATES[th["template"]](surf.getCanvas(), th)
        p = B.save_jpg(surf, out / f"{th['id']}.jpg", 92)
        if p.stat().st_size > 2_000_000:
            B.save_jpg(surf, p, 80)
        paths.append(p)
    _preview_sheet(paths, out / "_preview-mobile-and-desktop.png", spec)
    return paths


def _preview_sheet(paths, out, spec):
    """Simulated feed: each thumbnail at desktop (360x202) and mobile (168x94) size on YouTube dark UI."""
    rows = len(paths)
    W_, H_ = 1000, 60 + rows * 250
    surf = skia.Surface(W_, H_); c = surf.getCanvas(); c.clear(B.color("#0F0F0F"))
    B.draw_text(c, "Feed preview — desktop 360px / mobile 168px", 20, 38, "body_semi", 24, "#FFFFFF")
    for i, p in enumerate(paths):
        img = skia.Image.open(str(p))
        y = 70 + i * 250
        c.drawImageRect(img, skia.Rect.MakeXYWH(20, y, 360, 202), skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear))
        c.drawImageRect(img, skia.Rect.MakeXYWH(420, y, 168, 94), skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear))
        th = spec["thumbnails"][i]
        B.draw_text(c, th["id"], 620, y + 24, "mono_medium", 20, "#AAAAAA")
        lines = _wrap_simple(th.get("title", ""), 30)
        for k, ln in enumerate(lines[:3]):
            B.draw_text(c, ln, 620, y + 60 + k * 30, "body_semi", 22, "#FFFFFF")
    surf.makeImageSnapshot().save(str(out), skia.kPNG)


def _wrap_simple(s, n):
    words, lines, cur = s.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > n and cur:
            lines.append(cur); cur = w
        else:
            cur = (cur + " " + w).strip()
    return lines + ([cur] if cur else [])
