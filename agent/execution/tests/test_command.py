"""`command`: what taking a step sends, sized by the action's own text from the present — the
search never sized it. A step whose action carries no command sends nothing."""

from __future__ import annotations

from datetime import datetime, timezone

import pyoxigraph as ox
import pytest

from agent import clock
from agent.execution.command import command
from agent.store import update

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
T = "http://example.org/test#"


@pytest.fixture
def store(monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: NOW)
    st = ox.Store()
    update(st, f"""INSERT DATA {{
  GRAPH <{T}actions> {{
    <{T}Dose> a orexis:Action ; orexis:takes <{T}valve> , <{T}reading> ;
      execution:implementation [ execution:operation [ a execution:Command ; sh:select \"\"\"SELECT ?actuator ?payload WHERE {{
          $reading sosa:hasSimpleResult ?value . $valve <{T}cap> ?cap .
          BIND($valve AS ?actuator)
          BIND(CONCAT('{{"dose_ml": ', STR(xsd:integer(ROUND((0.45 - ?value) * 2000.0))), '}}') AS ?payload) }}\"\"\" ] ] .
    <{T}Look> a orexis:Action ; orexis:takes <{T}valve> .
    <{T}Ring> a orexis:Action ;
      execution:implementation [ execution:operation [ a execution:Command ; sh:select \"\"\"SELECT ?actuator ?payload WHERE {{
          ?me a orexis:Self ; <{T}bell> ?actuator . BIND('{{"ring": true}}' AS ?payload) }}\"\"\" ] ] . }}
  GRAPH <{T}world> {{ <{T}pump> <{T}cap> 500 . <{T}me> <{T}bell> <{T}my_bell> . <{T}you> <{T}bell> <{T}your_bell> }}
  GRAPH <{T}sensed> {{ <{T}soil> sosa:hasSimpleResult 0.35 }}
  GRAPH <{T}self> {{ <{T}me> a orexis:Self }}
  GRAPH <{T}catalogue> {{
    <{T}catalogue> a orexis:CatalogueGraph .
    <{T}actions> a orexis:ActionGraph , orexis:PublicGraph .
    <{T}world> a orexis:PublicGraph .
    <{T}sensed> a orexis:StateGraph , orexis:BeliefGraph .
    <{T}self> a orexis:SelfGraph , orexis:BeliefGraph . }} }}""")
    return st


def test_a_step_is_sized_from_the_reading_in_hand(store):
    said = {"step": T + "step", "fills": T + "Dose", "valve": T + "pump", "reading": T + "soil"}
    assert command(store, said) == [(T + "pump", {"dose_ml": 200})], "0.10 short, at two litres a fraction"


def test_a_step_whose_action_has_no_command_sends_nothing(store):
    assert command(store, {"step": T + "step", "fills": T + "Look", "valve": T + "pump"}) == []


def test_a_command_asks_the_self_for_the_agent_and_is_handed_nobody(store):
    """Who is taking the step is no token: the text asks `?me a orexis:Self` over the beliefs, and the
    self's graph is a belief, so it is among what a command reads — the bell of the agent the store
    is, and not the other agent's the world also states."""
    assert command(store, {"step": T + "step", "fills": T + "Ring"}) == [(T + "my_bell", {"ring": True})]
