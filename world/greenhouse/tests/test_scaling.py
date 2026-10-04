"""What the search spends against the world it stands in, and whether an aspect of the world that is
unrelated to a want changes what that want's search spends (#593).

Two metrics the sovereign named. A POSSIBLE WORLD'S SIZE against the present: a world is the readings
and their revisions, forked from the ground, never the public knowledge, so it is the ground's size
and a few percent of the store. And STABILITY: a lamp and a light sensor added to the greenhouse, with
a desire that the bed be lit, are a third scope; the soil want's search forks the same one world over
the same one candidate it did before, and the lamp — a second filling of the heating action — is
admitted in the light's scope alone. What does grow is each world's size, since a fork copies every
reading the agent holds, whatever scope it is of.
"""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

import pytest

from agent import clock
from agent.ontology import PUBLIC, STATE
from agent.runtime import boot
from agent.store import close_catalogue, graphs_of, quads, revisions_of, rows
from agent.sensing.received import received
from agent.belief.revise import revise
from agent.planning.planner import Planner

WORLD = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
GH = "http://example.org/orexis/world/greenhouse#"

LIGHT = '''
#  AN UNRELATED ASPECT: light on the bed, and a lamp that raises it.
:light_sensor a sosa:Sensor ; orexis:localId "light_sensor" ; sosa:observes climate:Light ; sosa:isHostedBy :bed ;
    ssn-system:hasSystemCapability [ ssn-system:hasSystemProperty
        [ a ssn-system:Frequency , schema:PropertyValue ; schema:value 10 ; schema:unitCode unit:MIN ] ] .
:bed_light_operating a ssn-system:OperatingRange ;
    ssn-system:inCondition [ a ssn-system:Condition , schema:PropertyValue ; ssn:forProperty climate:Light ;
                             schema:minValue 200 ; schema:maxValue 800 ; schema:unitCode unit:LUX ] .
:bed ssn-system:hasOperatingRange :bed_light_operating .
:lamp a climate:Heater ; orexis:localId "lamp" ; climate:warms :bed ; climate:warmsProperty climate:Light ;
    climate:degreesPerHour 400.0 ; climate:maxRunS 3600 .
'''
LIT = '''
:grower planning:holds :the_bed_is_lit .
:the_bed_is_lit a planning:Desire ; rdfs:label "the bed is lit" ; planning:metWhen :lit .
:lit a sh:NodeShape ;
    sh:targetNode :grower ;
    sh:property [
        sh:path ( orexis:actsFor [ sh:inversePath sosa:hasFeatureOfInterest ] ) ;
        planning:about climate:Light ;
        sh:qualifiedMaxCount 0 ;
        sh:qualifiedValueShape [
            sh:property [ sh:path sosa:observedProperty ; sh:hasValue climate:Light ] ;
            sh:property [ sh:path sensing:below ; sh:minCount 1 ] ] ;
        sh:message "the bed is dim" ] .
'''


@pytest.fixture
def lit_greenhouse(tmp_path):
    """The greenhouse with the light added — a copy, since a world imports its domains by the tree's shape."""
    world = tmp_path / "world" / "greenhouse"
    shutil.copytree(WORLD, world, ignore=shutil.ignore_patterns("tests", "secrets", "__pycache__"))
    (tmp_path / "domains").symlink_to(WORLD.parents[1] / "domains")
    (world / "world.ttl").write_text((world / "world.ttl").read_text() + LIGHT)
    society = world / "society.ttl"
    society.write_text(society.read_text()
                       .replace("actuation:hasActuator :pump , :heater .", "actuation:hasActuator :pump , :heater , :lamp .")
                       .replace("mqtt4ssn:hosts :moisture_probe , :thermometer , :pump , :heater ;",
                                "mqtt4ssn:hosts :moisture_probe , :thermometer , :pump , :heater , :light_sensor , :lamp ;"))
    (world / "desires.ttl").write_text((world / "desires.ttl").read_text() + LIT)
    return world


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
        plans = {r["p"].rsplit(".", 1)[-1] for r in rows(im, "SELECT ?p WHERE { GRAPH ?g { ?p a planning:Plan ; planning:outcome planning:Satisfied } }", ())}
        out[frozenset(plans) or scope] = (len(list(quads(im, ground))), sorted(len(list(quads(im, w))) for w in worlds),
                                           int(cands["n"]), int(cands["actions"]), plans)
    return present, state, out


def test_a_possible_world_is_the_readings_and_a_few_percent_of_the_present(monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: NOW)
    present, state, scopes = _pass(WORLD, {"thermometer": 12.0, "moisture_probe": 0.2})
    for ground, worlds, _, _, _ in scopes.values():
        assert worlds == [ground], "a world is a fork of its ground, nothing more"
        assert ground == state, "the readings and the sides concluded of them, and no public knowledge"
        assert ground * 20 < present, f"a world of {ground} quads against a present of {present}"


def test_an_unrelated_aspect_changes_nothing_of_the_soil_wants_search(monkeypatch, lit_greenhouse):
    """The light and the lamp are a third scope. The soil's search forks the one world over the one
    candidate it forked without them; the lamp's heating, a second filling of the heating action, is
    admitted in the light's scope and nowhere else; and what grows is each world's size, by the
    light's reading and its revisions, since a fork copies every reading."""
    monkeypatch.setattr(clock, "now", lambda: NOW)
    _, state, before = _pass(WORLD, {"thermometer": 12.0, "moisture_probe": 0.2})
    _, lit_state, after = _pass(lit_greenhouse, {"thermometer": 12.0, "moisture_probe": 0.2, "light_sensor": 100})
    soil_before, soil_after = before[frozenset({"SoilMoisture"})], after[frozenset({"SoilMoisture"})]
    assert (soil_before[1:], soil_after[1:]) == (([soil_before[0]], 1, 1, {"SoilMoisture"}),
                                                 ([soil_after[0]], 1, 1, {"SoilMoisture"}))
    assert len(after) == 3 and {p for _, _, _, _, plans in after.values() for p in plans} == {"SoilMoisture", "AirTemperature", "Light"}
    assert all(cands == 1 and actions == 1 for _, _, cands, actions, _ in after.values()), \
        f"one filling per scope, the lamp's in the light's alone: {after}"
    assert soil_after[0] == lit_state > soil_before[0] == state, "a world grows by the readings added, whatever their scope"
