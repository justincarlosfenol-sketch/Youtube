from dataclasses import replace

from breakeven.models.rent_vs_buy import Assumptions, mortgage_payment, simulate


def test_mortgage_payment_known_value():
    # $333,360 at 7.11% for 30 years -> ~$2,242.53/month
    assert abs(mortgage_payment(333_360, 0.0711, 30) - 2242.53) < 0.01


def test_baseline_breakeven_and_monotonicity():
    a = Assumptions()
    be = simulate(a).breakeven_years
    assert 9.0 < be < 10.0
    # lower rates and faster appreciation must make buying win sooner
    assert simulate(replace(a, mortgage_rate=0.06)).breakeven_years < be
    assert simulate(replace(a, home_growth=0.05)).breakeven_years < be
    # an undisciplined renter loses sooner
    assert simulate(replace(a, renter_invests_diff=False)).breakeven_years < be


def test_day_one_accounting():
    a = Assumptions()
    r = simulate(a)
    assert r.renter_nw[0] > r.buyer_nw[0]  # buyer pays closing + would pay selling costs
