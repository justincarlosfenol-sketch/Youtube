"""Data refresh + opportunity discovery.

    python -m breakeven data refresh        # FRED series -> data/cache/*.csv   (needs FRED_API_KEY, free)
    python -m breakeven ideas discover      # YouTube search outliers -> content/discovered.csv (needs YOUTUBE_API_KEY)

Keys are read from environment variables (or ~/.config/breakeven/env), never from the repo.
"""
from __future__ import annotations

import csv
import datetime as dt
import os
import statistics as st
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "cache"
ENV_FILE = Path(os.environ.get("BREAKEVEN_SECRETS", Path.home() / ".config" / "breakeven")) / "env"

FRED_SERIES = {
    "MORTGAGE30US": "Freddie Mac 30-yr fixed mortgage rate (weekly, %)",
    "MORTGAGE15US": "Freddie Mac 15-yr fixed mortgage rate (weekly, %)",
    "CSUSHPINSA": "S&P Cotality Case-Shiller US National Home Price Index (NSA)",
    "CPIAUCSL": "CPI-U, all items (SA)",
    "CUSR0000SEHA": "CPI-U rent of primary residence (SA)",
    "DGS10": "10-year Treasury constant maturity (%)",
    "MSPUS": "Median sales price of houses sold (quarterly)",
}

SEEDS = ["rent vs buy", "pay off mortgage or invest", "roth vs traditional", "lease vs buy car", "should i refinance",
         "15 vs 30 year mortgage", "is grad school worth it", "when to claim social security", "hsa vs 401k",
         "4% rule", "lump sum vs dollar cost averaging", "whole life vs term", "how long to become a millionaire",
         "coast fire", "high yield savings vs treasury bills", "emergency fund how much", "ev vs gas cost",
         "solar panels worth it", "real cost of owning a car", "cost of raising a child"]


def _key(name: str) -> str:
    if os.environ.get(name):
        return os.environ[name]
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if line.startswith(name + "="):
                return line.split("=", 1)[1].strip()
    raise SystemExit(f"{name} not set. Add it to {ENV_FILE} as {name}=... (see docs/06-launch-guide.md)")


def refresh_fred() -> list[Path]:
    key = _key("FRED_API_KEY")
    CACHE.mkdir(parents=True, exist_ok=True)
    out = []
    for sid, desc in FRED_SERIES.items():
        r = requests.get("https://api.stlouisfed.org/fred/series/observations",
                         params={"series_id": sid, "api_key": key, "file_type": "json"}, timeout=30)
        r.raise_for_status()
        obs = [(o["date"], o["value"]) for o in r.json()["observations"] if o["value"] != "."]
        p = CACHE / f"{sid}.csv"
        with open(p, "w", newline="") as f:
            w = csv.writer(f); w.writerow(["date", "value"]); w.writerows(obs)
        print(f"{sid:14s} {len(obs):6d} obs, latest {obs[-1][0]} = {obs[-1][1]}  ({desc})")
        out.append(p)
    (CACHE / "_refreshed_at.txt").write_text(dt.datetime.now().isoformat(timespec="minutes"))
    return out


def latest(series_id: str) -> tuple[str, float]:
    rows = list(csv.DictReader(open(CACHE / f"{series_id}.csv")))
    return rows[-1]["date"], float(rows[-1]["value"])


def cagr(series_id: str, start: str, end: str | None = None) -> float:
    rows = [r for r in csv.DictReader(open(CACHE / f"{series_id}.csv")) if r["date"] >= start and (end is None or r["date"] <= end)]
    a, b = float(rows[0]["value"]), float(rows[-1]["value"])
    yrs = (dt.date.fromisoformat(rows[-1]["date"]) - dt.date.fromisoformat(rows[0]["date"])).days / 365.25
    return (b / a) ** (1 / yrs) - 1


def discover(seeds: list[str] | None = None, per_seed: int = 15, years: int = 3) -> Path:
    """Find topics where small channels massively over-perform (demand > supply)."""
    key = _key("YOUTUBE_API_KEY")
    api = "https://www.googleapis.com/youtube/v3"
    after = (dt.datetime.utcnow() - dt.timedelta(days=365 * years)).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    for q in seeds or SEEDS:
        s = requests.get(f"{api}/search", params={"part": "snippet", "q": q, "type": "video", "maxResults": per_seed,
                                                  "order": "relevance", "publishedAfter": after, "relevanceLanguage": "en",
                                                  "regionCode": "US", "videoDuration": "medium", "key": key}, timeout=30).json()
        items = s.get("items", [])
        if not items:
            continue
        vids = ",".join(i["id"]["videoId"] for i in items)
        v = requests.get(f"{api}/videos", params={"part": "statistics,snippet,contentDetails", "id": vids, "key": key}, timeout=30).json()["items"]
        chans = ",".join({i["snippet"]["channelId"] for i in v})
        c = {x["id"]: int(x["statistics"].get("subscriberCount", 0) or 0) for x in
             requests.get(f"{api}/channels", params={"part": "statistics", "id": chans, "key": key}, timeout=30).json()["items"]}
        views = [int(x["statistics"].get("viewCount", 0)) for x in v]
        med = st.median(views) if views else 0
        for x in v:
            vc = int(x["statistics"].get("viewCount", 0)); subs = c.get(x["snippet"]["channelId"], 0)
            age_days = max((dt.datetime.utcnow() - dt.datetime.fromisoformat(x["snippet"]["publishedAt"].replace("Z", ""))).days, 1)
            rows.append({"seed": q, "title": x["snippet"]["title"], "channel": x["snippet"]["channelTitle"], "subs": subs,
                         "views": vc, "views_per_day": round(vc / age_days, 1), "outlier_vs_subs": round(vc / max(subs, 1), 2),
                         "outlier_vs_seed_median": round(vc / med, 2) if med else None, "published": x["snippet"]["publishedAt"][:10],
                         "url": f"https://youtu.be/{x['id']}"})
    rows.sort(key=lambda r: (-r["outlier_vs_subs"]))
    out = ROOT / "content" / "discovered.csv"
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    seeds_summary = {}
    for r in rows:
        seeds_summary.setdefault(r["seed"], []).append(r["views_per_day"])
    print("Demand by seed (median views/day of top results):")
    for sd, xs in sorted(seeds_summary.items(), key=lambda kv: -st.median(kv[1])):
        print(f"  {sd:40s} {st.median(xs):10,.0f}")
    return out
