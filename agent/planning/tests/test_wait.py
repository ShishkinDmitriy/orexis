"""The search may let the world move (#920): `planning:Wait`, the planning package's own action, booted
into every agent from `agent/planning/wait.ttl` and imported by no world.

A world written for the case and booted as an agent boots it, so what is held is what every agent
gets: the package's document read, the wait put in every scope by `scope_actions`, admitted by
`admit` where a later ground is laid and taken by `take` into that ground. One tank, its floor at ten
and reading four; a fill adding six from the water butt, admitted only while the butt holds water,
costing one and landing at once; and what is predicted, laid as a prediction the agent received.

- RAIN FILLS THE EMPTY BUTT half a minute on: nothing can be done now, so the plan WAITS for the rain
  and THEN fills — a tenth and one;
- THE TANK IS REFILLED by a prediction half a minute on, the butt full: the fill is admitted now and
  costs one, and waiting costs a tenth, so the plan is the wait alone;
- NOTHING IS PREDICTED, the butt full: one ground, so no wait is admitted at all and the plan is the
  fill; and with the butt empty there is nothing to do and nothing to wait for, which is the answer
  "no candidate" as it was.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from agent import clock
from agent.execution.executor import Executor
from agent.ontology import OREXIS, PREDICTION
from agent.planning.planner import Planner
from agent.runtime import boot
from agent.store import catalogue_of, entry, rows, update

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
T = "http://example.org/test#"
PLANNING = "http://example.org/orexis/planning#"
WAIT = PLANNING + "Wait"

_HEAD = """@prefix : <http://example.org/test#> .
@prefix orexis: <http://example.org/orexis#> .
@prefix planning: <http://example.org/orexis/planning#> .
@prefix belief: <http://example.org/orexis/belief#> .
@prefix execution: <http://example.org/orexis/execution#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
"""
_WORLD = _HEAD + """<> a orexis:WorldGraph .
:keeper a orexis:Agent ; orexis:localId "keeper" .
:tank1 a :Tank .
:butt a :Butt .
"""
#  THE FILL: from the butt while it holds water, six more in the tank, costing one and landing at once.
_ACTIONS = _HEAD + '''<> a orexis:ActionGraph .
:fill a orexis:Action ;
    orexis:takes :tank ;
    execution:implementation [ a execution:Implementation ; execution:operation [ a execution:Fictive ] ] ;
    planning:precondition """PREFIX : <http://example.org/test#>
        SELECT ?tank WHERE { ?tank a :Tank ; :level ?l . FILTER(?l < 10) :butt :holds ?w . FILTER(?w > 0) }""" ;
    planning:costs """SELECT ?cost WHERE { BIND(1.0 AS ?cost) }""" ;
    planning:effect [ a planning:Effect ;
        sh:rule [ a sh:SPARQLRule ; belief:delete """PREFIX : <http://example.org/test#>
        DELETE { $tank :level ?l } WHERE { $tank :level ?l }""" ] ,
                [ a sh:SPARQLRule ; sh:construct """PREFIX : <http://example.org/test#>
        CONSTRUCT { $tank :level ?next } WHERE { $tank :level ?l . BIND(?l + 6 AS ?next) }""" ] ] .
'''
_DESIRES = _HEAD + """<> a planning:DesireGraph ; orexis:beliefsOf :keeper .
:keeper planning:holds :full .
:full a planning:Desire ; planning:about :level ; planning:metWhen :at_least_ten .
:at_least_ten a sh:NodeShape ; sh:targetClass :Tank ;
    sh:property [ planning:about :level ; sh:path :level ; sh:minInclusive 10 ] .
"""
#  WHAT IS PREDICTED half a minute on, as (graph, what it adds, what it retracts).
RAIN = ("rain", f"<{T}butt> <{T}holds> 1 .", f"<{T}butt> <{T}holds> ?w")
REFILL = ("refill", f"<{T}tank1> <{T}level> 12 .", f"<{T}tank1> <{T}level> ?l")

_STEPS_Q = """
SELECT ?a ?nb ?la ?spent WHERE { GRAPH ?p { ?p a planning:Plan ; planning:spent ?spent .
  ?s a execution:Step ; planning:fills ?a ; execution:notBefore ?nb ; execution:landsAt ?la } }
ORDER BY ?la ?nb"""
_OUTCOME_Q = "SELECT ?o WHERE { GRAPH ?p { ?p a planning:Plan ; planning:outcome ?o } }"
_ADMITTED_Q = """
SELECT (COUNT(?c) AS ?n) WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?c a planning:Candidate ; planning:fills $wait } }"""
_IN_SCOPE_Q = "SELECT ?s WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a planning:ScopeGraph } GRAPH ?g { $wait planning:inScope ?s } }"
_SCOPES_Q = "SELECT ?s WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a planning:ScopeGraph } GRAPH ?g { ?s a planning:Scope } }"
_PREDICTED_Q = """
SELECT ?g WHERE { GRAPH ?p { ?step a execution:Step ; execution:adds|execution:retracts ?g } GRAPH ?g { ?s ?pr ?o } }"""
_OUTCOMES_Q = "SELECT ?o WHERE { GRAPH ?g { ?i a execution:Intention ; execution:outcome ?o } }"


def _tank(tmp_path, butt: int, *predicted):
    """The tank's world booted as the keeper, with what is `predicted` laid half a minute on."""
    (tmp_path / "beliefs").mkdir()
    (tmp_path / "world.ttl").write_text(_WORLD)
    (tmp_path / "actions.ttl").write_text(_ACTIONS)
    (tmp_path / "state.ttl").write_text(_HEAD + "<> a orexis:StateGraph ; orexis:beliefsOf :keeper .\n"
                                        f":tank1 :level 4 .\n:butt :holds {butt} .\n")
    (tmp_path / "beliefs" / "keeper.ttl").write_text(_DESIRES)
    (tmp_path / "beliefs" / "keeper.self.ttl").write_text(_HEAD + "<> a orexis:SelfGraph .\n"
                                                              ":keeper a orexis:Self , planning:Planner , execution:Executor .\n")
    beliefs = boot(tmp_path, "keeper")
    for name, adds, retracts in predicted:
        graph = f"{T}{name}"
        update(beliefs, f"""INSERT DATA {{ GRAPH <{graph}> {{ {adds} }}
  {entry(beliefs, graph, PREDICTION, OREXIS + "Received", start=NOW + timedelta(seconds=30))}
  GRAPH <{catalogue_of(beliefs)}> {{ <{graph}> orexis:retracts "DELETE {{ GRAPH $state {{ {retracts} }} }} WHERE {{ GRAPH $state {{ {retracts} }} }}" }} }}""")
    return beliefs


def _planned(beliefs):
    planner = Planner(beliefs, "keeper")
    planner.plan(NOW)
    (im,) = planner.imaginaria.values()
    steps = [(r["a"].rsplit("#", 1)[-1], (datetime.fromisoformat(r["nb"]) - NOW).total_seconds(),
              (datetime.fromisoformat(r["la"]) - NOW).total_seconds()) for r in rows(im, _STEPS_Q, ())]
    spent = {float(r["spent"]) for r in rows(im, _STEPS_Q, ())}
    (outcome,) = [r["o"].rsplit("#", 1)[-1] for r in rows(im, _OUTCOME_Q, ())]
    admitted = int(rows(im, _ADMITTED_Q, (), wait=WAIT)[0]["n"])
    return planner, im, outcome, steps, spent, admitted


@pytest.fixture(autouse=True)
def _at_noon(monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: NOW)


def test_every_agent_holds_the_wait_in_every_scope(tmp_path):
    """Booted from a world that names no wait: the package's document put it among the actions, and
    `scope_actions` wrote it into every scope though it touches no atom."""
    beliefs = _tank(tmp_path, 1)
    scopes = {r["s"] for r in rows(beliefs, _SCOPES_Q, ())}
    assert scopes and {r["s"] for r in rows(beliefs, _IN_SCOPE_Q, (), wait=WAIT)} == scopes


def test_rain_filling_the_butt_is_waited_for_and_then_the_tank_is_filled(tmp_path):
    """WAIT, THEN ACT. The butt is empty, so nothing is admitted now but the wait; it lands where the
    rain's ground begins, half a minute on, and there the fill is admitted and meets the want."""
    _, _, outcome, steps, spent, admitted = _planned(_tank(tmp_path, 0, RAIN))
    assert outcome == "Satisfied"
    assert steps == [("Wait", 0, 30), ("fill", 30, 30)], steps
    assert spent == {1.1}, "a tenth for the wait and one for the fill"
    assert admitted == 1, "one wait, from the present: the rain's is the last ground"


def test_a_tank_a_prediction_refills_is_met_by_waiting_and_not_by_a_dearer_fill(tmp_path):
    """The fill is admitted now and would meet the want at one; the wait meets it at a tenth, in the
    ground where the refill has landed. Its step predicts nothing — the refill is not its to predict
    (#919) — and, taken with no implementation, sends nothing and is answered at its landing."""
    beliefs = _tank(tmp_path, 1, REFILL)
    planner, im, outcome, steps, spent, admitted = _planned(beliefs)
    assert outcome == "Satisfied"
    assert steps == [("Wait", 0, 30)], steps
    assert spent == {0.1}
    assert rows(im, _PREDICTED_Q, ()) == [], "a wait predicts nothing"
    executor = Executor(beliefs, "keeper")
    executor.commit_plans()
    assert executor.walk(NOW) == 1, "taken: nothing to send, and nothing refused"
    for at, outcomes in ((NOW + timedelta(seconds=29), []), (NOW + timedelta(seconds=30), ["done"])):
        executor.walk(at)
        assert [r["o"] for r in rows(beliefs, _OUTCOMES_Q, ())] == outcomes, at


def test_with_nothing_predicted_no_wait_is_admitted(tmp_path):
    """One ground: there is nothing to wait for, so the fill is the plan and no wait was a candidate —
    and with the butt empty too, nothing is a candidate at all, the answer that asks to be equipped."""
    _, _, outcome, steps, spent, admitted = _planned(_tank(tmp_path, 1))
    assert (outcome, steps, spent, admitted) == ("Satisfied", [("fill", 0, 0)], {1.0}, 0)
    (tmp_path / "dry").mkdir()
    _, _, outcome, steps, _, admitted = _planned(_tank(tmp_path / "dry", 0))
    assert (outcome, steps, admitted) == ("NoCandidate", [], 0)
