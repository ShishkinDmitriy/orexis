"""The machine a transition is applied by (`transition.py`): its orders, what one order changes, and
the change applied — held on a bare store, with this test's own words, since what it promises is the
shape every caller shares and no caller's meaning (knowledge/domain/belief/transition.md)."""

from __future__ import annotations

import logging

import pyoxigraph as ox
import pytest

from agent.belief.transition import Change, Refused, Rule, applied, asked, ordered, run, scoped, templates, transitions

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


def _said(triples) -> set[tuple[str, str, str]]:
    return {(t.subject.value[len(T):], t.predicate.value[len(T):], t.object.value[len(T):]) for t in triples}


#  THE SWITCH TURNED OFF: the lamp's state before taken out, Dark put in, one text over one WHERE; and
#  a witness of the same order saying what it saw.
_DARKEN = Rule(0, _P + "DELETE { ?l :is ?was } INSERT { ?l :is :Dark } WHERE { :switch :says :off . ?l :is ?was }",
               "darken")
_WITNESS = Rule(0, _P + "INSERT { ?l :seen ?was } WHERE { ?l :is ?was }", "witness")


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
    found = next(r for r in transitions(store)[0] if r.name == T + "countRule")
    assert found.update and found.order == 0.0, "its text and its order travel with it"
    update(store, f"""PREFIX : <{T}> PREFIX sh: <http://www.w3.org/ns/shacl#>
        INSERT DATA {{ GRAPH :rules {{ :sawRule sh:deactivated true . :inference a sh:SPARQLRule ; sh:construct "CONSTRUCT {{}} WHERE {{}}" }} }}""")
    assert named(transitions(store)) == [["countRule"], ["echoRule"]]


def test_ordered_groups_the_rules_by_order_ascending():
    a, b, c = Rule(1, "a"), Rule(0, "b"), Rule(1, "c")
    assert ordered([a, b, c]) == [[b], [a, c]]
    assert ordered([]) == []


def test_an_update_is_asked_as_a_construct_per_template_over_its_one_where():
    """The update grammar finds the parts and the text keeps its own words: each template over the one
    WHERE, the prologue at the head, a `$token` as written; the short form's pattern is both."""
    both = templates(_P + "DELETE { $lamp :is ?was } # what it was\nINSERT { $lamp :is :Dark } WHERE { $lamp :is ?was }")
    assert both.delete == _P.rstrip("\n") + "\nCONSTRUCT { $lamp :is ?was }\nWHERE { $lamp :is ?was }"
    assert both.insert == _P.rstrip("\n") + "\nCONSTRUCT { $lamp :is :Dark }\nWHERE { $lamp :is ?was }"
    short = templates(_P + "DELETE WHERE { ?l :is :Lit }")
    assert short.delete.endswith("CONSTRUCT { ?l :is :Lit }\nWHERE { ?l :is :Lit }") and short.insert is None
    assert templates(_P + "INSERT { ?l :is :Dark } WHERE {}").delete is None


def test_asked_reads_one_state_for_every_rule_of_an_order():
    """Every rule of the order is asked of the state as it stands: the witness sees Lit, though the
    other rule of its order deletes it; and one execution is spent per rule, whatever it states."""
    store = _store()
    change = asked(store, [_DARKEN, _WITNESS], [STATE])
    assert _said(change.added) == {("lamp", "is", "Dark"), ("lamp", "seen", "Lit")}
    assert _said(change.deleted) == {("lamp", "is", "Lit")}
    assert change.executions == 2
    assert _facts(store, STATE) == {("lamp", "is", "Lit"), ("switch", "says", "off")}, "asking changes nothing"


def test_an_update_of_one_template_changes_what_that_template_says():
    """An `INSERT … WHERE` alone only adds, a `DELETE … WHERE` alone and the short `DELETE WHERE` only
    take out — each a transition as much as one stating both."""
    store = _store()
    rules = [Rule(0, _P + "INSERT { ?l :seen ?was } WHERE { ?l :is ?was }", "insert"),
             Rule(0, _P + "DELETE { :switch :says ?what } WHERE { :switch :says ?what }", "delete"),
             Rule(0, _P + "DELETE WHERE { ?l :is :Lit }", "short")]
    change = asked(store, rules, [STATE])
    assert _said(change.added) == {("lamp", "seen", "Lit")}
    assert _said(change.deleted) == {("switch", "says", "off"), ("lamp", "is", "Lit")}
    applied(store, change, STATE, [STATE])
    assert _facts(store, STATE) == {("lamp", "seen", "Lit")}


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


def test_scoped_says_the_world_a_rule_changes_and_every_graph_it_reads():
    """The engine's own update, in the text's own words: `WITH` the world changed, a `USING` per graph
    read, once each, before the one WHERE; the short `DELETE WHERE` spelled as the form it abbreviates,
    since it takes neither clause."""
    w = T + "w"
    both = scoped(_P + "DELETE { $lamp :is ?was } INSERT { $lamp :is :Dark } WHERE { $lamp :is ?was }", w, [w, STATE, w])
    assert both == _P.rstrip("\n") + (f"\nWITH <{w}>\nDELETE {{ $lamp :is ?was }}\nINSERT {{ $lamp :is :Dark }}\n"
                                      f"USING <{w}>\nUSING <{STATE}>\nWHERE {{ $lamp :is ?was }}")
    short = scoped(_P + "DELETE WHERE { ?l :is :Lit }", w, [w])
    assert short.endswith(f"WITH <{w}>\nDELETE {{ ?l :is :Lit }}\nUSING <{w}>\nWHERE {{ ?l :is :Lit }}")
    assert "DELETE" not in scoped(_P + "INSERT { ?l :is :Dark } WHERE { ?l :is ?w }", w, [w])


def test_run_changes_the_world_it_is_handed_alone_reading_every_graph_beside_it():
    """The switch is read where it stands, beside the world; the lamp's Lit is taken out of the world
    alone and Dark put in, and the same fact in a graph only read stands. One execution a rule."""
    store = _store()
    assert run(store, [_DARKEN], OTHER, [OTHER, STATE]) == 1
    assert _facts(store, OTHER) == {("lamp", "is", "Dark")}
    assert _facts(store, STATE) == {("lamp", "is", "Lit"), ("switch", "says", "off")}, "read, and not changed"


def test_run_applies_each_rule_to_what_the_rule_before_left():
    """One rule after another, by order and then as an order lists them: the witness run after the
    darkening sees Dark, where asked of one state with it, it saw Lit (#953)."""
    store = _store()
    run(store, [_DARKEN, _WITNESS], STATE, [STATE])
    assert _facts(store, STATE) == {("lamp", "is", "Dark"), ("lamp", "seen", "Dark"), ("switch", "says", "off")}
    store = _store()
    run(store, [Rule(1, _DARKEN.update, "later"), _WITNESS], STATE, [STATE])
    assert ("lamp", "seen", "Lit") in _facts(store, STATE), "an earlier order runs first, however listed"


#  WHAT THE RUNNER REFUSES, each a package's bug: a text naming its graphs four ways, one chaining a
#  second operation — and one ending in `;`, which chains nothing but an empty one — one that is no
#  DELETE/INSERT … WHERE, and one that will not parse.
_REFUSED = {
    "with": "WITH <urn:x> DELETE { ?l :is ?w } INSERT { ?l :is :Dark } WHERE { ?l :is ?w }",
    "using": "DELETE { ?l :is ?w } INSERT { ?l :is :Dark } USING <urn:x> WHERE { ?l :is ?w }",
    "templated": "DELETE { GRAPH <urn:x> { ?l :is ?w } } INSERT { ?l :is :Dark } WHERE { ?l :is ?w }",
    "graphed": "DELETE { ?l :is ?w } INSERT { ?l :is :Dark } WHERE { GRAPH ?g { ?l :is ?w } }",
    "chained": "DELETE WHERE { ?l :is :Lit } ; INSERT { ?l :is :Dark } WHERE { ?l :is ?w }",
    "trailing": "DELETE { ?l :is ?w } INSERT { ?l :is :Dark } WHERE { ?l :is ?w } ;",
    "data": "INSERT DATA { :lamp :is :Dark }",
    "construct": "CONSTRUCT { ?l :is :Dark } WHERE { ?l :is ?w }",
    "broken": "DELETE { ?l :is ?w } INSERT { ?l :is :Dark } WHERE { ?l :is ?w",
}


@pytest.mark.parametrize("name", sorted(_REFUSED))
def test_an_update_naming_its_graphs_or_chaining_operations_changes_nothing(name, caplog):
    """Said in the log, naming the rule; the whole of it changes nothing, its insert as much as its
    delete; and the rest of the order still runs."""
    store = _store()
    with caplog.at_level(logging.ERROR, logger="transition"):
        change = asked(store, [Rule(0, _P + _REFUSED[name], name), _WITNESS], [STATE])
    assert any(name in m for m in caplog.messages), caplog.messages
    assert _said(change.added) == {("lamp", "seen", "Lit")}, "the witness ran, and nothing of the refused rule"
    assert change.deleted == []
    with pytest.raises(Refused):
        templates(_P + _REFUSED[name])
    store = _store()
    with caplog.at_level(logging.ERROR, logger="transition"):
        run(store, [Rule(0, _P + _REFUSED[name], name), _WITNESS], STATE, [STATE])
    assert _facts(store, STATE) == {("lamp", "is", "Lit"), ("switch", "says", "off"), ("lamp", "seen", "Lit")}, \
        "run, the refused rule changes nothing and the witness still runs"


def test_a_refusal_says_why():
    """The reason is the log's to give, so it names the fault: graphs named, operations chained, a
    kind of update that is no DELETE/INSERT … WHERE."""
    reasons = {}
    for name in ("with", "graphed", "chained", "data"):
        with pytest.raises(Refused) as refused:
            templates(_P + _REFUSED[name])
        reasons[name] = str(refused.value)
    assert "names its own graphs" in reasons["with"] and "names its own graphs" in reasons["graphed"]
    assert "chains operations" in reasons["chained"]
    assert "InsertData" in reasons["data"]


def test_an_update_that_will_not_run_changes_nothing_whole(caplog):
    """A text the grammar takes and the engine will not run — here a `$token` nobody bound — changes
    nothing, and not its delete without its insert: one text is one change."""
    store = _store()
    rule = Rule(0, _P + "DELETE { ?l :is ?w } INSERT { $nobody :is :Dark } WHERE { ?l :is ?w }", "unbound")
    with caplog.at_level(logging.ERROR, logger="transition"):
        change = asked(store, [rule], [STATE])
    assert change.added == [] and change.deleted == []
    assert any("unbound" in m for m in caplog.messages), caplog.messages
    caplog.clear()
    with caplog.at_level(logging.ERROR, logger="transition"):
        run(store, [rule], STATE, [STATE])
    assert _facts(store, STATE) == {("lamp", "is", "Lit"), ("switch", "says", "off")}
    assert any("unbound" in m for m in caplog.messages), caplog.messages
