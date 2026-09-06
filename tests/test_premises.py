"""A step carries its precondition: the facts its rules read (#550).

What a diff's rule READ in the world it was planned from is the step's premises — the
positive patterns of the effect's WHERE and of the availability select, instantiated by the
engine for that binding and stated as the same canonical facts the prediction is made of.
Filled once along the winning path, persisted by the keeper, kept by a remembered plan.
Nothing reads them yet but these tests; the regression that keys a plan by them is #551.
"""
from __future__ import annotations

import pytest

from conftest import build_agent, genesis_store
from orexis_agent_deliberation import effects, remembered
from orexis_agent_deliberation.effects import _where_body
from orexis_agent_deliberation.planner import Planner, _Node
from orexis_agent_progression.act import Step, premises_from_json, premises_json
from orexis_agent_progression.ontology import STATE_GRAPH
from test_planning import _thirsty_with_a_nearly_empty_butt
from test_violation import CASES, _agent

ACTUATION = "http://example.org/orexis/actuation#"
HANOI = "http://example.org/orexis/hanoi#"
SOSA = "http://www.w3.org/ns/sosa/"


def _predicates(facts) -> set[str]:
    return {f[1] if f[0] != "keyed" else f[3] for f in facts}


def test_a_dose_reads_its_chain_its_conversion_and_the_standing_reading(monkeypatch):
    """The dosing rule's WHERE walks actsFor, the actuator, its source and the good's term,
    reads the agent's conversion belief and the standing reading. Every one is a premise of
    the step, and asking the rule again at the world it was planned from says the same."""
    agent, planner, desire = _thirsty_with_a_nearly_empty_butt(monkeypatch)
    plan = planner.plan(desire)
    dose = next(s for s in plan.steps if s.action == ACTUATION + "Dosing")
    assert dose.premises, "a planned dose carries what its rule read"
    read = _predicates(dose.premises)
    assert {ACTUATION + "hasActuator", ACTUATION + "actuates", ACTUATION + "drawsFrom",
            SOSA + "hasSimpleResult"} <= read, sorted(read)
    assert any(f[0] == "keyed" for f in dose.premises), \
        "the standing reading is read as the keyed fact the signature knows it by"
    #  Re-asked of the world the first step was planned from — the belief base itself —
    #  with the size the step was planned with: the same facts, exactly.
    first = plan.steps[0]
    bind = planner._bind(desire, node=_Node(graph=STATE_GRAPH), row=first, litres=first.quantity or 0.0)
    from orexis_agent_deliberation import signature
    again = signature.facts(effects.premises(agent.beliefs, first.action, keyed=tuple(planner._keys), **bind),
                            planner._keys)
    assert again == first.premises


def test_a_move_reads_what_put_it_on_the_menu(monkeypatch):
    """Hanoi's Move states its precondition in its availability select and almost nothing in
    its effect's WHERE, so the premises come from the row: the disk on its support, its size,
    the target being a peg. The absences (nothing on the disk, no smaller disk on the peg)
    are the regression's, and are not here."""
    agent = _agent(monkeypatch, *CASES["hanoi, one disk astray"])
    want = next(d for d in agent.pursuing())
    plan = Planner(agent, agent.me).plan(want)
    move = next(s for s in plan.steps if s.action == HANOI + "Move")
    assert move.premises, "a planned move carries what put it on the menu"
    read = _predicates(move.premises)
    assert {HANOI + "on", HANOI + "size", "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"} <= read, sorted(read)
    assert any(f[0] == move.via and f[1] == HANOI + "on" for f in move.premises), \
        "the moved disk's own support is a premise"


def test_the_ledger_keeps_the_premises_and_hands_them_back(monkeypatch):
    agent, planner, desire = _thirsty_with_a_nearly_empty_butt(monkeypatch)
    plan = planner.plan(desire)
    assert plan.steps and plan.steps[0].premises
    keeper = next(m for m in agent.modules if m.name == "intention")
    uri = keeper.adopt(plan.steps, desire.uri, "to pin the premises")
    walked = keeper.walked(uri)
    assert walked and walked[0].premises == plan.steps[0].premises
    assert premises_from_json(premises_json(plan.steps[0].premises)) == plan.steps[0].premises


def test_a_remembered_plan_keeps_each_steps_premises(monkeypatch):
    agent, planner, desire = _thirsty_with_a_nearly_empty_butt(monkeypatch)
    plan = planner.plan(desire)
    remembered.lift(agent, desire.uri, list(plan.steps), "some-world", None)
    kept = remembered.remembered_for(agent, desire.uri)[0][1]
    assert [s.premises for s in kept] == [s.premises for s in plan.steps]
    assert all(s.premises for s in kept)


def test_a_methods_first_member_inherits_the_premises(monkeypatch):
    """As the last member inherits the prediction: what made the abstract step applicable
    is what must hold when its first member is taken."""
    agent = build_agent("fern", genesis_store({"fern": 0.30}), monkeypatch)
    keeper = next(m for m in agent.modules if m.name == "intention")
    acquiring = "http://example.org/orexis/market#Acquiring"
    assert keeper._method_of(acquiring), "the market's protocol is the shipped method"
    facts = frozenset({("urn:a", "urn:b", "urn:c")})
    members = keeper._expanded([Step(action=acquiring, via="urn:venue", premises=facts,
                                     predicts=(frozenset(), frozenset()))])
    assert len(members) >= 2
    assert members[0].premises == facts and all(m.premises is None for m in members[1:])
    assert members[-1].predicts is not None and all(m.predicts is None for m in members[:-1])


def test_the_where_body_is_found_past_nested_braces_and_strings():
    text = 'CONSTRUCT { ?s <p> "a } brace" } WHERE { GRAPH <g> { ?s <p> ?o } FILTER(?o != "}") }'
    assert _where_body(text) == ' GRAPH <g> { ?s <p> ?o } FILTER(?o != "}") '
    assert _where_body("SELECT ?x { ?x <p> ?y }") is None, "no WHERE keyword, no body"
