"""Two beds, each with a probe and a pump of its own, under the one desire that the bed be
comfortable: two instances of one property, in two scopes by key (a-scope-is-a-predicate-on-a-key,
the two-instances seam, closed). Both dry, the derivation mints a want per bed — each named for its
bed, keyed by it, placed in its bed's scope and searched there — and both pumps are commanded in one
pass. Measured before it was believed: on the tree before, the same world minted one want in every
imaginarium, placed it in the first scope, found it unreachable there and commanded nothing.
"""

from __future__ import annotations

import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from agent import clock
from agent.runtime import UNFINISHED, Runtime, boot
from agent.store import rows
from agent.transport.mqtt.driver import Mqtt

WORLD = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
GH = "http://example.org/orexis/world/greenhouse#"

#  A SECOND BED, with ranges of its own, a probe and a pump — the first bed's, copied. The first
#  bed is `:bed`, the heater's as much as the pump's; this one is the second pump's alone.
BED2 = '''
:bed2 a sosa:FeatureOfInterest ; rdfs:label "the second bed" ;
    climate:driesPerDay 0.04 ; climate:litresPerFraction 2.0 ;
    ssn-system:hasOperatingRange :bed2_operating ; ssn-system:hasSurvivalRange :bed2_survival .
:bed2_operating a ssn-system:OperatingRange ;
    ssn-system:inCondition [ a ssn-system:Condition , schema:PropertyValue ; ssn:forProperty climate:SoilMoisture ;
                             schema:minValue 0.30 ; schema:maxValue 0.60 ; schema:unitCode unit:UNITLESS ] .
:bed2_survival a ssn-system:SurvivalRange ;
    ssn-system:inCondition [ a ssn-system:Condition , schema:PropertyValue ; ssn:forProperty climate:SoilMoisture ;
                             schema:minValue 0.10 ; schema:maxValue 0.85 ; schema:unitCode unit:UNITLESS ] .
:moisture_probe2 a sosa:Sensor ; orexis:localId "moisture_probe2" ; sosa:isHostedBy :bed2 ; sosa:observes climate:SoilMoisture ;
    ssn-system:hasSystemCapability [ ssn-system:hasSystemProperty
        [ a ssn-system:Frequency , schema:PropertyValue ; schema:value 10 ; schema:unitCode unit:MIN ] ] .
:pump2 a actuation:Valve ; rdfs:label "the second pump" ;
    actuation:actuates :bed2 ; actuation:actuatesProperty climate:SoilMoisture ; actuation:drawsFrom :water_butt ;
    actuation:mlPerSecond 10.0 ; actuation:maxDoseMl 500.0 .
'''
WIRED = '''
:moisture_probe2 mqtt4ssn:observesTopic :moisture2_readings .
:moisture2_readings a mqtt4ssn:Topic .
:moisture2_filter a mqtt4ssn:TopicFilter ;
    mqtt4ssn:hasFilterPattern "sensors/moisture_probe2/reading" ; mqtt4ssn:matchesTopic :moisture2_readings .
:pump2 mqtt4ssn:listensToTopic :pump2_commands .
:pump2_commands a mqtt4ssn:Topic .
:pump2_filter a mqtt4ssn:TopicFilter ;
    mqtt4ssn:hasFilterPattern "actuators/pump2/command" ; mqtt4ssn:matchesTopic :pump2_commands .
'''


def two_bed_world(tmp_path: Path) -> Path:
    """The greenhouse with a second bed — a copy, since a world imports its domains by the tree's shape."""
    world = tmp_path / "world" / "greenhouse"
    shutil.copytree(WORLD, world, ignore=shutil.ignore_patterns("tests", "secrets", "__pycache__"))
    (tmp_path / "domains").symlink_to(WORLD.parents[1] / "domains")
    (world / "world.ttl").write_text((world / "world.ttl").read_text() + BED2)
    society = world / "society.ttl"
    society.write_text(society.read_text()
                       .replace("orexis:actsFor :bed ;", "orexis:actsFor :bed , :bed2 ;")
                       .replace("actuation:hasActuator :pump , :heater .", "actuation:hasActuator :pump , :heater , :pump2 .")
                       .replace("mqtt4ssn:hosts :moisture_probe , :thermometer , :pump , :heater ;",
                                "mqtt4ssn:hosts :moisture_probe , :thermometer , :pump , :heater , :moisture_probe2 , :pump2 ;"))
    society.write_text(society.read_text() + WIRED)
    return world


@pytest.fixture
def two_beds(tmp_path):
    return two_bed_world(tmp_path)


class _Broker:
    def __init__(self):
        self.published = []

    def subscribe(self, pattern):
        pass

    def publish(self, topic, payload, retain=False):
        self.published.append(topic)


class _Clock:
    """One timeline: every read moves it on by a second, as a running agent's clock does."""

    def __init__(self, at):
        self.at = at

    def __call__(self):
        self.at += timedelta(seconds=1)
        return self.at


_WANTS_Q = """
SELECT ?w ?key WHERE {
  GRAPH ?g { ?w a planning:Want ; prov:wasDerivedFrom ?d . OPTIONAL { ?w planning:keyedBy ?key } } }"""
_SATISFIED_Q = "SELECT ?p WHERE { GRAPH ?g { ?p a planning:Plan ; planning:outcome planning:Satisfied } }"
_SCOPE_MEMBERS_Q = "SELECT ?m ?s WHERE { GRAPH ?g { ?m planning:inScope ?s } }"


def _local(iri: str | None) -> str | None:
    return iri.rsplit("#", 1)[-1].rsplit("/", 1)[-1] if iri else None


def test_two_dry_beds_are_two_wants_in_two_scopes_and_both_pumps_are_commanded_in_one_pass(monkeypatch, two_beds):
    """Three scopes: each bed's soil with its pump, and the air with the heater. The first bed is a
    member of its pump's scope and the heater's, the second of its pump's alone, the property of both
    pumps' — so what places a soil reading, a witness and a want is the MEET of what it names, and the
    bed is what tells the two apart. Each imaginarium holds its own bed's reading and mints its own
    want, keyed by its bed; the air's holds no soil reading and mints none; both pumps are commanded,
    once each, and the heater, the air being warm, is not."""
    time = _Clock(NOW)
    monkeypatch.setattr(clock, "now", time)
    beliefs = boot(two_beds, "grower")
    members = {}
    for r in rows(beliefs, _SCOPE_MEMBERS_Q, ()):
        members.setdefault(_local(r["m"]), set()).add(_local(r["s"]))
    assert len(members["bed"]) == 2 and len(members["bed2"]) == 1 and len(members["SoilMoisture"]) == 2, \
        f"the first bed is the pump's and the heater's, the second its pump's alone, the soil both pumps': {members}"
    assert len(members["grower"]) == 3 and members["grower"] == members["Dosing"] | members["Heating"], \
        "the agent, bound by every filling, is every scope's and tells nothing"
    broker = _Broker()
    runtime = Runtime(beliefs, "grower", transport=Mqtt(GH + "grower", broker))
    runtime.time = time
    for sensor, value in {"thermometer": 21.0, "moisture_probe": 0.2, "moisture_probe2": 0.2}.items():
        runtime.deliver(f"sensors/{sensor}/reading", f'{{"value": {value}}}'.encode(), NOW)
    assert runtime.run(passes=1, poll_s=0) == UNFINISHED
    planner = runtime.parts["planning"].planner
    found = [sorted((_local(r["w"]), _local(r.get("key"))) for r in rows(im, _WANTS_Q, ()))
             for im in planner.imaginaria.values()]
    assert sorted(found) == [[], [("the_bed_is_comfortable.pursued.bed.SoilMoisture", "bed")],
                             [("the_bed_is_comfortable.pursued.bed2.SoilMoisture", "bed2")]], found
    satisfied = [sorted(_local(r["p"]).rsplit(".pursued.", 1)[-1] for r in rows(im, _SATISFIED_Q, ()))
                 for im in planner.imaginaria.values()]
    assert sorted(satisfied) == [[], ["bed.SoilMoisture"], ["bed2.SoilMoisture"]], \
        f"each want planned in its own imaginarium, and the air's plans nothing: {satisfied}"
    assert sorted(broker.published) == ["actuators/pump/command", "actuators/pump2/command"]
    assert len(runtime.parts["execution"].executor.walking()) == 2
    #  AND THE NEXT PASS BLOCKS NOTHING: each dose was checked as it was taken, in the present the
    #  beliefs hold, both beds' readings among them (#916).
    assert runtime.run(passes=1, poll_s=0) == UNFINISHED
    assert planner.blocked == [] and len(broker.published) == 2, "one dose each, and nothing more"
