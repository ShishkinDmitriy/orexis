"""What the search spends against the world it stands in, and whether an aspect of the world that is
unrelated to a want changes what that want's search spends (#593).

Two metrics the sovereign named. A POSSIBLE WORLD'S SIZE against the present: a world is the SCOPE'S
readings, their revisions and what the agent believes of their subject, forked from a ground that holds
those alone, never the public knowledge, so it is one percent of the store. And STABILITY: a cold frame
beside the bed, its own thermometer and a heat lamp over it, is a third scope; the soil want's search
forks the same one world over the same one candidate it did before, that world is the same size, and
the lamp — a second filling of the heating action, keyed by the frame — is admitted in the frame's scope
alone and its step judged there alone. It was a lamp on the bed's light until the heating came to speak
the air's state (#944), which no light reading is judged into; `conftest.py` says why the frame keeps
what the light was for.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from agent import clock
from agent.ontology import PUBLIC, STATE, local_of
from agent.runtime import boot
from agent.store import close_catalogue, graphs_of, quads, revisions_of, rows
from agent.sensing.received import received
from agent.belief.revise import revise
from agent.belief.trigger import trigger
from agent.planning.planner import Planner

WORLD = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
GH = "http://example.org/orexis/world/greenhouse#"

#  THE GREENHOUSE WITH THE FRAME ADDED is the `framed_greenhouse` fixture of `conftest.py`, shared with the bench.

#  WHAT EACH PLAN IS ABOUT, off the want its row names and the property the want's met-test is about — a
#  want states no `planning:about` of its own, its shape's blocks do — and never off the plan's name,
#  which is for eyes; and the subject each candidate is filled with, which tells the bed's air from the
#  frame's.
_ABOUT_Q = """
SELECT DISTINCT ?about WHERE {
  GRAPH ?g { ?p a planning:Plan ; planning:outcome planning:Satisfied ; planning:for ?want }
  GRAPH ?w { ?want planning:metWhen|planning:unmetWhen ?shape . ?shape sh:property ?block . ?block planning:about ?about } }"""
_SUBJECTS_Q = """
SELECT DISTINCT ?s WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?c a planning:Candidate ;
                                        <http://example.org/orexis/actuation#subject> ?s } }"""


def _deliver(store, sensor: str, value: float, at: datetime) -> None:
    """A reading as the deliberator takes it: written, revised, and the transitions it triggers applied."""
    for graph in received(store, GH + "grower", GH + sensor, f'{{"value": {value}}}'.encode(), at):
        revise(store, graph, read=graphs_of(store, PUBLIC))
        close_catalogue(store)
        trigger(store, graph)


def _pass(world: Path, readings: dict) -> tuple[int, int, dict]:
    """One pass over `world` with `readings` delivered: the store's quads, the state's with its revisions,
    and per scope, keyed by what its plans are about and the subjects its candidates are filled with,
    `(ground quads, [world quads], candidates, actions)`."""
    store = boot(world, "grower")
    for sensor, value in readings.items():
        _deliver(store, sensor, value, NOW)
    present = sum(1 for _ in store)
    readings = graphs_of(store, STATE)
    state = sum(len(list(quads(store, g))) for g in [*readings, *revisions_of(store, *readings)])
    planner = Planner(store, "grower")
    planner.plan(NOW)
    out = {}
    for scope, im in planner.imaginaria.items():
        (ground,) = [r["g"] for r in rows(im, "SELECT ?g WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a planning:GroundGraph } }", ())]
        worlds = [r["w"] for r in rows(im, "SELECT ?w WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?w a planning:PossibleGraph } }", ())]
        cands = rows(im, "SELECT (COUNT(DISTINCT ?c) AS ?n) (COUNT(DISTINCT ?a) AS ?actions) WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?c a planning:Candidate ; planning:fills ?a } }", ())[0]
        plans = frozenset(local_of(r["about"]) for r in rows(im, _ABOUT_Q, ()))
        subjects = frozenset(local_of(r["s"]) for r in rows(im, _SUBJECTS_Q, ()))
        out[(plans, subjects) if plans else scope] = (len(list(quads(im, ground))), sorted(len(list(quads(im, w))) for w in worlds),
                                                      int(cands["n"]), int(cands["actions"]))
    return present, state, out


SOIL = (frozenset({"SoilMoisture"}), frozenset({"bed"}))


def test_a_possible_world_is_the_scopes_readings_and_a_percent_of_the_present(monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: NOW)
    present, state, scopes = _pass(WORLD, {"thermometer": 12.0, "moisture_probe": 0.2})
    assert len(scopes) == 2, scopes
    for ground, worlds, _, _ in scopes.values():
        assert worlds == [ground], "a world is a fork of its ground, nothing more"
        assert ground * 50 < present, f"a world of {ground} quads against a present of {present}"
    #  THE READINGS ARE PARTED BETWEEN THE SCOPES, each reading, its sides and what is believed of its
    #  subject to the one scope whose property it names: the two grounds together are the state, and
    #  neither is.
    assert sorted(ground for ground, *_ in scopes.values()) == [state // 2, state // 2]


def test_an_unrelated_aspect_changes_nothing_of_the_soil_wants_search(monkeypatch, framed_greenhouse):
    """The frame and the lamp are a third scope. The soil's search forks the one world over the one
    candidate it forked without them, and that world is the same size: the frame's reading is the
    frame's scope's and crosses into no other imaginarium. The lamp's heating, a second filling of the
    heating action, is admitted in the frame's scope and nowhere else."""
    monkeypatch.setattr(clock, "now", lambda: NOW)
    _, state, before = _pass(WORLD, {"thermometer": 12.0, "moisture_probe": 0.2})
    _, framed_state, after = _pass(framed_greenhouse, {"thermometer": 12.0, "moisture_probe": 0.2, "frame_thermometer": 5.0})
    soil_before, soil_after = before[SOIL], after[SOIL]
    assert soil_before == soil_after == (soil_before[0], [soil_before[0]], 1, 1), \
        f"the soil's search, with and without the frame: {soil_before} against {soil_after}"
    assert set(after) == {SOIL, (frozenset({"AirTemperature"}), frozenset({"bed"})),
                          (frozenset({"AirTemperature"}), frozenset({"frame"}))}, after
    assert all(cands == 1 and actions == 1 for _, _, cands, actions in after.values()), \
        f"one filling per scope, the lamp's in the frame's alone: {after}"
    assert framed_state > state and sum(ground for ground, *_ in after.values()) == framed_state, \
        "the reading added went to its own scope's ground and to no other"


class _Broker:
    """What the grower publishes, and nothing else of MQTT."""

    def __init__(self):
        self.published = []

    def subscribe(self, pattern):
        pass

    def publish(self, topic, payload, retain=False):
        self.published.append(topic)


def test_a_step_is_judged_by_its_own_filling_whichever_scope_admitted_it(monkeypatch, framed_greenhouse):
    """The heating action is the bed's air's and the frame's, filled by the heater in one and the lamp in
    the other. Asked of the lamp's step, the bed's air's imaginarium — which holds no frame reading —
    would answer no row and call it blocked. Each head is checked as it is about to be taken, in the
    present the beliefs hold, every scope's readings among them (#916): all three commands go out,
    nothing is blocked in the pass after, and all three intentions walk on."""
    from agent.runtime import UNFINISHED, Runtime
    from agent.transport.mqtt.driver import Mqtt
    time = _Clock(NOW)
    monkeypatch.setattr(clock, "now", time)
    beliefs = boot(framed_greenhouse, "grower")
    broker = _Broker()
    runtime = Runtime(beliefs, "grower", transport=Mqtt(GH + "grower", broker))
    runtime.time = time
    for sensor, value in {"thermometer": 12.0, "moisture_probe": 0.2, "frame_thermometer": 5.0}.items():
        runtime.deliver(f"sensors/{sensor}/reading", f'{{"value": {value}}}'.encode(), NOW)
    assert runtime.run(passes=1, poll_s=0) == UNFINISHED
    assert sorted(broker.published) == ["actuators/heater/command", "actuators/lamp/command", "actuators/pump/command"]
    assert len(runtime.parts["execution"].executor.walking()) == 3
    assert runtime.run(passes=1, poll_s=0) == UNFINISHED
    assert runtime.parts["planning"].planner.blocked == []
    assert len(runtime.parts["execution"].executor.walking()) == 3


class _Clock:
    """One timeline: every read moves it on by a second, as a running agent's clock does."""

    def __init__(self, at):
        self.at = at

    def __call__(self):
        self.at += timedelta(seconds=1)
        return self.at


def test_a_drift_outside_a_wants_scope_keeps_its_cone(monkeypatch, framed_greenhouse):
    """#565's second item, by construction since a scope's imaginarium holds the scope's readings alone
    (#884): a present that drifts in a fact a want never reads — the frame's air, under a soil plan —
    hashes to the same soil ground, so the soil's re-root finds the last pass's present and keeps its
    cone, while the frame's own search finds the present among what it imagined. A drift in the soil
    itself that nothing imagined drops the soil's cone.
    WHAT MOVES A PRESENT IS A STATE, NOT A NUMBER: a world is hashed within what is read, and no text
    reads the number a reading gave, so the frame going from 5 to 7 degrees under a floor of 10 would be
    the same place to the frame's own search too — cold both times. From 5 to 15 the frame is believed
    comfortable — the world the lamp's plan predicted — so the frame's present is that CHILD, a step
    landed as predicted, which no sensed world could say while a reading's instant was part of where it
    stood. The soil at 0.9 is believed wet, which no world of the soil's imagined: a surprise."""
    monkeypatch.setattr(clock, "now", lambda: NOW)
    store = boot(framed_greenhouse, "grower")

    def scope_of(term: str) -> str:
        """The local name of the one scope `term` is a member of, as the re-root names it."""
        (found,) = rows(store, f"""SELECT ?s WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph . ?g a planning:ScopeGraph }}
                                                 GRAPH ?g {{ <{term}> planning:inScope ?s }} }}""", ())
        return found["s"].rsplit("/", 1)[-1]

    heard: list = []
    planner = Planner(store, "grower")
    planner.rerooted.connect(lambda event: heard.append(event) or [])
    for sensor, value in {"thermometer": 21.0, "moisture_probe": 0.2, "frame_thermometer": 5.0}.items():
        _deliver(store, sensor, value, NOW)
    planner.plan(NOW)
    soil, frame = scope_of(GH + "pump"), scope_of(GH + "lamp")
    assert {e.present for e in heard} == {"first"} and len(heard) == 3
    #  THE FRAME DRIFTS AND THE SOIL DOES NOT: the soil's imaginarium holds no frame reading, so the
    #  ground it lays hashes as last pass's did, and its one world is kept under it; the last pass's
    #  ground — the match itself, whose facts the new one carries — is the one graph dropped. The
    #  frame's imaginarium finds the present in the world its plan reached.
    heard.clear()
    later = NOW + timedelta(minutes=10)
    _deliver(store, "frame_thermometer", 15.0, later)
    planner.plan(later)
    second = {e.scope: (e.present, e.kept, e.dropped) for e in heard}
    assert second[soil] == ("ground", 2, 1), f"the soil's ground and its world kept, last pass's ground gone: {second}"
    assert second[frame][0] == "child", f"comfortable, as the lamp's plan predicted: {second}"
    #  THE SOIL DRIFTS where nothing imagined it: wet, not moist as the dose predicted.
    heard.clear()
    latest = later + timedelta(minutes=10)
    _deliver(store, "moisture_probe", 0.9, latest)
    planner.plan(latest)
    third = {e.scope: (e.present, e.kept, e.dropped) for e in heard}
    assert third[soil][0] == "surprise" and third[frame][0] == "ground", third
