"""`admit`, one case per file, held to a PATCH of the store it leaves.

A case in `admit/` is an imaginarium with its ground laid and its wants derived; the test admits
the present ground for the agent, and `<case>.diff` is the candidates written: one per action
per legal filling, each the edge from the ground, saying what it fills and what with. A world
admitting nothing writes nothing, and that is a case too — zero is ordinary.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from orexis.agent import clock
from orexis.agent.store import rows
from orexis.agent.planning.admit import admit

CASES_DIR = Path(__file__).parent / "admit"
CASES = sorted(p for p in CASES_DIR.glob("*.trig") if "." not in p.stem)

_PRESENT_Q = """
SELECT ?g WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a planning:GroundGraph ; dcterms:temporal/orexis:start ?start } }
ORDER BY ?start LIMIT 1"""


@pytest.mark.parametrize("case", CASES, ids=[c.stem for c in CASES])
def test_admit_writes_the_candidates_the_patch_says(case, monkeypatch, request, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(case)
    (present,) = rows(store, _PRESENT_Q, ())
    admit(store, present["g"], snapshots.ME)
    snapshots.held_to_diff(case, request, "admit", snapshots.snapshot_of(store))


def test_every_case_is_read_and_no_diff_is_orphaned(snapshots):
    assert len(CASES) >= 3, [c.name for c in CASES]
    assert not snapshots.orphans_in(CASES_DIR)
