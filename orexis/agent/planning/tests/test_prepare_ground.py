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

from orexis.agent import clock
import pyoxigraph as ox

from orexis.agent.planning.prepare_ground import prepare_ground

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
