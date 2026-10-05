"""`lay_ground`, one case per file, held to a PATCH of the store it lays the grounds INTO.

The same belief bases `prepare_ground/` fills a second store from, laid in place: the present
as a ground of its own, and one more per boundary a prediction makes, each forked from the one
before with the prediction's retraction run and its facts added, classified with the stretch
it holds over and hashed — and a boundary whose ground hashes like the one before it laid as
no ground at all.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from agent import clock
from agent.planning.lay_ground import lay_ground
from agent.store import rows

CASES_DIR = Path(__file__).parent / "lay_ground"
CASES = sorted(p for p in CASES_DIR.glob("*.trig") if "." not in p.stem)


@pytest.mark.parametrize("case", CASES, ids=[c.stem for c in CASES])
def test_lay_ground_lays_the_grounds_the_patch_says(case, monkeypatch, request, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(case)
    lay_ground(store, snapshots.NOW)
    snapshots.held_to_diff(case, request, "lay_ground", snapshots.snapshot_of(store))


def test_a_period_is_told_by_the_whole_ground_and_its_hash_is_taken_within_what_is_read(monkeypatch, snapshots):
    """The level drops at half past and the temperature rises at one: three grounds. Laid where
    the level alone is read they are three grounds still — a boundary is a period by everything
    the ground holds — and the last two carry ONE hash, since the temperature is not where a
    world stands there. Folding them by what is read was built and struck: a want
    minted for a foreseen crossing came to be weighed in the present and its intention ended
    before its step was due (#858, `lay_ground`)."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    case = CASES_DIR / "two_stretches_in_one_scope_are_two_grounds.trig"
    store = snapshots.stand_in(case)
    grounds = lay_ground(store, snapshots.NOW, frozenset({"http://example.org/test#level"}))
    assert len(grounds) == 3
    hashes = [rows(store, "SELECT ?h WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . "
                          f"<{g}> orexis:hash ?h }} }}")[0]["h"] for g in grounds]
    assert hashes[0] != hashes[1], "the level dropped, which is read"
    assert hashes[1] == hashes[2], "the temperature rose, which is not"


def test_every_case_is_read_and_no_diff_is_orphaned(snapshots):
    assert len(CASES) >= 3, [c.name for c in CASES]
    assert not snapshots.orphans_in(CASES_DIR)
