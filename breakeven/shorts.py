"""Cut vertical Shorts (1080x1920) from a rendered flagship.

Layout: brand title band (top) / the 16:9 scene scaled to full width (middle) /
burned-in captions (lower third) / "Full model" end tag. Each Short reuses the
exact shots named in metadata.yaml -> shorts[].from_shots.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import skia
import yaml

from . import brand as B

VW, VH = 1080, 1920


def _overlay(path: Path, title: str, cta: str):
    surf = skia.Surface(VW, VH)
    c = surf.getCanvas(); c.clear(skia.ColorTRANSPARENT)
    c.drawRect(skia.Rect.MakeWH(VW, 520), B.paint(B.INK))
    c.drawRect(skia.Rect.MakeXYWH(0, 520 + 608, VW, VH - 1128), B.paint(B.INK))
    B.draw_mark(c, 64, 120, 84, line_hex=B.PAPER, gap_hex=B.INK)
    B.draw_text(c, "breakeven", 170, 178, "display_bold", 46, B.PAPER, tracking=-0.03)
    from .scenes.base import wrap
    lines = wrap(title, "display_black", 74, VW - 128)[:3]
    for i, ln in enumerate(lines):
        B.draw_text(c, ln.replace("*", ""), 64, 300 + i * 86, "display_black", 74, B.PAPER, tracking=-0.02)
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(64, VH - 300, VW - 128, 110), 55, 55), B.paint(B.EMBER))
    B.draw_text(c, cta, VW / 2, VH - 230, "display_bold", 42, B.INK, align="center")
    surf.makeImageSnapshot().save(str(path), skia.kPNG)


def _ass(lines: list[dict], t0: float, t1: float, path: Path):
    from .production import caption_chunks
    def ts(s):
        s = max(s, 0); h = int(s // 3600); m = int(s % 3600 // 60); sec = s % 60
        return f"{h}:{m:02d}:{sec:05.2f}"
    ev = []
    for ln in lines:
        if ln["end"] <= t0 or ln["start"] >= t1:
            continue
        for a, b, txt in caption_chunks(ln["text"], ln["start"], ln["end"], max_chars=52):
            if b <= t0 or a >= t1:
                continue
            ev.append(f"Dialogue: 0,{ts(a - t0)},{ts(min(b, t1) - t0)},Cap,,0,0,0,,{txt}")
    path.write_text(f"""[Script Info]
ScriptType: v4.00+
PlayResX: {VW}
PlayResY: {VH}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Inter Display,64,&H00E4EEF3,&H00E4EEF3,&H00171412,&H00171412,1,0,0,0,100,100,0,0,1,0,0,8,70,70,1210,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(ev) + "\n")


def make_shorts(video_dir: Path) -> list[Path]:
    video_dir = Path(video_dir).resolve(); out = video_dir / "output"
    tl = json.loads((out / "timeline.json").read_text())
    meta = yaml.safe_load((video_dir / "metadata.yaml").read_text())
    src = out / f"{tl['slug']}.mp4"
    sdir = out / "shorts"; sdir.mkdir(exist_ok=True)
    shots = {s["id"]: s for s in tl["shots"]}
    made = []
    for sh in meta.get("shorts", []):
        ids = sh["from_shots"]
        t0 = shots[ids[0]]["start"]; t1 = shots[ids[-1]]["start"] + shots[ids[-1]]["duration"]
        dur = t1 - t0
        if dur > 60:
            print(f"  ! {sh['id']} is {dur:.0f}s (>60s) — trim from_shots"); continue
        title = sh["title"].replace("#shorts", "").strip()
        ov, ass = sdir / f"{sh['id']}_overlay.png", sdir / f"{sh['id']}.ass"
        _overlay(ov, title, "Full model on the channel →")
        _ass(tl["lines"], t0, t1, ass)
        dst = sdir / f"{sh['id']}.mp4"
        fonts = (Path(__file__).resolve().parents[1] / "brand" / "fonts").as_posix()
        vf = (f"[0:v]scale={VW}:608,setsar=1[mid];color=c=0x121417:s={VW}x{VH}:d={dur:.3f}[bg];"
              f"[bg][mid]overlay=0:520[a];[a][1:v]overlay=0:0[b];[b]subtitles={ass.as_posix()}:fontsdir={fonts}[v]")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t0:.3f}", "-t", f"{dur:.3f}", "-i", str(src), "-i", str(ov),
                        "-filter_complex", vf, "-map", "[v]", "-map", "0:a", "-af", f"afade=t=in:d=0.15,afade=t=out:st={dur-0.4:.3f}:d=0.4",
                        "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p", "-r", "30",
                        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(dst)], check=True)
        ov.unlink(); made.append(dst)
        (sdir / f"{sh['id']}.txt").write_text(f"{sh['title']}\n\nFull model: (link the flagship via 'Related video' in Studio)\n")
    return made
