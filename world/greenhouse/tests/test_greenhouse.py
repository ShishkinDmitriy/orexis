"""The greenhouse in the 0.2.0 runtime: readings arrive over MQTT, sensing writes them and the rules
conclude their sides, the grower's desire mints a want where a side is below, the plan's step is
taken by sending the device a command sized from the reading, and the next reading answers it.
The broker is a fake client: what is subscribed to and published is what is held."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from agent import clock
from agent.ontology import OREXIS
from agent.runtime import UNFINISHED, Runtime, boot
from agent.series import HISTORY, Sink, install
from agent.store import graphs_of, rows
from agent.transport.mqtt.driver import Mqtt

WORLD = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
GH = "http://example.org/orexis/world/greenhouse#"


class Broker:
    """What the grower subscribes to and publishes, and nothing else of MQTT."""

    def __init__(self):
        self.subscribed, self.published = [], []

    def subscribe(self, pattern):
        self.subscribed.append(pattern)

    def publish(self, topic, payload, retain=False):
        self.published.append((topic, json.loads(payload), retain))


class Clock:
    """One timeline for the world and the agent: a test sets where it stands, and every read
    after that moves it on by a second, as a running agent's clock does."""

    def __init__(self, at):
        self.at = at

    def __call__(self):
        self.at += timedelta(seconds=1)
        return self.at


def _grower(monkeypatch):
    time = Clock(NOW)
    monkeypatch.setattr(clock, "now", time)
    beliefs = boot(WORLD, "grower")
    broker = Broker()
    runtime = Runtime(beliefs, "grower", transport=Mqtt(GH + "grower", broker))
    runtime.time = time
    return runtime, broker


def _sides(beliefs) -> set[tuple[str, str]]:
    q = """SELECT ?p ?side WHERE { ?obs sosa:observedProperty ?p ; ?side ?range .
           VALUES ?side { sensing:below sensing:inside sensing:above } }"""
    return {(r["p"].rsplit("#", 1)[-1], r["side"].rsplit("#", 1)[-1])
            for r in rows(beliefs, q, graphs_of(beliefs, OREXIS + "BeliefGraph"))}


def test_the_grower_listens_to_the_instruments_of_the_bed_it_acts_for(monkeypatch):
    _, broker = _grower(monkeypatch)
    assert sorted(broker.subscribed) == ["sensors/moisture_probe/reading", "sensors/thermometer/reading"]


def test_a_reading_is_written_and_its_side_concluded(monkeypatch):
    runtime, _ = _grower(monkeypatch)
    runtime.deliver("sensors/moisture_probe/reading", b'{"value": 0.2}', NOW)
    runtime.drain(NOW)
    assert ("SoilMoisture", "below") in _sides(runtime.beliefs), "under the bed's floor of 0.30"


def test_a_dry_bed_is_dosed_by_a_command_sized_from_the_reading_and_the_next_reading_answers_it(monkeypatch):
    """0.2 against a range of 0.30 to 0.60: the middle is 0.45, two litres a fraction make half a
    litre, which is the pump's cap. The dose goes out on the pump's topic, not retained; the next
    reading, 0.45, is revised inside and the intention is done."""
    runtime, broker = _grower(monkeypatch)
    runtime.deliver("sensors/thermometer/reading", b'{"value": 21.0}', NOW)
    runtime.deliver("sensors/moisture_probe/reading", b'{"value": 0.2}', NOW)
    assert runtime.run(passes=1, poll_s=0) == UNFINISHED
    assert broker.published == [("actuators/pump/command", {"dose_ml": 500}, False)]
    assert len(runtime.started["execution"].walking()) == 1, "the world has not answered yet"
    runtime.time.at = NOW + timedelta(minutes=5)
    runtime.deliver("sensors/moisture_probe/reading", b'{"value": 0.45}', runtime.time.at)
    runtime.run(passes=2, poll_s=0)
    assert runtime.started["execution"].walking() == [], "the reading was revised inside and answered the dose"
    assert ("SoilMoisture", "inside") in _sides(runtime.beliefs)
    assert len(broker.published) == 1, "one dose, and nothing more once the bed is comfortable"


@pytest.fixture
def history():
    written = []
    install(HISTORY, Sink(HISTORY, "greenhouse-grower", lambda bucket, record: written.extend(record)))
    yield written
    install(HISTORY, None)


def test_history_holds_every_reading_and_the_dose_taken_and_landed(monkeypatch, history):
    """Both kinds of point, each from the package that decided it (#825): sensing's three readings,
    measured under their properties, and execution's dose — taken when the command went out, and
    landed when the next reading was revised inside — tagged with the action, the want it was for
    and the values the action takes."""
    runtime, broker = _grower(monkeypatch)
    runtime.deliver("sensors/thermometer/reading", b'{"value": 21.0}', NOW)
    runtime.deliver("sensors/moisture_probe/reading", b'{"value": 0.2}', NOW)
    runtime.run(passes=1, poll_s=0)
    runtime.time.at = NOW + timedelta(minutes=5)
    runtime.deliver("sensors/moisture_probe/reading", b'{"value": 0.45}', runtime.time.at)
    runtime.run(passes=2, poll_s=0)
    assert runtime.started["execution"].walking() == [], "the dose landed"
    observed = [(p["measurement"], p["fields"]["value"], p["time"]) for p in history if p["measurement"] != "Step"]
    assert observed == [("AirTemperature", 21.0, NOW), ("SoilMoisture", 0.2, NOW),
                        ("SoilMoisture", 0.45, NOW + timedelta(minutes=5))]
    steps = [p for p in history if p["measurement"] == "Step"]
    assert [p["fields"] for p in steps] == [{"taken": True}, {"landed": True}]
    (taken, landed) = steps
    assert taken["tags"] == landed["tags"], "one step, said twice"
    assert taken["tags"]["action"] == "Dosing" and set(taken["tags"]) == {"action", "want", "valve", "reading"}
    assert taken["tags"]["valve"] == "pump"
    assert taken["time"] < landed["time"], "taken, then answered"
    assert len(broker.published) == 1


def test_a_dose_the_world_never_answers_is_a_failure_and_a_silent_probe_is_counted(monkeypatch):
    """The gauges of two passes, a window each (#826, amended). The first doses the dry bed: one
    intention standing and none failed — `failed` written as nought and not left out, which is what
    an outcome compared while unbound did — and the plan's world met its want, which an `EXISTS` read
    against the default graph never saw. A day later the thermometer reports and the probe has not:
    the dose was never answered, so the intention failed, and the probe is past its cadences, so it
    is silent. Sensing is loaded here, so silence is counted beside the mind's figures."""
    runtime, broker, windows = _unanswered(monkeypatch, interval_s=0)
    dosed, a_day_later = ({p["measurement"]: p["fields"] for p in w} for w in windows[:2])
    assert {"store", "process", "plans", "cone", "intentions", "acts", "revisions", "silence", "pass"} <= set(dosed)
    assert dosed["intentions"] == {"standing": 1, "done": 0, "failed": 0, "superseded": 0, "abandoned": 0}
    assert dosed["acts"] == {"taken": 1, "notTaken": 0} and dosed["silence"] == {"silent": 0}
    assert dosed["plans"]["satisfied"] == 1 and dosed["cone"]["met"] == 1
    assert dosed["revisions"]["unsettled"] == 0 < dosed["revisions"]["revisions"]
    assert a_day_later["intentions"]["failed"] == 1 and a_day_later["intentions"]["standing"] == 0
    assert a_day_later["silence"] == {"silent": 1}, "the probe, and not the thermometer that reported"
    assert len(broker.published) == 1


def _unanswered(monkeypatch, *, interval_s: float):
    """The dry bed dosed, and a day later the thermometer alone — with a metrics sink loaded and who
    speaks said as `main` says it, the window `interval_s` long, and the last written as a stop
    writes it: the runtime, the broker, and every window written."""
    from agent import metrics
    from agent.runtime import world_name
    from agent.series import METRICS

    writes = []
    install(METRICS, Sink(METRICS, "greenhouse-grower-metrics", lambda bucket, record: writes.append(list(record))))
    metrics.configure(interval_s=interval_s)
    metrics.identify(world=world_name(WORLD), agent="grower")
    try:
        runtime, broker = _grower(monkeypatch)
        runtime.deliver("sensors/thermometer/reading", b'{"value": 21.0}', NOW)
        runtime.deliver("sensors/moisture_probe/reading", b'{"value": 0.2}', NOW)
        runtime.run(passes=1, poll_s=0)
        runtime.time.at = NOW + timedelta(days=1)
        runtime.deliver("sensors/thermometer/reading", b'{"value": 21.0}', runtime.time.at)
        runtime.run(passes=1, poll_s=0)
        runtime.report()
    finally:
        install(METRICS, None)
        metrics.reset()
        metrics.identify()
    return runtime, broker, [w for w in writes if w]


def test_a_want_derived_under_a_desire_is_told_by_the_desire_and_the_dose_by_how_late_it_was(monkeypatch):
    """The events of the same two passes, in the one window a stop writes (#826, amended). The dry
    bed's want is searched and adopted, each tallied under the desire it was derived under — the
    bed's comfort, which reads across worlds and agents — and never under the want, which is on no
    point. The dose's landing, never answered, is tallied as timed out, late by the patience past the
    landing the plan placed, tagged by its action. The thermometer's second reading came a day after
    its first, against the minute the world states."""
    runtime, broker, (window,) = _unanswered(monkeypatch, interval_s=3600)
    desire = "the_bed_is_comfortable"
    by = {}
    for p in window:
        by.setdefault(p["measurement"], []).append(p)
    (search,), (adopted,), (landing,) = [s for s in by["search"] if s["tags"]["outcome"] == "Satisfied"], by["adopted"], by["landing"]
    assert search["tags"]["desire"] == adopted["tags"]["desire"] == landing["tags"]["desire"] == desire
    assert adopted["fields"]["passes_max"] == 1.0 and adopted["fields"]["replan"] == 0
    assert landing["tags"]["action"] == "Dosing" and landing["fields"]["timed_out"] == 1 == landing["fields"]["count"]
    assert landing["fields"]["late_s_max"] > 0
    (received,) = [p for p in by["received"] if p["tags"]["sensor"] == "thermometer"]
    assert received["fields"]["interval_s_max"] == 86400.0 and received["fields"]["cadence_s_max"] > 0
    for p in window:
        assert p["tags"]["world"] == "greenhouse" and p["tags"]["agent"] == "grower", p
        said = {*p["tags"].values(), *p["tags"], *p["fields"], *map(str, p["fields"].values())}
        assert not {s for s in said if s.startswith(desire) and s != desire} and "want" not in said, p


def test_a_cold_bed_is_heated_for_as_long_as_the_gap_takes(monkeypatch):
    """16 degrees against 18 to 24: the middle is 21, five degrees at two an hour is two and a half
    hours, and the heater runs at most an hour a command."""
    runtime, broker = _grower(monkeypatch)
    runtime.deliver("sensors/moisture_probe/reading", b'{"value": 0.45}', NOW)
    runtime.deliver("sensors/thermometer/reading", b'{"value": 16.0}', NOW)
    runtime.run(passes=1, poll_s=0)
    assert broker.published == [("actuators/heater/command", {"heat_s": 3600}, False)]
