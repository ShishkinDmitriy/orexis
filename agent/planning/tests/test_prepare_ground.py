"""`prepare_ground`, one case per file, held to a PATCH of the store it FILLS.

A case in `prepare_ground/` is a belief base: its graphs, and a catalogue saying what each one is.
The function fills a second, empty store with what no step may change — the copy alone,
since laying the grounds is `lay_ground`'s and the Planner calls the two in turn — and
`<case>.diff` is that second store, so `diff` of case against snapshot is exactly what crossed
and what did not.

THE DIFF READS AS THE FAILURE MODE. A graph that did not make it shows as `# DROPPED:`, and
that is the silent failure this function exists to prevent: a pattern reaching a graph nobody
copied returns an EMPTY RESULT rather than an error — no rows, no exception, and a planner
that quietly finds every lever useless. Which graphs cross is therefore worth a case each
rather than an assertion counting them.

The private graphs a case names are given here, beside it, because they are the CALLER's
argument and not a fact in the world: what the agent alone holds and a rule still names.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from agent import clock
import pyoxigraph as ox

from agent.planning.lay_ground import lay_ground
from agent.planning.ontology import GROUND_GRAPH
from agent.planning.prepare_ground import CROSSING, prepare_ground
from agent.store import forget_graph, graph_names, graphs_of, quads

CASES_DIR = Path(__file__).parent / "prepare_ground"
CASES = sorted(p for p in CASES_DIR.glob("*.trig") if "." not in p.stem)


@pytest.mark.parametrize("case", CASES, ids=[c.stem for c in CASES])
def test_prepare_ground_fills_the_store_as_the_snapshot_says(case, monkeypatch, request, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(case)
    into = ox.Store()
    prepare_ground(store, into)
    snapshots.held_to_diff(case, request, "prepare_ground", snapshots.snapshot_of(into))


def test_every_case_is_read_and_no_snapshot_is_orphaned(snapshots):
    """A glob that stopped matching would pass every case by running none."""
    assert len(CASES) >= 3, [c.name for c in CASES]
    assert not snapshots.orphans_in(CASES_DIR)


def test_a_second_filling_refreshes_the_copy_and_keeps_what_the_store_made(monkeypatch, snapshots):
    """The imaginarium outlives the pass, so the filling is called again on a store that holds
    a copy: a reading the beliefs replaced is replaced here, a forecast the beliefs swept is
    gone here, and the ground the store laid for itself is untouched."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    beliefs = snapshots.stand_in(CASES_DIR / "a_forecast_holding_later_crosses_whole.trig")
    into = prepare_ground(beliefs, ox.Store())
    lay_ground(into, snapshots.NOW)
    grounds = set(graphs_of(into, GROUND_GRAPH))
    assert grounds, "the store made grounds of its own"
    replaced, swept, *_ = sorted(graphs_of(beliefs, *CROSSING))
    old = next(iter(beliefs.quads_for_pattern(None, None, None, ox.NamedNode(replaced))))
    beliefs.remove(old)
    new = ox.Quad(old.subject, old.predicate, ox.Literal("moved on"), ox.NamedNode(replaced))
    beliefs.add(new)
    forget_graph(beliefs, swept)
    prepare_ground(beliefs, into)
    held = set(quads(into, replaced))
    assert new in held and old not in held, "the row replaced, not laid beside the old one"
    assert swept not in graph_names(into), "the graph the beliefs swept is gone from the copy"
    assert set(graphs_of(into, GROUND_GRAPH)) == grounds, "what the store made stays"
