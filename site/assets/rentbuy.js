// Rent vs buy model: a line-for-line port of breakeven/models/rent_vs_buy.py.
// Parity with the Python model is checked by tests/test_calculator_parity.py.
export function simulate(a) {
  const n = a.years * 12;
  const mg = (x) => Math.pow(1 + x, 1 / 12) - 1;
  const gHome = mg(a.home_growth), gRent = mg(a.rent_growth), gInv = mg(a.invest_return), gCost = mg(a.cost_inflation);
  const down = a.home_price * a.down_pct, loan = a.home_price - down, closing = a.home_price * a.buy_closing_pct;
  const r = a.mortgage_rate / 12, N = a.term_years * 12;
  const pi = r === 0 ? loan / N : (loan * r) / (1 - Math.pow(1 + r, -N));
  let balance = loan, value = a.home_price, rent = a.rent_monthly, ins = a.insurance_annual / 12;
  let rp = down + closing, rb = down + closing, bp = 0, bb = 0;
  const buyer = [], renter = [], ownerCost = [];
  let first = null;
  for (let i = 0; i < n; i++) {
    const interest = balance * r;
    const princ = balance > 0 ? Math.min(pi - interest, balance) : 0;
    const pay = balance > 0 ? interest + princ : 0;
    balance -= princ;
    const tax = (value * a.property_tax_pct) / 12, maint = (value * a.maintenance_pct) / 12;
    const oc = pay + tax + ins + maint;
    if (i === 0) first = { principal: princ, interest, tax, insurance: ins, maintenance: maint, total: oc, rent };
    const diff = oc - rent;
    rp *= 1 + gInv; bp *= 1 + gInv;
    if (diff > 0) { if (a.renter_invests_diff) { rp += diff; rb += diff; } }
    else { bp += -diff; bb += -diff; }
    value *= 1 + gHome;
    const rg = Math.max(rp - rb, 0), bg = Math.max(bp - bb, 0);
    renter.push(rp - rg * a.cap_gains_tax);
    buyer.push(value * (1 - a.sell_cost_pct) - balance + bp - bg * a.cap_gains_tax);
    ownerCost.push(oc);
    rent *= 1 + gRent; ins *= 1 + gCost;
  }
  let be = null;
  for (let i = 0; i < n; i++) {
    let ok = true;
    for (let j = i; j < Math.min(i + 12, n); j++) if (buyer[j] < renter[j]) { ok = false; break; }
    if (ok) { be = (i + 1) / 12; break; }
  }
  return { buyer, renter, ownerCost, pi, first, breakevenYears: be };
}

export const DEFAULTS = {
  home_price: 416700, down_pct: 0.2, mortgage_rate: 0.0711, term_years: 30, buy_closing_pct: 0.02, sell_cost_pct: 0.06,
  property_tax_pct: 0.009, insurance_annual: 3012, maintenance_pct: 0.01, rent_monthly: 2243, rent_growth: 0.03,
  home_growth: 0.04, invest_return: 0.07, cost_inflation: 0.03, cap_gains_tax: 0.15, years: 30, renter_invests_diff: true,
};
