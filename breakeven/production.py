"""Script -> timeline -> rendered, mixed, captioned video.

Video folder layout (videos/<slug>/):
  script.yaml     shots, narration lines, scene params, source ids
  sources.yaml    S-ids -> citation (required for every [S#] used)
  model.py        optional; computes data.json from the analytical model
  data.json       values referenced in script as "@a.b.c" (params) or {{a.b|fmt}} (text)
  voice/<line>.wav  optional human takes (override TTS per line)
  build/          cache (ignored by git)
  output/         final deliverables
"""
from __future__ import annotations

import hashlib
import json
import multiprocessing as mp
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import yaml

from . import audio as A
from . import tts
from .anim import money, money_short

FPS = 30
W, H = 1920, 1080
PKG = Path(__file__).resolve().parent
CODE_FILES = [PKG / "scenes" / "library.py", PKG / "scenes" / "base.py", PKG / "brand.py", PKG / "anim.py"]

DEFAULTS = {"pad_before": 0.35, "gap": 0.32, "pad_after": 0.55}


# ---------------------------------------------------------------------------
# script loading & data binding
def _lookup(data: dict, dotted: str):
    cur = data
    for part in dotted.split("."):
        if isinstance(cur, list):
            cur = cur[int(part)]
        else:
            if part not in cur:
                raise KeyError(f"data.json has no '{dotted}' (failed at '{part}')")
            cur = cur[part]
    return cur


_FMT = {
    "money": lambda v: money(v),
    "money_short": lambda v: money_short(v).replace("K", " thousand").replace("M", " million"),
    "pct": lambda v: f"{v:.2f}".rstrip("0").rstrip(".") + "%",
    "pct1": lambda v: f"{v:.1f}%",
    "y1": lambda v: f"{v:.1f}",
    "int": lambda v: f"{int(round(v)):,}",
    "money_m": lambda v: "$" + f"{v/1e6:.2f}".rstrip("0").rstrip(".") + " million",
    "money_k": lambda v: "$" + f"{round(v/1000):,.0f}" + ",000",
}


def _bind(obj, data):
    if isinstance(obj, str):
        if obj.startswith("@"):
            return _lookup(data, obj[1:])

        def sub(m):
            v, f = _lookup(data, m.group(1)), m.group(2)
            return _FMT[f](v) if f else (v if isinstance(v, str) else _FMT["int"](v))
        return re.sub(r"\{\{\s*([\w.]+)\s*(?:\|\s*(\w+))?\s*\}\}", sub, obj)
    if isinstance(obj, list):
        return [_bind(x, data) for x in obj]
    if isinstance(obj, dict):
        return {k: _bind(v, data) for k, v in obj.items()}
    return obj


def load(video_dir: Path) -> dict:
    video_dir = Path(video_dir).resolve()
    model = video_dir / "model.py"
    if model.exists():
        import os
        env = {**os.environ, "PYTHONPATH": str(PKG.parent) + os.pathsep + os.environ.get("PYTHONPATH", "")}
        subprocess.run([sys.executable, str(model)], check=True, cwd=video_dir, env=env)
    data = json.loads((video_dir / "data.json").read_text()) if (video_dir / "data.json").exists() else {}
    script = yaml.safe_load((video_dir / "script.yaml").read_text())
    script = _bind(script, data)
    sources = yaml.safe_load((video_dir / "sources.yaml").read_text()) if (video_dir / "sources.yaml").exists() else {}
    script["_sources"] = sources or {}
    script["_data"] = data
    return script


# ---------------------------------------------------------------------------
# timeline
def build_timeline(video_dir: Path, script: dict | None = None) -> dict:
    video_dir = Path(video_dir).resolve()
    script = script or load(video_dir)
    build = video_dir / "build"; build.mkdir(parents=True, exist_ok=True)
    t = 0.0
    shots, lines_out, voice_chunks = [], [], []
    origins = set()
    chapter_label = None
    for si, shot in enumerate(script["shots"]):
        sid = shot.get("id", f"s{si:02d}")
        if shot.get("chapter_label"):
            chapter_label = shot["chapter_label"]
        start = t
        cues = {}
        local = shot.get("pad_before", DEFAULTS["pad_before"]) if shot.get("lines") else 0.0
        for li, ln in enumerate(shot.get("lines", [])):
            lid = ln.get("id", f"{sid}_l{li:02d}")
            x, origin = tts.load_line_audio(video_dir, lid, ln.get("say", ln["text"]))
            origins.add(origin)
            x48 = A.resample(x, tts.SR, A.SR)
            dur = len(x48) / A.SR
            cues[f"L{li}"] = local
            cues[f"L{li}_end"] = local + dur
            if ln.get("cue"):
                cues[ln["cue"]] = local + float(ln.get("cue_offset", 0.0))
            lines_out.append({"id": lid, "shot": sid, "start": start + local, "end": start + local + dur,
                              "text": ln["text"], "sources": ln.get("sources", []), "sfx": ln.get("sfx"), "origin": origin})
            voice_chunks.append((start + local, x48))
            local += dur + ln.get("gap", DEFAULTS["gap"])
        if shot.get("lines"):
            local = local - shot["lines"][-1].get("gap", DEFAULTS["gap"]) + shot.get("pad_after", DEFAULTS["pad_after"])
        dur = max(local, shot.get("min_duration", 0.0), shot.get("duration", 0.0))
        cues["end"] = dur
        shots.append({"id": sid, "scene": shot["scene"], "params": shot.get("params", {}), "start": start, "duration": dur,
                      "cues": cues, "chapter": shot.get("chapter"), "chapter_label": chapter_label,
                      "music": shot.get("music"), "sfx_start": shot.get("sfx_start",
                                                                        "whoosh" if shot["scene"] == "chapter" else None)})
        t += dur
    total = t
    # narration track
    voice = np.zeros(int(total * A.SR) + A.SR, np.float32)
    for st, x in voice_chunks:
        a = int(st * A.SR); voice[a:a + len(x)] += x
    voice = voice[: int(total * A.SR)]
    sf.write(build / "narration.wav", voice, A.SR)
    tl = {"slug": script.get("slug", video_dir.name), "fps": FPS, "duration": total, "shots": shots, "lines": lines_out,
          "voice_origins": sorted(origins)}
    (build / "timeline.json").write_text(json.dumps(tl, indent=1))
    return tl


# ---------------------------------------------------------------------------
# rendering
def _code_hash() -> str:
    h = hashlib.sha1()
    for f in CODE_FILES:
        h.update(f.read_bytes())
    return h.hexdigest()[:10]


def _shot_frames(tl: dict) -> list[tuple[int, int]]:
    out = []
    for sh in tl["shots"]:
        f0 = round(sh["start"] * FPS)
        f1 = round((sh["start"] + sh["duration"]) * FPS)
        out.append((f0, max(f1 - f0, 1)))
    return out


def _render_shot(job: dict) -> str:
    import skia
    from .scenes.library import make
    out = Path(job["out"])
    if out.exists():
        return str(out)
    tmp = out.with_suffix(".part.mp4")
    scene = make(job["scene"], job["params"], job["cues"], job["duration"],
                 {"chapter_label": job["chapter_label"]})
    buf = np.zeros((H, W, 4), np.uint8)
    surf = skia.Surface(buf, colorType=skia.kRGBA_8888_ColorType)
    canvas = surf.getCanvas()
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
           "-c:v", "libx264", "-preset", "medium", "-crf", "15", "-tune", "animation",
           "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-g", "60", str(tmp)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(job["nframes"]):
        canvas.clear(skia.ColorBLACK)
        scene.draw(canvas, i / FPS)
        surf.flushAndSubmit() if hasattr(surf, "flushAndSubmit") else None
        proc.stdin.write(buf.tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError(f"ffmpeg failed for {out.name}")
    tmp.rename(out)
    return str(out)


def render_still(video_dir: Path, shot_id: str, t: float, out: Path) -> Path:
    """Render a single frame (for review/QA)."""
    import skia
    from .scenes.library import make
    tl = json.loads((Path(video_dir) / "build" / "timeline.json").read_text())
    sh = next(s for s in tl["shots"] if s["id"] == shot_id)
    scene = make(sh["scene"], sh["params"], sh["cues"], sh["duration"], {"chapter_label": sh["chapter_label"]})
    surf = skia.Surface(W, H)
    scene.draw(surf.getCanvas(), t)
    surf.makeImageSnapshot().save(str(out), skia.kPNG)
    return out


def render(video_dir: Path, workers: int | None = None, final_name: str | None = None) -> Path:
    video_dir = Path(video_dir)
    script = load(video_dir)
    tl = build_timeline(video_dir, script)
    build, outdir = video_dir / "build", video_dir / "output"
    (build / "shots").mkdir(parents=True, exist_ok=True); outdir.mkdir(exist_ok=True)
    ch = _code_hash()
    jobs = []
    for sh, (f0, nf) in zip(tl["shots"], _shot_frames(tl)):
        key = hashlib.sha1(json.dumps([sh["scene"], sh["params"], sh["cues"], sh["duration"], sh["chapter_label"], nf, ch],
                                      sort_keys=True, default=str).encode()).hexdigest()[:14]
        jobs.append({**sh, "nframes": nf, "out": str(build / "shots" / f"{sh['id']}_{key}.mp4")})
    todo = [j for j in jobs if not Path(j["out"]).exists()]
    print(f"[render] {len(jobs)} shots, {len(todo)} to render, {tl['duration']:.1f}s total")
    if todo:
        with mp.get_context("fork").Pool(workers or max(1, mp.cpu_count())) as pool:
            for i, p in enumerate(pool.imap_unordered(_render_shot, todo), 1):
                print(f"  [{i}/{len(todo)}] {Path(p).name}")
    concat = build / "concat.txt"
    concat.write_text("".join(f"file '{Path(j['out']).resolve()}'\n" for j in jobs))
    video_only = build / "video_only.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy",
                    str(video_only)], check=True)
    mixed = mix_audio(video_dir, tl, script)
    slug = final_name or tl["slug"]
    final = outdir / f"{slug}.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video_only), "-i", str(mixed), "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-movflags", "+faststart",
                    "-shortest", str(final)], check=True)
    write_captions(tl, outdir / f"{slug}.en.srt")
    (outdir / "timeline.json").write_text(json.dumps(tl, indent=1))
    print(f"[render] wrote {final}")
    return final


def mix_audio(video_dir: Path, tl: dict, script: dict) -> Path:
    from .scenes.library import make
    build = Path(video_dir) / "build"
    voice, _ = sf.read(build / "narration.wav", dtype="float32")
    total = tl["duration"]
    # music intensity breakpoints from shot hints
    pts, cur = [(0.0, 0.5)], 0.5
    for sh in tl["shots"]:
        lvl = sh.get("music")
        if lvl is not None:
            pts += [(sh["start"], cur), (sh["start"] + 1.5, float(lvl))]; cur = float(lvl)
    pts.append((total, cur))
    music = A.score(total, pts, seed=script.get("music_seed", 7))
    fx = np.zeros(int(total * A.SR) + 3 * A.SR, np.float32)

    def place(t, kind):
        s = A.sfx(kind); a = int(max(t, 0) * A.SR); fx[a:a + len(s)] += s[: len(fx) - a]

    for sh in tl["shots"]:
        if sh.get("sfx_start"):
            place(sh["start"], sh["sfx_start"])
        scene = make(sh["scene"], sh["params"], sh["cues"], sh["duration"], {})
        for (et, kind) in getattr(scene, "audio_events", lambda: [])():
            place(sh["start"] + et, kind)
    for ln in tl["lines"]:
        if ln.get("sfx"):
            place(ln["start"], ln["sfx"])
    out = A.mix(voice, music, fx[: len(voice) + A.SR])[: int(total * A.SR)]
    raw = build / "mix_raw.wav"
    sf.write(raw, out, A.SR)
    # loudness normalise for YouTube (-14 LUFS integrated, -1.5 dBTP)
    final = build / "mix.wav"
    meas = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(raw), "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json",
                           "-f", "null", "-"], capture_output=True, text=True).stderr
    js = json.loads(meas[meas.rindex("{"): meas.rindex("}") + 1])
    af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={js['input_i']}:measured_TP={js['input_tp']}:"
          f"measured_LRA={js['input_lra']}:measured_thresh={js['input_thresh']}:offset={js['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-af", af, "-ar", "48000", str(final)], check=True)
    return final


# ---------------------------------------------------------------------------
# captions
def _ts(s: float) -> str:
    ms = int(round(s * 1000)); h, ms = divmod(ms, 3_600_000); m, ms = divmod(ms, 60_000); sec, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"


def caption_chunks(text: str, start: float, end: float, max_chars: int = 74) -> list[tuple[float, float, str]]:
    text = text.replace("*", "")
    words = text.split()
    chunks, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 > max_chars and cur:
            chunks.append(cur); cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        chunks.append(cur)
    total = sum(len(c) for c in chunks) or 1
    out, t = [], start
    for c in chunks:
        d = (end - start) * len(c) / total
        out.append((t, t + d, c)); t += d
    return out


def _two_lines(s: str, width: int = 42) -> str:
    if len(s) <= width:
        return s
    words, best = s.split(), None
    for i in range(1, len(words)):
        a, b = " ".join(words[:i]), " ".join(words[i:])
        score = max(len(a), len(b))
        if best is None or score < best[0]:
            best = (score, a + "\n" + b)
    return best[1]


def write_captions(tl: dict, path: Path) -> Path:
    n, out = 1, []
    for ln in tl["lines"]:
        for a, b, txt in caption_chunks(ln["text"], ln["start"], ln["end"]):
            out.append(f"{n}\n{_ts(a)} --> {_ts(b)}\n{_two_lines(txt)}\n")
            n += 1
    path.write_text("\n".join(out))
    return path


def chapters(tl: dict) -> list[tuple[float, str]]:
    ch = [(0.0, "Intro")]
    for sh in tl["shots"]:
        if sh["scene"] == "chapter":
            ch.append((sh["start"], sh["params"].get("title", "")))
    return ch
