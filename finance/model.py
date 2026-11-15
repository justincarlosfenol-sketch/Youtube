"""24-month financial model: conservative / moderate / optimistic.

EVERY input below is an ASSUMPTION, not a result. Replace them with actuals
from the dashboard as data arrives (the dashboard tracks the same quantities).
Run:  python finance/model.py   -> finance/scenarios.csv + docs/07-financial-model.md tables
"""
from __future__ import annotations

import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MONTHS = 24

SETUP = {  # one-time, USD
    "USB dynamic microphone (e.g. Samson Q2U / Rode PodMic USB)": 150,
    "Reflection filter / acoustic foam": 50,
    "Domain name (year 1)": 15,
}

SCENARIOS = {
    #                         cons     mod      opt
    "videos_per_month":      (4.33,    4.33,    4.33),
    "v1_views_28d":          (250,     700,     1800),    # first flagship's first-month views
    "new_video_growth_mo":   (0.10,    0.14,    0.18),    # monthly growth of a NEW video's first-month views
    "growth_cap_multiple":   (12,      20,      30),      # ceiling on that growth
    "tail_share_mo":         (0.08,    0.12,    0.15),    # library: each month after month 1, views = share x first-month views
    "shorts_views_per_mo":   (3000,    12000,   40000),   # funnel only; Shorts ad revenue treated as ~0
    "avg_view_minutes":      (3.6,     4.2,     4.8),     # long-form average view duration
    "subs_per_view":         (0.010,   0.014,   0.020),
    "ad_rpm":                (6.0,     10.0,    15.0),    # USD per 1,000 long-form views, only after YPP
    "affiliate_per_1k":      (0.80,    2.00,    4.00),    # USD per 1,000 long-form views (from month 2)
    "product_per_1k":        (0.50,    1.50,    3.00),    # spreadsheet models etc. (from month 2)
    "sponsor_cpm":           (25,      40,      60),      # USD per 1,000 views of a sponsored video
    "sponsor_min_views":     (10000,   10000,   10000),   # avg first-month views/video before sponsors engage
    "sponsor_fill":          (0.25,    0.50,    0.75),    # share of videos sponsored once eligible
    "monthly_tools":         (5,       25,      60),      # domain, newsletter, optional analytics tools
    "human_hours_per_video": (2.0,     1.5,     1.2),
}
YPP_HOURS, YPP_SUBS = 8000, 1000


def run(idx: int) -> list[dict]:
    p = {k: v[idx] for k, v in SCENARIOS.items()}
    first_month = []          # first-month views of each video, by publish month
    rows, cum_profit = [], -sum(SETUP.values())
    subs = 0.0
    hours_hist = []
    ypp_month = None
    for m in range(1, MONTHS + 1):
        mult = min((1 + p["new_video_growth_mo"]) ** (m - 1), p["growth_cap_multiple"])
        new_v = p["v1_views_28d"] * mult
        first_month.append(new_v)
        n = p["videos_per_month"]
        long_views = n * new_v + sum(p["tail_share_mo"] * fm * n for fm in first_month[:-1])
        hours = long_views * p["avg_view_minutes"] / 60
        hours_hist.append(hours)
        subs += (long_views + p["shorts_views_per_mo"] * 0.3) * p["subs_per_view"]
        if ypp_month is None and sum(hours_hist[-12:]) >= YPP_HOURS and subs >= YPP_SUBS:
            ypp_month = m
        ads = long_views / 1000 * p["ad_rpm"] if ypp_month and m > ypp_month else 0.0  # first payout the month after acceptance
        aff = long_views / 1000 * p["affiliate_per_1k"] if m >= 2 else 0.0
        prod = long_views / 1000 * p["product_per_1k"] if m >= 2 else 0.0
        spons = (n * p["sponsor_fill"] * new_v / 1000 * p["sponsor_cpm"]) if new_v >= p["sponsor_min_views"] else 0.0
        revenue = ads + aff + prod + spons
        costs = p["monthly_tools"] + 0.1 * prod   # ~10% marketplace fee on products
        profit = revenue - costs
        cum_profit += profit
        hrs = n * p["human_hours_per_video"]
        rows.append({"month": m, "long_views": round(long_views), "shorts_views": p["shorts_views_per_mo"],
                     "watch_hours": round(hours), "watch_hours_12m": round(sum(hours_hist[-12:])), "subs": round(subs),
                     "ypp": int(bool(ypp_month and m >= ypp_month)), "rev_ads": round(ads, 2), "rev_affiliate": round(aff, 2),
                     "rev_products": round(prod, 2), "rev_sponsors": round(spons, 2), "revenue": round(revenue, 2),
                     "costs": round(costs, 2), "profit": round(profit, 2), "cum_profit": round(cum_profit, 2),
                     "human_hours": round(hrs, 1), "rev_per_human_hour": round(revenue / hrs, 2) if hrs else 0})
    return rows


def main():
    names = ["conservative", "moderate", "optimistic"]
    allrows = []
    summary = []
    for i, nm in enumerate(names):
        rows = run(i)
        for r in rows:
            allrows.append({"scenario": nm, **r})
        ypp = next((r["month"] for r in rows if r["ypp"]), None)
        be = next((r["month"] for r in rows if r["cum_profit"] >= 0), None)
        k1 = next((r["month"] for r in rows if r["revenue"] >= 1000), None)
        k5 = next((r["month"] for r in rows if r["revenue"] >= 5000), None)
        m12, m24 = rows[11], rows[23]
        summary.append((nm, ypp, be, k1, k5, m12, m24, sum(r["revenue"] for r in rows[:12]), sum(r["revenue"] for r in rows[12:])))
    with open(HERE / "scenarios.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(allrows[0].keys())); w.writeheader(); w.writerows(allrows)

    def mo(x):
        return f"month {x}" if x else "not within 24 mo"
    md = ["| Scenario | YPP (8,000 h + 1,000 subs) | Cumulative break-even | First $1k month | First $5k month | Month-12 revenue | Month-24 revenue | Year-1 revenue | Year-2 revenue | Month-24 profit margin |",
          "|---|---|---|---|---|---:|---:|---:|---:|---:|"]
    for nm, ypp, be, k1, k5, m12, m24, y1, y2 in summary:
        margin = m24["profit"] / m24["revenue"] * 100 if m24["revenue"] else 0
        md.append(f"| {nm} | {mo(ypp)} | {mo(be)} | {mo(k1)} | {mo(k5)} | ${m12['revenue']:,.0f} | ${m24['revenue']:,.0f} | ${y1:,.0f} | ${y2:,.0f} | {margin:.0f}% |")
    mix = ["| Scenario (month 24) | Ads | Affiliate | Products | Sponsors | Revenue per human hour |", "|---|---:|---:|---:|---:|---:|"]
    for s in summary:
        m24 = s[6]
        mix.append(f"| {s[0]} | ${m24['rev_ads']:,.0f} | ${m24['rev_affiliate']:,.0f} | ${m24['rev_products']:,.0f} | ${m24['rev_sponsors']:,.0f} | ${m24['rev_per_human_hour']:,.0f} |")
    assum = ["| Assumption | Conservative | Moderate | Optimistic |", "|---|---:|---:|---:|"]
    for k, v in SCENARIOS.items():
        assum.append(f"| `{k}` | {v[0]:,} | {v[1]:,} | {v[2]:,} |")
    doc = ROOT / "docs" / "07-financial-model.md"
    tmpl = (HERE / "report_template.md").read_text()
    doc.write_text(tmpl.replace("{{SUMMARY}}", "\n".join(md)).replace("{{MIX}}", "\n".join(mix))
                   .replace("{{ASSUMPTIONS}}", "\n".join(assum))
                   .replace("{{SETUP}}", "\n".join(f"| {k} | ${v} |" for k, v in SETUP.items()) + f"\n| **Total** | **${sum(SETUP.values())}** |"))
    print("\n".join(md)); print(); print("\n".join(mix))


if __name__ == "__main__":
    main()
