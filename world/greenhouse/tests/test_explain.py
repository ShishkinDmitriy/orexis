"""`orexis-explain` held to points made by hand for each finding, so each question is seen to name a thing once and say
nothing stood out otherwise; to a journal's steps; and to a round trip of the rows a live store answers through
`points_of` (knowledge/runbooks/reflect.md)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pyoxigraph as ox

from onboarding.explain import _STEPS_Q, QUESTIONS, Stated, points_of, report, steps

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

T = lambda minutes: NOW + timedelta(minutes=minutes)


def _metric(measurement: str, at: datetime, fields: dict, **tags) -> dict:
    return {"measurement": measurement, "time": at, "tags": {"world": "w", "agent": "a", **tags}, "fields": fields}


def _reading(sensor: str, at: datetime, value: float, raw: float | None = None, measurement: str = "SoilMoisture") -> dict:
    fields = {"value": value, **({"raw": raw} if raw is not None else {})}
    return {"measurement": measurement, "time": at, "tags": {"feature": "bed", "sensor": sensor}, "fields": fields}


def _sections(history, metrics_, stated_: Stated) -> dict[str, list[str]]:
    return {title: lines for title, _, lines in report("w", "a", history, metrics_, stated_).sections}


def test_every_question_names_what_it_found_in_the_series_own_words():
    """Points made by hand for each finding: a want unreachable under one desire, a dose timed out, a
    desire never searched, a desire whose every search was exhausted, a probe past 1.0 and one whose
    raw count stuck — and the agent's own word that it doubted the probe."""
    held = Stated(desires=frozenset({"the_bed_is_comfortable", "the_bed_is_lit"}), fractions=frozenset({"moisture_probe"}))
    metrics_ = [
        _metric("unreachable", T(0), {"count": 3}, desire="the_bed_is_lit"),
        _metric("unreachable", T(60), {"count": 2}, desire="the_bed_is_lit"),
        _metric("landing", T(10), {"count": 2, "landed": 1, "timed_out": 1, "late_s_sum": 1200.0, "late_s_mean": 600.0, "late_s_max": 900.0},
                action="Dosing", desire="the_bed_is_comfortable"),
        _metric("landing", T(20), {"count": 1, "landed": 1, "timed_out": 0, "late_s_sum": 300.0, "late_s_mean": 300.0, "late_s_max": 300.0},
                action="Heating", desire="the_bed_is_comfortable"),
        _metric("search", T(0), {"count": 4, "budget_max": 300.0, "weighed_sum": 1200.0, "weighed_max": 300.0},
                desire="the_bed_is_comfortable", scope="pump", outcome="Exhausted"),
        _metric("search", T(60), {"count": 1, "budget_max": 300.0, "weighed_sum": 300.0, "weighed_max": 300.0},
                desire="the_bed_is_comfortable", scope="pump", outcome="Exhausted"),
        _metric("doubted", T(70), {"silent": 1, "stuck": 0}, sensor="moisture_probe"),
        _metric("doubted", T(80), {"silent": 1, "stuck": 1}, sensor="moisture_probe"),
    ]
    history = [
        _reading("moisture_probe", T(0), 0.4, 400), _reading("moisture_probe", T(10), 1.02, 1020),
        _reading("moisture_probe", T(20), 1.05, 1050), _reading("moisture_probe", T(30), 0.9, 900),
        _reading("moisture_probe", T(40), 0.9, 900), _reading("moisture_probe", T(50), 0.9, 900),
        _reading("thermometer", T(0), 21.0, 21.0, "AirTemperature"), _reading("thermometer", T(10), 21.4, 21.4, "AirTemperature"),
        {"measurement": "Step", "time": T(5), "tags": {"action": "Dosing", "want": "w1", "valve": "pump"}, "fields": {"taken": True}},
        {"measurement": "Step", "time": T(15), "tags": {"action": "Dosing", "want": "w1", "valve": "pump"}, "fields": {"landed": False}},
    ]
    found = _sections(history, metrics_, held)
    assert found["wants nothing reached"] == ["the_bed_is_lit: unreachable in 5 pass(es) over 2 window(s), from 2026-01-01T12:00Z to 2026-01-01T13:00Z (1h 0m)"]
    assert found["landings"] == [
        "Dosing: 2 verdict(s), 1 landed, 1 timed out, 0 ended undone; late_s mean 600 s, max 900 s; "
        "from 2026-01-01T12:10Z to 2026-01-01T12:10Z (0m); journal: 1 step(s) taken, 0 landed — STOOD OUT",
        "Heating: 1 verdict(s), 1 landed, 0 timed out, 0 ended undone; late_s mean 300 s, max 300 s; from 2026-01-01T12:20Z to 2026-01-01T12:20Z (0m)"]
    assert found["desires never unmet"] == ["the_bed_is_lit: no search over the window"]
    assert found["searches exhausted"] == [
        "the_bed_is_comfortable: every one of 5 search(es) exhausted, budget 300, weighed 300 a search, max 300; "
        "from 2026-01-01T12:00Z to 2026-01-01T13:00Z (1h 0m)"]
    assert found["probes"] == [
        "moisture_probe (SoilMoisture): 2 reading(s) past 1.0, to 1.05, from 2026-01-01T12:10Z to 2026-01-01T12:20Z (10m)",
        "moisture_probe (SoilMoisture): raw count 900 unchanged for 3 readings, from 2026-01-01T12:30Z to 2026-01-01T12:50Z (20m)",
        "moisture_probe: said silent in 2 window(s), from 2026-01-01T13:10Z to 2026-01-01T13:20Z (10m)",
        "moisture_probe: said stuck in 1 window(s), from 2026-01-01T13:20Z to 2026-01-01T13:20Z (0m)"]
    #  A THERMOMETER IS NO FRACTION: 21 is not "past 1.0", and a reading in degrees is held to no calibration point here.
    assert not any(line.startswith("thermometer") for line in found["probes"])


def test_a_quiet_season_says_nothing_stood_out_and_a_mixed_one_is_not_exhausted():
    """No point at all: every question says nothing stood out, and a desire held is idle only where one
    is stated; a desire whose searches ended Satisfied as well as Exhausted is not one whose EVERY search
    was; a probe reading inside 0..1 with a raw count that always moved is not named."""
    quiet = _sections([], [], Stated())
    assert set(quiet) == {title for title, _, _ in QUESTIONS} and all(lines == [] for lines in quiet.values())
    assert report("w", "a", [], [], Stated()).text().count("nothing stood out") == len(QUESTIONS)
    mixed = [_metric("search", T(0), {"count": 2}, desire="d", outcome="Exhausted"),
             _metric("search", T(10), {"count": 1}, desire="d", outcome="Satisfied")]
    history = [_reading("moisture_probe", T(i * 10), 0.3 + i * 0.001, 300 + i) for i in range(5)]
    found = _sections(history, mixed, Stated(desires=frozenset({"d"}), fractions=frozenset({"moisture_probe"})))
    assert found["searches exhausted"] == [] and found["desires never unmet"] == [] and found["probes"] == []


def test_the_steps_a_journal_keeps_are_the_points_the_questions_read():
    """A dose taken and answered undone, as the executor's events state them: read back from the journal by its
    action, a taking and a verdict, at their instants — and nothing before `since`."""
    journal = ox.Store()
    journal.load(path=str(Path(__file__).parent / "a_dose_undone.nq"), format=ox.RdfFormat.N_QUADS)
    assert steps(journal.query(_STEPS_Q)) == [
        {"measurement": "Step", "tags": {"action": "Dosing"}, "fields": {"taken": True}, "time": T(5)},
        {"measurement": "Step", "tags": {"action": "Dosing"}, "fields": {"landed": False}, "time": T(15)}]
    assert [p["time"] for p in steps(journal.query(_STEPS_Q), since=T(10))] == [T(15)]


class _Record:
    def __init__(self, values):
        self.values = values


class _Table:
    def __init__(self, records):
        self.records = records


def test_the_rows_a_store_answers_pivot_back_into_the_points_the_sink_wrote():
    """The store answers one row per field, with the tags as columns beside Flux's own; `points_of` is
    the point the agent wrote, fields together, tags apart, in time order."""
    written = [_metric("landing", T(10), {"count": 2, "landed": 1}, action="Dosing"),
               _reading("moisture_probe", T(0), 0.4, 400)]
    rows_ = []
    for p in written:
        for name, value in p["fields"].items():
            rows_.append(_Record({"result": "_result", "table": 0, "_start": T(-100), "_stop": T(100), "_time": p["time"],
                                  "_measurement": p["measurement"], "_field": name, "_value": value, **p["tags"]}))
    back = points_of([_Table(rows_[:2]), _Table(rows_[2:])])
    assert back == [written[1], written[0]], back
