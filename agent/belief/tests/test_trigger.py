"""`trigger`, one case per file, held to a PATCH of the store it leaves
(knowledge/domain/belief/transition.md, a-transition-changes-the-state-and-an-inference-only-concludes).

A case in `trigger/` is a store with a tick that has arrived — a graph of a kind a transition is
`belief:triggeredBy` — the agent's own state before it, public knowledge, and the transitions in a
rules graph, as a domain would ship them. The test triggers the tick's transitions and `<case>.diff` is
what that changed: the state taken out where it stood, a graph left empty forgotten, and what was
inserted in the state graph the runner prepares for the tick, over the tick's period. The words are
this test's own — a counter and its ticks — so that what is held is the machine and no domain's
meaning.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from agent.belief.revise import revise
from agent.belief.trigger import Triggered, trigger
from agent.ontology import KNOWN
from agent.store import graphs_of, rows, update

CASES_DIR = Path(__file__).parent / "trigger"
CASES = sorted(p for p in CASES_DIR.glob("*.trig") if "." not in p.stem)
T = "http://example.org/test#"
TICK = T + "tick2"

#  WHAT THE COUNTER IS HELD TO, in the agent's own state whatever its period.
_HELD_Q = "SELECT ?p ?o WHERE { <http://example.org/test#counter> ?p ?o FILTER(?p != rdf:type) }"

#  THE AGENT'S OWN STATE: every state graph it derived, which is where a transition writes — never a
#  tick or a graph heard, which are state graphs it received.
_OWN_STATE_Q = """SELECT ?g WHERE { GRAPH ?c { ?c a orexis:CatalogueGraph .
    ?g a orexis:StateGraph ; orexis:arrivedBy orexis:Derived } } ORDER BY ?g"""


def _held(store) -> dict[str, str]:
    own = [r["g"] for r in rows(store, _OWN_STATE_Q)]
    return {r["p"].rsplit("#", 1)[-1]: r["o"] for r in rows(store, _HELD_Q, own)}


@pytest.mark.parametrize("case", CASES, ids=[c.stem for c in CASES])
def test_trigger_changes_what_the_patch_says(case, request, snapshots):
    store = snapshots.stand_in(case)
    triggered = trigger(store, TICK)
    assert triggered.finished
    snapshots.held_to_diff(case, request, "trigger", snapshots.snapshot_of(store))


def test_every_case_is_read_and_no_diff_is_orphaned(snapshots):
    assert CASES, "the glob stopped matching"
    assert not snapshots.orphans_in(CASES_DIR)


def test_a_graph_of_a_kind_no_transition_declares_triggers_nothing(snapshots):
    """The world graph is no tick: triggering on it applies nothing, spends nothing, and is done."""
    store = snapshots.stand_in(CASES_DIR / "a_state_is_replaced_where_it_stood.trig")
    assert trigger(store, T + "world") == Triggered(0, 0, True)
    assert _held(store) == {"count": "1"}


def test_an_order_is_applied_whole_and_a_cut_is_continued_to_the_same_state(snapshots):
    """A budget of one execution begins the first order — two rules, applied whole — and stops before
    the second; continued from the order it stopped at, the state is the one an uncut call leaves, and
    no order is applied twice: the count is 2, not 3."""
    case = CASES_DIR / "two_transitions_of_one_order_read_the_same_state.trig"
    whole = snapshots.stand_in(case)
    assert trigger(whole, TICK) == Triggered(3, 2, True)
    store = snapshots.stand_in(case)
    first = trigger(store, TICK, budget=1)
    assert first == Triggered(2, 1, False), first
    assert _held(store) == {"count": "2", "saw": "1"}, "the first order whole, and nothing of the second"
    assert trigger(store, TICK, done=first.done) == Triggered(1, 2, True)
    assert _held(store) == _held(whole) == {"count": "2", "saw": "1", "echo": "2"}


def test_a_transition_is_no_inference(snapshots):
    """Revision runs the default rule set to a fixpoint and never deletes; a rule saying what triggers
    it is no part of it, so revising the tick concludes nothing and leaves the count as it was."""
    store = snapshots.stand_in(CASES_DIR / "a_state_is_replaced_where_it_stood.trig")
    assert revise(store, TICK, read=graphs_of(store, *KNOWN)) == 0
    assert _held(store) == {"count": "1"}
    assert not rows(store, "SELECT ?g WHERE { GRAPH ?c { ?g a belief:RevisionGraph } }")


def test_an_arrivals_state_graph_said_again_takes_the_later_arrivals_period(snapshots):
    """The tick's own state graph already holds a count of an earlier arrival under its name, the count
    deletes it there and inserts the next: one row, the later tick's period, and no period left over."""
    store = snapshots.stand_in(CASES_DIR / "a_state_is_replaced_where_it_stood.trig")
    trigger(store, TICK)
    update(store, f"""DELETE {{ GRAPH ?c {{ ?p <http://example.org/orexis#start> ?s . ?p <http://example.org/orexis#end> ?e }} }}
INSERT {{ GRAPH ?c {{ ?p <http://example.org/orexis#start> "2026-01-01T12:20:00+00:00"^^xsd:dateTime .
                     ?p <http://example.org/orexis#end> "2026-01-01T12:40:00+00:00"^^xsd:dateTime }} }}
WHERE {{ GRAPH ?c {{ <{TICK}> dcterms:temporal ?p . ?p <http://example.org/orexis#start> ?s ; <http://example.org/orexis#end> ?e }} }}""")
    trigger(store, TICK)
    periods = rows(store, """SELECT ?s ?e WHERE { GRAPH ?c { $g dcterms:temporal ?p . ?p orexis:start ?s ; orexis:end ?e } }""",
                   (), g=TICK + "/believed")
    assert [(p["s"][:19], p["e"][:19]) for p in periods] == [("2026-01-01T12:20:00", "2026-01-01T12:40:00")], periods
    assert _held(store) == {"count": "3"}
