"""The ledger: a plan copied in, what stands, and the patience that absorbs the second one.

A package may test itself where the thing means something alone, and this does: a plan graph
is a handful of quads in the ledger's own vocabulary, so the keeper can be asked the whole of
what it promises without a world, a search or a capability.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pyoxigraph as ox
import pytest

from orexis.agent import clock
from orexis.agent.execution.keeper import DEFAULT_PATIENCE_S, Keeper
from orexis.agent.execution.ontology import EXECUTION, intentions_graph
from orexis.agent.store import bindings, query_over, update

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
AGENT, ME = "keeper", "http://example.org/test#keeper"
WANT = "http://example.org/test#want"
PLAN = "http://example.org/test#plan"


@pytest.fixture(autouse=True)
def stopped_clock(monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: NOW)


def a_plan(steps: int = 2) -> ox.Store:
    """A plan of `steps` steps in the ledger's own words, chained — what the search writes."""
    st = ox.Store()
    chain = "\n".join(
        f'  <{PLAN}.{n}> a execution:Step ; execution:fills <http://example.org/test#fill> ; '
        f'execution:partOf <{PLAN}> '
        + (f'; execution:then <{PLAN}.{n + 1}> .' if n + 1 < steps else '.')
        for n in range(steps))
    update(st, f"INSERT DATA {{ GRAPH <{PLAN}> {{\n{chain}\n}} }}")
    return st


def keeper(beliefs: ox.Store | None = None, holder: str | None = None) -> Keeper:
    return Keeper(ox.Store(), beliefs if beliefs is not None else ox.Store(), AGENT, holder)


def test_a_committed_plan_stands_at_its_head():
    """The head is the step nothing points `execution:then` at — read off the chain, never
    written twice."""
    k = keeper()
    intention = k.commit(a_plan(2), PLAN, WANT)
    assert intention is not None
    (standing,) = k.standing()
    assert standing.want == WANT
    assert standing.at == f"{PLAN}.0", "the ledger stands at the head, not at the last step"


def test_every_step_crosses_with_the_plan():
    """A copy and not a rewrite: what the ledger does not read, it also does not drop."""
    k = keeper()
    k.commit(a_plan(3), PLAN, WANT)
    steps = bindings(query_over(
        k.intentions, "SELECT ?s WHERE { ?s a execution:Step }", intentions_graph(AGENT)))
    assert len(steps) == 3, steps


def test_a_second_plan_inside_the_patience_is_absorbed():
    """The amortisation: within your patience, a second impulse to do the same thing is not
    re-decided. One intention stands, not two."""
    k = keeper()
    assert k.commit(a_plan(), PLAN, WANT) is not None
    assert k.commit(a_plan(), PLAN, WANT) is None, "a second plan for one want was adopted"
    assert len(k.standing()) == 1


def test_past_the_patience_a_new_plan_supersedes_the_old(monkeypatch):
    """And the old one is recorded as superseded — a commitment abandoned without a reason is
    indistinguishable from one forgotten."""
    k = keeper()
    first = k.commit(a_plan(), PLAN, WANT)
    monkeypatch.setattr(clock, "now", lambda: NOW + timedelta(seconds=DEFAULT_PATIENCE_S + 1))
    second = k.commit(a_plan(), PLAN, WANT)
    assert second is not None and second != first
    assert [s.uri for s in k.standing()] == [second], "the superseded one is still standing"
    ended = bindings(query_over(
        k.intentions, f"SELECT ?o WHERE {{ <{first}> <{EXECUTION}outcome> ?o }}",
        intentions_graph(AGENT)))
    assert ended and ended[0]["o"] == "superseded"


def test_a_resolved_commitment_stays_in_the_ledger():
    """A ledger that forgot its resolutions could not answer the only question an operator
    brings to it."""
    k = keeper()
    intention = k.commit(a_plan(), PLAN, WANT)
    k.resolve(intention, "done")
    assert k.standing() == []
    kept = bindings(query_over(k.intentions, f"SELECT ?p WHERE {{ <{intention}> ?p ?o }}",
                               intentions_graph(AGENT)))
    assert kept, "the resolved intention was removed rather than resolved"


def test_an_empty_plan_is_an_answer_and_not_a_commitment():
    """The search reached the want's met state in no steps: there is nothing to carry out."""
    assert keeper().commit(ox.Store(), PLAN, WANT) is None


