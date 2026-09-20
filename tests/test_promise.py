"""A promise the level beneath keeps (#523, a-level-is-a-vocabulary-and-a-bridge). A step of
an action nobody takes, with a bridge declared for it, raises its predicted fact — translated
through the bridge — as a want this agent holds, pursued by the ordinary path over the actions
that are taken; the step waits on the same fact, and its verdict withdraws the promise and
writes the coarse fact the bridge says is the same thing."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from orexis_agent_progression.act import Step
from orexis_agent_progression.ontology import ACTIONS_GRAPH, STATE_GRAPH, promises_graph
from orexis_agent_progression.store import bindings
from conftest import build_agent, genesis_store, stake_of

T = "urn:toy#"


def _fern_with_a_ferry(monkeypatch, bridged=True):
    fern = build_agent("fern", genesis_store({"fern": 0.30}), monkeypatch)
    bridge = f"""
      <{T}FerryOnFoot> a orexis:Bridge ; orexis:refines <{T}Ferry> ;
          sh:construct "CONSTRUCT {{ $via <{T}at> $about }} WHERE {{ }}" ;
          orexis:estimates <{T}stepsAway> .
      <{T}stepsAway> sh:select "SELECT (1 AS ?estimate) WHERE {{ }}" .""" if bridged else ""
    fern.beliefs.update(f"""INSERT DATA {{ GRAPH <{ACTIONS_GRAPH}> {{
      <{T}Ferry> a orexis:Action . {bridge} }} }}""")
    fern.beliefs.update(f"INSERT DATA {{ GRAPH <{STATE_GRAPH}> {{ <{T}box> <{T}on> <{T}pierA> }} }}")
    return fern


def _ferry(want):
    return Step(action=T + "Ferry", via=T + "box", about=T + "pierB", want=want, urgency_after=0.0,
                predicts=(frozenset({(T + "box", T + "on", T + "pierB")}),
                          frozenset({(T + "box", T + "on", T + "pierA")})))


def test_a_taker_less_step_with_a_bridge_raises_its_promise_as_a_want(monkeypatch):
    fern = _fern_with_a_ferry(monkeypatch)
    keeper, want = fern.keeper, stake_of(fern).uri
    from orexis_agent_progression.execution import carry_out
    uri = keeper.adopt(_ferry(want), want, "ferry the box over")
    assert carry_out(fern, keeper.current(uri), None, uri) is False, "nobody takes Ferry: it stands"
    promised = [d for d in fern.pursuing() if d.uri.startswith("http://example.org/orexis#promise_")]
    assert len(promised) == 1 and promised[0].state == "unmet", "the promise is a want the agent holds"
    rows = bindings(fern.beliefs.query_union(f"""
SELECT ?w ?step ?sel WHERE {{ GRAPH <{promises_graph(fern.id)}> {{
  <{fern.me.uri}> orexis:holds ?w . ?w progression:promisedBy ?step ; orexis:estimates ?est . ?est sh:select ?sel }} }}"""))
    assert len(rows) == 1 and "?estimate" in rows[0]["sel"], "with the bridge's estimate, bound to this promise"
    assert keeper.open_expectations(want), "and the step waits on the translated fact"
    # the level beneath keeps the promise: the box is at pier B, in the lower vocabulary
    fern.beliefs.update(f"INSERT DATA {{ GRAPH <{STATE_GRAPH}> {{ <{T}box> <{T}at> <{T}pierB> }} }}")
    assert keeper.open_expectations(want) == [], "the promised fact answered the step"
    assert not [d for d in fern.pursuing() if d.uri.startswith("http://example.org/orexis#promise_")], \
        "the promise is withdrawn"
    on = bindings(fern.beliefs.query_over(f"SELECT ?p WHERE {{ <{T}box> <{T}on> ?p }}", STATE_GRAPH))
    assert [r["p"] for r in on] == [T + "pierB"], \
        "the coarse fact is written: the bridge says at pier B and on pier B are one thing"
    assert keeper.standing(want=want) == [], "the plan of one Ferry finished"


def test_a_taker_less_step_without_a_bridge_is_a_promise_nobody_keeps(monkeypatch, caplog):
    fern = _fern_with_a_ferry(monkeypatch, bridged=False)
    keeper, want = fern.keeper, stake_of(fern).uri
    from orexis_agent_progression.execution import carry_out
    uri = keeper.adopt(_ferry(want), want, "ferry the box over")
    with caplog.at_level("ERROR", logger="execution"):
        assert carry_out(fern, keeper.current(uri), None, uri) is False
    assert any("no bridge refines it" in r.message for r in caplog.records)
    assert not [d for d in fern.pursuing() if d.uri.startswith("http://example.org/orexis#promise_")]
    assert keeper.standing(want=want), "it stands, said loudly, for the gate to refuse (#532)"
