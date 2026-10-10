"""The bridges: a rule concluding one vocabulary's fact from another's, read as a head that runs
backwards — and `keeps`, what the Planner asks of a step when it hands a plan down: whether a
bridge's head binds a fact the step adds, so that the step is kept below and not taken fictively."""

from __future__ import annotations

from agent.planning.bridge import heads, keeps
from agent.store import update

from .test_refine import _predicting, _store


def test_a_rule_with_one_head_triple_is_a_bridge():
    [(declared, head, where, names)] = heads(_store())
    assert head[1] == ":on" and "at" in where


def test_a_transition_is_no_bridge():
    """A rule saying what fires it changes a state when something arrives, and concludes no
    vocabulary's facts from another's: with one head triple plain in its WHERE it would read as a
    bridge, and it is left out (a-transition-changes-the-state-and-an-inference-only-concludes)."""
    store = _store()
    update(store, '''INSERT DATA { GRAPH <http://example.org/test#rules> {
  <http://example.org/test#moved> a sh:SPARQLRule ; belief:firesOn orexis:StateGraph ;
    sh:construct """PREFIX : <http://example.org/test#>
    CONSTRUCT { ?disk :was ?cell } WHERE { ?disk :at ?cell }""" } }''')
    assert [head[1] for _, head, _, _ in heads(store)] == [":on"]


def test_a_step_is_kept_below_where_a_bridge_concludes_a_fact_it_adds():
    store = _store()
    assert keeps(store, _predicting(store, ":d :on :pegB"))
    store = _store()
    assert not keeps(store, _predicting(store, ":d :painted :red")), "no rule concludes a colour"
    store = _store()
    assert not keeps(store, _predicting(store, "")), "a step that adds nothing is kept by nothing"
