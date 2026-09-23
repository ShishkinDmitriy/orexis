"""The three layers meet over a pot: a reading revised, its ladder predicted, a want derived and
searched, the plan handed down, the step taken, and the world answering with the next reading.

Sensing writes and the mind reads, and neither imports the other: `revise` and `predict` leave
graphs of the kinds the Planner lays its grounds from and the Executor holds a step to, and the
sentence `surprise` answers is what a container would wake the Planner on. One world
(`worlds/a_pot_and_its_probe.trig`), four stories:

- a reading below the region is dosed, and the reading that arrives inside it is the answer;
- a reading inside the region crosses below it within the hour, and the dose is placed at the
  crossing the drift found — the search is rooted at the ground the crossing makes;
- the sensor is late, the forecast whose window has begun stands in for the reading, and a dose
  admits on its band rather than on a reading that has lapsed;
- the sensor has been silent past the whole ladder, the pot is unmeasured, and what is planned is
  a look — taken by nudging the sensor, answered by the reading that comes.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from agent import clock
from agent.execution.executor import Executor
from agent.planning.planner import Planner
from agent.sensing.predict import predict
from agent.sensing.revise import revise
from agent.sensing.surprise import surprise
from agent.store import rows

WORLD = Path(__file__).parent / "worlds" / "a_pot_and_its_probe.trig"
TEST = "http://example.org/test#"
ZZ, MOISTURE, PROBE = TEST + "zz", TEST + "moisture", TEST + "probe"
HORIZON_S = 900.0

_HEAD_Q = """
SELECT ?want ?action ?due WHERE {
  GRAPH ?g { ?i a execution:Intention ; execution:pursues ?want ; execution:by ?step .
             ?step planning:fills ?action . OPTIONAL { ?step execution:notBefore ?due }
             FILTER NOT EXISTS { ?i execution:resolvedAt ?done } } }"""

_OUTCOMES_Q = "SELECT ?o WHERE { GRAPH ?g { ?i a execution:Intention ; execution:outcome ?o } } ORDER BY ?o"


@pytest.fixture
def agent(monkeypatch, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    beliefs = snapshots.stand_in(WORLD)
    nudged: list[dict] = []
    executor = Executor(beliefs, snapshots.AGENT, take=lambda said, intention: nudged.append(said))
    planner = Planner(beliefs, snapshots.AGENT, executor=executor)
    return beliefs, planner, executor, nudged


def _reading(beliefs, snapshots, value: float, minutes: float) -> str | None:
    """A reading arrives: revised, compared with what was predicted for its instant, and its
    ladder predicted — the trio a container puts every reading through, in that order."""
    at = snapshots.NOW + timedelta(minutes=minutes)
    revise(beliefs, snapshots.ME, ZZ, MOISTURE, value, at, HORIZON_S, sensor=PROBE)
    said = surprise(beliefs, ZZ, MOISTURE)
    predict(beliefs, snapshots.ME, ZZ, MOISTURE, now=at)
    return said


def _head(executor) -> dict | None:
    head = next(iter(rows(executor.intentions, _HEAD_Q, ())), None)
    if head and head.get("due"):
        head["due"] = datetime.fromisoformat(head["due"])
    return head


def test_a_reading_below_is_dosed_and_the_next_reading_answers(agent, snapshots):
    beliefs, planner, x, nudged = agent
    assert _reading(beliefs, snapshots, 0.05, 0) is not None, "the first reading is news"
    planner.plan(snapshots.NOW)
    head = _head(x)
    assert head and head["action"] == TEST + "Dosing", head
    assert head["due"] == snapshots.NOW, "in trouble now, so the dose is placed now"
    assert x.tick(snapshots.NOW) and x.drain() == 1
    assert nudged[-1]["pot"] == ZZ and nudged[-1]["valve"] == TEST + "pump"
    x.tick(snapshots.NOW + timedelta(seconds=61))
    assert x.walking(), "landed, and the world has not answered: the pot still reads below"
    assert _reading(beliefs, snapshots, 0.22, 2) is not None, "a reading inside where below was predicted"
    x.tick(snapshots.NOW + timedelta(minutes=2))
    assert x.walking() == [] and [r["o"] for r in rows(x.intentions, _OUTCOMES_Q, ())] == ["done"]


def test_a_foreseen_crossing_places_the_dose_at_the_crossing(agent, snapshots):
    """Read inside at noon, the pot crosses below at 12:54 by the drift; the want is minted
    there, its search rooted at the ground the crossing makes, and the plan's first step may
    not be taken before it."""
    beliefs, planner, x, nudged = agent
    _reading(beliefs, snapshots, 0.25, 0)
    planner.plan(snapshots.NOW)
    head = _head(x)
    assert head and head["action"] == TEST + "Dosing"
    crossing = snapshots.NOW + timedelta(minutes=54, seconds=23)
    assert head["due"] == crossing, head["due"]
    assert x.tick(snapshots.NOW) == [], "not due: the trouble is foreseen, not now"
    assert x.tick(crossing) and x.drain() == 1
    _reading(beliefs, snapshots, 0.25, 56)      # watered, and the probe says so
    x.tick(snapshots.NOW + timedelta(minutes=56))
    assert x.walking() == []


def test_a_late_sensors_forecast_stands_in_and_a_dose_admits_on_its_band(agent, snapshots):
    """Read below at eleven and silent since: at noon the reading has lapsed and the first
    window of its ladder stands in — below — so the dose is available on the forecast's band
    and placed now, on no reading at all."""
    beliefs, planner, x, nudged = agent
    _reading(beliefs, snapshots, 0.05, -60)
    planner.plan(snapshots.NOW)
    head = _head(x)
    assert head and head["action"] == TEST + "Dosing", head
    assert head["due"] == snapshots.NOW


def test_silence_past_the_ladder_is_unmeasured_and_a_look_is_planned(agent, snapshots):
    """Read two days ago and nothing since: every window of the ladder has closed, the pot is
    unmeasured, and the one lever that admits is the look — taken by nudging the probe, and
    answered by the reading it sends, whatever band that is."""
    beliefs, planner, x, nudged = agent
    _reading(beliefs, snapshots, 0.22, -2 * 24 * 60)
    planner.plan(snapshots.NOW)
    head = _head(x)
    assert head and head["action"] == TEST + "Observing", head
    assert x.tick(snapshots.NOW) and x.drain() == 1
    assert nudged[-1]["sensor"] == PROBE
    _reading(beliefs, snapshots, 0.31, 1)       # above the region, and still the answer to a look
    x.tick(snapshots.NOW + timedelta(minutes=1))
    assert x.walking() == [] and [r["o"] for r in rows(x.intentions, _OUTCOMES_Q, ())] == ["done"]
    planner.plan(snapshots.NOW + timedelta(minutes=1))
    assert _head(x) is None, "above the region, and nothing here lowers it: no plan, and no look either"
