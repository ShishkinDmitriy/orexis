"""Withdrawing what the derivation no longer implies — tested where the function lives.

`wanted` IS the derivation's answer: a derived want it does not name goes, one it names stays,
a debt is not the derivation's to judge, and a want a plan is walking is kept whatever its
desire reads.
"""

from __future__ import annotations

from agent.store import bindings, query_over, update
from agent.planning.find_wants import find_wants
from agent.execution.executor import Executor
from agent.planning.withdraw import withdraw


def test_a_want_the_derivation_no_longer_implies_goes_and_the_named_one_stays(wants):
    wants.derived("urn:test:a")
    wants.derived("urn:test:b")
    assert withdraw(wants.store, {"urn:test:a"}, wants.at) == ["urn:test:b"]
    assert find_wants(wants.store) == ["urn:test:a"]


def test_a_debt_is_not_the_derivations_to_withdraw(wants):
    wants.owed("urn:test:owed")
    assert withdraw(wants.store, set(), wants.at) == []
    assert find_wants(wants.store) == ["urn:test:owed"], "the ledger's, and it stands"


def test_a_want_a_plan_is_walking_is_kept(wants):
    """The world has not answered yet, and taking the want away would leave a plan in flight
    with nothing it was for."""
    wants.derived("urn:test:walking")
    update(wants.store, """INSERT DATA {
  GRAPH <urn:test:intentions> { <urn:test:i> a execution:Intention ; execution:pursues <urn:test:walking> }
  GRAPH <urn:test:catalogue> { <urn:test:intentions> a execution:IntentionGraph } }""")
    assert withdraw(wants.store, set(Executor(wants.store, "keeper", intentions=wants.store).walking()), wants.at) == []
    assert find_wants(wants.store) == ["urn:test:walking"]


def test_forgetting_a_want_leaves_what_replacing_one_leaves(wants):
    """A want IS its graph where the derivation named it, so withdrawing the last want in a
    graph takes the graph and what the catalogue said of it — nothing is left behind."""
    wants.derived()
    assert withdraw(wants.store, set(), wants.at) == ["urn:test:want"]
    assert find_wants(wants.store, uri="urn:test:want") == []
    assert not bindings(query_over(wants.store, f"SELECT ?p WHERE {{ <{wants.graph_of()}> ?p ?o }}",
                                   "urn:test:catalogue")), "and the catalogue says nothing of its graph"
