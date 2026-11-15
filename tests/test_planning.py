import datetime as dt

from breakeven.planning import build_calendar, load_ideas


def test_calendar_has_13_flagships_and_pins():
    rows = load_ideas()
    assert len(rows) >= 50
    cal = build_calendar(dt.date(2026, 12, 1), rows=rows)
    longs = [c for c in cal if c["type"] == "LONG-FORM"]
    assert len(longs) == 13
    assert longs[0]["idea_id"] == "1"
    assert len({c["idea_id"] for c in longs}) == 13  # no repeats
