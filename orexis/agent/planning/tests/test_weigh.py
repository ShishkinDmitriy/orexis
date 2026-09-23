"""`weigh`, one case per file, held to a PATCH of the store it leaves.

A case in `weigh/` is an imaginarium with something still to be weighed. The test weighs
whatever `unweighed` lists — every desire in every ground, every want in the present, every
candidate leaving a world its want has weighed — which is what a pass would weigh next.
`<case>.diff` is the weighings: the verdict, the violation rows, whether the world is on the
frontier, and for a candidate passed over, which world it repeats.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from orexis.agent import clock
from orexis.agent.planning.unweighed import unweighed
from orexis.agent.planning.weigh import weigh

CASES_DIR = Path(__file__).parent / "weigh"
CASES = sorted(p for p in CASES_DIR.glob("*.trig") if "." not in p.stem)

#  THE FILTERS STAND AT THE TOP OF THE WHERE, not inside the catalogue's group: a FILTER
#  inside a group cannot see a variable bound outside it, so inside `GRAPH ?cat` the `?for`
#  the union bound was unbound, NOT EXISTS matched any weighing at all, and a store holding
#  one had nothing left to weigh. The trap AGENTS.md records for UNION and BIND, met here.
@pytest.mark.parametrize("case", CASES, ids=[c.stem for c in CASES])
def test_weigh_writes_the_weighings_the_patch_says(case, monkeypatch, request, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(case)
    weighed = [weigh(store, pair["for"], pair["about"]) for pair in unweighed(store)]
    assert weighed, f"{case.name} has nothing left to weigh"
    snapshots.held_to_diff(case, request, "weigh", snapshots.snapshot_of(store))


def test_every_case_is_read_and_no_diff_is_orphaned(snapshots):
    assert len(CASES) >= 3, [c.name for c in CASES]
    assert not snapshots.orphans_in(CASES_DIR)
