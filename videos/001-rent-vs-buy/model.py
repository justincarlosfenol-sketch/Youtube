"""Computes every number used in video 001 and writes data.json.

Run: python videos/001-rent-vs-buy/model.py
All narration numbers and chart data are bound from this file, so the script
can never drift from the model.
"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict, replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

import numpy as np  # noqa: E402

from breakeven.models.rent_vs_buy import Assumptions, breakeven_grid, rent_for_ptr, simulate  # noqa: E402

BASE = Assumptions()


def yearly(res, a: Assumptions, step_months: int = 3):
    """Net worth series sampled every `step_months`, with the t=0 point prepended."""
    loan = a.home_price * (1 - a.down_pct)
    b0 = a.home_price * (1 - a.sell_cost_pct) - loan
    r0 = a.home_price * (a.down_pct + a.buy_closing_pct)
    idx = np.arange(step_months - 1, len(res.months), step_months)
    x = [0.0] + [float(res.months[i]) / 12 for i in idx]
    b = [b0] + [float(res.buyer_nw[i]) for i in idx]
    r = [r0] + [float(res.renter_nw[i]) for i in idx]
    return x, b, r


def adv(a: Assumptions):
    res = simulate(a)
    x, b, r = yearly(res, a, 12)
    return x, [bb - rr for bb, rr in zip(b, r)], res.breakeven_years


def main():
    a = BASE
    res = simulate(a)
    x, b, r = yearly(res, a)
    bd = res.first_month_breakdown
    down = a.home_price * a.down_pct
    closing = a.home_price * a.buy_closing_pct
    owner_total = sum(v for k, v in bd.items() if k != "Rent")
    y = lambda yr: (float(res.buyer_nw[yr * 12 - 1]), float(res.renter_nw[yr * 12 - 1]))  # noqa: E731

    data = {
        "inputs": {k: v for k, v in asdict(a).items()},
        "price": a.home_price, "rate_pct": a.mortgage_rate * 100, "rent": a.rent_monthly,
        "down": down, "loan": a.home_price - down, "closing": closing, "upfront": down + closing,
        "pi": res.monthly_pi,
        "m1": {"interest": bd["Interest"], "principal": bd["Principal"], "tax": bd["Property tax"],
               "insurance": bd["Insurance"], "maintenance": bd["Maintenance"]},
        "owner_total": owner_total,
        "delta": owner_total - a.rent_monthly,
        "delta_pct_of_pi": (owner_total - a.rent_monthly) / res.monthly_pi * 100,
        "interest_share_pct": bd["Interest"] / res.monthly_pi * 100,
        "interest_cents": round(bd["Interest"] / res.monthly_pi * 100),
        "ptr": a.price_to_rent(),
        "be": res.breakeven_years,
        "day0": {"buyer": b[0], "renter": r[0]},
        "y1": {"buyer": y(1)[0], "renter": y(1)[1], "gap": y(1)[1] - y(1)[0]},
        "y30": {"buyer": y(30)[0], "renter": y(30)[1], "gap": y(30)[0] - y(30)[1]},
        "race": {"x": x, "buyer": b, "renter": r},
    }

    # levers
    def lever(field, values, labels):
        stops = []
        for v, lab in zip(values, labels):
            xx, aa, be = adv(replace(a, **{field: v}))
            stops.append({"label": lab, "be": be, "adv": aa})
        return {"x": xx, "stops": stops}

    data["lever_home"] = lever("home_growth", [0.03, 0.04, 0.05], ["3%", "4%", "5%"])
    data["lever_rate"] = lever("mortgage_rate", [0.05, 0.06, 0.0711], ["5%", "6%", "7.11%"])
    ptr_vals = [12.0, a.price_to_rent(), 18.0]
    stops = []
    for p, lab in zip(ptr_vals, ["12", f"{a.price_to_rent():.1f}", "18"]):
        xx, aa, be = adv(replace(a, rent_monthly=rent_for_ptr(a, p)))
        stops.append({"label": lab, "be": be, "adv": aa})
    data["lever_ptr"] = {"x": xx, "stops": stops}

    # heatmap: rows = mortgage rate, cols = price-to-rent
    rates = [0.05, 0.055, 0.06, 0.065, 0.0711, 0.075, 0.08]
    ptrs = [10, 12, 14, a.price_to_rent(), 18, 20, 22]
    grid = breakeven_grid(a, "rent_monthly", [rent_for_ptr(a, p) for p in ptrs], "mortgage_rate", rates)
    data["heat"] = {
        "values": [[None if np.isnan(v) else round(float(v), 1) for v in row] for row in grid],
        "rows": [f"{r*100:.2f}".rstrip("0").rstrip(".") + "%" for r in rates],
        "cols": [f"{p:.1f}".rstrip("0").rstrip(".") for p in ptrs],
        "today": {"row": 4, "col": 3},
    }
    spend = simulate(replace(a, renter_invests_diff=False))
    data["be_spender"] = spend.breakeven_years
    data["sources_note"] = "See sources.yaml"
    (HERE / "data.json").write_text(json.dumps(data, indent=1))
    print(f"breakeven {data['be']:.2f}y | spender {data['be_spender']:.2f}y | PI {data['pi']:.2f} | "
          f"owner {owner_total:.0f} | delta {data['delta']:.0f} | y30 gap {data['y30']['gap']:.0f}")


if __name__ == "__main__":
    main()
