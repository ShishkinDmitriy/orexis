"""The meddler: someone who waters the pots and never asks the society first.

Imported by path like the other stand-ins: firmware is not a package and must never become one.
The interesting properties are negative — what it cannot do (speak anywhere but rain topics is
the ACL's, tested with the generators) and what nobody can learn (its schedule is memoryless).
"""

from __future__ import annotations

import importlib.util
import json
import random
from pathlib import Path

import pytest

MEDDLER_PY = (Path(__file__).resolve().parents[1]
              / "firmware" / "simulated-meddler" / "meddler.py")


def _load():
    spec = importlib.util.spec_from_file_location("_sim_meddler", MEDDLER_PY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


med = _load()


def _meddler(**env):
    environ = {"MEDDLER_TOPICS": json.dumps(["rain/fern", "rain/tomato"]),
               "MEDDLER_MEAN_DAYS": "2", "MEDDLER_TIMESCALE": "24",
               "MQTT_USERNAME": "u", "MQTT_PASSWORD": "p", **env}
    poured: list[tuple[str, str, bool]] = []
    with pytest.MonkeyPatch.context() as mp:
        for key, value in environ.items():
            mp.setenv(key, value)
        meddler = med.Meddler()
    meddler.client.publish = (
        lambda topic, payload, qos=0, retain=False: poured.append((topic, payload, retain)))
    return meddler, poured


def test_the_visits_average_the_stated_mean_through_the_worlds_clock():
    """Two simulated days at timescale 24 is two real hours — the exponential draws must
    average that, or the world's weather would not survive a change of pace."""
    meddler, _ = _meddler()
    meddler.rng = random.Random(0)
    draws = [meddler._interval_s() for _ in range(2000)]
    assert sum(draws) / len(draws) == pytest.approx(2 * 86400 / 24, rel=0.1)


def test_a_pour_is_a_dose_shaped_kindness_and_never_retained():
    """The soil takes {"ml": N} however it arrives; retained rain would be a flood the broker
    replays onto every restarting sensor."""
    meddler, poured = _meddler()
    meddler.rng = random.Random(1)
    meddler.pour("rain/fern")
    assert len(poured) == 1
    topic, payload, retained = poured[0]
    assert topic == "rain/fern" and not retained
    ml = json.loads(payload)["ml"]
    assert 150 <= ml <= 500, "a passing kindness, not a proper watering"


def test_each_pot_keeps_its_own_clock():
    meddler, _ = _meddler()
    assert set(meddler._due) == {"rain/fern", "rain/tomato"}
    assert meddler._due["rain/fern"] != meddler._due["rain/tomato"], \
        "kindness is not coordinated"


def test_a_meddler_with_nothing_to_water_is_refused():
    with pytest.raises(SystemExit, match="nothing to water"):
        _meddler(MEDDLER_TOPICS="[]")


def test_a_world_that_wants_no_meddling_states_no_mean():
    with pytest.raises(SystemExit, match="positive"):
        _meddler(MEDDLER_MEAN_DAYS="0")
