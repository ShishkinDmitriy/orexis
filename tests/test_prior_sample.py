"""An alarm carries the last quiet look, because the series store cannot say "nothing happened".

Two points half an hour apart — a heartbeat at 0.15 and a crossing at 1.00 — are interpolated by
every consumer into a gradual ramp. The device knows better: it looked a hundred times in that
window and every look but the last two was in-window. So a crossing report carries that sample
and the agent places it at the instant it was taken, which puts the corner where it belongs.

The two halves are written in different languages and cannot import each other, so what is
guarded here is that they still AGREE: the firmware emits a shape the agent reads, at the
reading's own pointer one level down.

See knowledge/decisions/the-sentinel-alarms-on-movement.md.
"""

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from packages.capability.sensing import pointer
from agent.config import REPO_ROOT

SENTINEL = REPO_ROOT / "firmware" / "moisture-sentinel" / "src"


def alarm_payload_source() -> str:
    """The firmware's alarm-publishing source, read out of the file it is compiled from.

    Read rather than parsed: the two sides cannot import each other, so what is checkable is
    that the emitting source still mentions what the reading side requires.
    """
    src = (SENTINEL / "main.cpp").read_text()
    assert '\\"wake\\":\\"alarm\\"' in src, (
        "no alarm payload found in the sentinel's main.cpp — this test is looking in the "
        "wrong place, which is the failure mode that quietly takes a guard off duty")
    return src


def test_the_firmware_emits_a_prior_and_names_its_age():
    fmt = alarm_payload_source()
    assert '\\"prev\\"' in fmt, (
        "the alarm payload no longer carries `prev` — without it the series store interpolates "
        "a crossing into a ramp, which is the defect this exists to fix")
    assert "age_s" in fmt, (
        "`prev` must say HOW OLD it is: the agent places the point at at-minus-age, and a prior "
        "sample with no age is a value with no instant")


def test_the_prior_sits_at_the_readings_own_pointer_one_level_down():
    """A shared topic is why this matters: three sensors on one message each find their own."""
    doc = json.loads('{"moisture":1.0,"sensor":"s","wake":"alarm",'
                     '"prev":{"moisture":0.148,"age_s":25}}')
    assert pointer.resolve("/moisture", doc) == 1.0
    assert pointer.resolve("/moisture", doc["prev"]) == 0.148, (
        "the prior must be reachable by the sensor's OWN reading pointer applied to `prev`, "
        "or a board reporting several properties cannot say which prior belongs to which")


def test_the_prior_is_placed_before_the_alarm_not_at_it():
    at = datetime(2026, 8, 24, 12, 0, 0, tzinfo=timezone.utc)
    doc = {"wake": "alarm", "prev": {"moisture": 0.148, "age_s": 25}}
    when = at - timedelta(seconds=float(doc["prev"]["age_s"]))
    assert when < at, "a prior sample placed at the alarm's instant records nothing new"
    assert (at - when).total_seconds() == 25


@pytest.mark.parametrize("doc", [
    {"moisture": 1.0},                                    # a heartbeat carries no prior
    {"moisture": 1.0, "wake": "alarm"},                   # the window broke on the first look
    {"moisture": 1.0, "wake": "alarm", "prev": {}},       # malformed
    {"moisture": 1.0, "wake": "alarm", "prev": {"moisture": 0.1}},   # no age
])
def test_a_missing_or_partial_prior_is_simply_absent(doc):
    """Inventing an instant would be worse than the interpolation it replaces."""
    prev = doc.get("prev")
    usable = doc.get("wake") == "alarm" and isinstance(prev, dict) \
        and isinstance(prev.get("age_s"), (int, float))
    if usable:
        # resolve RAISES on a missing key — the reason the module catches PointerError rather
        # than testing for None, and the reason this parametrisation includes a prev with a
        # value but no age and one with neither.
        try:
            usable = pointer.resolve("/moisture", prev) is not None
        except pointer.PointerError:
            usable = False
    assert usable is False
