"""The executor: a plan copied in, what stands, the patience that absorbs the second one — and
the plan carried out, step by step, on two doors a test can drive and two threads that drive them.

A package may test itself where the thing means something alone, and this does: a plan graph
is a handful of quads in execution's own vocabulary, so the executor can be asked the whole of
what it promises without a world, a search or a capability.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone

import pyoxigraph as ox
import pytest

from agent import clock
from agent.execution.executor import DEFAULT_PATIENCE_S, Executor
from agent.execution.ontology import EXECUTION, PATIENCE_S, intentions_graph
from agent.store import bindings, put_graph, query_over, rows, update

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
AGENT, ME = "keeper", "http://example.org/test#keeper"
WANT = "http://example.org/test#want"
PLAN = "http://example.org/test#plan"


@pytest.fixture(autouse=True)
def stopped_clock(monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: NOW)


def a_plan(steps: int = 2, plan: str = PLAN) -> ox.Store:
    """A plan of `steps` steps in execution's own words, chained — what the search writes."""
    st = ox.Store()
    chain = "\n".join(
        f'  <{plan}.{n}> a execution:Step ; '
        f'execution:partOf <{plan}> '
        + (f'; execution:then <{plan}.{n + 1}> .' if n + 1 < steps else '.')
        for n in range(steps))
    update(st, f"INSERT DATA {{ GRAPH <{plan}> {{\n{chain}\n}} }}")
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


def test_a_plan_from_another_store_is_brought_in_whole_and_adopted_by_reference():
    """The intention refers to the plan and holds only its own rows; a plan found in a store of its
    own — a case's — is brought in whole under its own name first, so the reference reaches it."""
    k = executor()
    intention = k.commit(a_plan(3), PLAN, WANT)
    steps = bindings(query_over(k.intentions, "SELECT ?s WHERE { ?s a execution:Step }", PLAN))
    assert len(steps) == 3, steps
    own = bindings(query_over(k.intentions, "SELECT ?s WHERE { ?s a execution:Step }", intentions_graph(AGENT)))
    assert own == [], "no step is copied into the intentions"
    adopts = bindings(query_over(k.intentions, f"SELECT ?p WHERE {{ <{intention}> execution:adopts ?p }}", intentions_graph(AGENT)))
    assert adopts == [{"p": PLAN}]


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


def predicting(source: ox.Store, step: str, adds: str, retracts: str, plan: str = PLAN) -> ox.Store:
    """`source`, its `step` predicting the triples of `adds` gained and those of `retracts` lost —
    each a Turtle-ish `s p o` text — in the two graphs a step names, as the extraction writes them."""
    update(source, f"""INSERT DATA {{
  GRAPH <{plan}> {{ <{step}> execution:adds <{step}.adds> ; execution:retracts <{step}.retracts> }}
  GRAPH <{step}.adds> {{ {adds} }}
  GRAPH <{step}.retracts> {{ {retracts} }} }}""")
    return source


def _predicting(steps: int = 1, plan: str = PLAN) -> ox.Store:
    """A plan whose first step predicts the disk moving from A to B, in the two graphs a step
    names, and lands at NOW."""
    source = predicting(a_plan(steps, plan), f"{plan}.0", f"<{DISK}> <{ON}> <{PEG_B}>", f"<{DISK}> <{ON}> <{PEG_A}>", plan)
    update(source, f"""INSERT DATA {{ GRAPH <{plan}> {{ <{plan}.0> execution:landsAt "{NOW.isoformat()}"^^xsd:dateTime }} }}""")
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
    source = predicting(a_plan(2), f"{PLAN}.0", f"<{soil}> <{inside}> <{bed_range}>", f"<{soil}> <{below}> <{bed_range}>")
    update(source, f"""INSERT DATA {{ GRAPH <{PLAN}> {{ <{PLAN}.0> execution:landsAt "{NOW.isoformat()}"^^xsd:dateTime }} }}""")
    x = Executor(beliefs, AGENT, ox.Store())
    x.commit(source, PLAN, WANT)
    x.tick(NOW)
    assert x.drain() == 1
    assert x.tick(NOW) == [] and x.standing()[0].at == f"{PLAN}.0", "still below: the world has not answered"
    update(beliefs, f"DELETE DATA {{ GRAPH <{revisions}> {{ <{soil}> <{below}> <{bed_range}> }} }} ; "
                    f"INSERT DATA {{ GRAPH <{revisions}> {{ <{soil}> <{inside}> <{bed_range}> }} }}")
    assert x.tick(NOW) == [] and x.standing()[0].at == f"{PLAN}.1", "revised inside: the intention moved"


def test_a_step_of_a_fictive_action_is_taken_by_the_executor_itself():
    """The action the step fills is fictive — its implementation says so — and a plain executor
    writes the prediction into the readings for that step and holds every other step to the
    world."""
    beliefs = _beliefs(PEG_A)
    move = "http://example.org/test#Move"
    update(beliefs, f"""INSERT DATA {{
  GRAPH <http://example.org/test#actions> {{ <{move}> a orexis:Action ;
      execution:implementation [ execution:operation [ a execution:Fictive ] ] }}
  GRAPH <http://example.org/test#catalogue> {{ <http://example.org/test#actions> a orexis:ActionGraph }} }}""")
    x = Executor(beliefs, AGENT, ox.Store())
    source = _predicting(1)
    update(source, f"INSERT DATA {{ GRAPH <{PLAN}> {{ <{PLAN}.0> <http://example.org/orexis/planning#fills> <{move}> }} }}")
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


def test_the_patience_is_the_agents_stance_where_its_self_graph_states_one(snapshots):
    """`execution:patienceS 5` in the keeper's self graph (knowledge/domain/kernel/stance.md): a step
    unanswered five seconds past its landing fails, where the default would have waited a minute.
    With none stated, the default holds."""
    assert Executor(_beliefs(PEG_A), AGENT, ox.Store()).patience_s == DEFAULT_PATIENCE_S
    x = Executor(snapshots.stating(_beliefs(PEG_A), {PATIENCE_S: 5}), AGENT, ox.Store())
    assert x.patience_s == 5.0
    intention = x.commit(_predicting(1), PLAN, WANT)
    x.tick(NOW)
    x.drain()
    x.tick(NOW + timedelta(seconds=4))
    assert _resolved(x, intention) == [] and len(x.standing()) == 1
    x.tick(NOW + timedelta(seconds=5))
    assert _resolved(x, intention) == [{"o": "failed"}]


def test_the_patience_runs_from_the_latest_landing_where_the_plan_states_one():
    """A step whose landing is a band — `landsAt` the earliest, `notAfter` the latest (#596) — is
    looked at from the earliest and given up a patience past the latest, not past the earliest: a
    dose the sensor may show any time within a cadence is not failed a minute into it."""
    x = Executor(_beliefs(PEG_A), AGENT, ox.Store())
    source = _predicting(1)
    latest = NOW + timedelta(minutes=10)
    update(source, f'INSERT DATA {{ GRAPH <{PLAN}> {{ <{PLAN}.0> execution:notAfter "{latest.isoformat()}"^^xsd:dateTime }} }}')
    intention = x.commit(source, PLAN, WANT)
    x.tick(NOW)
    x.drain()
    x.tick(NOW + timedelta(seconds=DEFAULT_PATIENCE_S))
    assert _resolved(x, intention) == [] and len(x.standing()) == 1, "a patience past the earliest is still inside the band"
    x.tick(latest + timedelta(seconds=DEFAULT_PATIENCE_S - 1))
    assert _resolved(x, intention) == []
    x.tick(latest + timedelta(seconds=DEFAULT_PATIENCE_S))
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


def test_a_step_taken_late_lands_late_by_as_much(monkeypatch):
    """A plan places a step at the instants of the worlds it searched; taken a hundred seconds
    after its opening — the step before it waited on a peer — it lands a hundred seconds after
    its placed landing, and the patience runs from there."""
    x = Executor(_beliefs(PEG_A), AGENT, ox.Store())
    source = _predicting(1)
    update(source, f"""INSERT DATA {{ GRAPH <{PLAN}> {{ <{PLAN}.0> execution:notBefore "{NOW.isoformat()}"^^xsd:dateTime }} }}""")
    intention = x.commit(source, PLAN, WANT)
    late = NOW + timedelta(seconds=100)
    monkeypatch.setattr(clock, "now", lambda: late)
    x.tick(late)
    x.drain()
    x.tick(late + timedelta(seconds=DEFAULT_PATIENCE_S - 1))
    assert _resolved(x, intention) == [], "held to the landing it was placed at, it would have failed already"
    x.tick(late + timedelta(seconds=DEFAULT_PATIENCE_S))
    assert _resolved(x, intention) == [{"o": "failed"}]


def test_a_second_plan_for_a_want_is_walked_by_steps_of_its_own(monkeypatch):
    """The first plan's step was taken and failed; the second, found for the same want, is published
    under a name of its own, as planning publishes every plan, and so are its steps. Its head is its
    own and due, not the first's taken step waiting."""
    x = Executor(_beliefs(PEG_A), AGENT, ox.Store())
    first = x.commit(_predicting(1), PLAN, WANT)
    x.tick(NOW)
    x.drain()
    x.tick(NOW + timedelta(seconds=DEFAULT_PATIENCE_S))
    assert _resolved(x, first) == [{"o": "failed"}]
    second = x.commit(_predicting(1, PLAN + "2"), PLAN + "2", WANT)
    (standing,) = x.standing()
    assert standing.uri == second and standing.at == f"{PLAN}2.0"
    assert x.tick(NOW + timedelta(seconds=DEFAULT_PATIENCE_S)) == [standing.at], "due, since it was never taken"


#  THE COMMITTED STEPS, as beliefs over their landing windows (#849).
COMMITTED = EXECUTION + "CommittedStepGraph"
_WINDOWS_Q = """
SELECT ?g ?start ?end WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a $kind ; dcterms:temporal ?p .
  ?p orexis:start ?start ; orexis:end ?end } } ORDER BY ?g"""


def _windows(beliefs: ox.Store) -> list[tuple[str, datetime, datetime]]:
    return [(r["g"], datetime.fromisoformat(r["start"]), datetime.fromisoformat(r["end"]))
            for r in rows(beliefs, _WINDOWS_Q, (), kind=COMMITTED)]


def _placed(plan: ox.Store) -> ox.Store:
    """The first step placed: due in five minutes, landing a quarter past, filling a disk."""
    update(plan, f"""INSERT DATA {{ GRAPH <{PLAN}> {{
      <{PLAN}.0> execution:notBefore "{(NOW + timedelta(minutes=5)).isoformat()}"^^xsd:dateTime ;
                 execution:landsAt "{(NOW + timedelta(minutes=15)).isoformat()}"^^xsd:dateTime ;
                 <http://example.org/test#disk> <{DISK}> }} }}""")
    return plan


def test_a_committed_steps_window_closes_a_patience_past_its_latest_landing():
    """Where the plan states a latest landing, the window a committed step is believed over runs to
    it and the patience past it, and `execution:answeredWithinS` says so, while `landsWithinS` stays
    the earliest — the two numbers a drift's high and low trajectories are divided by (#596)."""
    beliefs = _beliefs(PEG_A)
    plan = _placed(_predicting(1))
    update(plan, f"""INSERT DATA {{ GRAPH <{PLAN}> {{
      <{PLAN}.0> execution:notAfter "{(NOW + timedelta(minutes=25)).isoformat()}"^^xsd:dateTime }} }}""")
    Executor(beliefs, AGENT, ox.Store()).commit(plan, PLAN, WANT)
    [(first, start, end)] = _windows(beliefs)
    assert (start, end) == (NOW + timedelta(minutes=5), NOW + timedelta(minutes=25, seconds=DEFAULT_PATIENCE_S))
    held = {(r["p"], r["o"]) for r in rows(beliefs, "SELECT ?p ?o WHERE { GRAPH $g { ?s ?p ?o } }", (), g=first)}
    assert (EXECUTION + "landsWithinS", "600") in held and (EXECUTION + "answeredWithinS", "1260") in held


def test_a_committed_step_is_a_belief_over_its_landing_window():
    """Adopted, every step stands in the beliefs as a graph of its own, holding from the step's
    opening to its landing plus the patience, carrying its filling as the plan states it and the
    window's two lengths in seconds — never the step's prediction, which is the plan's — and each
    is said to whoever hears a belief written. A step placed at no instant opens at the adoption and
    lands as it is taken, so its window is the patience alone."""
    beliefs, told = _beliefs(PEG_A), []
    x = Executor(beliefs, AGENT, ox.Store(), on_write=told.append)
    x.commit(_placed(_predicting(2)), PLAN, WANT)
    windows = _windows(beliefs)
    assert [(s, e) for _, s, e in windows] == [
        (NOW + timedelta(minutes=5), NOW + timedelta(minutes=15, seconds=DEFAULT_PATIENCE_S)),
        (NOW, NOW + timedelta(seconds=DEFAULT_PATIENCE_S))]
    assert told == [g for g, _, _ in windows], "each window is said as it is written"
    (first, _, _) = windows[0]
    held = {(r["p"], r["o"]) for r in rows(beliefs, "SELECT ?p ?o WHERE { GRAPH $g { ?s ?p ?o } }", (), g=first)}
    assert (EXECUTION + "landsWithinS", "600") in held and (EXECUTION + "answeredWithinS", "660") in held
    assert ("http://example.org/test#disk", DISK) in held, "the filling, copied as the plan states it"
    assert not any(p in (EXECUTION + "adds", EXECUTION + "retracts") for p, _ in held), "the prediction stays the plan's"
    assert ("http://www.w3.org/1999/02/22-rdf-syntax-ns#type", EXECUTION + "Step") in held


def test_a_window_closes_when_the_world_answers_and_an_ended_one_is_swept():
    """The world answers the taken step: its window closes at that instant, said as a belief
    written, and the next tick forgets what has ended; the step behind it stands untouched."""
    beliefs, told = _beliefs(PEG_A), []
    x = Executor(beliefs, AGENT, ox.Store(), on_write=told.append)
    x.commit(_predicting(2), PLAN, WANT)
    assert len(_windows(beliefs)) == 2 and len(told) == 2
    x.tick(NOW)
    x.drain()
    update(beliefs, f"DELETE DATA {{ GRAPH <{STATE}> {{ <{DISK}> <{ON}> <{PEG_A}> }} }} ; "
                    f"INSERT DATA {{ GRAPH <{STATE}> {{ <{DISK}> <{ON}> <{PEG_B}> }} }}")
    at = NOW + timedelta(seconds=10)
    x.tick(at)
    assert x.standing()[0].at == f"{PLAN}.1", "answered"
    (closed,) = [(g, e) for g, _, e in _windows(beliefs) if g.endswith("plan_0")]
    assert closed[1] == at, "closed at the instant the world answered"
    assert told[-1] == closed[0], "and said"
    x.tick(at + timedelta(seconds=1))
    assert [g for g, _, _ in _windows(beliefs)] == [g for g in told[:2] if g.endswith("plan_1")], "swept; the next step's stands"


def test_an_intention_that_ends_closes_every_window_it_opened():
    """Superseded, failed or abandoned, nothing of the intention flows on: every step's window
    closes now, the untaken ones with their whole stretch ahead, and a tick sweeps them."""
    beliefs, told = _beliefs(PEG_A), []
    x = Executor(beliefs, AGENT, ox.Store(), on_write=told.append)
    intention = x.commit(_placed(_predicting(2)), PLAN, WANT)
    x.resolve(intention, "superseded")
    assert [e for _, _, e in _windows(beliefs)] == [NOW, NOW], "both closed at the resolution"
    assert len(told) == 4, "written twice, closed twice"
    x.tick(NOW)
    assert _windows(beliefs) == []
