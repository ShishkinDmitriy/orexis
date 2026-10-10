"""The machine a transition is applied by (`transition.py`): its orders, what one order changes, and
the change applied — held on a bare store, with this test's own words, since what it promises is the
shape every caller shares and no caller's meaning (knowledge/domain/belief/transition.md)."""

from __future__ import annotations

import logging

import pyoxigraph as ox

from agent.belief.transition import Change, Rule, applied, asked, ordered, transitions

T = "http://example.org/test#"
STATE, OTHER = T + "state", T + "other"
_P = f"PREFIX : <{T}>\n"


def _store() -> ox.Store:
    """A lamp lit in one graph and, the same fact, in another; a switch saying off."""
    store = ox.Store()
    lamp, is_, lit = ox.NamedNode(T + "lamp"), ox.NamedNode(T + "is"), ox.NamedNode(T + "Lit")
    for g in (STATE, OTHER):
        store.add(ox.Quad(lamp, is_, lit, ox.NamedNode(g)))
    store.add(ox.Quad(ox.NamedNode(T + "switch"), ox.NamedNode(T + "says"), ox.NamedNode(T + "off"), ox.NamedNode(STATE)))
    return store


def _facts(store, graph: str) -> set[tuple[str, str, str]]:
    return {(q.subject.value.rsplit("#", 1)[-1], q.predicate.value.rsplit("#", 1)[-1], q.object.value.rsplit("#", 1)[-1])
            for q in store.quads_for_pattern(None, None, None, ox.NamedNode(graph))}


#  THE SWITCH TURNED OFF: the lamp's state before taken out, Dark put in; and a witness of the same
#  order saying what it saw.
_DARKEN = Rule(0, _P + "CONSTRUCT { ?l :is :Dark } WHERE { :switch :says :off . ?l :is ?any }",
               _P + "DELETE { ?l :is ?was } WHERE { :switch :says :off . ?l :is ?was }", "darken")
_WITNESS = Rule(0, _P + "CONSTRUCT { ?l :seen ?was } WHERE { ?l :is ?was }", None, "witness")


def test_transitions_are_every_active_transition_the_rules_graphs_hold_in_their_orders(snapshots):
    """What the present's runner and a ground's both apply (`trigger`, `lay_ground`): the trigger case
    of two orders, read by its type off the rules graph — the count and the witness of order nought, the
    echo of order one — and one rule deactivated or no transition is no part of them."""
    from pathlib import Path
    from agent.store import update
    case = Path(__file__).parent / "trigger" / "two_transitions_of_one_order_read_the_same_state.trig"
    store = snapshots.stand_in(case)
    named = lambda orders: [sorted(r.name[len(T):] for r in order) for order in orders]
    assert named(transitions(store)) == [["countRule", "sawRule"], ["echoRule"]]
    found = transitions(store)[0][0]
    assert found.construct and found.delete and found.order == 0.0, "its texts and its order travel with it"
    update(store, f"""PREFIX : <{T}> PREFIX sh: <http://www.w3.org/ns/shacl#>
        INSERT DATA {{ GRAPH :rules {{ :sawRule sh:deactivated true . :inference a sh:SPARQLRule ; sh:construct "CONSTRUCT {{}} WHERE {{}}" }} }}""")
    assert named(transitions(store)) == [["countRule"], ["echoRule"]]


def test_ordered_groups_the_rules_by_order_ascending():
    a, b, c = Rule(1, "a"), Rule(0, "b"), Rule(1, "c")
    assert ordered([a, b, c]) == [[b], [a, c]]
    assert ordered([]) == []


def test_asked_reads_one_state_for_every_rule_of_an_order():
    """Every rule of the order is asked of the state as it stands: the witness sees Lit, though the
    other rule of its order deletes it; and one execution is spent per rule, whatever it states."""
    store = _store()
    change = asked(store, [_DARKEN, _WITNESS], [STATE])
    said = lambda triples: {(t.subject.value[len(T):], t.predicate.value[len(T):], t.object.value[len(T):]) for t in triples}
    assert said(change.added) == {("lamp", "is", "Dark"), ("lamp", "seen", "Lit")}
    assert said(change.deleted) == {("lamp", "is", "Lit")}
    assert change.executions == 2
    assert _facts(store, STATE) == {("lamp", "is", "Lit"), ("switch", "says", "off")}, "asking changes nothing"


def test_applied_deletes_from_its_targets_alone_then_adds():
    """The deletions go first and only from the targets — the same fact in a graph that is no target
    stands — and the additions after, into the one graph named: a fact deleted and added again is
    there. The targets left empty are said, as they stood before the additions."""
    store = _store()
    change = asked(store, [_DARKEN], [STATE])
    emptied = applied(store, Change(change.added + change.deleted, change.deleted, 1), STATE, [STATE])
    assert _facts(store, STATE) == {("lamp", "is", "Dark"), ("lamp", "is", "Lit"), ("switch", "says", "off")}
    assert _facts(store, OTHER) == {("lamp", "is", "Lit")}, "no target, so not deleted from"
    assert emptied == []
    store = _store()
    emptied = applied(store, asked(store, [_DARKEN], [STATE, OTHER]), T + "next", [OTHER])
    assert emptied == [OTHER] and _facts(store, OTHER) == set()
    assert _facts(store, T + "next") == {("lamp", "is", "Dark")}


def test_a_delete_that_names_its_graphs_or_is_no_delete_deletes_nothing(caplog):
    """A delete saying its own graphs, one that is no `DELETE … WHERE`, and one that will not parse are
    a package's bug: said in the log, each deletes nothing, and the rest of the order still runs."""
    store = _store()
    rules = [Rule(0, None, _P + "WITH <urn:x> DELETE { ?l :is ?w } WHERE { ?l :is ?w }", "with"),
             Rule(0, None, _P + "DELETE { ?l :is ?w } USING <urn:x> WHERE { ?l :is ?w }", "using"),
             Rule(0, None, _P + "INSERT { ?l :is :Dark } WHERE { ?l :is ?w }", "insert"),
             Rule(0, None, _P + "DELETE { ?l :is ?w } WHERE { ?l :is ?w", "broken"),
             Rule(0, None, _P + "DELETE WHERE { ?l :is :Lit }", "short")]
    with caplog.at_level(logging.ERROR, logger="transition"):
        change = asked(store, rules, [STATE])
    said = " ".join(caplog.messages)
    assert all(name in said for name in ("with", "using", "insert", "broken")), caplog.messages
    assert "short" not in said
    assert {(t.subject.value[len(T):], t.object.value[len(T):]) for t in change.deleted} == {("lamp", "Lit")}, \
        "the short form is asked as a CONSTRUCT WHERE, and the others matched nothing"
