"""`init_imaginarium`, one case per file, held to a PATCH of the store it FILLS.

A case in `init_imaginarium/` is a belief base: its graphs, and a catalogue saying what each one is.
The function fills a second, empty store with what no step may change, and
`<case>.patch` is that second store — so `diff` of case against snapshot is exactly
what crossed and what did not.

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

from orexis_agent_execution import clock
import pyoxigraph as ox

from orexis_agent_planning.imaginarium import init_imaginarium

CASES_DIR = Path(__file__).parent / "init_imaginarium"
CASES = sorted(p for p in CASES_DIR.glob("*.trig") if "." not in p.stem)

#  What the caller names as the agent's own, per case — `Imaginarium(store, *private)`'s
#  argument. A case not listed here names none, which is a claim of its own.
#  NOTHING IS NAMED ANY MORE. The caller used to list which of its own graphs crossed; the
#  function asks the catalogue for them — the readings, the predictions, the picks, the desires
#  and the wants — because which graphs are the agent's own is a question the store answers and
#  a list a caller keeps is a second place the answer lives.
SCOPE = "scope/1"


@pytest.mark.parametrize("case", CASES, ids=[c.stem for c in CASES])
def test_init_imaginarium_fills_the_store_as_the_snapshot_says(case, monkeypatch, request, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(case)
    into = ox.Store()
    init_imaginarium(store, into, SCOPE, snapshots.NOW)
    snapshots.held_to_patch(case, request, "init_imaginarium", snapshots.snapshot_of(into))


def test_every_case_is_read_and_no_snapshot_is_orphaned(snapshots):
    """A glob that stopped matching would pass every case by running none."""
    assert len(CASES) >= 3, [c.name for c in CASES]
    assert not snapshots.orphans_in(CASES_DIR)
