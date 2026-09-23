"""`reroot`, one case per file, held to a PATCH of the store it leaves.

A case in `reroot/` is an imaginarium a pass left — its ground, its worlds with the candidates
that made them, the weighings of each — with the beliefs moved on, the copy refreshed and the
NEXT present laid beside the old one: the store the Planner hands `reroot` at the start of
the pass after. The test finds the present — the newest ground laid from nothing — and
re-roots the store at it; `<case>.diff` is what that decided. A reader sees which world was
found to be the present, the candidates handed from it to the new ground, every world beneath
it re-stamped to the new instant with its spent rebased, and everything else the last pass
made marked `# DROPPED:`, with the weighings and candidates about it gone from the catalogue.

The three cases are the three things a present can be: the world a step reached, the world
the last pass stood in (nothing happened), and none of them (a surprise). They were written
from real two-disk passes by a script rather than by hand, because a world's rows are the
search's to write and a case that spelled them by hand would be a second writer.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from orexis.agent import clock
from orexis.agent.store import rows
from orexis.agent.planning.reroot import reroot

CASES_DIR = Path(__file__).parent / "reroot"
CASES = sorted(p for p in CASES_DIR.glob("*.trig") if "." not in p.stem)

#  THE PRESENT: the newest ground laid from nothing — a boundary's ground says what it was
#  laid from, the present says nothing.
_PRESENT_Q = """
SELECT ?g WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a planning:GroundGraph ; dcterms:temporal/orexis:start ?start .
               FILTER NOT EXISTS { ?g prov:wasDerivedFrom ?parent } } }
ORDER BY DESC(?start) LIMIT 1"""

_WORLDS_Q = """
SELECT ?w ?at ?spent WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?w a planning:PossibleGraph .
               OPTIONAL { ?w planning:atInstant ?at } OPTIONAL { ?w planning:spent ?spent } } }"""


def _present(store) -> str:
    (found,) = rows(store, _PRESENT_Q, ())
    return found["g"]


@pytest.mark.parametrize("case", CASES, ids=[c.stem for c in CASES])
def test_reroot_leaves_the_store_the_patch_says(case, monkeypatch, request, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW + timedelta(minutes=1))
    store = snapshots.stand_in(case)
    reroot(store, _present(store))
    snapshots.held_to_diff(case, request, "reroot", snapshots.snapshot_of(store))


def test_every_kept_world_is_re_stamped_and_none_loses_its_instant(snapshots):
    """The re-stamping is one update that DELETES every kept world's instant and INSERTS the
    moved one — so an operation the engine lacked would bind nothing and strip every instant
    in silence, and `world_at` would refuse each world as saying no instant. Adding a
    duration to an instant and taking one instant from another were measured to bind on
    0.5.9; this holds the engine to it, and to the rebased spent beside it."""
    store = snapshots.stand_in(CASES_DIR / "a_step_taken_as_predicted_keeps_its_cone.trig")
    assert reroot(store, _present(store)) is not None, "the moved disk is a world the pass imagined"
    kept = rows(store, _WORLDS_Q, ())
    assert kept, "the cone beneath the match is kept"
    assert all(r.get("at") and r.get("spent") is not None for r in kept), kept
    later = snapshots.NOW + timedelta(minutes=1)
    assert min(datetime.fromisoformat(r["at"]) for r in kept) >= later, \
        "every kept world stands at or after the new present"
    assert min(float(r["spent"]) for r in kept) == 1.0, "the match's spent was taken off: its children cost one"


def test_a_surprise_keeps_nothing(snapshots):
    store = snapshots.stand_in(CASES_DIR / "a_surprise_drops_everything.trig")
    assert reroot(store, _present(store)) is None
    assert rows(store, _WORLDS_Q, ()) == []


def test_every_case_is_read_and_no_diff_is_orphaned(snapshots):
    assert len(CASES) >= 3, [c.name for c in CASES]
    assert not snapshots.orphans_in(CASES_DIR)
