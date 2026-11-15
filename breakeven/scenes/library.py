"""The Breakeven scene library. Each class is a reusable, parameterised shot."""
from __future__ import annotations

import math

import numpy as np
import skia

from .. import brand as B
from ..anim import appear, clamp, ease_in_out, ease_out, ease_out_back, lerp, money, money_short, prog
from .base import MARGIN, H, W, Scene, dashed_line, draw_rich, rrect, wrap

REGISTRY: dict[str, type[Scene]] = {}


def register(cls):
    REGISTRY[cls.name] = cls
    return cls


def _hex(name_or_hex: str | None, default: str = B.PAPER) -> str:
    if not name_or_hex:
        return default
    return name_or_hex if name_or_hex.startswith("#") else getattr(B, name_or_hex.upper())


# ---------------------------------------------------------------------------
@register
class TitleCard(Scene):
    """Chapter opener. params: number, title, kicker"""
    name = "chapter"

    def draw(self, c, t):  # no chrome on chapter cards
        from .base import background
        background(c)
        self.draw_content(c, t)

    def draw_content(self, c, t):
        a = appear(t, 0.0, 0.5)
        msize = 120
        B.draw_mark(c, MARGIN, H / 2 - 230, msize, line_hex=B.PAPER, gap_hex=B.INK, progress=ease_in_out(prog(t, 0, 1.0)))
        num = self.p.get("number", "")
        B.draw_text(c, f"CHAPTER {num}", MARGIN, H / 2 - 40, "mono_medium", 30, B.EMBER, a, tracking=0.18)
        ta = appear(t, 0.25, 0.7)
        y = H / 2 + 80 + (1 - ta) * 40
        B.draw_text(c, self.p.get("title", ""), MARGIN - 6, y, "serif", 132, B.PAPER, ta)
        if self.p.get("kicker"):
            ka = appear(t, 0.6, 0.7)
            B.draw_text(c, self.p["kicker"], MARGIN, y + 90, "body", 40, B.MUTED, ka)


# ---------------------------------------------------------------------------
@register
class BigNumber(Scene):
    """One or two hero numbers.
    params: kicker, items:[{value, count, kind, label, sub, color, cue}], equals_cue, verdict:{text,cue,color}
    """
    name = "bignumber"

    def draw_content(self, c, t):
        items = self.p["items"]
        if self.p.get("kicker"):
            ka = appear(t, 0.0, 0.5)
            B.draw_text(c, self.p["kicker"].upper(), W / 2, 250, "mono_medium", 30, B.MUTED, ka, align="center", tracking=0.16)
        n = len(items)
        xs = [W / 2] if n == 1 else [W * 0.30, W * 0.70] if n == 2 else [W * (i + 1) / (n + 1) for i in range(n)]
        size = 230 if n == 1 else 170
        for it, x in zip(items, xs):
            st = self.cue(it.get("cue"), 0.2)
            a = appear(t, st, 0.55)
            if a <= 0:
                continue
            s = ease_out_back(prog(t, st, 0.6))
            col = _hex(it.get("color"), B.PAPER)
            if "count" in it:
                v = it["count"] * ease_out(prog(t, st, it.get("count_dur", 1.2)))
                d = it.get("decimals", 0)
                kind = it.get("kind", "money")
                txt = money(v, d) if kind == "money" else f"{v:.{d}f}{it.get('suffix', '')}"
            else:
                txt = it["value"]
            c.save()
            c.translate(x, H / 2 + 60)
            c.scale(0.85 + 0.15 * s, 0.85 + 0.15 * s)
            B.draw_text(c, txt, 0, 0, "display_black", size, col, a, align="center", tracking=-0.02)
            c.restore()
            if it.get("label"):
                B.draw_text(c, it["label"], x, H / 2 + 150, "body_semi", 40, B.PAPER, a * 0.95, align="center")
            if it.get("sub"):
                B.draw_text(c, it["sub"], x, H / 2 + 205, "body", 30, B.MUTED, a, align="center")
        if self.p.get("equals_cue") is not None and n == 2:
            ea = appear(t, self.cue(self.p["equals_cue"]), 0.4)
            s = ease_out_back(prog(t, self.cue(self.p["equals_cue"]), 0.5))
            c.save(); c.translate(W / 2, H / 2 + 38); c.scale(s, s)
            B.draw_text(c, self.p.get("operator", "="), 0, 0, "display_black", 160, B.GOLD, ea, align="center")
            c.restore()
        v = self.p.get("verdict")
        if v:
            va = appear(t, self.cue(v.get("cue"), 1.0), 0.5)
            draw_rich(c, v["text"], W / 2, H - 170, "serif_italic", 54, B.PAPER, _hex(v.get("color"), B.EMBER), va, align="center")


# ---------------------------------------------------------------------------
@register
class Statement(Scene):
    """Big editorial sentence. *word* highlights. params: text, cue, size, color"""
    name = "statement"

    def draw_content(self, c, t):
        size = self.p.get("size", 88)
        lines = wrap(self.p["text"], "serif", size, W - 2 * MARGIN - 200)
        lh = size * 1.22
        y0 = H / 2 - (len(lines) - 1) * lh / 2 + size * 0.3
        st = self.cue(self.p.get("cue"), 0.15)
        for i, ln in enumerate(lines):
            a = appear(t, st + i * 0.22, 0.6)
            draw_rich(c, ln, MARGIN + 60, y0 + i * lh + (1 - a) * 24, "serif", size, B.PAPER,
                      _hex(self.p.get("color"), B.EMBER), a)
        if self.p.get("footnote"):
            fa = appear(t, self.cue(self.p.get("footnote_cue"), st + 1.0), 0.6)
            B.draw_text(c, self.p["footnote"], MARGIN + 60, y0 + len(lines) * lh + 30, "body", 34, B.MUTED, fa)


# ---------------------------------------------------------------------------
@register
class StackCompare(Scene):
    """Rent bar vs stacked ownership-cost bar.
    params: left:{label,value,color}, layers:[{label,value,color,cue}], right_label,
            waterline_cue (draws the 'what people compare' line at left value), delta_cue, max
    """
    name = "stack"
    grid = False

    def draw_content(self, c, t):
        left, layers = self.p["left"], self.p["layers"]
        vmax = self.p.get("max", max(left["value"], sum(l["value"] for l in layers)) * 1.12)
        base_y, top_y = H - 190, 230
        scale = (base_y - top_y) / vmax
        bw = 300
        lx, rx = W * 0.30 - bw / 2, W * 0.62 - bw / 2
        # baseline
        c.drawLine(MARGIN, base_y, W - MARGIN, base_y, B.paint(B.INK_3, 1, stroke=3))
        # left bar
        la = appear(t, self.cue(left.get("cue"), 0.2), 0.8)
        lh = left["value"] * scale * la
        rrect(c, lx, base_y - lh, bw, lh, 10, _hex(left.get("color"), B.TIDE))
        B.draw_text(c, left["label"], lx + bw / 2, base_y + 60, "body_semi", 38, B.PAPER, la, align="center")
        B.draw_text(c, money(left["value"] * la), lx + bw / 2, base_y - lh - 26, "display_bold", 54, B.PAPER, la, align="center")
        # right stack
        y = base_y
        total_shown = 0.0
        for i, l in enumerate(layers):
            st = self.cue(l.get("cue"), 0.6 + i * 0.6)
            a = ease_out(prog(t, st, 0.7))
            if a <= 0:
                continue
            h = l["value"] * scale * a
            col = _hex(l.get("color"), B.EMBER)
            c.drawRect(skia.Rect.MakeXYWH(rx, y - h, bw, h), B.paint(col, 0.92 if i % 2 == 0 else 0.78))
            c.drawLine(rx, y - h, rx + bw, y - h, B.paint(B.INK, 1, stroke=3))
            # label to the right
            if h > 26:
                B.draw_text(c, l["label"], rx + bw + 34, y - h / 2 + 12, "body_medium", 32, B.PAPER, a)
                B.draw_text(c, money(l["value"]), rx + bw + 34 + B.text_width(l["label"], B.font("body_medium", 32)) + 18,
                            y - h / 2 + 12, "mono_medium", 30, B.MUTED, a)
            y -= h
            total_shown += l["value"] * a
        if total_shown > 0:
            B.draw_text(c, money(total_shown), rx + bw / 2, y - 26, "display_bold", 54, B.PAPER, 1, align="center")
        B.draw_text(c, self.p.get("right_label", "Owning"), rx + bw / 2, base_y + 60, "body_semi", 38, B.PAPER,
                    appear(t, 0.5, 0.6), align="center")
        # waterline at rent level
        if self.p.get("waterline_cue") is not None:
            wa = appear(t, self.cue(self.p["waterline_cue"]), 0.6)
            wy = base_y - left["value"] * scale
            dashed_line(c, MARGIN, wy, MARGIN + (rx + bw + 40 - MARGIN) * wa, wy, B.GOLD, 0.95, 3, (14, 10))
            if self.p.get("waterline_label"):
                words = self.p["waterline_label"].split()
                half = (len(words) + 1) // 2
                for k, ln in enumerate((" ".join(words[:half]), " ".join(words[half:]))):
                    B.draw_text(c, ln, lx - 36, wy - 50 + k * 30, "mono_medium", 22, B.GOLD, wa, align="right", tracking=0.08)
        if self.p.get("delta_cue") is not None:
            da = appear(t, self.cue(self.p["delta_cue"]), 0.6)
            delta = sum(l["value"] for l in layers) - left["value"]
            txt = ("+" if delta >= 0 else "") + money(delta) + self.p.get("delta_suffix", " / month")
            rrect(c, W - MARGIN - 420, 210, 420, 120, 16, B.INK_2, da)
            B.draw_text(c, txt, W - MARGIN - 210, 288, "display_bold", 52, B.BRICK if delta > 0 else B.MINT, da, align="center")


# ---------------------------------------------------------------------------
@register
class SplitBar(Scene):
    """Horizontal bar split into parts. params: title, total_label, parts:[{label,value,color,cue}]"""
    name = "splitbar"

    def draw_content(self, c, t):
        parts = self.p["parts"]
        total = sum(p["value"] for p in parts)
        x0, x1, y, h = MARGIN + 40, W - MARGIN - 40, H / 2 - 40, 150
        if self.p.get("title"):
            B.draw_text(c, self.p["title"], x0, 260, "display_bold", 64, B.PAPER, appear(t, 0, 0.5))
        rrect(c, x0, y, x1 - x0, h, 14, B.INK_2)
        xx = x0
        for i, p in enumerate(parts):
            st = self.cue(p.get("cue"), 0.3 + i * 0.8)
            a = ease_out(prog(t, st, 0.9))
            wfull = (x1 - x0) * p["value"] / total
            w = wfull * a
            col = _hex(p.get("color"), B.EMBER)
            c.save(); c.clipRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x0, y, x1 - x0, h), 14, 14), skia.ClipOp.kIntersect, True)
            c.drawRect(skia.Rect.MakeXYWH(xx, y, w, h), B.paint(col))
            c.restore()
            la = appear(t, st + 0.3, 0.5)
            pct = p["value"] / total * 100
            lx = xx + (wfull / 2 if wfull > 360 else 0)
            al = "center" if wfull > 360 else "left"
            if wfull <= 360:
                lx, al = x1, "right"
            B.draw_text(c, money(p["value"]), lx, y + h + 90, "display_black", 76, col, la, align=al)
            B.draw_text(c, f"{p['label']}  ·  {pct:.0f}%", lx, y + h + 140, "body_medium", 32, B.PAPER, la, align=al)
            xx += wfull
        if self.p.get("total_label"):
            B.draw_text(c, self.p["total_label"], x0, y - 30, "mono_medium", 26, B.MUTED, appear(t, 0.1, 0.5), tracking=0.1)


# ---------------------------------------------------------------------------
@register
class Assumptions(Scene):
    """Grid of assumption cards. params: title, cards:[{label,value,source,color,cue}], cols"""
    name = "assumptions"

    def draw_content(self, c, t):
        cards = self.p["cards"]
        cols = self.p.get("cols", 3)
        if self.p.get("title"):
            B.draw_text(c, self.p["title"], MARGIN, 200, "serif", 64, B.PAPER, appear(t, 0, 0.5))
        gw = (W - 2 * MARGIN - (cols - 1) * 28) / cols
        gh = 196
        rows = math.ceil(len(cards) / cols)
        y0 = 250 if rows <= 3 else 235
        n = len(cards)
        span = max(self.duration - 1.5, 1.0)
        for i, cd in enumerate(cards):
            r, k = divmod(i, cols)
            x, y = MARGIN + k * (gw + 28), y0 + r * (gh + 26)
            st = self.cue(cd.get("cue"), 0.3 + i * span / max(n, 1) * 0.8)
            a = appear(t, st, 0.5)
            if a <= 0:
                continue
            yy = y + (1 - a) * 20
            rrect(c, x, yy, gw, gh, 16, B.INK_2, a)
            c.drawRect(skia.Rect.MakeXYWH(x, yy + 22, 6, gh - 44), B.paint(_hex(cd.get("color"), B.EMBER), a))
            B.draw_text(c, cd["label"].upper(), x + 34, yy + 54, "mono_medium", 21, B.MUTED, a, tracking=0.1)
            B.draw_text(c, cd["value"], x + 34, yy + 128, "display_bold", 62, B.PAPER, a)
            if cd.get("source"):
                B.draw_text(c, cd["source"], x + 34, yy + 170, "mono", 19, B.MUTED, a * 0.9)


# ---------------------------------------------------------------------------
class _Chart:
    """Axis mapping helper for line charts."""

    def __init__(self, x0, y0, x1, y1, xmin, xmax, ymin, ymax):
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1
        self.xmin, self.xmax, self.ymin, self.ymax = xmin, xmax, ymin, ymax

    def X(self, v):
        return self.x0 + (v - self.xmin) / (self.xmax - self.xmin) * (self.x1 - self.x0)

    def Y(self, v):
        return self.y1 - (v - self.ymin) / (self.ymax - self.ymin) * (self.y1 - self.y0)


def _nice_step(span: float, target: int = 5) -> float:
    raw = span / target
    mag = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 2.5, 5, 10):
        if raw <= m * mag:
            return m * mag
    return 10 * mag


@register
class Race(Scene):
    """Two series racing over time; marks the crossing (breakeven).
    params: series:[{name,color,y:[...]}], x:[...] (years), x_max, y_max, y_min,
            draw_start_cue, draw_end_cue, breakeven:{x,label}, annotations:[{x,series,text,cue}],
            y_label, end_labels: bool
    """
    name = "race"
    grid = False

    def setup(self):
        self.x = np.asarray(self.p["x"], float)
        xmax = self.p.get("x_max", float(self.x[-1]))
        mask = self.x <= xmax + 1e-9
        self.x = self.x[mask]
        self.series = [dict(s, y=np.asarray(s["y"], float)[mask]) for s in self.p["series"]]
        ymax = self.p.get("y_max") or max(float(s["y"].max()) for s in self.series) * 1.08
        ymin = self.p.get("y_min", 0)
        self.ch = _Chart(MARGIN + 150, 210, W - MARGIN - 250, H - 200, 0, xmax, ymin, ymax)

    def draw_content(self, c, t):
        ch = self.ch
        ga = appear(t, 0, 0.6)
        # gridlines + y labels
        step = _nice_step(ch.ymax - ch.ymin, 5)
        v = math.ceil(ch.ymin / step) * step
        while v <= ch.ymax + 1e-6:
            y = ch.Y(v)
            c.drawLine(ch.x0, y, ch.x1, y, B.paint(B.INK_3, ga, stroke=1.5, cap_round=False))
            B.draw_text(c, money_short(v), ch.x0 - 24, y + 9, "mono", 24, B.MUTED, ga, align="right")
            v += step
        xstep = _nice_step(ch.xmax, 6)
        xv = 0.0
        while xv <= ch.xmax + 1e-6:
            B.draw_text(c, f"{xv:g}", ch.X(xv), ch.y1 + 42, "mono", 24, B.MUTED, ga, align="center")
            xv += xstep
        B.draw_text(c, self.p.get("x_label", "YEARS"), ch.x1, ch.y1 + 84, "mono_medium", 22, B.MUTED, ga, align="right", tracking=0.12)
        if self.p.get("y_label"):
            B.draw_text(c, self.p["y_label"].upper(), ch.x0 - 150, ch.y0 - 40, "mono_medium", 22, B.MUTED, ga, tracking=0.12)
        if ch.ymin < 0:
            c.drawLine(ch.x0, ch.Y(0), ch.x1, ch.Y(0), B.paint(B.PAPER, 0.4 * ga, stroke=2, cap_round=False))

        s0, s1 = self._draw_window()
        pr = ease_in_out(prog(t, s0, s1 - s0))
        xcur = ch.xmax * pr
        n_vis = max(2, int(np.searchsorted(self.x, xcur, side="right")))
        tips = [float(np.interp(min(xcur, self.x[-1]), self.x, s["y"])) for s in self.series]
        label_y = [ch.Y(v) for v in tips]
        if len(label_y) == 2 and abs(label_y[0] - label_y[1]) < 76:
            mid = (label_y[0] + label_y[1]) / 2
            up = 0 if tips[0] >= tips[1] else 1
            label_y[up], label_y[1 - up] = mid - 38, mid + 38
        for si, s in enumerate(self.series):
            col = _hex(s.get("color"), B.EMBER)
            path = skia.Path()
            xs, ys = self.x[:n_vis], s["y"][:n_vis]
            path.moveTo(ch.X(xs[0]), ch.Y(ys[0]))
            for xx, yy in zip(xs[1:], ys[1:]):
                path.lineTo(ch.X(xx), ch.Y(yy))
            # interpolate tip
            if n_vis < len(self.x):
                yt = float(np.interp(xcur, self.x, s["y"]))
                path.lineTo(ch.X(xcur), ch.Y(yt))
            else:
                yt = float(s["y"][-1])
                xcur_ = self.x[-1]
            c.drawPath(path, B.paint(col, ga, stroke=7))
            tipx = ch.X(min(xcur, self.x[-1]))
            c.drawCircle(tipx, ch.Y(yt), 10, B.paint(col, ga))
            if self.p.get("end_labels", True):
                ly = label_y[si]
                B.draw_text(c, s["name"], tipx + 22, ly - 4, "body_semi", 30, col, ga)
                B.draw_text(c, money_short(yt), tipx + 22 + B.text_width(s["name"], B.font("body_semi", 30)) + 14, ly - 4,
                            "mono_medium", 26, B.PAPER, ga * 0.9)

        be = self.p.get("breakeven")
        if be and be.get("x") is not None and xcur >= be["x"]:
            bt = s0 + (s1 - s0) * self._inv_ease(be["x"] / ch.xmax)
            ba = appear(t, bt, 0.5)
            bx = ch.X(be["x"])
            by = ch.Y(float(np.interp(be["x"], self.x, self.series[0]["y"])))
            dashed_line(c, bx, ch.y0, bx, ch.y1, B.GOLD, 0.8 * ba, 3, (12, 10))
            pulse = 1 + 0.5 * math.exp(-3 * max(t - bt, 0)) * abs(math.sin(10 * max(t - bt, 0)))
            c.drawCircle(bx, by, 22 * ba * pulse, B.paint(B.INK))
            c.drawCircle(bx, by, 22 * ba * pulse, B.paint(B.GOLD, ba, stroke=7))
            rrect(c, bx - 200, ch.y0 - 74, 400, 64, 12, B.GOLD, ba)
            B.draw_text(c, be.get("label", f"BREAKEVEN · YEAR {be['x']:.1f}").upper(), bx, ch.y0 - 31, "mono_medium", 26,
                        B.INK, ba, align="center", tracking=0.08)
        for an in self.p.get("annotations", []):
            aa = appear(t, self.cue(an.get("cue"), 1.0), 0.5)
            if aa <= 0:
                continue
            si = an.get("series", 0)
            ax = ch.X(an["x"]); ay = ch.Y(float(np.interp(an["x"], self.x, self.series[si]["y"])))
            tx, ty = ax + an.get("dx", 60), ay + an.get("dy", -110)
            c.drawLine(ax, ay, tx, ty + 14, B.paint(B.PAPER, 0.6 * aa, stroke=2))
            lines = an["text"].split("\n")
            for k, ln in enumerate(lines):
                B.draw_text(c, ln, tx + 8, ty - (len(lines) - 1 - k) * 38, "body_medium", 30, B.PAPER, aa)

    def _draw_window(self):
        s0 = self.cue(self.p.get("draw_start_cue"), 0.6)
        be = self.p.get("breakeven") or {}
        if be.get("cue") is not None and be.get("x") is not None:
            # choose the draw end so the lines cross exactly on the spoken cue
            frac = self._inv_ease(be["x"] / self.ch.xmax)
            s1 = s0 + (self.cue(be["cue"]) + be.get("cue_offset", 0.0) - s0) / max(frac, 1e-3)
        else:
            s1 = self.cue(self.p.get("draw_end_cue"), max(s0 + 1.0, self.duration * 0.75))
        return s0, s1

    def audio_events(self):
        be = self.p.get("breakeven")
        if not be or be.get("x") is None or be.get("sfx") is False:
            return []
        s0, s1 = self._draw_window()
        bt = s0 + (s1 - s0) * self._inv_ease(be["x"] / self.ch.xmax)
        return [(bt - 1.6, "riser"), (bt, "chime")]

    @staticmethod
    def _inv_ease(target: float) -> float:
        lo, hi = 0.0, 1.0
        for _ in range(40):
            mid = (lo + hi) / 2
            if ease_in_out(mid) < target:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2


# ---------------------------------------------------------------------------
@register
class Lever(Scene):
    """One input slides between stops; the 'buying advantage' curve morphs and the
    breakeven readout updates.  params: label, stops:[{label, be, adv:[...], cue}], x:[...]
    adv = buyer_nw - renter_nw per year (crossing zero = breakeven)."""
    name = "lever"

    def setup(self):
        self.x = np.asarray(self.p["x"], float)
        self.stops = self.p["stops"]
        win = self.x <= self.p.get("scale_years", 15)
        allv = np.concatenate([np.asarray(s["adv"], float)[win] for s in self.stops])
        lim = max(abs(allv.min()), abs(allv.max())) * 1.15
        self.ch = _Chart(MARGIN + 150, 420, W - MARGIN - 60, H - 170, 0, self.x[-1], -lim, lim)
        # sequence of slider moves: [{stop: index, cue}] (defaults to visiting stops in order)
        seq = self.p.get("sequence") or [{"stop": i, "cue": s.get("cue")} for i, s in enumerate(self.stops)]
        self.seq = [(self.cue(m.get("cue"), 0.4 + i * 2.5), int(m["stop"])) for i, m in enumerate(seq)]

    def _state(self, t):
        """Slider position (float index into stops) at time t."""
        pos = float(self.seq[0][1])
        for i in range(1, len(self.seq)):
            ts, target = self.seq[i]
            prev = self.seq[i - 1][1]
            if t < ts:
                break
            pos = lerp(prev, target, ease_in_out(prog(t, ts, 0.9)))
        return pos

    def draw_content(self, c, t):
        ch = self.ch
        a = appear(t, 0, 0.5)
        B.draw_text(c, self.p["label"].upper(), MARGIN, 205, "mono_medium", 28, B.MUTED, a, tracking=0.14)
        # slider track
        sx0, sx1, sy = MARGIN, MARGIN + 900, 290
        c.drawLine(sx0, sy, sx1, sy, B.paint(B.INK_3, a, stroke=8))
        k = len(self.stops)
        pos = self._state(t)
        for i, s in enumerate(self.stops):
            px = sx0 + (sx1 - sx0) * (i / (k - 1) if k > 1 else 0.5)
            c.drawCircle(px, sy, 7, B.paint(B.MUTED, a))
            act = 1 - clamp(abs(pos - i))
            B.draw_text(c, s["label"], px, sy + 62, "display_bold", 38, B.PAPER if act > 0.5 else B.MUTED, a, align="center")
        kx = sx0 + (sx1 - sx0) * (pos / (k - 1) if k > 1 else 0.5)
        c.drawCircle(kx, sy, 20, B.paint(B.EMBER, a))
        c.drawCircle(kx, sy, 20, B.paint(B.INK, a, stroke=4))
        # interpolated advantage curve
        i0 = int(math.floor(pos)); i1 = min(i0 + 1, k - 1); f = pos - i0
        adv = (1 - f) * np.asarray(self.stops[i0]["adv"], float) + f * np.asarray(self.stops[i1]["adv"], float)
        # gridlines with values, zero line + labels
        step = _nice_step(ch.ymax, 2)
        v = step
        while v < ch.ymax:
            for sv in (v, -v):
                c.drawLine(ch.x0, ch.Y(sv), ch.x1, ch.Y(sv), B.paint(B.INK_3, a, stroke=1.5, cap_round=False))
                B.draw_text(c, ("+" if sv > 0 else "") + money_short(sv), ch.x1, ch.Y(sv) - 10, "mono", 20, B.MUTED, a, align="right")
            v += step
        c.drawLine(ch.x0, ch.Y(0), ch.x1, ch.Y(0), B.paint(B.PAPER, 0.5 * a, stroke=2, cap_round=False))
        c.save()
        c.clipRect(skia.Rect.MakeLTRB(ch.x0 - 4, ch.y0 - 6, ch.x1 + 4, ch.y1 + 6))
        B.draw_text(c, "BUYING AHEAD", ch.x0 - 20, ch.Y(0) - 60, "mono_medium", 20, B.EMBER, a, align="right", tracking=0.08)
        B.draw_text(c, "RENTING AHEAD", ch.x0 - 20, ch.Y(0) + 76, "mono_medium", 20, B.TIDE, a, align="right", tracking=0.08)
        for xv in (0, 5, 10, 15, 20, 25, 30):
            if xv <= ch.xmax:
                B.draw_text(c, str(xv), ch.X(xv), ch.y1 + 40, "mono", 22, B.MUTED, a, align="center")
        B.draw_text(c, "YEARS", ch.x1, ch.y1 + 78, "mono_medium", 20, B.MUTED, a, align="right", tracking=0.12)
        # fill above/below zero
        def area(sign, hex_):
            pth = skia.Path(); pth.moveTo(ch.X(self.x[0]), ch.Y(0))
            for xx, yy in zip(self.x, adv):
                pth.lineTo(ch.X(xx), ch.Y(max(yy, 0) if sign > 0 else min(yy, 0)))
            pth.lineTo(ch.X(self.x[-1]), ch.Y(0)); pth.close()
            c.drawPath(pth, B.paint(hex_, 0.28 * a))
        area(1, B.EMBER); area(-1, B.TIDE)
        line = skia.Path(); line.moveTo(ch.X(self.x[0]), ch.Y(adv[0]))
        for xx, yy in zip(self.x[1:], adv[1:]):
            line.lineTo(ch.X(xx), ch.Y(yy))
        c.drawPath(line, B.paint(B.PAPER, a, stroke=5))
        # crossing
        cross = None
        for j in range(1, len(adv)):
            if adv[j - 1] < 0 <= adv[j]:
                cross = self.x[j - 1] + (self.x[j] - self.x[j - 1]) * (-adv[j - 1]) / (adv[j] - adv[j - 1])
                break
        if cross is not None:
            c.drawCircle(ch.X(cross), ch.Y(0), 16, B.paint(B.INK, a))
            c.drawCircle(ch.X(cross), ch.Y(0), 16, B.paint(B.GOLD, a, stroke=6))
        c.restore()
        # readout
        cur = self.stops[int(round(pos))]
        be = cur.get("be")
        txt = f"{be:.1f} yrs" if be is not None else cur.get("never_label", "30+ yrs")
        rrect(c, W - MARGIN - 560, 175, 560, 160, 18, B.INK_2, a)
        B.draw_text(c, "BUYING BREAKS EVEN AFTER", W - MARGIN - 530, 222, "mono_medium", 22, B.MUTED, a, tracking=0.1)
        B.draw_text(c, txt, W - MARGIN - 530, 305, "display_black", 76, B.GOLD if be is not None else B.BRICK, a)


# ---------------------------------------------------------------------------
@register
class Heatmap(Scene):
    """Breakeven map. params: title, xs_labels, ys_labels, values (rows=ys), x_title, y_title,
    highlight:{row,col,cue,label}, reveal_cue"""
    name = "heatmap"

    @staticmethod
    def _col(v):
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return B.color("#24282F")
        stops = [(1, "#F5B700"), (5, "#FF8A2A"), (10, "#E5484D"), (20, "#6B2A2A")]
        v = clamp(v, 1, 20)
        for (a, ca), (b, cb) in zip(stops, stops[1:]):
            if v <= b:
                f = (v - a) / (b - a)
                ra, rb = int(ca[1:3], 16), int(cb[1:3], 16)
                ga, gb = int(ca[3:5], 16), int(cb[3:5], 16)
                ba_, bb = int(ca[5:7], 16), int(cb[5:7], 16)
                return skia.Color(int(lerp(ra, rb, f)), int(lerp(ga, gb, f)), int(lerp(ba_, bb, f)))
        return B.color(stops[-1][1])

    def draw_content(self, c, t):
        vals = self.p["values"]
        rows, cols = len(vals), len(vals[0])
        x0, y0 = MARGIN + 260, 250
        cw = (W - MARGIN - 80 - x0) / cols
        chh = (H - 230 - y0) / rows
        a = appear(t, 0, 0.5)
        if self.p.get("title"):
            B.draw_text(c, self.p["title"], MARGIN, 178, "serif", 54, B.PAPER, a)
        rc = self.cue(self.p.get("reveal_cue"), 0.3)
        for r in range(rows):
            B.draw_text(c, self.p["ys_labels"][r], x0 - 30, y0 + r * chh + chh / 2 + 12, "mono_medium", 30, B.PAPER, a, align="right")
            for k in range(cols):
                ca = appear(t, rc + (r + k) * 0.06, 0.4)
                v = vals[r][k]
                p = skia.Paint(AntiAlias=True, Color=self._col(v))
                p.setAlphaf(ca)
                rect = skia.Rect.MakeXYWH(x0 + k * cw + 4, y0 + r * chh + 4, cw - 8, chh - 8)
                c.drawRRect(skia.RRect.MakeRectXY(rect, 8, 8), p)
                never = v is None or (isinstance(v, float) and math.isnan(v))
                txt = "30+" if never else f"{v:.1f}"
                B.draw_text(c, txt, x0 + k * cw + cw / 2, y0 + r * chh + chh / 2 + 13, "display_bold", 36,
                            B.MUTED if never else B.INK, ca, align="center")
        for k in range(cols):
            B.draw_text(c, self.p["xs_labels"][k], x0 + k * cw + cw / 2, y0 + rows * chh + 44, "mono_medium", 28, B.PAPER, a, align="center")
        B.draw_text(c, self.p.get("x_title", "").upper(), x0 + cols * cw / 2, y0 + rows * chh + 92, "mono_medium", 22, B.MUTED, a, align="center", tracking=0.12)
        c.save(); c.translate(MARGIN + 30, y0 + rows * chh / 2); c.rotate(-90)
        B.draw_text(c, self.p.get("y_title", "").upper(), 0, 0, "mono_medium", 22, B.MUTED, a, align="center", tracking=0.12)
        c.restore()
        hl = self.p.get("highlight")
        if hl:
            ha = appear(t, self.cue(hl.get("cue"), rc + 2.0), 0.5)
            rect = skia.Rect.MakeXYWH(x0 + hl["col"] * cw - 2, y0 + hl["row"] * chh - 2, cw + 4, chh + 4)
            c.drawRRect(skia.RRect.MakeRectXY(rect, 10, 10), B.paint(B.PAPER, ha, stroke=6, cap_round=False))
            if hl.get("label"):
                px, py = x0 + hl["col"] * cw + cw / 2, y0 + hl["row"] * chh
                pw = B.text_width(hl["label"], B.font("mono_medium", 20)) + 34
                rrect(c, px - pw / 2, py - 15, pw, 30, 15, B.PAPER, ha)
                B.draw_text(c, hl["label"], px, py + 7, "mono_medium", 20, B.INK, ha, align="center", tracking=0.06)


# ---------------------------------------------------------------------------
@register
class Checklist(Scene):
    """params: title, items:[{text, cue, mark}] mark in {'check','x','dot','num'}"""
    name = "checklist"

    def draw_content(self, c, t):
        a = appear(t, 0, 0.5)
        if self.p.get("title"):
            B.draw_text(c, self.p["title"], MARGIN, 210, "serif", 64, B.PAPER, a)
        items = self.p["items"]
        y = 330
        for i, it in enumerate(items):
            st = self.cue(it.get("cue"), 0.4 + i * 1.2)
            ia = appear(t, st, 0.5)
            if ia <= 0:
                y += 140; continue
            mk = it.get("mark", "num")
            cx, cy = MARGIN + 30, y - 14
            c.drawCircle(cx, cy, 30, B.paint(B.EMBER if mk != "x" else B.BRICK, ia))
            if mk == "num":
                B.draw_text(c, str(i + 1), cx, cy + 12, "display_bold", 34, B.INK, ia, align="center")
            elif mk == "check":
                pth = skia.Path(); pth.moveTo(cx - 12, cy); pth.lineTo(cx - 3, cy + 10); pth.lineTo(cx + 14, cy - 10)
                c.drawPath(pth, B.paint(B.INK, ia, stroke=6))
            lines = wrap(it["text"], "body_medium", 44, W - 2 * MARGIN - 140)
            for k, ln in enumerate(lines):
                draw_rich(c, ln, MARGIN + 100 + (1 - ia) * 30, y + k * 56, "body_medium", 44, B.PAPER, B.GOLD, ia)
            y += 80 + 56 * len(lines)


# ---------------------------------------------------------------------------
@register
class EndScreen(Scene):
    """Last 20 s. Leaves space for YouTube end-screen elements.
    params: headline, url, next_label"""
    name = "endscreen"

    def draw_content(self, c, t):
        a = appear(t, 0, 0.6)
        B.draw_mark(c, MARGIN, 150, 110, line_hex=B.PAPER, gap_hex=B.INK, progress=ease_in_out(prog(t, 0, 1.2)))
        B.draw_text(c, self.p.get("headline", "Run your own numbers"), MARGIN, 360, "serif", 76, B.PAPER, a)
        if self.p.get("url"):
            B.draw_text(c, self.p["url"], MARGIN, 430, "mono_medium", 34, B.EMBER, a, tracking=0.04)
        # end-screen element zones (YouTube overlays real elements here)
        zx, zy, zw, zh = W - MARGIN - 760, 520, 760, 428
        rrect(c, zx, zy, zw, zh, 18, B.INK_2, a)
        B.draw_text(c, self.p.get("next_label", "NEXT MODEL").upper(), zx + 30, zy - 22, "mono_medium", 24, B.MUTED, a, tracking=0.12)
        c.drawCircle(MARGIN + 160, 760, 150, B.paint(B.INK_2, a))
        B.draw_text(c, "SUBSCRIBE", MARGIN + 160, 960, "mono_medium", 24, B.MUTED, a, align="center", tracking=0.12)


def make(scene_type: str, params, cues, duration, meta) -> Scene:
    if scene_type not in REGISTRY:
        raise KeyError(f"Unknown scene '{scene_type}'. Available: {sorted(REGISTRY)}")
    return REGISTRY[scene_type](params, cues, duration, meta)
