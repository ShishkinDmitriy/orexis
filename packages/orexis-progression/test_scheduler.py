"""Progression's clock, held: the scheduler runs no user code, a timer's function lands on the
loop and never on the thread that kept its time, and a cancelled deadline never lands.
Each was broken once and seen to fail before it was trusted."""

from __future__ import annotations

import threading
import time

from orexis_progression.scheduler import Scheduler
from orexis_progression.timer import Timer
from orexis_reactive.loop import Loop


def _wait_for(pred, timeout: float = 3.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline and not pred():
        time.sleep(0.01)


def test_a_timer_lands_on_the_loop_and_never_on_the_clock():
    loop, by = Loop("test-loop"), Scheduler(on=Loop("unused"))
    by = Scheduler(on=loop, name="test-clock")
    ran_on: list[threading.Thread] = []
    t = Timer(0.02, lambda: ran_on.append(threading.current_thread()), repeat=False, by=by)
    t.start()
    _wait_for(lambda: ran_on)
    assert len(ran_on) == 1, f"a deadline landed {len(ran_on)} times"
    assert ran_on[0].name == "test-loop", \
        "fn ran on the clock's thread — a landing must be an enqueue, never a run"
    by.stop(); loop.stop()


def test_a_cadence_rearms_after_its_function_ran_not_when_the_clock_landed():
    loop = Loop("test-loop"); by = Scheduler(on=loop, name="test-clock")
    fired: list[float] = []

    def slow():
        fired.append(time.monotonic())
        time.sleep(0.05)              # longer than the interval

    t = Timer(0.01, slow, by=by)
    t.start()
    _wait_for(lambda: len(fired) >= 3, timeout=5)
    t.stop()
    gaps = [b - a for a, b in zip(fired, fired[1:])]
    assert gaps and min(gaps) >= 0.05, \
        f"a second copy of a slow tick queued behind the first: gaps {gaps}"
    by.stop(); loop.stop()


def test_a_cancelled_deadline_never_lands():
    loop = Loop("test-loop"); by = Scheduler(on=loop, name="test-clock")
    fired: list[str] = []
    old = Timer(0.03, lambda: fired.append("old"), repeat=False, by=by)
    old.start(); old.stop()
    new = Timer(0.03, lambda: fired.append("new"), repeat=False, by=by)
    new.start()
    _wait_for(lambda: fired)
    time.sleep(0.1)
    assert fired == ["new"], f"the cancelled deadline still landed: {fired}"
    assert by.pending == 0
    by.stop(); loop.stop()


def test_the_scheduler_itself_skips_a_cancelled_entry():
    """The timer's own stop guards the function; this guards the CLOCK — a cancelled entry
    must never be handed to the loop at all, or a stopped deadline still costs an item."""
    loop = Loop("test-loop"); by = Scheduler(on=loop, name="test-clock")
    landed: list[str] = []
    gone = by.at(0.03, lambda: landed.append("gone")); gone.cancel()
    by.at(0.05, lambda: landed.append("kept"))
    _wait_for(lambda: landed)
    time.sleep(0.05)
    assert landed == ["kept"], f"a cancelled entry reached the loop: {landed}"
    by.stop(); loop.stop()
