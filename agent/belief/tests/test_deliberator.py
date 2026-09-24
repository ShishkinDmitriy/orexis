"""The deliberator: a queue of what was written, a pass within a budget, and a cut continued.

Held over the `revise/` cases, since a pass is `revise` sequenced: what a source's revisions
are is the case's claim, and what is tested here is the sequencing — that a changed source is
revised and leaves the queue, that a budget cuts a pass and the next continues, that nothing
changed spends nothing, and that a cut survives a new deliberator over the same store.
"""

from __future__ import annotations

from pathlib import Path

from agent import clock
from agent.belief.deliberator import Deliberator
from agent.belief.ontology import SETTLED
from agent.store import rows

CASES_DIR = Path(__file__).parent / "revise"
SENSED = "http://example.org/test#sensed"
_CONCLUDED_Q = "SELECT ?s ?p ?o WHERE { GRAPH $g { ?s ?p ?o } }"
_SETTLED_Q = "SELECT ?v WHERE { GRAPH ?c { $g $settled ?v } }"


def _settled(store) -> str | None:
    found = rows(store, _SETTLED_Q, (), g=SENSED + "/revisions", settled=SETTLED)
    return found[0]["v"] if found else None


def test_a_changed_source_is_revised_on_the_pass_and_leaves_the_queue(monkeypatch, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(CASES_DIR / "a_reading_below_its_range_is_concluded_below.trig")
    deliberator = Deliberator(store, snapshots.AGENT)
    deliberator.changed(SENSED)
    assert deliberator.pending == [SENSED]
    assert deliberator.deliberate() > 0
    assert deliberator.pending == []
    assert rows(store, _CONCLUDED_Q, (), g=SENSED + "/revisions")
    assert _settled(store) == "true"


def test_nothing_changed_spends_nothing(monkeypatch, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(CASES_DIR / "a_reading_below_its_range_is_concluded_below.trig")
    assert Deliberator(store, snapshots.AGENT).deliberate() == 0


def test_a_budget_cuts_the_pass_and_the_next_continues(monkeypatch, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(CASES_DIR / "a_chain_settles_in_a_later_round.trig")
    deliberator = Deliberator(store, snapshots.AGENT, budget=2)
    deliberator.changed(SENSED)
    assert deliberator.deliberate() == 2
    assert deliberator.pending == [SENSED] and _settled(store) == "false"
    deliberator.budget = 64
    assert deliberator.deliberate() > 0
    assert deliberator.pending == [] and _settled(store) == "true"
    assert {r["p"].rsplit("#", 1)[-1] for r in rows(store, _CONCLUDED_Q, (), g=SENSED + "/revisions")} == {"side", "isDry"}


def test_a_cut_survives_a_new_deliberator_over_the_store(monkeypatch, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(CASES_DIR / "a_chain_settles_in_a_later_round.trig")
    first = Deliberator(store, snapshots.AGENT, budget=2)
    first.changed(SENSED)
    first.deliberate()
    second = Deliberator(store, snapshots.AGENT)
    assert second.pending == [SENSED], "the row said the rules did not settle"
    second.deliberate()
    assert second.pending == [] and _settled(store) == "true"
