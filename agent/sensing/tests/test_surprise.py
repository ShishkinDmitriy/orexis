"""`surprise` — a reading against the prediction holding at its instant, asked between
`revise` and `predict`, which is the trio a reading arriving goes through.

Built from a predict case rather than a case directory of its own: a read that writes nothing
is held to what it answers, and what it answers about is the ladder `predict` leaves.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from agent import clock
from agent.sensing.predict import predict
from agent.sensing.revise import revise
from agent.sensing.surprise import surprise

CASE = Path(__file__).parent / "predict" / "a_widening_spread_crosses_later_than_the_ladder_says.trig"
TEST = "http://example.org/test#"
ZZ, MOISTURE = TEST + "zz", TEST + "moisture"


@pytest.fixture
def predicted(monkeypatch, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(CASE)
    assert predict(store, snapshots.ME, ZZ, MOISTURE), "the ladder stands"
    return store


def _arrives(store, snapshots, value: float, minutes: float) -> str | None:
    at = snapshots.NOW + timedelta(minutes=minutes)
    revise(store, snapshots.ME, ZZ, MOISTURE, value, at, 900.0, sensor=TEST + "probe")
    return surprise(store, ZZ, MOISTURE)


def test_a_reading_on_the_predicted_sides_is_no_surprise(predicted, snapshots):
    """At a quarter past, the first window says inside both ranges: a reading of 0.24 is the
    world going on as believed."""
    assert _arrives(predicted, snapshots, 0.24, 16) is None


def test_a_reading_off_the_predicted_sides_is_a_surprise(predicted, snapshots):
    """The first window allows inside the operating range alone, and a reading of 0.05 is
    below it: the sentence names what contradicted what, and says nothing of the survival
    range, inside which the reading still is."""
    said = _arrives(predicted, snapshots, 0.05, 16)
    assert said == "moisture of zz read Below zz.operating.moisture where Inside was expected", said


def test_a_boundary_crossed_inside_the_predicted_set_is_absorbed(predicted, snapshots):
    """By half past three the crossed window allows inside AND below the operating range: a
    reading below is among them, and wakes nothing — the hysteresis a margin would have
    bought."""
    assert _arrives(predicted, snapshots, 0.09, 210) is None


def test_a_reading_before_its_window_is_held_to_the_first_prediction(predicted, snapshots):
    """Arrived at five past, before any window opens: the first prediction is what it is
    held to, and 0.5 is above both ranges where inside was expected."""
    said = _arrives(predicted, snapshots, 0.5, 5)
    assert said == ("moisture of zz read Above zz.operating.moisture where Inside was expected; "
                    "Above zz.survival.moisture where Inside was expected"), said


def test_a_reading_nothing_predicted_is_news(monkeypatch, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(CASE)
    predict(store, snapshots.ME, ZZ, MOISTURE)
    revise(store, snapshots.ME, ZZ, MOISTURE, 0.24, snapshots.NOW + timedelta(minutes=16), 900.0)
    predict(store, snapshots.ME, ZZ, MOISTURE)     # the ladder rewritten from the new reading
    revise(store, snapshots.ME, TEST + "other", MOISTURE, 0.2, snapshots.NOW, 900.0)
    assert surprise(store, TEST + "other", MOISTURE) == "moisture of other read against no region where nothing was predicted"


def test_nothing_read_is_nothing_to_say(predicted):
    assert surprise(predicted, TEST + "nobody", MOISTURE) is None
