"""`command`: what taking a step sends, sized by the action's own text from the present — the
search never sized it. A step whose action carries no command sends nothing.

THE READING IN HAND IS AN OBSERVATION, AND THE TEXT NAMES IT (#944). A sensor's percepts are kept,
each ended where the next began, and none is a belief: a command is handed the beliefs and nothing
else, since an observation is sensing's and no word of this package's, so a text sizing a step from
a reading names the kind it is kept in, in its own `GRAPH` clauses joined with the catalogue, and the
one holding at `$now` — the sensor's latest, with no ordering of its own. A text that names no graph
reads no observation at all."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pyoxigraph as ox
import pytest

from agent import clock
from agent.execution.command import command
from agent.store import update

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
T = "http://example.org/test#"

#  THE READING HOLDING AT `$now`, in the observation graph that holds it, found by sensing's kind.
_HELD = """GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?held a sensing:ObservationGraph ; dcterms:temporal ?p .
                       ?p orexis:start ?from . OPTIONAL { ?p orexis:end ?to }
                       FILTER(?from <= $now && (!BOUND(?to) || $now < ?to)) }
          GRAPH ?held { ?reading sosa:hasFeatureOfInterest $subject ; sosa:hasSimpleResult ?value }"""
#  THE SAME READING, asked as though the beliefs held it.
_BLIND = "?reading sosa:hasFeatureOfInterest $subject ; sosa:hasSimpleResult ?value ."
#  A DOSE SIZED FROM IT: two litres a fraction, to 0.45.
_SIZED = ("$valve <" + T + "cap> ?cap . BIND($valve AS ?actuator) "
          """BIND(CONCAT('{"dose_ml": ', STR(xsd:integer(ROUND((0.45 - ?value) * 2000.0))), '}') AS ?payload)""")


def _period(start: datetime, end: datetime) -> str:
    return (f'dcterms:temporal [ a dcterms:PeriodOfTime ; orexis:start "{start.isoformat()}"^^xsd:dateTime ; '
            f'orexis:end "{end.isoformat()}"^^xsd:dateTime ]')


def _command(name: str, reads: str) -> str:
    return (f'<{T}{name}> a orexis:Action ; orexis:takes <{T}valve> , <{T}subject> ; '
            f'execution:implementation [ execution:operation [ a execution:Command ; sh:select """'
            f'SELECT ?actuator ?payload WHERE {{ {reads} {_SIZED} }}""" ] ] .')


@pytest.fixture
def store(monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: NOW)
    st = ox.Store()
    earlier, latest = NOW - timedelta(minutes=11), NOW - timedelta(minutes=1)
    update(st, f"""INSERT DATA {{
  GRAPH <{T}actions> {{
    {_command("Dose", _HELD)}
    {_command("Blind", _BLIND)}
    <{T}Look> a orexis:Action ; orexis:takes <{T}valve> .
    <{T}Ring> a orexis:Action ;
      execution:implementation [ execution:operation [ a execution:Command ; sh:select \"\"\"SELECT ?actuator ?payload WHERE {{
          ?me a orexis:Self ; <{T}bell> ?actuator . BIND('{{"ring": true}}' AS ?payload) }}\"\"\" ] ] . }}
  GRAPH <{T}world> {{ <{T}pump> <{T}cap> 500 . <{T}me> <{T}bell> <{T}my_bell> . <{T}you> <{T}bell> <{T}your_bell> }}
  GRAPH <{T}read_before> {{ <{T}soil_before> sosa:hasFeatureOfInterest <{T}bed> ; sosa:hasSimpleResult 0.30 }}
  GRAPH <{T}read_last> {{ <{T}soil_last> sosa:hasFeatureOfInterest <{T}bed> ; sosa:hasSimpleResult 0.35 ;
                                          sensing:previous <{T}soil_before> }}
  GRAPH <{T}self> {{ <{T}me> a orexis:Self }}
  GRAPH <{T}catalogue> {{
    <{T}catalogue> a orexis:CatalogueGraph .
    <{T}actions> a orexis:ActionGraph , orexis:PublicGraph .
    <{T}world> a orexis:PublicGraph .
    <{T}read_before> a sensing:ObservationGraph ; {_period(earlier, latest)} .
    <{T}read_last> a sensing:ObservationGraph ; {_period(latest, NOW + timedelta(minutes=19))} .
    <{T}self> a orexis:SelfGraph , orexis:BeliefGraph . }} }}""")
    return st


def test_a_step_is_sized_from_the_observation_its_text_finds_holding_now(store):
    """Two readings of the bed are kept: 0.30, ended a minute ago, and 0.35, holding now. The dose's text
    orders nothing and is answered once, by the latest — the one whose graph holds at the instant the
    step is taken, found by the text's own `GRAPH` clauses."""
    said = {"step": T + "step", "fills": T + "Dose", "valve": T + "pump", "subject": T + "bed"}
    assert command(store, said) == [(T + "pump", {"dose_ml": 200})], "0.10 short, at two litres a fraction"


def test_a_text_that_names_no_observation_graph_reads_none(store):
    """Execution hands a command the beliefs and nothing else: an observation is sensing's, no belief,
    and no word of this package's (#944), so a text reading a number it does not find by its kind
    answers nothing — and a step whose command answers nothing is not taken (#869)."""
    said = {"step": T + "step", "fills": T + "Blind", "valve": T + "pump", "subject": T + "bed"}
    assert command(store, said) == []


def test_a_step_whose_action_has_no_command_sends_nothing(store):
    assert command(store, {"step": T + "step", "fills": T + "Look", "valve": T + "pump"}) == []


def test_a_command_asks_the_self_for_the_agent_and_is_handed_nobody(store):
    """Who is taking the step is no token: the text asks `?me a orexis:Self` over the beliefs, and the
    self's graph is a belief, so it is among what a command reads — the bell of the agent the store
    is, and not the other agent's the world also states."""
    assert command(store, {"step": T + "step", "fills": T + "Ring"}) == [(T + "my_bell", {"ring": True})]
