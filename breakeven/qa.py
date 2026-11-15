"""Automated quality gate. Produces output/qa-report.md; errors block approval."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import yaml

BANNED = [r"\bguarantee[sd]?\b", r"\brisk[- ]free\b", r"\bcan'?t lose\b", r"\bget rich\b", r"\bsecret\b",
          r"\bthey don'?t want you to know\b", r"\bhack\b", r"\bsure thing\b", r"\b100% safe\b", r"\byou should buy\b",
          r"\byou should sell\b"]


class Report:
    def __init__(self):
        self.items = []

    def add(self, level, check, msg):
        self.items.append({"level": level, "check": check, "msg": msg})

    ok = lambda self, c, m: self.add("PASS", c, m)        # noqa: E731
    warn = lambda self, c, m: self.add("WARN", c, m)      # noqa: E731
    err = lambda self, c, m: self.add("ERROR", c, m)      # noqa: E731

    @property
    def errors(self):
        return [i for i in self.items if i["level"] == "ERROR"]


def _probe(path: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
                       capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def _loudness(path: Path) -> tuple[float, float]:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-map", "0:a", "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    summ = r[r.rfind("Summary:"):]
    i = float(re.search(r"I:\s+(-?[\d.]+) LUFS", summ).group(1))
    tp = float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", summ).group(1))
    return i, tp


def _black(path: Path) -> list[tuple[float, float]]:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-map", "0:v", "-vf",
                        "blackdetect=d=0.5:pix_th=0.04", "-an", "-f", "null", "-"], capture_output=True, text=True).stderr
    return [(float(a), float(b)) for a, b in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", r)]


def run(video_dir: Path, quick: bool = False) -> Report:
    from PIL import Image
    video_dir = Path(video_dir).resolve()
    out = video_dir / "output"
    rep = Report()
    meta = json.loads((out / "metadata.json").read_text())
    tl = json.loads((out / "timeline.json").read_text())
    sources = yaml.safe_load((video_dir / "sources.yaml").read_text()) or {}

    # --- technical -----------------------------------------------------------
    vf = out / meta["video_file"]
    if not vf.exists():
        rep.err("video", f"missing {vf.name}")
    else:
        pr = _probe(vf)
        v = next(s for s in pr["streams"] if s["codec_type"] == "video")
        a = next((s for s in pr["streams"] if s["codec_type"] == "audio"), None)
        dur = float(pr["format"]["duration"])
        (rep.ok if (v["width"], v["height"]) == (1920, 1080) else rep.err)("resolution", f"{v['width']}x{v['height']}")
        fps = eval(v["r_frame_rate"])  # noqa: S307 - ffprobe fraction
        (rep.ok if abs(fps - 30) < 0.01 else rep.warn)("frame rate", f"{fps:.2f} fps")
        (rep.ok if v["codec_name"] == "h264" and v.get("pix_fmt") == "yuv420p" else rep.err)("codec", f"{v['codec_name']} {v.get('pix_fmt')}")
        if a is None:
            rep.err("audio", "no audio stream")
        else:
            (rep.ok if a["codec_name"] == "aac" and a["sample_rate"] == "48000" else rep.warn)("audio codec", f"{a['codec_name']} {a['sample_rate']} Hz")
        (rep.ok if abs(dur - tl["duration"]) < 0.6 else rep.err)("duration", f"{dur:.1f}s file vs {tl['duration']:.1f}s timeline")
        (rep.ok if dur >= 480 else rep.warn)("mid-roll eligible", f"{dur/60:.2f} min (mid-roll ads need 8:00+)")
        if not quick:
            i, tp = _loudness(vf)
            (rep.ok if -15.0 <= i <= -13.0 else rep.err)("loudness", f"{i:.1f} LUFS integrated (target -14)")
            (rep.ok if tp <= -1.0 else rep.warn)("true peak", f"{tp:.1f} dBFS (max -1.0)")
            bl = [b for b in _black(vf) if b[1] - b[0] > 1.0]
            (rep.warn if bl else rep.ok)("black frames", f"{len(bl)} black segments >1s" + (f": {bl[:3]}" if bl else ""))

    # --- captions ------------------------------------------------------------
    srt = out / meta["captions_file"]
    if srt.exists():
        blocks = srt.read_text().strip().split("\n\n")
        long_lines = [b for b in blocks if any(len(l) > 42 for l in b.split("\n")[2:])]
        too_many = [b for b in blocks if len(b.split("\n")) > 4]
        (rep.ok if not too_many else rep.warn)("captions", f"{len(blocks)} cues; {len(long_lines)} with a line >42 chars; {len(too_many)} with >2 lines")
    else:
        rep.err("captions", "missing .srt")

    # --- editorial -------------------------------------------------------------
    text_blob = " ".join(l["text"] for l in tl["lines"])
    unresolved = re.findall(r"\{\{[^}]+\}\}|(?<![\w])@[a-z_]+\.", text_blob)
    (rep.err if unresolved else rep.ok)("data binding", f"{len(unresolved)} unresolved template tokens")
    used = {s for l in tl["lines"] for s in l.get("sources", [])}
    missing = sorted(used - set(sources))
    (rep.err if missing else rep.ok)("sources exist", f"cited {len(used)} source ids; missing: {missing}")
    unverified = sorted(s for s in used if not (sources.get(s) or {}).get("verified"))
    (rep.warn if unverified else rep.ok)("sources verified", f"unverified (human must open & confirm): {unverified}")
    numeric_unsourced = [l["id"] for l in tl["lines"] if re.search(r"\d", l["text"]) and not l.get("sources")]
    (rep.warn if numeric_unsourced else rep.ok)("numbers sourced", f"lines with numbers but no source id: {numeric_unsourced}")
    blob_all = (text_blob + " " + meta["description"] + " " + " ".join(meta["titles"])).lower()
    hits = [p for p in BANNED if re.search(p, blob_all)]
    (rep.err if hits else rep.ok)("banned claims", f"matches: {hits}")

    # --- packaging -----------------------------------------------------------
    for t in meta["titles"]:
        (rep.err if len(t) > 100 else rep.warn if len(t) > 70 else rep.ok)("title length", f"{len(t)} chars: {t}")
    (rep.err if len(meta["description"]) > 5000 else rep.ok)("description length", f"{len(meta['description'])} chars")
    ch = meta["chapters"]
    gaps = [b["t"] - a["t"] for a, b in zip(ch, ch[1:])]
    ok_ch = ch and ch[0]["t"] == 0 and len(ch) >= 3 and all(g >= 10 for g in gaps)
    (rep.ok if ok_ch else rep.err)("chapters", f"{len(ch)} chapters, first at 0:00, min gap {min(gaps) if gaps else 0:.0f}s")
    tags_len = sum(len(t) for t in meta["tags"]) + 2 * len(meta["tags"])
    (rep.err if tags_len > 500 else rep.ok)("tags", f"{len(meta['tags'])} tags, {tags_len}/500 chars")
    if "[CALCULATOR LINK" in meta["description"]:
        rep.warn("links", "calculator link placeholder still in description (set site_url in channel.yaml)")
    for th in meta["thumbnails"]:
        p = out / th["file"]
        if not p.exists():
            rep.err("thumbnail", f"missing {th['file']}"); continue
        im = Image.open(p)
        good = im.size == (1280, 720) and p.stat().st_size < 2_000_000
        (rep.ok if good else rep.err)("thumbnail", f"{th['id']}: {im.size[0]}x{im.size[1]}, {p.stat().st_size/1024:.0f} KB")

    # --- policy ----------------------------------------------------------------
    if meta["contains_synthetic_media"]:
        rep.warn("voice", "Synthetic (TTS) narration present: the altered/synthetic disclosure will be set and the description "
                          "says so. Recommended: record human narration (python -m breakeven teleprompter <slug>).")
    else:
        rep.ok("voice", "human narration")
    return rep


def write(rep: Report, path: Path) -> Path:
    icon = {"PASS": "✅", "WARN": "⚠️", "ERROR": "❌"}
    lines = ["# QA report", "", f"**{len(rep.errors)} errors, {sum(i['level']=='WARN' for i in rep.items)} warnings**", "",
             "| | Check | Result |", "|---|---|---|"]
    lines += [f"| {icon[i['level']]} | {i['check']} | {i['msg']} |" for i in rep.items]
    path.write_text("\n".join(lines) + "\n")
    return path
