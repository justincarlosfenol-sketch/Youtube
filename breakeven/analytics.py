"""Analytics warehouse (SQLite) + YouTube Analytics collector + CSV imports.

    python -m breakeven analytics pull          # YouTube Analytics API -> data/analytics.db
    python -m breakeven analytics import-costs finance/ledger.csv
    python -m breakeven analytics import-revenue finance/revenue.csv   # affiliate/sponsor/product income
    python -m breakeven analytics demo          # seed clearly-labelled DEMO data to test the dashboard
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import math
import random
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "analytics.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS videos(
  video_id TEXT PRIMARY KEY, slug TEXT, title TEXT, published_at TEXT, duration_s REAL, is_short INTEGER DEFAULT 0,
  series TEXT, thumbnail_template TEXT, production_hours REAL, production_cost REAL);
CREATE TABLE IF NOT EXISTS video_daily(
  video_id TEXT, date TEXT, views INTEGER, minutes_watched REAL, avg_view_duration_s REAL, avg_view_pct REAL,
  subs_gained INTEGER, subs_lost INTEGER, likes INTEGER, comments INTEGER, shares INTEGER,
  impressions INTEGER, ctr REAL, est_revenue REAL, PRIMARY KEY(video_id, date));
CREATE TABLE IF NOT EXISTS channel_daily(
  date TEXT PRIMARY KEY, views INTEGER, minutes_watched REAL, subs_gained INTEGER, subs_lost INTEGER, est_revenue REAL);
CREATE TABLE IF NOT EXISTS revenue(date TEXT, stream TEXT, amount REAL, source TEXT, video_slug TEXT, note TEXT);
CREATE TABLE IF NOT EXISTS costs(date TEXT, category TEXT, amount REAL, video_slug TEXT, note TEXT);
CREATE TABLE IF NOT EXISTS affiliate(date TEXT, program TEXT, video_slug TEXT, clicks INTEGER, conversions INTEGER, revenue REAL);
"""


def connect(path: Path = DB) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    return con


# ---------------------------------------------------------------------------
# YouTube Analytics API
def pull(days: int = 400) -> None:
    from googleapiclient.discovery import build
    from .upload import _client
    yt, creds = _client()
    ya = build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False)
    con = connect()
    end = dt.date.today(); start = end - dt.timedelta(days=days)
    # channel daily
    base_metrics = "views,estimatedMinutesWatched,subscribersGained,subscribersLost"
    try:
        r = ya.reports().query(ids="channel==MINE", startDate=str(start), endDate=str(end), dimensions="day",
                               metrics=base_metrics + ",estimatedRevenue").execute()
        has_rev = True
    except Exception:  # not monetized / no monetary scope yet
        r = ya.reports().query(ids="channel==MINE", startDate=str(start), endDate=str(end), dimensions="day",
                               metrics=base_metrics).execute()
        has_rev = False
    for row in r.get("rows", []):
        con.execute("INSERT OR REPLACE INTO channel_daily VALUES (?,?,?,?,?,?)",
                    (row[0], row[1], row[2], row[3], row[4], row[5] if has_rev else 0.0))
    # uploads list -> videos table
    ch = yt.channels().list(part="contentDetails", mine=True).execute()
    uploads = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    ids, tok = [], None
    while True:
        pl = yt.playlistItems().list(part="contentDetails", playlistId=uploads, maxResults=50, pageToken=tok).execute()
        ids += [i["contentDetails"]["videoId"] for i in pl["items"]]
        tok = pl.get("nextPageToken")
        if not tok:
            break
    for i in range(0, len(ids), 50):
        vs = yt.videos().list(part="snippet,contentDetails", id=",".join(ids[i:i + 50])).execute()
        for v in vs["items"]:
            dur = _iso_dur(v["contentDetails"]["duration"])
            con.execute("""INSERT INTO videos(video_id,title,published_at,duration_s,is_short) VALUES(?,?,?,?,?)
                           ON CONFLICT(video_id) DO UPDATE SET title=excluded.title, published_at=excluded.published_at,
                           duration_s=excluded.duration_s""",
                        (v["id"], v["snippet"]["title"], v["snippet"]["publishedAt"][:10], dur, int(dur <= 180)))
    # per-video daily
    vm = "views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained,subscribersLost,likes,comments,shares"
    for vid in ids:
        r = ya.reports().query(ids="channel==MINE", startDate=str(start), endDate=str(end), dimensions="day",
                               filters=f"video=={vid}", metrics=vm + (",estimatedRevenue" if has_rev else "")).execute()
        imp = _impressions(ya, vid, start, end)
        for row in r.get("rows", []):
            im = imp.get(row[0], (None, None))
            con.execute("INSERT OR REPLACE INTO video_daily VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (vid, row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], im[0], im[1],
                         row[10] if has_rev else 0.0))
    con.execute("INSERT OR REPLACE INTO meta VALUES('source','youtube')")
    con.execute("INSERT OR REPLACE INTO meta VALUES('pulled_at',?)", (dt.datetime.now().isoformat(timespec="minutes"),))
    con.commit()
    _link_slugs(con)
    print(f"pulled {len(ids)} videos into {DB}")


def _impressions(ya, vid, start, end) -> dict:
    """Thumbnail impressions + CTR where the API exposes them; silently empty otherwise."""
    try:
        r = ya.reports().query(ids="channel==MINE", startDate=str(start), endDate=str(end), dimensions="day",
                               filters=f"video=={vid}", metrics="videoThumbnailImpressions,videoThumbnailImpressionsClickRate").execute()
        return {row[0]: (row[1], row[2]) for row in r.get("rows", [])}
    except Exception:
        return {}


def _iso_dur(s: str) -> float:
    import re
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", s)
    h, mi, se = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mi * 60 + se


def _link_slugs(con):
    """Attach local production data (slug, series, template, hours, cost) via output/upload.json + production.yaml."""
    import yaml
    for up in (ROOT / "videos").glob("*/output/upload.json"):
        vd = up.parents[1]
        rec = json.loads(up.read_text())
        prod = yaml.safe_load((vd / "production.yaml").read_text()) if (vd / "production.yaml").exists() else {}
        con.execute("UPDATE videos SET slug=?, series=?, thumbnail_template=?, production_hours=?, production_cost=? WHERE video_id=?",
                    (vd.name, prod.get("series"), rec.get("thumbnail_id", "").split("-")[-1], prod.get("hours"), prod.get("cost"),
                     rec["video_id"]))
    con.commit()


# ---------------------------------------------------------------------------
# CSV imports
def import_costs(path: Path) -> int:
    con = connect(); n = 0
    con.execute("DELETE FROM costs")
    for r in csv.DictReader(open(path)):
        con.execute("INSERT INTO costs VALUES (?,?,?,?,?)", (r["date"], r["category"], float(r["amount"]), r.get("video_slug", ""), r.get("note", "")))
        n += 1
    con.commit(); return n


def import_revenue(path: Path) -> int:
    """CSV columns: date,stream(adsense|affiliate|sponsor|product|membership|other),amount,source,video_slug,note"""
    con = connect(); n = 0
    con.execute("DELETE FROM revenue")
    for r in csv.DictReader(open(path)):
        con.execute("INSERT INTO revenue VALUES (?,?,?,?,?,?)", (r["date"], r["stream"], float(r["amount"]), r.get("source", ""),
                                                                 r.get("video_slug", ""), r.get("note", "")))
        n += 1
    con.commit(); return n


# ---------------------------------------------------------------------------
# DEMO data — synthetic, for testing the dashboard only. Never mixed with real data.
def seed_demo(path: Path = ROOT / "data" / "demo.db", weeks: int = 26, seed: int = 3) -> Path:
    if path.exists():
        path.unlink()
    rng = random.Random(seed)
    con = connect(path)
    con.execute("INSERT INTO meta VALUES('source','DEMO')")
    start = dt.date(2026, 12, 1)
    series_cycle = ["Breakeven", "Breakeven", "Run It Back", "Breakeven", "Real Cost", "Paycheck", "Money Behind"]
    templates = ["number", "versus", "chart"]
    titles = [r["working_title"] for r in csv.DictReader(open(ROOT / "content" / "ideas.csv"))]
    vids = []
    for w in range(weeks):
        pub = start + dt.timedelta(days=7 * w)
        q = rng.lognormvariate(0, 0.7)  # quality/luck multiplier
        tpl = templates[w % 3]
        vid = f"demo{w:03d}"
        dur = rng.uniform(480, 780)
        vids.append((vid, pub, q, dur, tpl))
        con.execute("INSERT INTO videos VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (vid, f"{w+1:03d}-demo", titles[w % len(titles)], str(pub), dur, 0, series_cycle[w % 7], tpl,
                     rng.uniform(6, 11), rng.choice([0, 0, 25, 40])))
    end = start + dt.timedelta(days=7 * weeks + 14)
    d = start
    growth = 1.0
    while d <= end:
        growth *= 1.008
        ch_views = ch_min = ch_sg = ch_sl = ch_rev = 0
        for vid, pub, q, dur, tpl in vids:
            age = (d - pub).days
            if age < 0:
                continue
            ctr = max(0.015, rng.gauss(0.045 + (0.012 if tpl == "chart" else 0), 0.008)) * min(q, 2.5) ** 0.3
            imp = int(1200 * q * growth ** 0.6 * (math.exp(-age / 9) + 0.12) * rng.uniform(0.7, 1.3))
            views = int(imp * ctr)
            pct = min(0.75, max(0.2, rng.gauss(0.42 + 0.05 * math.log(q + 0.5), 0.04)))
            avd = dur * pct
            mins = views * avd / 60
            ypp = d >= start + dt.timedelta(days=120)
            rev = views / 1000 * rng.uniform(7, 12) if ypp else 0.0
            sg = int(views * rng.uniform(0.008, 0.02)); sl = int(sg * 0.1)
            con.execute("INSERT INTO video_daily VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (vid, str(d), views, mins, avd, pct * 100, sg, sl, int(views * .04), int(views * .006), int(views * .003),
                         imp, ctr * 100, rev))
            ch_views += views; ch_min += mins; ch_sg += sg; ch_sl += sl; ch_rev += rev
        con.execute("INSERT INTO channel_daily VALUES (?,?,?,?,?,?)", (str(d), ch_views, ch_min, ch_sg, ch_sl, ch_rev))
        if d.day == 1 and d > start:
            for stream, lo, hi in (("affiliate", 50, 900), ("product", 20, 600), ("sponsor", 0, 0)):
                amt = rng.uniform(lo, hi) * growth ** 0.5
                if stream == "sponsor" and d >= start + dt.timedelta(days=150):
                    amt = rng.choice([0, 1500, 2500])
                if amt:
                    con.execute("INSERT INTO revenue VALUES (?,?,?,?,?,?)", (str(d), stream, round(amt, 2), "demo", "", "DEMO"))
            for cat, amt in (("software", 49.0), ("voice actor", 0.0), ("hosting", 6.0)):
                if amt:
                    con.execute("INSERT INTO costs VALUES (?,?,?,?,?)", (str(d), cat, amt, "", "DEMO"))
        d += dt.timedelta(days=1)
    con.commit()
    return path
