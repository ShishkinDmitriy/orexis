"""Two couriers driving at each other down the lane's one row, booted as the lane's agents boot and walked by
its simulator ten seconds at a time (`world/lane/tests/test_lane.py`, whose head-on variant this is), each
courier's secret stated in its self graph so every draw is the same: with these two, courier B goes first.

`meeting` is the lane at the moment the two have drawn and both know who won, walked once a module; `walker`
walks a fresh one to any moment; a test that changes a store works on a copy (`copied`).
"""

from __future__ import annotations

import importlib.util
from datetime import timedelta
from pathlib import Path

import pyoxigraph as ox
import pytest

#  THE LANE'S OWN HARNESS, loaded from beside the world it walks: a world's tests are no package.
_spec = importlib.util.spec_from_file_location(
    "lane_harness", Path(__file__).resolve().parents[3] / "world" / "lane" / "tests" / "test_lane.py")
_lane_tests = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_lane_tests)
_HEAD_ON, _lane, variant = _lane_tests._HEAD_ON, _lane_tests._lane, _lane_tests.variant
CADENCE_S, L, NOW = _lane_tests.CADENCE_S, _lane_tests.L, _lane_tests.NOW

_WON_Q = "SELECT ?w WHERE { GRAPH ?g { ?draw coordination:wonBy ?w } }"


class Lane:
    """The head-on lane, its bus and the world's time, which moves only when `tick` says."""

    def __init__(self, bus, time):
        self.bus, self.time = bus, time

    def store(self, who: str) -> ox.Store:
        return self.bus.runtimes[who.rsplit("#", 1)[-1]].beliefs

    @property
    def at(self):
        return self.time["at"]

    def tick(self) -> None:
        self.time["at"] += timedelta(seconds=CADENCE_S)
        self.bus.simulator.step(self.time["at"])
        for runtime in self.bus.runtimes.values():
            runtime.run(passes=1, poll_s=0)

    def won(self, who: str) -> set[str]:
        return {r["w"].value for r in self.store(who).query(_WON_Q, prefixes={"coordination": "http://example.org/orexis/coordination#"})}


def walk(tmp_path, monkeypatch, until, limit: int = 20) -> Lane:
    """The head-on lane from its first fixes, a tick at a time until `until(lane)` holds."""
    bus, time = _lane(monkeypatch, variant(tmp_path, "head_on", _HEAD_ON))
    bus.simulator.open()
    bus.simulator.step(NOW)
    for runtime in bus.runtimes.values():
        runtime.run(passes=1, poll_s=0)
    lane = Lane(bus, time)
    for _ in range(limit):
        if until(lane):
            return lane
        lane.tick()
    raise AssertionError(f"not reached within {limit} ticks")


@pytest.fixture(scope="module")
def meeting(tmp_path_factory):
    """The lane once both couriers have concluded who won their draw."""
    patch = pytest.MonkeyPatch()
    try:
        yield walk(tmp_path_factory.mktemp("meeting"), patch,
                   lambda lane: lane.won(L + "courier_a") and lane.won(L + "courier_b"))
    finally:
        patch.undo()


@pytest.fixture
def walker(tmp_path, monkeypatch):
    """`walk`, on a lane of the test's own."""
    return lambda until, limit=20: walk(tmp_path, monkeypatch, until, limit)


def _copied(store: ox.Store) -> ox.Store:
    out = ox.Store()
    out.extend(store)
    return out


@pytest.fixture
def copied():
    """A store holding what a store holds, to change without changing it."""
    return _copied
