"""A step carries its precondition: the facts its rules read (#550).

What a diff's rule READ in the world it was planned from is the step's precondition — the
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
from orexis_agent_progression.act import Step, precondition_from_json, precondition_json
from orexis_agent_progression.ontology import STATE_GRAPH
from orexis_agent_progression.store import bindings
from test_planning import _thirsty_with_a_nearly_empty_butt, MOISTURE
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
    assert dose.precondition, "a planned dose carries what its rule read"
    read = _predicates(dose.precondition)
    assert {ACTUATION + "hasActuator", ACTUATION + "actuates", ACTUATION + "drawsFrom",
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"} <= read, sorted(read)
    #  The standing reading is a premise by WHAT IT IS (#576) — the band the domain asserted
    #  on it, a plain triple — and never by its number.
    readings = [f for f in dose.precondition if f[0] == "keyed"]
    assert readings and all(f[3].endswith("#type") for f in readings), readings
    assert any(str(f[4]).startswith("http://example.org/orexis#band.") for f in readings), "the member band"
    assert SOSA + "hasSimpleResult" not in read
    assert any(f[0] == "keyed" for f in dose.precondition), \
        "the standing reading is read as the keyed fact the signature knows it by"
    #  Re-asked of the world the first step was planned from — the belief base itself —
    #  with the size the step was planned with: the same facts, exactly.
    first = plan.steps[0]
    bind = planner._bind(desire, node=_Node(graph=STATE_GRAPH), row=first, litres=first.quantity or 0.0)
    from orexis_agent_deliberation import signature
    again = signature.by_class(signature.facts(
        effects.precondition(agent.beliefs, first.action, keyed=tuple(planner._compiled.keys), **bind), planner._compiled.keys))
    assert again == first.precondition


def test_a_move_reads_what_put_it_on_the_menu(monkeypatch):
    """Hanoi's Move states its precondition in its availability select and almost nothing in
    its effect's WHERE, so the precondition comes from the row: the disk on its support, its size,
    the target being a peg. The absences (nothing on the disk, no smaller disk on the peg)
    are the regression's, and are not here."""
    agent = _agent(monkeypatch, *CASES["hanoi, one disk astray"])
    want = next(d for d in agent.pursuing())
    plan = Planner(agent, agent.me).plan(want)
    move = next(s for s in plan.steps if s.action == HANOI + "Move")
    assert move.precondition, "a planned move carries what put it on the menu"
    read = _predicates(move.precondition)
    assert {HANOI + "on", HANOI + "size", "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"} <= read, sorted(read)
    assert any(f[0] == move.via and f[1] == HANOI + "on" for f in move.precondition), \
        "the moved disk's own support is a premise"


def test_the_ledger_keeps_the_precondition_and_hands_it_back(monkeypatch):
    agent, planner, desire = _thirsty_with_a_nearly_empty_butt(monkeypatch)
    plan = planner.plan(desire)
    assert plan.steps and plan.steps[0].precondition
    keeper = next(m for m in agent.modules if m.name == "intention")
    uri = keeper.adopt(plan.steps, desire.uri, "to pin the precondition")
    walked = keeper.walked(uri)
    assert walked and walked[0].precondition == plan.steps[0].precondition
    assert precondition_from_json(precondition_json(plan.steps[0].precondition)) == plan.steps[0].precondition


def test_a_remembered_plan_keeps_each_steps_precondition(monkeypatch):
    agent, planner, desire = _thirsty_with_a_nearly_empty_butt(monkeypatch)
    plan = planner.plan(desire)
    remembered.lift(agent, desire.uri, list(plan.steps), None)
    kept = remembered.remembered_for(agent, desire.uri)[0][1]
    assert [s.precondition for s in kept] == [s.precondition for s in plan.steps]
    assert all(s.precondition for s in kept)


def test_a_methods_first_member_inherits_the_precondition(monkeypatch):
    """As the last member inherits the prediction: what made the abstract step applicable
    is what must hold when its first member is taken."""
    agent = build_agent("fern", genesis_store({"fern": 0.30}), monkeypatch)
    keeper = next(m for m in agent.modules if m.name == "intention")
    acquiring = "http://example.org/orexis/market#Acquiring"
    assert keeper._method_of(acquiring), "the market's protocol is the shipped method"
    facts = frozenset({("urn:a", "urn:b", "urn:c")})
    members = keeper._expanded([Step(action=acquiring, via="urn:venue", precondition=facts,
                                     predicts=(frozenset(), frozenset()))])
    assert len(members) >= 2
    assert members[0].precondition == facts and all(m.precondition is None for m in members[1:])
    assert members[-1].predicts is not None and all(m.predicts is None for m in members[:-1])


def test_the_where_body_is_found_past_nested_braces_and_strings():
    text = 'CONSTRUCT { ?s <p> "a } brace" } WHERE { GRAPH <g> { ?s <p> ?o } FILTER(?o != "}") }'
    assert _where_body(text) == ' GRAPH <g> { ?s <p> ?o } FILTER(?o != "}") '
    assert _where_body("SELECT ?x { ?x <p> ?y }") is None, "no WHERE keyword, no body"


def test_an_optional_the_world_leaves_unbound_states_no_premise(monkeypatch):
    """A rule's OPTIONAL the world does not satisfy reads nothing, and the precondition says nothing
    of it. The type lookup that follows the body used to bind such a variable FREELY: with no
    moisture reading in the world, `?was` was unbound after the body, `OPTIONAL { ?was a ?t }`
    bound it to any observation there was — the water butt's — and the precondition of a dose
    said the butt's reading was read. The lookup asks about a stand-in now, the node where
    bound and nothing where not."""
    from orexis_agent_deliberation import signature
    from orexis_agent_progression.ontology import picks_graph
    agent, planner, desire = _thirsty_with_a_nearly_empty_butt(monkeypatch)
    agent.beliefs.update(f"""DELETE {{ GRAPH <{STATE_GRAPH}> {{ ?obs ?p ?o }} }}
        WHERE {{ GRAPH <{STATE_GRAPH}> {{ ?obs <{SOSA}observedProperty> <{MOISTURE}> ; ?p ?o }} }}""")
    keys = signature.keys_of(agent.beliefs.query)
    pump = bindings(agent.beliefs.query(
        f"SELECT ?p WHERE {{ <{agent.me.uri}> actuation:hasActuator ?p }}"))[0]["p"]
    read = effects.precondition(agent.beliefs, ACTUATION + "Dosing", keyed=tuple(keys),
                            me=agent.me.uri, subject=agent.me.acts_for, about=MOISTURE,
                            state=STATE_GRAPH, picks=picks_graph("gardener"), litres=0.1,
                            via=pump, want=desire.uri)
    assert read, "the rule's chain is read"
    typed = [t for t in read if t.predicate.value.endswith("#type")
             and t.object.value == SOSA + "Observation"]
    assert not typed, "no moisture reading stands, so no observation is a premise of the dose"


def test_a_comment_in_a_rule_is_prose_and_not_a_string():
    """The WHERE-body matcher skips strings so a brace inside one does not count; it did not
    skip `#` comments, so an apostrophe in a rule's prose — "the engine's decimal" — opened a
    string that never closed, and the body was None: no precondition, silently, for every step of
    that action, the moment a rule's comments held an odd number of them."""
    text = """CONSTRUCT { ?s ?p ?o } WHERE {
        #  a comment with an apostrophe: the engine's decimal, and a brace { that is prose
        ?s ?p ?o .
        OPTIONAL { ?s <urn:q> ?q }   # and a closing brace in prose: }
    }"""
    body = _where_body(text)
    assert body is not None and "OPTIONAL { ?s <urn:q> ?q }" in body
    assert _where_body("SELECT * WHERE { ?s ?p 'a { brace in a string' }") == " ?s ?p 'a { brace in a string' "
