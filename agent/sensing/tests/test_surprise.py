"""`surprise` — an observation against the prediction holding at its instant, on numbers and
the subject's range bounds, asked between `received` and `predict`.

Built from a predict case rather than a case directory of its own: a read that writes nothing
is held to what it answers, and what it answers about is the stretches `predict` leaves.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from agent import clock
from agent.sensing.predict import predict
from agent.sensing.received import received
from agent.sensing.surprise import surprise
from agent.sensing.wiring import Sensor, sensors_of

CASE = Path(__file__).parent / "predict" / "a_slow_dryer_crosses_later_than_the_ladders_rung.trig"
TEST = "http://example.org/test#"


@pytest.fixture
def predicted(monkeypatch, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(CASE)
    (probe,) = sensors_of(store, snapshots.ME)
    assert predict(store, snapshots.ME, probe), "the stretches stand"
    return store, probe


def _arrives(predicted, snapshots, value: float, minutes: float) -> str | None:
    store, probe = predicted
    at = snapshots.NOW + timedelta(minutes=minutes)
    received(store, snapshots.ME, probe, f'{{"value": {value}}}'.encode(), at, horizon=900.0)
    return surprise(store, probe)


def test_a_reading_on_the_predicted_side_of_every_bound_is_no_surprise(predicted, snapshots):
    """At a quarter past, the first stretch says inside the operating range: 0.24 is the world
    going on as believed."""
    assert _arrives(predicted, snapshots, 0.24, 16) is None


def test_a_reading_across_a_bound_is_a_surprise(predicted, snapshots):
    """The first stretch says inside; 0.05 is under the operating floor, and the sentence names
    the bound and what was expected."""
    said = _arrives(predicted, snapshots, 0.05, 16)
    assert said is not None and said.startswith("moisture of zz read 0.05, under the floor of zz.operating, where ") \
        and said.endswith(" was expected"), said


def test_a_reading_on_the_stretch_after_the_crossing_is_absorbed(predicted, snapshots):
    """Past 19:12 the stretch says under the operating floor and inside the survival range:
    0.09 there is what was foreseen, and wakes nothing."""
    assert _arrives(predicted, snapshots, 0.09, 460) is None


def test_a_reading_before_its_stretch_is_held_to_the_first_prediction(predicted, snapshots):
    """Arrived at five past, before any stretch opens: the first prediction is what it is held
    to, and 0.5 is over the ceiling where inside was expected."""
    assert _arrives(predicted, snapshots, 0.5, 5) is not None


def test_a_reading_nothing_predicted_is_news(monkeypatch, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(CASE)
    other = Sensor(uri=TEST + "thermometer", subject=TEST + "other", observes=TEST + "moisture")
    received(store, snapshots.ME, other, b'{"value": 0.2}', snapshots.NOW, horizon=900.0)
    assert surprise(store, other) == "moisture of other read 0.2 where nothing was predicted"


def test_nothing_read_is_nothing_to_say(predicted, snapshots):
    store, _ = predicted
    assert surprise(store, Sensor(uri=TEST + "nobody", subject=TEST + "nobody", observes=TEST + "moisture")) is None
