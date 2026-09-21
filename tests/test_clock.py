"""One timeline, and a clock that may run fast (#646,
the-agent-keeps-one-timeline-and-its-clock-may-run-fast).

Every instant an agent writes and every stretch it keeps are in one timeline; a compressed world
is the runtime's clock running fast, paced by a deployment fact, with the one conversion at the
sleep. The mind never learns a unit: a day is a day of the timeline, and the drift's arithmetic
is untouched.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from orexis_agent_deliberation import judging, pursuit
from orexis_agent_deliberation.derive_wants import derive_wants
from orexis_agent_progression import clock
from orexis_agent_progression.ontology import picks_graph
from orexis_agent_progression.scheduler import Scheduler
from orexis_agent_progression.timer import Timer
from conftest import build_agent, genesis_store, wired_sensors, write_reading

MOISTURE = "http://example.org/orexis/water#SoilMoisture"


@pytest.fixture
def paced():
    """The simulation's pace — ten bench minutes a day — for one test, and a real clock after."""
    clock.configure(pace=144.0, epoch=datetime.now(timezone.utc))
    try:
        yield 144.0
    finally:
        clock.configure(pace=1.0, epoch=None)


def test_a_real_clock_is_the_wall_clock():
    assert clock.pace() == 1.0
    assert abs((clock.now() - datetime.now(timezone.utc)).total_seconds()) < 0.01


def test_the_clock_runs_at_the_pace(paced):
    before = clock.now()
    time.sleep(0.1)
    ahead = (clock.now() - before).total_seconds()
    assert 12.0 < ahead < 20.0, f"a tenth of a real second is fourteen of the world's: {ahead}"
    assert clock.real_delay(144.0) == pytest.approx(1.0), "the one conversion: a delay in the world's seconds is real seconds over the pace"


def test_a_deadline_in_the_worlds_seconds_lands_in_real_seconds_over_the_pace(paced):
    """The scheduler keeps real time and converts once, where it sleeps."""
    landed = []
    keeper = Scheduler(on=SimpleNamespace(submit=lambda fn, *a, **k: landed.append(fn(*a, **k))), name="paced-test")
    try:
        Timer(72.0, lambda: landed.append("landed"), repeat=False, by=keeper).start()
        deadline = time.monotonic() + 3.0
        while len(landed) < 2 and time.monotonic() < deadline:
            time.sleep(0.05)
        assert "landed" in landed, "seventy-two of the world's seconds are half a real second at a pace of a hundred and forty-four"
    finally:
        keeper.stop(timeout=1.0)


def test_the_simulation_fern_foresees_and_places_under_the_worlds_pace(monkeypatch, paced):
    """The bench in the tests' clothes: the fern at 0.47, drying at 0.12 a day, may be below its
    floor by five of the world's hours, so the crossing is an hour out — the start of the window
    that reaches five — twenty-five bench seconds; foreseeing six, it derives the want AT the
    crossing and places the purchase ahead of it. Nothing in the agent knows the pace: the
    crossing is an hour of its own timeline, and the placed instant is in it."""
    st = genesis_store({("fern", MOISTURE): 0.47})
    #  THE INSTANT THE WORLD WAS MADE, which is what the crossing is an hour out FROM. Read at
    #  assert time instead, `clock.now()` has run on by however long genesis and boot took —
    #  times the world's pace, so 4.6 bench seconds of boot is 660 of the agent's, and the
    #  tolerance was absorbing that rather than measuring anything. Under enough parallel load
    #  it stopped fitting: boot alone is 4.18s of a 6.25s budget on this bench, measured.
    made = clock.now()
    agent = build_agent("fern", st, monkeypatch)
    desire = next(d for d in agent.considering() if getattr(d, "observed_property", None) == MOISTURE and not d.is_epistemic)
    derive_wants(agent.beliefs.engine)   # a crossing is what the last judging found
    #  AND THE PROJECTION WITH IT, which every production caller of the derivation pairs with
    #  it (`pursuit.derived`) and this raw one must too. The planner compiles a want's met-test
    #  from the desire modality, so a want minted without a rebuild has no met-test to be
    #  judged by — and used to be judged anyway, because the measure read the belief base live
    #  and needed no projection at all. See #766.
    agent.desires.rebuild()
    crossing = judging.crossing_of(agent.beliefs.engine, desire.uri)
    assert crossing is not None
    ahead = (crossing - made).total_seconds()
    assert abs(ahead - 3600.0) < 300.0, f"an hour of the agent's timeline from when the world was made: {ahead}"
    from conftest import open_round_for
    open_round_for(agent, "fern", seconds=3600.0)   # an hour of the world: twenty-five real seconds
    uri = pursuit.pursue(agent, desire)
    assert uri is not None, "a purchase that lands in nine hundred of the world's seconds is ahead of a crossing four hours out"
    child = next(d for d in agent.considering() if getattr(d, "observed_property", None) == MOISTURE and not d.is_epistemic)
    assert child.holds_at is not None and abs((child.holds_at - crossing).total_seconds()) < 1.0
