"""`predict`, one case per file, held to a PATCH of the store it leaves.

A case in `predict/` is a belief base with a reading in hand and the drifts the packages
declare; the diff is the ladder of predictions the reading comes to — one graph per window,
each carrying the key's node and the revisions the drift's width reaches against every region
the world states, holding during its window, its row saying which reading it was derived from
and how it supersedes the standing node — and a first window split where the bisection places
the crossing.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from agent import clock
from agent.sensing.predict import predict
from agent.store import rows

CASES_DIR = Path(__file__).parent / "predict"
CASES = sorted(p for p in CASES_DIR.glob("*.trig") if "." not in p.stem)

TEST = "http://example.org/test#"

_WINDOWS_Q = """
SELECT ?g ?start ?end WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a orexis:PredictionGraph ; dcterms:temporal ?p .
               ?p orexis:start ?start . OPTIONAL { ?p orexis:end ?end } } }
ORDER BY ?start"""

#  WHERE EACH CASE'S FIRST WINDOW OPENS AND WHERE THE CROSSING FALLS, in minutes past noon —
#  the ladder's rungs where nothing crosses, the bisection's instant where something does.
OPENS = {
    "a_fast_dryer_crosses_inside_the_first_window": [15, 54, 60, 300],
    "a_widening_spread_crosses_later_than_the_ladder_says": [15, 60, 202, 300],
    "a_key_no_drift_moves_is_carried_one_window_forward": [15],
    "a_reading_already_below_predicts_no_crossing": [15, 60, 300],
}


@pytest.mark.parametrize("case", CASES, ids=[c.stem for c in CASES])
def test_predict_writes_the_ladder_the_patch_says(case, monkeypatch, request, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(case)
    written = predict(store, snapshots.ME, TEST + "zz", TEST + "moisture")
    snapshots.held_to_diff(case, request, "predict", snapshots.snapshot_of(store))
    opened = [int((_at(r["start"]) - snapshots.NOW).total_seconds() // 60) for r in rows(store, _WINDOWS_Q, ())]
    assert opened == OPENS[case.stem], opened
    assert len(written) == len(opened)


def test_the_ladder_is_rewritten_whole_by_the_next_reading(monkeypatch, snapshots):
    """Predicted twice from one reading, the store holds one ladder: every prediction derived
    from the reading's graph goes before its own is written."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(CASES_DIR / "a_reading_already_below_predicts_no_crossing.trig")
    first = predict(store, snapshots.ME, TEST + "zz", TEST + "moisture")
    again = predict(store, snapshots.ME, TEST + "zz", TEST + "moisture")
    assert first == again
    assert [r["g"] for r in rows(store, _WINDOWS_Q, ())] == again


def _at(text: str):
    from datetime import datetime
    return datetime.fromisoformat(text)


def test_every_case_is_read_and_no_diff_is_orphaned(snapshots):
    assert set(OPENS) == {c.stem for c in CASES}, [c.name for c in CASES]
    assert not snapshots.orphans_in(CASES_DIR)
