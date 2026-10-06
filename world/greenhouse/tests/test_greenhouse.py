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
from agent.execution.executor import DEFAULT_PATIENCE_S
from agent.ontology import OREXIS
from agent.runtime import UNFINISHED, Runtime, boot
from agent.series import HISTORY, Sink, install
from agent.store import graphs_of, revisions_of, rows
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
    reading, 0.45, is revised inside and the intention is done — the dose lands when that reading is
    due, a cadence after the step's instant, so an answer is looked for from then and not before: the
    clock here ticks per read, so the step stands a few seconds after NOW and the reading comes a
    minute past the cadence."""
    runtime, broker = _grower(monkeypatch)
    runtime.deliver("sensors/thermometer/reading", b'{"value": 21.0}', NOW)
    runtime.deliver("sensors/moisture_probe/reading", b'{"value": 0.2}', NOW)
    assert runtime.run(passes=1, poll_s=0) == UNFINISHED
    assert broker.published == [("actuators/pump/command", {"dose_ml": 500}, False)]
    assert len(runtime.parts["execution"].executor.walking()) == 1, "the world has not answered yet"
    runtime.time.at = NOW + timedelta(minutes=11)
    runtime.deliver("sensors/moisture_probe/reading", b'{"value": 0.45}', runtime.time.at)
    runtime.run(passes=2, poll_s=0)
    assert runtime.parts["execution"].executor.walking() == [], "the reading was revised inside and answered the dose"
    assert ("SoilMoisture", "inside") in _sides(runtime.beliefs)
    assert len(broker.published) == 1, "one dose, and nothing more once the bed is comfortable"


_PREDICTED_Q = """
SELECT ?start ?value WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a orexis:PredictionGraph ; dcterms:temporal/orexis:start ?start }
  GRAPH ?g { ?o sosa:observedProperty <http://example.org/orexis/climate#SoilMoisture> ; sosa:hasSimpleResult ?value } }
ORDER BY ?start"""


def test_a_committed_dose_is_a_flow_the_beds_prediction_accumulates(monkeypatch):
    """#849. Adopted, the dose stands in the beliefs as a committed step holding over its landing
    window — from the step's instant to the probe's next reading plus the patience — and the actuation
    domain's drift reads it there: the bed's prediction, rewritten as the window is written, rises to
    the aim the command sizes to, 0.45, by the time the next reading is due, and dries from there, so
    the one stretch of the day reads inside its range — 0.41 at its end, a day's drying under the aim —
    where the drying alone read 0.2 and below. When the reading answers the dose the window closes and
    the next tick forgets it."""
    runtime, broker = _grower(monkeypatch)
    runtime.deliver("sensors/thermometer/reading", b'{"value": 21.0}', NOW)
    runtime.deliver("sensors/moisture_probe/reading", b'{"value": 0.2}', NOW)
    runtime.run(passes=1, poll_s=0)
    assert broker.published == [("actuators/pump/command", {"dose_ml": 500}, False)]
    committed = "http://example.org/orexis/execution#CommittedStepGraph"
    (window,) = graphs_of(runtime.beliefs, committed)
    (period,) = rows(runtime.beliefs, "SELECT ?s ?e WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . $g dcterms:temporal ?p . ?p orexis:start ?s ; orexis:end ?e } }", (), g=window)
    opens, closes = datetime.fromisoformat(period["s"]), datetime.fromisoformat(period["e"])
    assert timedelta(minutes=11) <= closes - opens <= timedelta(minutes=11, seconds=5), "a cadence, and the patience"
    predicted = [(datetime.fromisoformat(r["start"]), float(r["value"])) for r in rows(runtime.beliefs, _PREDICTED_Q, ())]
    assert [(s >= closes - timedelta(seconds=DEFAULT_PATIENCE_S), round(v, 2)) for s, v in predicted] == [(True, 0.41)], \
        f"one stretch from where the reading is due, risen to the aim and dried a day, not dried from 0.2: {predicted}"
    sides = _predicted_sides(runtime.beliefs)
    assert ("SoilMoisture", "inside") in sides and ("SoilMoisture", "below") not in sides, f"foreseen inside, never below: {sides}"
    runtime.time.at = NOW + timedelta(minutes=11)
    runtime.deliver("sensors/moisture_probe/reading", b'{"value": 0.45}', runtime.time.at)
    runtime.run(passes=2, poll_s=0)
    assert runtime.parts["execution"].executor.walking() == []
    assert graphs_of(runtime.beliefs, committed) == [], "answered: closed, then swept"


def _predicted_sides(beliefs) -> set[tuple[str, str]]:
    """The sides of every predicted observation, read with its revisions as a reader of a prediction does."""
    q = """SELECT ?p ?side WHERE { ?obs sosa:observedProperty ?p ; ?side ?range .
           VALUES ?side { sensing:below sensing:inside sensing:above } }"""
    predicted = graphs_of(beliefs, OREXIS + "PredictionGraph")
    return {(r["p"].rsplit("#", 1)[-1], r["side"].rsplit("#", 1)[-1])
            for r in rows(beliefs, q, [*predicted, *revisions_of(beliefs, *predicted)])}


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
    runtime.time.at = NOW + timedelta(minutes=11)
    runtime.deliver("sensors/moisture_probe/reading", b'{"value": 0.45}', runtime.time.at)
    runtime.run(passes=2, poll_s=0)
    assert runtime.parts["execution"].executor.walking() == [], "the dose landed"
    observed = [(p["measurement"], p["fields"]["value"], p["time"]) for p in history if p["measurement"] != "Step"]
    assert observed == [("AirTemperature", 21.0, NOW), ("SoilMoisture", 0.2, NOW),
                        ("SoilMoisture", 0.45, NOW + timedelta(minutes=11))]
    #  THE RAW COUNT BESIDE THE READING (#894): this world scales no sensor, so the number the sensor
    #  gave is the reading, and the point says so twice rather than leaving the second field off.
    assert all(p["fields"] == {"value": p["fields"]["value"], "raw": p["fields"]["value"]}
               for p in history if p["measurement"] != "Step")
    #  TAGGED BY THE LOCAL NAME OF THE IRI, since this world states no `orexis:localId` of a sensor or
    #  of the bed; tagged by a stated id, these points carried none and no panel could filter for them (#885).
    #  The bed is tagged `feature`, for its SOSA role, and no longer `plant` (#834).
    assert [(p["tags"]["sensor"], p["tags"]["feature"]) for p in history if p["measurement"] != "Step"] == \
        [("thermometer", "bed"), ("moisture_probe", "bed"), ("moisture_probe", "bed")]
    steps = [p for p in history if p["measurement"] == "Step"]
    assert [p["fields"] for p in steps] == [{"taken": True}, {"landed": True}]
    (taken, landed) = steps
    assert taken["tags"] == landed["tags"], "one step, said twice"
    assert taken["tags"]["action"] == "Dosing" and set(taken["tags"]) == {"action", "want", "valve", "reading"}
    assert taken["tags"]["valve"] == "pump"
    assert taken["time"] < landed["time"], "taken, then answered"
    assert len(broker.published) == 1


def test_every_reading_the_grower_writes_is_drawn_by_one_greenhouse_panel(monkeypatch, history):
    """`orexis-dashboards greenhouse` is held to what the agent writes, as the terrace's is: each
    point's measurement and sensor are filtered for by exactly one panel. This world states no
    `orexis:localId` of a sensor or of the bed, and keyed on one the generator read it as observing
    nothing and wrote no readings dashboard (#885)."""
    from onboarding.dashboards import render

    runtime, broker = _grower(monkeypatch)
    runtime.deliver("sensors/thermometer/reading", b'{"value": 21.0}', NOW)
    runtime.deliver("sensors/moisture_probe/reading", b'{"value": 0.2}', NOW)
    runtime.drain(NOW)
    panels = render("greenhouse")["panels"]
    assert [p["title"] for p in panels] == ["bed — SoilMoisture", "bed — AirTemperature"], "by subject, then by sensor"
    queries = [t["query"] for panel in panels for t in panel["targets"]]
    drawn = {(p["measurement"], p["tags"]["sensor"]):
             [q for q in queries if f'r._measurement == "{p["measurement"]}"' in q
              and f'r.sensor == "{p["tags"]["sensor"]}"' in q] for p in history if p["measurement"] != "Step"}
    assert len(drawn) == 2 and all(len(found) == 1 for found in drawn.values()), drawn


def test_a_dose_the_world_never_answers_is_a_failure_and_a_silent_probe_is_counted(monkeypatch):
    """The levels and counts of two passes, a window each (#826, amended). The first doses the dry
    bed: one intention standing, one act taken, and the plan's world met its want, which an `EXISTS`
    read against the default graph never saw. A day later the thermometer reports and the probe has
    not: the reading sets the executor walking at once, the dose was never answered, so the intention
    failed, and planning, hearing it end, plans a second dose in that same pass. The probe is past its
    cadences, so it is silent and the present holds no reading to size that dose from: its command
    answers nothing, the step is not taken and the intention fails at once (#869) — it was counted
    taken before, having sent nothing. Sensing is loaded here, so silence is said beside the mind's
    figures."""
    runtime, broker, windows = _unanswered(monkeypatch, interval_s=0)
    dosed, a_day_later = windows[:2]
    of = lambda window, name: [p for p in window if p["measurement"] == name]
    one = lambda window, name: (lambda found: found[0]["fields"])(of(window, name))
    assert {"pass", "imaginarium", "intentions", "act", "revisions", "silence"} <= {p["measurement"] for p in dosed}
    assert one(dosed, "intentions") == {"standing": 1} and one(dosed, "silence") == {"silent": 0}
    assert one(dosed, "act")["count"] == one(dosed, "act")["taken"] == 1
    assert sum(p["fields"]["satisfied"] for p in of(dosed, "imaginarium")) == 1
    #  TWO MET: the soil want in the world its dose made, and the desire in the air's ground, which
    #  holds the air's reading alone — the soil the desire is also about is not there to read dry.
    assert sum(p["fields"]["met"] for p in of(dosed, "imaginarium")) == 2
    assert one(dosed, "revisions")["unsettled"] == 0 < one(dosed, "revisions")["revisions"]
    assert [(p["tags"]["outcome"], p["fields"]["count"]) for p in of(a_day_later, "intention")] == [("failed", 2)]
    assert one(a_day_later, "intentions") == {"standing": 0}
    assert one(a_day_later, "act") == {"count": 1, "taken": 0}, "the second dose, sized from no reading"
    assert one(a_day_later, "silence") == {"silent": 1}, "the probe, and not the thermometer that reported"
    #  AND WHICH (#894): the series names the probe silent, so reflection reads which and not how many —
    #  and the thermometer stuck, since this test hands it 21.0 exactly twice a day apart, which is the
    #  unchanged number sensing says stuck of (#462); a simulated instrument jitters so that it is not.
    assert [(p["tags"]["sensor"], p["fields"]) for p in of(a_day_later, "doubted")] == \
        [("moisture_probe", {"silent": 1, "stuck": 0}), ("thermometer", {"silent": 0, "stuck": 1})]
    assert of(dosed, "doubted") == [], "a sensor nobody doubts is on no point"
    assert len(broker.published) == 1


def _unanswered(monkeypatch, *, interval_s: float):
    """The dry bed dosed, and a day later the thermometer alone — with a metrics sink loaded and who
    speaks said as `main` says it, the window `interval_s` long, and the last written as a stop
    writes it: the runtime, the broker, and every window written."""
    from agent.metrics import window as metrics
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
        runtime.stop()                                   # as a stop does: the last window written
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
    (search,), (adopted,), (landing,) = [s for s in by["search"] if s["tags"]["outcome"] == "Satisfied"], by["published"], by["landing"]
    assert search["tags"]["desire"] == adopted["tags"]["desire"] == landing["tags"]["desire"] == desire
    assert adopted["fields"]["passes_max"] == 1.0 and adopted["fields"]["count"] == 2, "the dose, then its replan"
    assert adopted["fields"]["replan"] == 1, "the second, planned the pass the first failed"
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


def test_a_cold_dry_bed_is_two_wants_planned_apart(monkeypatch):
    """#593: the pump and the heater write the same predicates — a reading's side — and over
    predicates alone they were one scope, so a cold dry bed was one want searched over both levers
    at once, four worlds for two steps. Over keys the pump's reading is the soil's and the heater's
    the air's, so the bed is two wants in two imaginaria of one world each, and both commands go
    out in the one pass."""
    runtime, broker = _grower(monkeypatch)
    runtime.deliver("sensors/thermometer/reading", b'{"value": 12.0}', NOW)
    runtime.deliver("sensors/moisture_probe/reading", b'{"value": 0.2}', NOW)
    assert runtime.run(passes=1, poll_s=0) == UNFINISHED
    assert sorted(t for t, _, _ in broker.published) == ["actuators/heater/command", "actuators/pump/command"]
    imaginaria = runtime.parts["planning"].planner.imaginaria
    assert len(imaginaria) == 2, "one imaginarium per scope, and the bed's two properties are two"
    worlds = [len(rows(im, "SELECT ?w WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?w a planning:PossibleGraph } }", ()))
              for im in imaginaria.values()]
    assert worlds == [1, 1], f"one step each, searched apart: {worlds}"
    assert len(runtime.parts["execution"].executor.walking()) == 2
    #  AND EACH HEAD IS CHECKED AS IT IS TAKEN, in the present the beliefs hold (#916): the soil's
    #  imaginarium holds the soil's reading alone, and the heater's step asked there would read no air
    #  and be called blocked; asked of the beliefs, every scope's readings are there, and both commands
    #  went out above. A second pass, both steps standing, blocks neither.
    assert runtime.run(passes=1, poll_s=0) == UNFINISHED
    assert runtime.parts["planning"].planner.blocked == []
    assert len(runtime.parts["execution"].executor.walking()) == 2


def test_a_foreseen_crossing_is_planned_ahead_and_dosed_when_it_arrives(monkeypatch):
    """#858: the bed reads 0.31 and dries 0.04 a day, so the forecast crosses the floor in six hours.
    The want minted for that instant was weighed in the present ground, read met there and was
    withdrawn in the pass that minted it — every pass, thirty log lines a minute, and the foresight
    never became a dose. It is weighed in the ground holding at its instant now: the search roots
    there, where the predicted reading is below, finds the dose, and the executor holds the step
    until it is due. Nothing is sent while the bed is comfortable, the plan survives the passes
    between, and the dose goes out once the crossing has come and the present admits it."""
    runtime, broker = _grower(monkeypatch)
    runtime.deliver("sensors/thermometer/reading", b'{"value": 21.0}', NOW)
    runtime.deliver("sensors/moisture_probe/reading", b'{"value": 0.31}', NOW)
    runtime.run(passes=2, poll_s=0)
    assert broker.published == [], "comfortable now, so nothing is sent"
    (want,) = runtime.parts["execution"].executor.walking()
    runtime.run(passes=2, poll_s=0)
    assert runtime.parts["execution"].executor.walking() == [want], "the plan placed ahead survives the passes"
    assert broker.published == []
    runtime.time.at = NOW + timedelta(hours=7)
    runtime.deliver("sensors/moisture_probe/reading", b'{"value": 0.2995}', runtime.time.at)
    runtime.run(passes=2, poll_s=0)
    assert [t for t, _, _ in broker.published] == ["actuators/pump/command"], "the foreseen crossing came, and the dose with it"
