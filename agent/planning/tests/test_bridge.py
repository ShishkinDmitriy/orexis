"""The bridges: a rule concluding one vocabulary's fact from another's, read as a head that runs
backwards — and `keeps`, what the Planner asks of a step when it hands a plan down: whether a
bridge's head binds a fact the step adds, so that the step is kept below and not taken fictively."""

from __future__ import annotations

from agent.planning.bridge import heads, keeps

from .test_refine import T, _iri, _store


def test_a_rule_with_one_head_triple_is_a_bridge():
    [(declared, head, where, names)] = heads(_store())
    assert head[1] == ":on" and "at" in where


def test_a_step_is_kept_below_where_a_bridge_concludes_a_fact_it_adds():
    store = _store()
    assert keeps(store, [[_iri(T + "d"), T + "on", _iri(T + "pegB")]])
    assert not keeps(store, [[_iri(T + "d"), T + "painted", _iri(T + "red")]]), "no rule concludes a colour"
    assert not keeps(store, []), "a step that adds nothing is kept by nothing"
