"""What the search spends against the world it stands in, and whether an aspect of the world that is
unrelated to a want changes what that want's search spends (#593).

Two metrics the sovereign named. A POSSIBLE WORLD'S SIZE against the present: a world is the SCOPE'S
readings and their revisions, forked from a ground that holds those alone, never the public knowledge,
so it is one percent of the store. And STABILITY: a lamp and a light sensor added to the greenhouse,
with a desire that the bed be lit, are a third scope; the soil want's search forks the same one world
over the same one candidate it did before, that world is the same twelve quads, and the lamp — a
second filling of the heating action — is admitted in the light's scope alone and its step judged
there alone.
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
from agent.planning.planner import Planner

WORLD = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
GH = "http://example.org/orexis/world/greenhouse#"

#  THE GREENHOUSE WITH THE LIGHT ADDED is the `lit_greenhouse` fixture of `conftest.py`, shared with the bench.


def _pass(world: Path, readings: dict) -> tuple[int, int, dict]:
    """One pass over `world` with `readings` delivered: the store's quads, the state's with its revisions, and per scope
    `(ground quads, [world quads], candidates, actions, plans)`."""
    store = boot(world, "grower")
    for sensor, value in readings.items():
        for graph in received(store, GH + "grower", GH + sensor, f'{{"value": {value}}}'.encode(), NOW):
            revise(store, graph, read=graphs_of(store, PUBLIC))
            close_catalogue(store)
    present = sum(1 for _ in store)
    readings = graphs_of(store, STATE)
    state = sum(len(list(quads(store, g))) for g in [*readings, *revisions_of(store, *readings)])
    planner = Planner(store, "grower", budget=128)
    planner.plan(NOW)
    out = {}
    for scope, im in planner.imaginaria.items():
        (ground,) = [r["g"] for r in rows(im, "SELECT ?g WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a planning:GroundGraph } }", ())]
        worlds = [r["w"] for r in rows(im, "SELECT ?w WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?w a planning:PossibleGraph } }", ())]
        cands = rows(im, "SELECT (COUNT(DISTINCT ?c) AS ?n) (COUNT(DISTINCT ?a) AS ?actions) WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?c a planning:Candidate ; planning:fills ?a } }", ())[0]
        #  WHAT EACH PLAN IS ABOUT, off the want its row names and the property the want's met-test is
        #  about — a want states no `planning:about` of its own, its shape's blocks do — and never off
        #  the plan's name, which is for eyes.
        plans = {local_of(r["about"]) for r in rows(im, """
            SELECT DISTINCT ?about WHERE {
              GRAPH ?g { ?p a planning:Plan ; planning:outcome planning:Satisfied ; planning:for ?want }
              GRAPH ?w { ?want planning:metWhen|planning:unmetWhen ?shape . ?shape sh:property ?block . ?block planning:about ?about } }""", ())}
        out[frozenset(plans) or scope] = (len(list(quads(im, ground))), sorted(len(list(quads(im, w))) for w in worlds),
                                           int(cands["n"]), int(cands["actions"]), plans)
    return present, state, out


def test_a_possible_world_is_the_scopes_readings_and_a_percent_of_the_present(monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: NOW)
    present, state, scopes = _pass(WORLD, {"thermometer": 12.0, "moisture_probe": 0.2})
    for ground, worlds, _, _, _ in scopes.values():
        assert worlds == [ground], "a world is a fork of its ground, nothing more"
        assert ground * 50 < present, f"a world of {ground} quads against a present of {present}"
    #  THE READINGS ARE PARTED BETWEEN THE SCOPES, each reading and its sides to the one scope whose
    #  property it names: the two grounds together are the state, and neither is.
    assert sorted(ground for ground, *_ in scopes.values()) == [state // 2, state // 2]


def test_an_unrelated_aspect_changes_nothing_of_the_soil_wants_search(monkeypatch, lit_greenhouse):
    """The light and the lamp are a third scope. The soil's search forks the one world over the one
    candidate it forked without them, and that world is the same size: the light's reading is the
    light's scope's and crosses into no other imaginarium. The lamp's heating, a second filling of the
    heating action, is admitted in the light's scope and nowhere else."""
    monkeypatch.setattr(clock, "now", lambda: NOW)
    _, state, before = _pass(WORLD, {"thermometer": 12.0, "moisture_probe": 0.2})
    _, lit_state, after = _pass(lit_greenhouse, {"thermometer": 12.0, "moisture_probe": 0.2, "light_sensor": 100})
    soil_before, soil_after = before[frozenset({"SoilMoisture"})], after[frozenset({"SoilMoisture"})]
    assert soil_before == soil_after == (soil_before[0], [soil_before[0]], 1, 1, {"SoilMoisture"}), \
        f"the soil's search, with and without the light: {soil_before} against {soil_after}"
    assert len(after) == 3 and {p for _, _, _, _, plans in after.values() for p in plans} == {"SoilMoisture", "AirTemperature", "Light"}
    assert all(cands == 1 and actions == 1 for _, _, cands, actions, _ in after.values()), \
        f"one filling per scope, the lamp's in the light's alone: {after}"
    assert lit_state > state and sum(ground for ground, *_ in after.values()) == lit_state, \
        "the reading added went to its own scope's ground and to no other"


class _Broker:
    """What the grower publishes, and nothing else of MQTT."""

    def __init__(self):
        self.published = []

    def subscribe(self, pattern):
        pass

    def publish(self, topic, payload, retain=False):
        self.published.append(topic)


def test_a_step_is_judged_in_the_scope_that_admitted_its_filling(monkeypatch, lit_greenhouse):
    """The heating action is the air's and the light's, filled by the heater in one and the lamp in the
    other. Both steps standing, the next pass asks each imaginarium whether the present still admits
    the heads due: asked of the lamp's step, the air's imaginarium — which holds no light reading —
    would answer no row and call it blocked. A step is judged where its filling was admitted: nothing
    is blocked, and all three intentions walk on."""
    from agent.runtime import UNFINISHED, Runtime
    from agent.transport.mqtt.driver import Mqtt
    time = _Clock(NOW)
    monkeypatch.setattr(clock, "now", time)
    beliefs = boot(lit_greenhouse, "grower")
    broker = _Broker()
    runtime = Runtime(beliefs, "grower", transport=Mqtt(GH + "grower", broker))
    runtime.time = time
    for sensor, value in {"thermometer": 12.0, "moisture_probe": 0.2, "light_sensor": 100}.items():
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


def test_a_drift_outside_a_wants_scope_keeps_its_cone(monkeypatch, lit_greenhouse):
    """#565's second item, by construction since a scope's imaginarium holds the scope's readings alone
    (#884): a present that drifts in a fact a want never reads — the light, under a soil plan — hashes
    to the same soil ground, so the soil's re-root finds the last pass's present and keeps its cone,
    while the light's own search is surprised. A drift in the soil itself drops the soil's cone."""
    monkeypatch.setattr(clock, "now", lambda: NOW)
    store = boot(lit_greenhouse, "grower")

    def deliver(sensor: str, value: float, at: datetime) -> None:
        for graph in received(store, GH + "grower", GH + sensor, f'{{"value": {value}}}'.encode(), at):
            revise(store, graph, read=graphs_of(store, PUBLIC))
            close_catalogue(store)

    def scope_of(term: str) -> str:
        """The local name of the scope `term` is a member of, as the re-root names it."""
        (found,) = rows(store, f"""PREFIX climate: <http://example.org/orexis/climate#>
            SELECT ?s WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph . ?g a planning:ScopeGraph }}
                               GRAPH ?g {{ climate:{term} planning:inScope ?s }} }}""", ())
        return found["s"].rsplit("/", 1)[-1]

    heard: list = []
    planner = Planner(store, "grower", budget=128)
    planner.rerooted.connect(lambda event: heard.append(event) or [])
    for sensor, value in {"thermometer": 21.0, "moisture_probe": 0.2, "light_sensor": 100}.items():
        deliver(sensor, value, NOW)
    planner.plan(NOW)
    soil, light = scope_of("SoilMoisture"), scope_of("Light")
    assert {e.present for e in heard} == {"first"} and len(heard) == 3
    #  THE LIGHT DRIFTS AND THE SOIL DOES NOT: the soil's imaginarium holds no light reading, so the
    #  ground it lays hashes as last pass's did, and its one world is kept under it; the last pass's
    #  ground — the match itself, whose facts the new one carries — is the one graph dropped. The
    #  light's imaginarium is surprised and drops what it imagined.
    heard.clear()
    later = NOW + timedelta(minutes=10)
    deliver("light_sensor", 150, later)
    planner.plan(later)
    second = {e.scope: (e.present, e.kept, e.dropped) for e in heard}
    assert second[soil] == ("ground", 2, 1), f"the soil's ground and its world kept, last pass's ground gone: {second}"
    assert second[light][0] == "surprise", second
    #  THE SOIL DRIFTS: a reading the soil's want reads moved, nothing it imagined holds, the cone goes.
    heard.clear()
    latest = later + timedelta(minutes=10)
    deliver("moisture_probe", 0.25, latest)
    planner.plan(latest)
    third = {e.scope: (e.present, e.kept, e.dropped) for e in heard}
    assert third[soil][0] == "surprise" and third[light][0] == "ground", third
