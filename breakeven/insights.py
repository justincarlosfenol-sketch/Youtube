"""Turn the analytics warehouse into comparable per-video metrics and
pattern-based recommendations. Guards against single-video conclusions:
a pattern is only reported when every compared group has >= MIN_GROUP videos.
"""
from __future__ import annotations

import datetime as dt
import sqlite3
import statistics as st

MIN_GROUP = 3
MIN_VIDEOS = 6
YPP_HOURS = 8000      # long-form bar from 1 Feb 2027 (4,000 before)
YPP_SUBS = 1000


def _median(xs):
    xs = [x for x in xs if x is not None]
    return st.median(xs) if xs else None


def video_table(con: sqlite3.Connection, window_days: int = 28) -> list[dict]:
    rows = con.execute("SELECT video_id, slug, title, published_at, duration_s, is_short, series, thumbnail_template, "
                       "production_hours, production_cost FROM videos ORDER BY published_at").fetchall()
    out = []
    aff = {r[0]: r[1] for r in con.execute("SELECT video_slug, SUM(amount) FROM revenue WHERE video_slug!='' GROUP BY video_slug")}
    for vid, slug, title, pub, dur, short, series, tpl, hours, cost in rows:
        end = (dt.date.fromisoformat(pub) + dt.timedelta(days=window_days)).isoformat()
        w = con.execute("SELECT SUM(views), SUM(minutes_watched), SUM(impressions), SUM(subs_gained)-SUM(subs_lost), "
                        "SUM(est_revenue), SUM(views*avg_view_pct)/NULLIF(SUM(views),0) FROM video_daily "
                        "WHERE video_id=? AND date<?", (vid, end)).fetchone()
        tot = con.execute("SELECT SUM(views), SUM(minutes_watched), SUM(est_revenue) FROM video_daily WHERE video_id=?", (vid,)).fetchone()
        views28, mins28, imp28, subs28, rev28, pct28 = w
        other_rev = aff.get(slug, 0.0) or 0.0
        total_rev = (tot[2] or 0) + other_rev
        out.append({
            "video_id": vid, "slug": slug, "title": title, "published": pub, "duration_min": round((dur or 0) / 60, 1),
            "is_short": bool(short), "series": series or "—", "template": tpl or "—",
            "views_28d": views28 or 0, "ctr_28d": round(100 * views28 / imp28, 2) if imp28 else None,
            "avd_pct_28d": round(pct28, 1) if pct28 else None, "subs_per_1k": round(1000 * subs28 / views28, 1) if views28 else None,
            "views_total": tot[0] or 0, "watch_hours_total": round((tot[1] or 0) / 60, 1),
            "revenue_total": round(total_rev, 2), "production_hours": hours, "production_cost": cost or 0,
            "profit": round(total_rev - (cost or 0), 2),
            "rev_per_prod_hour": round(total_rev / hours, 2) if hours else None,
        })
    return out


def kpis(con: sqlite3.Connection, days: int | None = None) -> dict:
    last = con.execute("SELECT MAX(date) FROM channel_daily").fetchone()[0]
    if not last:
        return {}
    lo = "0000-00-00" if days is None else (dt.date.fromisoformat(last) - dt.timedelta(days=days - 1)).isoformat()
    v, m, sg, sl, rev = con.execute("SELECT SUM(views),SUM(minutes_watched),SUM(subs_gained),SUM(subs_lost),SUM(est_revenue) "
                                    "FROM channel_daily WHERE date>=?", (lo,)).fetchone()
    other = con.execute("SELECT stream, SUM(amount) FROM revenue WHERE date>=? GROUP BY stream", (lo,)).fetchall()
    costs = con.execute("SELECT SUM(amount) FROM costs WHERE date>=?", (lo,)).fetchone()[0] or 0
    prod = con.execute("SELECT SUM(production_cost), SUM(production_hours) FROM videos WHERE published_at>=?", (lo,)).fetchone()
    y365 = (dt.date.fromisoformat(last) - dt.timedelta(days=364)).isoformat()
    hours365 = (con.execute("SELECT SUM(minutes_watched) FROM channel_daily WHERE date>=?", (y365,)).fetchone()[0] or 0) / 60
    subs_total = con.execute("SELECT SUM(subs_gained)-SUM(subs_lost) FROM channel_daily").fetchone()[0] or 0
    revenue = (rev or 0) + sum(a for _, a in other)
    total_cost = costs + (prod[0] or 0)
    imp = con.execute("SELECT SUM(impressions), SUM(views) FROM video_daily WHERE date>=? AND impressions IS NOT NULL", (lo,)).fetchone()
    pct = con.execute("SELECT SUM(views*avg_view_pct)/NULLIF(SUM(views),0) FROM video_daily WHERE date>=?", (lo,)).fetchone()[0]
    return {
        "as_of": last, "views": v or 0, "watch_hours": round((m or 0) / 60, 1), "subs_net": (sg or 0) - (sl or 0),
        "subs_total": subs_total, "ad_revenue": round(rev or 0, 2),
        "other_revenue": {s: round(a, 2) for s, a in other}, "revenue": round(revenue, 2),
        "costs": round(total_cost, 2), "profit": round(revenue - total_cost, 2),
        "rpm": round(1000 * revenue / v, 2) if v else None,
        "ctr": round(100 * imp[1] / imp[0], 2) if imp and imp[0] else None,
        "avd_pct": round(pct, 1) if pct else None,
        "rev_per_prod_hour": round(revenue / prod[1], 2) if prod[1] else None,
        "ypp": {"hours_365": round(hours365), "hours_target": YPP_HOURS, "subs": subs_total, "subs_target": YPP_SUBS},
    }


def patterns(videos: list[dict]) -> list[dict]:
    longs = [v for v in videos if not v["is_short"] and v["views_28d"]]
    if len(longs) < MIN_VIDEOS:
        return [{"kind": "info", "text": f"Not enough data for pattern analysis yet: {len(longs)}/{MIN_VIDEOS} long-form videos "
                                         "with 28 days of data. Keep publishing; decisions wait for repeatable evidence."}]
    out = []

    def compare(key, metric, label, fmt="{:.1f}"):
        groups = {}
        for v in longs:
            if v.get(metric) is not None and v.get(key) not in (None, "—"):
                groups.setdefault(v[key], []).append(v[metric])
        groups = {k: g for k, g in groups.items() if len(g) >= MIN_GROUP}
        if len(groups) < 2:
            return
        med = sorted(((_median(g), k, len(g)) for k, g in groups.items()), reverse=True)
        best, worst = med[0], med[-1]
        lift = (best[0] / worst[0] - 1) * 100 if worst[0] else 0
        if lift >= 15:
            out.append({"kind": "pattern", "text": f"{label}: '{best[1]}' (median {fmt.format(best[0])}, n={best[2]}) beats "
                                                   f"'{worst[1]}' (median {fmt.format(worst[0])}, n={worst[2]}) by {lift:.0f}%.",
                        "action": f"Default to '{best[1]}'; keep 1 in 4 uploads testing alternatives."})

    compare("template", "ctr_28d", "Thumbnail template → CTR", "{:.2f}%")
    compare("series", "views_28d", "Series → 28-day views", "{:,.0f}")
    compare("series", "avd_pct_28d", "Series → retention", "{:.1f}%")
    # duration buckets
    for v in longs:
        v["length_bucket"] = "< 9 min" if v["duration_min"] < 9 else "9–12 min" if v["duration_min"] <= 12 else "> 12 min"
    compare("length_bucket", "avd_pct_28d", "Length → retention", "{:.1f}%")
    compare("length_bucket", "views_28d", "Length → 28-day views", "{:,.0f}")

    med_views = _median([v["views_28d"] for v in longs])
    outliers = [v for v in longs if v["views_28d"] >= 2 * med_views]
    if outliers:
        out.append({"kind": "opportunity", "text": "Over-performers (≥2× median 28-day views): " +
                    "; ".join(f"{v['title']} ({v['views_28d']:,})" for v in outliers[:5]),
                    "action": "Plan a sequel or spin-off and a 3-Short cutdown for each; refresh annually."})
    ctr = _median([v["ctr_28d"] for v in longs])
    if ctr is not None and ctr < 4:
        out.append({"kind": "warning", "text": f"Median CTR is {ctr:.1f}% (below ~4%).",
                    "action": "Packaging problem before a topic problem: run Test & Compare on the next 3 uploads."})
    avd = _median([v["avd_pct_28d"] for v in longs])
    if avd is not None and avd < 35:
        out.append({"kind": "warning", "text": f"Median retention is {avd:.0f}% of runtime.",
                    "action": "Check the retention graph for the first 30 s; tighten cold opens and add an open loop before minute 2."})
    if not out:
        out.append({"kind": "info", "text": "No pattern exceeds the 15% lift threshold across groups of ≥3 videos yet."})
    return out


def timeseries(con: sqlite3.Connection) -> dict:
    daily = con.execute("SELECT date, views, minutes_watched/60.0, subs_gained-subs_lost, est_revenue FROM channel_daily ORDER BY date").fetchall()
    months = {}
    for d, *_r, rev in daily:
        months.setdefault(d[:7], {"adsense": 0.0, "affiliate": 0.0, "sponsor": 0.0, "product": 0.0})["adsense"] += rev or 0
    for d, stream, amt in con.execute("SELECT date, stream, amount FROM revenue"):
        m = months.setdefault(d[:7], {"adsense": 0.0, "affiliate": 0.0, "sponsor": 0.0, "product": 0.0})
        m[stream if stream in m else "product"] += amt
    return {"daily": [{"date": d, "views": v, "hours": round(h, 1), "subs": s} for d, v, h, s, _ in daily],
            "monthly_revenue": [{"month": k, **{s: round(x, 2) for s, x in v.items()}} for k, v in sorted(months.items())]}
