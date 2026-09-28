"""`predict`, one case per file, held to a PATCH of the store it leaves.

A case in `predict/` is a belief base with an observation in hand, the pot's ranges and the
drift the domain declares; the diff is the predictions the observation comes to — one graph
per stretch between the instants the reading changes range, each carrying a predicted
observation with the number the drift gives on that side, holding during its stretch, its row
saying which observation it was derived from and how it supersedes the standing node.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from agent import clock
from agent.prediction.predict import predict
from agent.store import rows

CASES_DIR = Path(__file__).parent / "predict"
CASES = sorted(p for p in CASES_DIR.glob("*.trig") if "." not in p.stem)
PROBE = "http://example.org/test#probe"

_WINDOWS_Q = """
SELECT ?g ?start ?end WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a orexis:PredictionGraph ; dcterms:temporal ?p .
               ?p orexis:start ?start . OPTIONAL { ?p orexis:end ?end } } }
ORDER BY ?start"""

#  WHERE EACH STRETCH OPENS, in minutes past noon, with the minutes a crossing may be placed
#  within: a crossing is placed by division and rounded up to the whole second. The arithmetic is
#  the drift's: 0.25 less the rate per day, so the operating floor at 0.10 is met 0.15 / rate days
#  out and the survival floor at 0.02 is met 0.23 / rate days out. The shower and the corridor are
#  read in their own files.
OPENS = {
    "a_slow_dryer_crosses_the_floor_after_seven_hours": [(15, 0), (432, 0.02), (662.4, 0.02)],
    "a_fast_dryer_crosses_both_floors_within_two_hours": [(15, 0), (54, 0.02), (82.8, 0.02)],
    "a_reading_already_below_crosses_only_the_survival_floor": [(15, 0), (86.4, 0.02)],
    "a_key_no_drift_moves_is_carried_an_hour_forward": [(15, 0)],
    "two_drifts_moving_one_property_add": [(15, 0), (36, 0.02), (55.2, 0.02)],
    "a_forecast_shower_lifts_the_reading_back_inside": [(15, 0), (28.8, 0.02), (144, 0.02), (316.8, 0.02), (432, 0.02)],
    "a_forecast_range_opens_a_corridor_on_its_dry_side": [(15, 0), (28.8, 0.02), (144, 0.02)],
}


@pytest.mark.parametrize("case", CASES, ids=[c.stem for c in CASES])
def test_predict_writes_the_stretches_the_patch_says(case, monkeypatch, request, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(case)
    written = predict(store, snapshots.ME, PROBE)
    snapshots.held_to_diff(case, request, "predict", snapshots.snapshot_of(store))
    opened = [(datetime.fromisoformat(r["start"]) - snapshots.NOW).total_seconds() / 60 for r in rows(store, _WINDOWS_Q, ())]
    assert len(opened) == len(OPENS[case.stem]), opened
    for got, (minute, within) in zip(opened, OPENS[case.stem]):
        assert abs(got - minute) <= within + 1e-9, (opened, OPENS[case.stem])
    assert len(written) == len(opened)


def test_the_stretches_are_rewritten_whole_by_the_next_prediction(monkeypatch, snapshots):
    """Predicted twice from one observation, the store holds one set of stretches: every
    prediction derived from the observation's graph goes before its own is written."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(CASES_DIR / "a_fast_dryer_crosses_both_floors_within_two_hours.trig")
    first = predict(store, snapshots.ME, PROBE)
    again = predict(store, snapshots.ME, PROBE)
    assert first == again
    assert [r["g"] for r in rows(store, _WINDOWS_Q, ())] == again


def test_every_case_is_read_and_no_diff_is_orphaned(snapshots):
    assert set(OPENS) == {c.stem for c in CASES}, [c.name for c in CASES]
    assert not snapshots.orphans_in(CASES_DIR)
