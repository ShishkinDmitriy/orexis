"""`orexis-explain` held to what the grower writes: the fixed questions run over points the agent's
own sinks recorded — the greenhouse played by its simulator in-process, with no InfluxDB in the room —
and over points made by hand for the findings the greenhouse does not produce, so each question is
seen to name a thing once and say nothing stood out otherwise. The rows a live store answers are
pivoted back into those same points (`points_of`), held here to a round trip.

The season run is the in-process stand-in for the issue's measurement — the greenhouse at pace 600
for a real hour, which needs the containers — and prints its figures under `-s`: points read, the
report's time, and what each question answered (knowledge/runbooks/reflect.md).
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from agent import clock
from agent.metrics import window as metrics
from agent.runtime import Runtime, boot, world_name
from agent.series import HISTORY, METRICS, Sink, install
from agent.transport.mqtt.driver import Mqtt
from onboarding.explain import QUESTIONS, Stated, points_of, report, stated
from simulation.simulator import Simulator

WORLD = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
GH = "http://example.org/orexis/world/greenhouse#"
#  HOW LONG A SEASON THE SUITE PLAYS, in simulated hours at the greenhouse's ten-minute cadence: a day
#  is 144 passes; `OREXIS_EXPLAIN_HOURS` plays longer for the runbook's figures.
HOURS = float(os.environ.get("OREXIS_EXPLAIN_HOURS", "24"))

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
        "from 2026-01-01T12:10Z to 2026-01-01T12:10Z (0m); history: 1 step(s) taken, 0 landed — STOOD OUT",
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


class _Bus:
    """One broker: what the simulator publishes reaches the grower, what the grower publishes reaches
    the simulator, and every command is kept."""

    def __init__(self):
        self.runtime = self.simulator = None
        self.commands = []

    def subscribe(self, pattern):
        pass

    def publish(self, topic, payload, retain=False):
        payload = payload if isinstance(payload, bytes) else payload.encode()
        if topic.startswith("sensors/"):
            self.runtime.deliver(topic, payload, clock.now())
        else:
            self.commands.append((topic, payload))
            self.simulator.command(topic, payload)


def test_the_growers_season_is_reported_from_what_its_sinks_wrote(monkeypatch):
    """The greenhouse played by its simulator for `HOURS`, a reading every ten minutes, the grower
    dosing the bed as it dries, with a history and a metrics sink recording and a window a pass long:
    the report over those points names the dose's landings and finds nothing wrong — no want
    unreachable, the one desire searched, no search exhausted, no reading past a calibration point, no
    raw count repeated (the simulated instrument jitters, #879), no sensor doubted — which is the honest
    answer for a world that works. The raw count rides on every reading."""
    time_ = {"at": NOW}
    monkeypatch.setattr(clock, "now", lambda: time_["at"])
    history, windows = [], []
    install(HISTORY, Sink(HISTORY, "greenhouse-grower", lambda bucket, record: history.extend(record)))
    install(METRICS, Sink(METRICS, "greenhouse-grower-metrics", lambda bucket, record: windows.extend(record)))
    metrics.configure(interval_s=0)
    metrics.identify(world=world_name(WORLD), agent="grower")
    try:
        bus = _Bus()
        bus.simulator = Simulator(WORLD, bus, now=NOW)
        bus.runtime = Runtime(boot(WORLD, "grower"), "grower", transport=Mqtt(GH + "grower", bus))
        bus.simulator.open()
        passes, started = 0, time.perf_counter()
        while time_["at"] < NOW + timedelta(hours=HOURS):
            bus.simulator.step(time_["at"])
            bus.runtime.run(passes=1, poll_s=0)
            passes += 1
            time_["at"] += timedelta(minutes=10)
        ran_s = time.perf_counter() - started
        bus.runtime.stop()
    finally:
        install(HISTORY, None)
        install(METRICS, None)
        metrics.reset()
        metrics.identify()
    held = stated("greenhouse", "grower")
    started = time.perf_counter()
    season = report("greenhouse", "grower", history, windows, held)
    report_s = time.perf_counter() - started
    found = {title: lines for title, _, lines in season.sections}
    print(f"\n{passes} passes over {HOURS:g} simulated hours in {ran_s:.1f} s; {len(history)} history and {len(windows)} metrics "
          f"points; report in {report_s * 1000:.1f} ms\n{season.text()}")
    doses = [t for t, _ in bus.commands if t == "actuators/pump/command"]
    assert doses and len(doses) == len([p for p in history if p["measurement"] == "Step" and p["fields"].get("taken")])
    assert all("raw" in p["fields"] for p in history if p["measurement"] != "Step"), "the raw count rides on every reading"
    assert found["wants nothing reached"] == [] and found["desires never unmet"] == [] and found["searches exhausted"] == []
    (dosing,) = found["landings"]
    assert dosing.startswith(f"Dosing: {len(doses)} verdict(s), {len(doses)} landed, 0 timed out") and "STOOD OUT" not in dosing
    assert found["probes"] == [], found["probes"]
    assert held.desires == {"the_bed_is_comfortable"} and held.fractions == {"moisture_probe"}
