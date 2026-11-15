"""The website calculator (JS) must reproduce the Python model exactly."""
import json
import subprocess
from dataclasses import asdict, replace
from pathlib import Path

from breakeven.models.rent_vs_buy import Assumptions, simulate

ROOT = Path(__file__).resolve().parents[1]
CASES = [{}, {"mortgage_rate": 0.05}, {"home_growth": 0.03}, {"rent_monthly": 1600}, {"renter_invests_diff": False},
         {"down_pct": 0.1, "maintenance_pct": 0.02}, {"invest_return": 0.1, "home_growth": 0.05}]


def test_js_matches_python():
    base = Assumptions()
    inputs = [asdict(replace(base, **c)) for c in CASES]
    js = f"""import {{simulate}} from '{ROOT}/site/assets/rentbuy.js';
const cases = {json.dumps(inputs)};
console.log(JSON.stringify(cases.map(a => {{const r = simulate(a); return [r.breakevenYears, r.buyer[359], r.renter[359], r.pi];}})));"""
    out = subprocess.run(["node", "--input-type=module", "-e", js], capture_output=True, text=True, check=True).stdout
    for case, (be, b360, r360, pi) in zip(inputs, json.loads(out)):
        py = simulate(Assumptions(**case))
        assert (be is None) == (py.breakeven_years is None), case
        if be is not None:
            assert abs(be - py.breakeven_years) < 1e-9, case
        assert abs(b360 - py.buyer_nw[-1]) < 1e-4 and abs(r360 - py.renter_nw[-1]) < 1e-4, case
        assert abs(pi - py.monthly_pi) < 1e-6
