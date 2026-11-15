"""Human approval gate + YouTube Data API v3 upload.

Safety rules enforced in code:
  * No upload without output/approval.json written by `approve` (a human).
  * approval.json pins the SHA-256 of the exact video file; any re-render
    invalidates it.
  * Uploads are PRIVATE (or scheduled via publishAt). Nothing goes public
    without a person flipping it in YouTube Studio or explicitly scheduling.
  * Credentials live outside the repo: ~/.config/breakeven/ (or $BREAKEVEN_SECRETS).
"""
from __future__ import annotations

import datetime as dt
import getpass
import hashlib
import json
import os
from pathlib import Path

SECRETS = Path(os.environ.get("BREAKEVEN_SECRETS", Path.home() / ".config" / "breakeven"))
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",           # captions, thumbnails, metadata
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/yt-analytics-monetary.readonly",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def approve(video_dir: Path, thumbnail_id: str, title_index: int = 0, reviewer: str | None = None,
            allow_unverified: bool = False) -> Path:
    from . import qa
    video_dir = Path(video_dir).resolve(); out = video_dir / "output"
    meta = json.loads((out / "metadata.json").read_text())
    rep = qa.run(video_dir, quick=True)
    if rep.errors:
        raise SystemExit(f"QA has {len(rep.errors)} errors; fix them first: {[e['check'] for e in rep.errors]}")
    unver = [i for i in rep.items if i["check"] == "sources verified" and i["level"] == "WARN"]
    if unver and not allow_unverified:
        raise SystemExit("Some sources are not marked verified in sources.yaml. Open each URL, confirm the figure, set "
                         "verified: true — or pass --allow-unverified if you accept the risk.")
    if thumbnail_id not in [t["id"] for t in meta["thumbnails"]]:
        raise SystemExit(f"unknown thumbnail {thumbnail_id}")
    rec = {
        "approved_by": reviewer or getpass.getuser(),
        "approved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "video_sha256": sha256(out / meta["video_file"]),
        "thumbnail_id": thumbnail_id,
        "title": meta["titles"][title_index],
        "statement": "I watched the full video, checked the numbers against sources, and approve it for upload.",
    }
    p = out / "approval.json"
    p.write_text(json.dumps(rec, indent=1))
    return p


def _client():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    SECRETS.mkdir(parents=True, exist_ok=True)
    tok = SECRETS / "token.json"
    creds = Credentials.from_authorized_user_file(str(tok), SCOPES) if tok.exists() else None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            cs = SECRETS / "client_secret.json"
            if not cs.exists():
                raise SystemExit(f"Missing OAuth client file: {cs}\nSee docs/06-launch-guide.md, step 'YouTube API'.")
            creds = InstalledAppFlow.from_client_secrets_file(str(cs), SCOPES).run_local_server(port=0)
        tok.write_text(creds.to_json())
        os.chmod(tok, 0o600)
    return build("youtube", "v3", credentials=creds, cache_discovery=False), creds


def upload(video_dir: Path, publish_at: str | None = None, dry_run: bool = False) -> dict:
    """publish_at: RFC3339 UTC time to schedule (video stays private until then)."""
    from googleapiclient.http import MediaFileUpload
    video_dir = Path(video_dir).resolve(); out = video_dir / "output"
    meta = json.loads((out / "metadata.json").read_text())
    ap_path = out / "approval.json"
    if not ap_path.exists():
        raise SystemExit("Not approved. Run: python -m breakeven approve <slug> --thumbnail <id>")
    ap = json.loads(ap_path.read_text())
    vf = out / meta["video_file"]
    if sha256(vf) != ap["video_sha256"]:
        raise SystemExit("Video file changed since approval. Re-review and re-approve.")
    status = {"privacyStatus": "private", "selfDeclaredMadeForKids": False,
              "containsSyntheticMedia": bool(meta["contains_synthetic_media"])}
    if publish_at:
        status["publishAt"] = publish_at
    body = {
        "snippet": {"title": ap["title"], "description": meta["description"], "tags": meta["tags"],
                    "categoryId": meta["category_id"], "defaultLanguage": meta["default_language"],
                    "defaultAudioLanguage": meta["default_language"]},
        "status": status,
    }
    if meta.get("paid_promotion"):
        body["paidProductPlacementDetails"] = {"hasPaidProductPlacement": True}
    thumb = out / next(t["file"] for t in meta["thumbnails"] if t["id"] == ap["thumbnail_id"])
    if dry_run:
        print(json.dumps({**body, "snippet": {**body["snippet"], "description": body["snippet"]["description"][:300] + "…"}}, indent=1))
        print("thumbnail:", thumb); return body
    yt, _ = _client()
    parts = "snippet,status" + (",paidProductPlacementDetails" if "paidProductPlacementDetails" in body else "")
    req = yt.videos().insert(part=parts, body=body, media_body=MediaFileUpload(str(vf), chunksize=8 << 20, resumable=True))
    resp = None
    while resp is None:
        st, resp = req.next_chunk()
        if st:
            print(f"  uploaded {st.progress()*100:.0f}%")
    vid = resp["id"]
    yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(thumb), mimetype="image/jpeg")).execute()
    yt.captions().insert(part="snippet", body={"snippet": {"videoId": vid, "language": "en", "name": "English", "isDraft": False}},
                         media_body=MediaFileUpload(str(out / meta["captions_file"]), mimetype="application/octet-stream")).execute()
    rec = {"video_id": vid, "url": f"https://youtu.be/{vid}", "uploaded_at": dt.datetime.now(dt.timezone.utc).isoformat(),
           "privacy": "private", "publish_at": publish_at, "title": ap["title"], "thumbnail_id": ap["thumbnail_id"]}
    (out / "upload.json").write_text(json.dumps(rec, indent=1))
    print(f"Uploaded PRIVATE: {rec['url']}  -> review in Studio, then set end screen + pinned comment (see output/description.txt)")
    return rec
