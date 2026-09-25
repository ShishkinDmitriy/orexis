"""The executor: a plan copied in, what stands, the patience that absorbs the second one — and
the plan carried out, step by step, on two doors a test can drive and two threads that drive them.

A package may test itself where the thing means something alone, and this does: a plan graph
is a handful of quads in execution's own vocabulary, so the executor can be asked the whole of
what it promises without a world, a search or a capability.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta, timezone

import pyoxigraph as ox
import pytest

from agent import clock
from agent.execution.executor import DEFAULT_PATIENCE_S, Executor
from agent.execution.ontology import EXECUTION, intentions_graph
from agent.hash_named_graph import facts_of
from agent.store import bindings, put_graph, query_over, update

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
AGENT, ME = "keeper", "http://example.org/test#keeper"
WANT = "http://example.org/test#want"
PLAN = "http://example.org/test#plan"


@pytest.fixture(autouse=True)
def stopped_clock(monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: NOW)


def a_plan(steps: int = 2) -> ox.Store:
    """A plan of `steps` steps in execution's own words, chained — what the search writes."""
    st = ox.Store()
    chain = "\n".join(
        f'  <{PLAN}.{n}> a execution:Step ; '
        f'execution:partOf <{PLAN}> '
        + (f'; execution:then <{PLAN}.{n + 1}> .' if n + 1 < steps else '.')
        for n in range(steps))
    update(st, f"INSERT DATA {{ GRAPH <{PLAN}> {{\n{chain}\n}} }}")
    return st


def executor(beliefs: ox.Store | None = None, holder: str | None = None, **kw) -> Executor:
    return Executor(beliefs if beliefs is not None else ox.Store(), AGENT, ox.Store(), holder, **kw)


def test_a_committed_plan_stands_at_its_head():
    """The head is the step nothing points `execution:then` at — read off the chain, never
    written twice."""
    k = executor()
    intention = k.commit(a_plan(2), PLAN, WANT)
    assert intention is not None
    (standing,) = k.standing()
    assert standing.want == WANT
    assert standing.at == f"{PLAN}.0", "the intention stands at the head, not at the last step"


def test_every_step_crosses_with_the_plan():
    """A copy and not a rewrite: what execution does not read, it also does not drop."""
    k = executor()
    k.commit(a_plan(3), PLAN, WANT)
    steps = bindings(query_over(
        k.intentions, "SELECT ?s WHERE { ?s a execution:Step }", intentions_graph(AGENT)))
    assert len(steps) == 3, steps


def test_a_second_plan_inside_the_patience_is_absorbed():
    """The amortisation: within your patience, a second impulse to do the same thing is not
    re-decided. One intention stands, not two."""
    k = executor()
    assert k.commit(a_plan(), PLAN, WANT) is not None
    assert k.commit(a_plan(), PLAN, WANT) is None, "a second plan for one want was adopted"
    assert len(k.standing()) == 1


def test_past_the_patience_a_new_plan_supersedes_the_old(monkeypatch):
    """And the old one is recorded as superseded — a commitment abandoned without a reason is
    indistinguishable from one forgotten."""
    k = executor()
    first = k.commit(a_plan(), PLAN, WANT)
    monkeypatch.setattr(clock, "now", lambda: NOW + timedelta(seconds=DEFAULT_PATIENCE_S + 1))
    second = k.commit(a_plan(), PLAN, WANT)
    assert second is not None and second != first
    assert [s.uri for s in k.standing()] == [second], "the superseded one is still standing"
    ended = bindings(query_over(
        k.intentions, f"SELECT ?o WHERE {{ <{first}> <{EXECUTION}outcome> ?o }}",
        intentions_graph(AGENT)))
    assert ended and ended[0]["o"] == "superseded"


def test_a_resolved_commitment_stays_among_the_intentions():
    """Intentions that forgot their resolutions could not answer the only question an operator
    brings to it."""
    k = executor()
    intention = k.commit(a_plan(), PLAN, WANT)
    k.resolve(intention, "done")
    assert k.standing() == []
    kept = bindings(query_over(k.intentions, f"SELECT ?p WHERE {{ <{intention}> ?p ?o }}",
                               intentions_graph(AGENT)))
    assert kept, "the resolved intention was removed rather than resolved"


def test_an_empty_plan_is_an_answer_and_not_a_commitment():
    """The search reached the want's met state in no steps: there is nothing to carry out."""
    assert executor().commit(ox.Store(), PLAN, WANT) is None




# --- carrying a commitment out --------------------------------------------------------------------

_ACTS_Q = """SELECT ?a ?taken ?at ?done WHERE {
  ?a a execution:Act ; execution:taken ?taken ; execution:takenAt ?at ; execution:doneAt ?done } ORDER BY ?a"""


def _acts(x: Executor) -> list[dict]:
    return bindings(query_over(x.intentions, _ACTS_Q, intentions_graph(AGENT)))


def _resolved(x: Executor, intention: str) -> list[dict]:
    return bindings(query_over(x.intentions, f"SELECT ?o WHERE {{ <{intention}> execution:outcome ?o }}",
                               intentions_graph(AGENT)))


def test_a_committed_plan_is_taken_step_by_step_and_resolved_done():
    """One tick hands the head over, one drain takes it and the intention moves to the next
    step; the last step resolves it `done`, and every act is on record."""
    x = executor()
    intention = x.commit(a_plan(2), PLAN, WANT)
    assert x.tick(NOW) == [f"{PLAN}.0"], "the head is due at once where the plan states no instant"
    assert x.tick(NOW) == [], "and handed over once while it is in flight"
    assert x.drain() == 1
    (standing,) = x.standing()
    assert standing.at == f"{PLAN}.1"
    assert x.tick(NOW) == [f"{PLAN}.1"] and x.drain() == 1
    assert x.standing() == [] and _resolved(x, intention) == [{"o": "done"}]
    acts = _acts(x)
    assert [a["taken"] for a in acts] == ["true", "true"]
    assert all(a["done"] >= a["at"] for a in acts), "the act says when it was handed over and when the taker returned"


def test_a_step_waits_for_its_instant():
    """`execution:notBefore` on the head keeps it out of the queue until the timekeeper stands
    at that instant."""
    x = executor()
    source = a_plan(1)
    later = NOW + timedelta(hours=1)
    update(source, f'INSERT DATA {{ GRAPH <{PLAN}> {{ <{PLAN}.0> execution:notBefore '
                   f'"{later.isoformat()}"^^xsd:dateTime }} }}')
    x.commit(source, PLAN, WANT)
    assert x.tick(NOW) == []
    assert x.tick(later) == [f"{PLAN}.0"]


def test_a_step_that_cannot_be_taken_fails_the_intention():
    """The act is recorded as not taken, the intention resolves `failed`, and the executor
    outlives the taker that raised."""
    def refuse(said, intention):
        raise RuntimeError("no valve answers")
    x = executor(take=refuse)
    intention = x.commit(a_plan(2), PLAN, WANT)
    x.tick(NOW)
    assert x.drain() == 1
    assert _resolved(x, intention) == [{"o": "failed"}]
    assert [a["taken"] for a in _acts(x)] == ["false"]
    assert x.standing() == []



def test_what_a_step_says_reaches_the_log(caplog):
    """Taking a step, today, is saying its name and its filling — in the package's words,
    which this layer repeats without reading."""
    x = executor()
    source = a_plan(1)
    update(source, f"INSERT DATA {{ GRAPH <{PLAN}> {{ <{PLAN}.0> <http://example.org/test#disk> "
                   f"<http://example.org/test#disk_1> }} }}")
    x.commit(source, PLAN, WANT)
    with caplog.at_level(logging.INFO, logger="executor"):
        x.tick(NOW)
        x.drain()
    assert any("disk=disk_1" in r.getMessage() and "plan.0" in r.getMessage() for r in caplog.records), \
        [r.getMessage() for r in caplog.records]


def test_the_two_threads_carry_a_plan_out():
    """Started, the timekeeper finds the committed plan and the executing thread takes its
    three steps; stopped, both threads are gone and the intention says `done`."""
    x = executor(poll_s=0.05)
    x.start()
    try:
        intention = x.commit(a_plan(3), PLAN, WANT)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not _resolved(x, intention):
            time.sleep(0.02)
    finally:
        x.stop()
    assert _resolved(x, intention) == [{"o": "done"}]
    assert len(_acts(x)) == 3


# --- the world answers, or it does not --------------------------------------------------------

STATE = "http://example.org/test#sensed"
DISK, ON, PEG_A, PEG_B = ("http://example.org/test#disk_1", "http://example.org/test#on",
                          "http://example.org/test#PegA", "http://example.org/test#PegB")


def _beliefs(on: str) -> ox.Store:
    """A belief base whose one reading says where the disk is, with the catalogue that says
    the graph is the state."""
    st = ox.Store()
    put_graph(st, "http://example.org/test#world", f"""
@prefix orexis: <http://example.org/orexis#> .
GRAPH <{STATE}> {{ <{DISK}> <{ON}> <{on}> }}
GRAPH <http://example.org/test#catalogue> {{
  <http://example.org/test#catalogue> a orexis:CatalogueGraph .
  <{STATE}> a orexis:StateGraph }}""", dataset=True)
    return st


def _predicting(steps: int = 1) -> ox.Store:
    """A plan whose first step predicts the disk moving from A to B, in the canonical facts a
    world's digest is made of, and lands at NOW."""
    source = a_plan(steps)
    (before,) = facts_of(_beliefs(PEG_A), STATE)
    (after,) = facts_of(_beliefs(PEG_B), STATE)
    predicts = json.dumps({"adds": [after], "retracts": [before]})
    update(source, f"""INSERT DATA {{ GRAPH <{PLAN}> {{ <{PLAN}.0> execution:predicts {json.dumps(predicts)} ;
                                                       execution:landsAt "{NOW.isoformat()}"^^xsd:dateTime }} }}""")
    return source


def test_a_step_that_predicts_something_waits_for_the_world_to_answer():
    """Taken, the step stays the head until the present holds what it predicted; when the
    reading says the disk is on B, the intention moves on."""
    beliefs = _beliefs(PEG_A)
    x = Executor(beliefs, AGENT, ox.Store())
    intention = x.commit(_predicting(2), PLAN, WANT)
    x.tick(NOW)
    assert x.drain() == 1
    (standing,) = x.standing()
    assert standing.at == f"{PLAN}.0", "taken, and still the head: the world has not answered"
    assert x.tick(NOW) == [] and x.standing()[0].at == f"{PLAN}.0"
    update(beliefs, f"DELETE DATA {{ GRAPH <{STATE}> {{ <{DISK}> <{ON}> <{PEG_A}> }} }} ; "
                    f"INSERT DATA {{ GRAPH <{STATE}> {{ <{DISK}> <{ON}> <{PEG_B}> }} }}")
    assert x.tick(NOW) == [] and x.standing()[0].at == f"{PLAN}.1", "the world answered: the intention moved"
    assert x.tick(NOW) == [f"{PLAN}.1"], "and the next head is due on the pass after"
    assert _resolved(x, intention) == []


def test_a_step_predicting_a_side_is_answered_by_the_readings_revision():
    """A step speaks the concept the rules conclude — the soil comes to be inside its range — and
    the side lives in the graph derived from the reading's. A new reading alone answers nothing;
    once the rules conclude `inside` of it, in the revision graph the catalogue says was derived
    from the state, the intention moves on."""
    soil, bed_range = "http://example.org/test#soil", "http://example.org/test#bed_operating"
    below, inside = ("http://example.org/orexis/sensing#below", "http://example.org/orexis/sensing#inside")
    revisions = STATE + "/revisions"
    beliefs = _beliefs(PEG_A)
    update(beliefs, f"""INSERT DATA {{ GRAPH <{revisions}> {{ <{soil}> <{below}> <{bed_range}> }}
        GRAPH <http://example.org/test#catalogue> {{ <{revisions}> <http://www.w3.org/ns/prov#wasDerivedFrom> <{STATE}> ; a <http://example.org/orexis#BeliefGraph> }} }}""")
    source = a_plan(2)
    def fact(side):
        one = ox.Store()
        update(one, f"INSERT DATA {{ GRAPH <{revisions}> {{ <{soil}> <{side}> <{bed_range}> }} }}")
        (said,) = facts_of(one, revisions)
        return said
    predicts = json.dumps({"adds": [fact(inside)], "retracts": [fact(below)]})
    update(source, f"""INSERT DATA {{ GRAPH <{PLAN}> {{ <{PLAN}.0> execution:predicts {json.dumps(predicts)} ;
                                                       execution:landsAt "{NOW.isoformat()}"^^xsd:dateTime }} }}""")
    x = Executor(beliefs, AGENT, ox.Store())
    x.commit(source, PLAN, WANT)
    x.tick(NOW)
    assert x.drain() == 1
    assert x.tick(NOW) == [] and x.standing()[0].at == f"{PLAN}.0", "still below: the world has not answered"
    update(beliefs, f"DELETE DATA {{ GRAPH <{revisions}> {{ <{soil}> <{below}> <{bed_range}> }} }} ; "
                    f"INSERT DATA {{ GRAPH <{revisions}> {{ <{soil}> <{inside}> <{bed_range}> }} }}")
    assert x.tick(NOW) == [] and x.standing()[0].at == f"{PLAN}.1", "revised inside: the intention moved"


def test_a_step_of_a_fictive_action_is_taken_by_the_executor_itself():
    """The action's row says fictive and the step carries it; a plain executor writes the
    prediction into the readings for that step and holds every other step to the world."""
    beliefs = _beliefs(PEG_A)
    x = Executor(beliefs, AGENT, ox.Store())
    source = _predicting(1)
    update(source, f"INSERT DATA {{ GRAPH <{PLAN}> {{ <{PLAN}.0> execution:fictive true }} }}")
    intention = x.commit(source, PLAN, WANT)
    x.tick(NOW)
    x.drain()
    (where,) = bindings(query_over(beliefs, f"SELECT ?on WHERE {{ <{DISK}> <{ON}> ?on }}", STATE))
    assert where["on"] == PEG_B
    x.tick(NOW)
    assert _resolved(x, intention) == [{"o": "done"}]


def test_a_fictive_executor_is_the_world_of_its_own_steps():
    """Taking a step writes what it predicted into the readings, so the very next pass finds
    the world answered: hanoi has no instrument, and the step's prediction is its physics."""
    beliefs = _beliefs(PEG_A)
    x = Executor(beliefs, AGENT, ox.Store(), fictive=True)
    intention = x.commit(_predicting(1), PLAN, WANT)
    x.tick(NOW)
    x.drain()
    (where,) = bindings(query_over(beliefs, f"SELECT ?on WHERE {{ <{DISK}> <{ON}> ?on }}", STATE))
    assert where["on"] == PEG_B, "the executor moved the disk, since nothing else could"
    x.tick(NOW)
    assert _resolved(x, intention) == [{"o": "done"}]


def test_a_world_that_does_not_answer_by_the_patience_fails_the_intention():
    """Past the landing by the patience with the reading unchanged, the step is unmet and the
    intention resolves `failed`; before that it merely waits."""
    x = Executor(_beliefs(PEG_A), AGENT, ox.Store())
    intention = x.commit(_predicting(1), PLAN, WANT)
    x.tick(NOW)
    x.drain()
    x.tick(NOW + timedelta(seconds=DEFAULT_PATIENCE_S - 1))
    assert _resolved(x, intention) == [] and len(x.standing()) == 1
    x.tick(NOW + timedelta(seconds=DEFAULT_PATIENCE_S))
    assert _resolved(x, intention) == [{"o": "failed"}]


def test_a_step_is_not_held_to_the_world_before_it_lands():
    """The landing is when the prediction is first asked of the present: a reading that
    already says B before the landing is not read as the step having landed."""
    x = Executor(_beliefs(PEG_B), AGENT, ox.Store())
    source = _predicting(1)
    later = NOW + timedelta(hours=1)
    update(source, f'DELETE {{ GRAPH <{PLAN}> {{ <{PLAN}.0> execution:landsAt ?t }} }} '
                   f'INSERT {{ GRAPH <{PLAN}> {{ <{PLAN}.0> execution:landsAt "{later.isoformat()}"^^xsd:dateTime }} }} '
                   f'WHERE {{ GRAPH <{PLAN}> {{ <{PLAN}.0> execution:landsAt ?t }} }}')
    intention = x.commit(source, PLAN, WANT)
    x.tick(NOW)
    x.drain()
    x.tick(NOW)
    assert _resolved(x, intention) == [], "not yet landed, so not yet asked"
    x.tick(later)
    assert _resolved(x, intention) == [{"o": "done"}]
