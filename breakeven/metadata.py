"""Build the upload package metadata: titles, description, chapters, tags."""
from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def channel() -> dict:
    return yaml.safe_load((ROOT / "channel.yaml").read_text())


def _ts(s: float) -> str:
    s = int(s)
    h, r = divmod(s, 3600); m, sec = divmod(r, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def build(video_dir: Path) -> dict:
    from .production import chapters, load
    video_dir = Path(video_dir).resolve()
    out = video_dir / "output"
    tl = json.loads((out / "timeline.json").read_text())
    script = load(video_dir)
    meta_in = yaml.safe_load((video_dir / "metadata.yaml").read_text()) if (video_dir / "metadata.yaml").exists() else {}
    thumbs = yaml.safe_load((video_dir / "thumbnails.yaml").read_text())["thumbnails"]
    from .production import _bind
    thumbs = _bind(thumbs, script["_data"])
    meta_in = _bind(meta_in, script["_data"])
    ch = channel()
    sources = script["_sources"]
    used = sorted({s for ln in tl["lines"] for s in ln.get("sources", [])}, key=lambda x: (x[0], int(x[1:])))

    chaps = chapters(tl)
    calc = (ch.get("site_url") or "").rstrip("/")
    calc_url = f"{calc}/{meta_in.get('calculator_path', tl['slug'])}/" if calc else "[CALCULATOR LINK — set site_url in channel.yaml]"

    d = []
    d.append(meta_in.get("hook", "").strip())
    d.append("")
    d.append(f"🧮 Free calculator (every assumption adjustable): {calc_url}")
    if ch.get("models_store_url"):
        d.append(f"📊 The full spreadsheet model: {ch['models_store_url']}")
    if ch.get("newsletter_url"):
        d.append(f"✉️ One model a week, in your inbox: {ch['newsletter_url']}")
    d += ["", "CHAPTERS"] + [f"{_ts(t)} {name}" for t, name in chaps]
    if meta_in.get("assumptions"):
        d += ["", "KEY ASSUMPTIONS"] + [f"• {a}" for a in meta_in["assumptions"]]
    d += ["", "SOURCES"]
    for sid in used:
        s = sources.get(sid, {})
        d.append(f"[{sid}] {s.get('claim', '')} — {s.get('source', '')} {s.get('url', '')}".strip())
    aff = ch.get("affiliates") or {}
    chosen = [aff[k] for k in meta_in.get("affiliates", []) if k in aff]
    if chosen:
        d += ["", ch["affiliate_disclosure"]] + [f"• {a['label']}: {a['url']}" for a in chosen]
    d += ["", ch["disclaimer"]]
    synthetic = "tts" in tl.get("voice_origins", [])
    if synthetic:
        d += ["", ch["synthetic_voice_disclosure"]]
    if meta_in.get("hashtags"):
        d += ["", " ".join(meta_in["hashtags"])]
    description = "\n".join(d).strip() + "\n"

    pkg = {
        "slug": tl["slug"],
        "titles": [t["title"] for t in thumbs],
        "title": thumbs[0]["title"],
        "thumbnails": [{"id": t["id"], "file": f"thumbnails/{t['id']}.jpg", "paired_title": t["title"]} for t in thumbs],
        "description": description,
        "tags": meta_in.get("tags", []),
        "category_id": ch.get("default_category_id", "27"),
        "default_language": ch.get("default_language", "en"),
        "chapters": [{"t": t, "title": n} for t, n in chaps],
        "contains_synthetic_media": synthetic,
        "paid_promotion": bool(meta_in.get("paid_promotion", False)),
        "made_for_kids": False,
        "duration": tl["duration"],
        "video_file": f"{tl['slug']}.mp4",
        "captions_file": f"{tl['slug']}.en.srt",
        "pinned_comment": meta_in.get("pinned_comment", ""),
        "shorts": meta_in.get("shorts", []),
    }
    (out / "metadata.json").write_text(json.dumps(pkg, indent=1))
    (out / "description.txt").write_text(description)
    return pkg
