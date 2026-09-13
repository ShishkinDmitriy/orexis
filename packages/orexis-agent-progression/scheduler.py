"""The scheduler: one thread that sleeps until the next deadline and enqueues what is due.

THE SECOND OF THE THREE THREADS, and the one that runs no user code at all. The three-layer
ruling (layered-by-timescale-and-interruptibility) gives each row one thread of its own: the
reactive loop runs work, the deliberation worker searches, and this one KEEPS TIME. It holds
a heap of deadlines, sleeps until the earliest, and when it lands it does exactly one thing —
`loop.submit(callback)` — and goes back to sleep. A callback never runs here, so a slow one
cannot delay the next deadline's enqueue; and a wait is never a sleep on the loop, because a
wait IS an entry here that enqueues a check when it is due.

Before this file there were as many clock threads as pending timers — a `threading.Timer`
each — and the clock threads ran the callbacks. Eight callers, eight threads doing the
agent's work at once, and no thread anyone could point at as the one keeping time.

The contract is `at(delay_s, callback) -> Entry` and `Entry.cancel()`. A cancelled entry is
left in the heap and skipped when it surfaces, which is cheaper than re-heaping and is what
lets a deadline be stopped from inside the round that owned it. `scheduler()` answers with the
process's one, started on first use; a `Scheduler` built by hand is what a test holds.
"""

from __future__ import annotations

import heapq
import itertools
import logging
import threading
from . import clock
import time

from orexis_agent_reactive.loop import Loop, loop

log = logging.getLogger("scheduler")


class Entry:
    """One deadline. `cancel()` before it lands and it never enqueues."""

    __slots__ = ("due", "callback", "cancelled")

    def __init__(self, due: float, callback):
        self.due = due
        self.callback = callback
        self.cancelled = False

    def cancel(self) -> None:
        self.cancelled = True


class Scheduler:
    """A heap of deadlines and the one thread that sleeps until the earliest."""

    def __init__(self, on: Loop | None = None, name: str = "scheduler"):
        self.name = name
        self._on = on
        self._heap: list[tuple[float, int, Entry]] = []
        self._seq = itertools.count()
        self._cv = threading.Condition()
        self._thread: threading.Thread | None = None
        self._stopped = False

    # --- the contract -----------------------------------------------------------------------

    def at(self, delay_s: float, callback) -> Entry:
        """Enqueue `callback` onto the loop `delay_s` from now. Returns the entry, to cancel."""
        #  THE ONE CONVERSION (the-agent-keeps-one-timeline-and-its-clock-may-run-fast): a
        #  delay is in the agent's seconds, and the sleep is real seconds over the pace.
        entry = Entry(time.monotonic() + clock.real_delay(delay_s), callback)
        with self._cv:
            if self._stopped:
                raise RuntimeError(f"{self.name}: stopped, and would never land this")
            heapq.heappush(self._heap, (entry.due, next(self._seq), entry))
            if self._thread is None:
                self._thread = threading.Thread(target=self._keep_time, name=self.name,
                                                daemon=True)
                self._thread.start()
            self._cv.notify()
        return entry

    @property
    def pending(self) -> int:
        """Deadlines not yet landed, cancelled ones included — for a report, never a decision."""
        with self._cv:
            return sum(1 for _, _, e in self._heap if not e.cancelled)

    def stop(self, timeout: float | None = 5.0) -> None:
        with self._cv:
            if self._stopped:
                return
            self._stopped = True
            thread = self._thread
            self._cv.notify_all()
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout)

    # --- the thread -------------------------------------------------------------------------

    def _keep_time(self) -> None:
        while True:
            with self._cv:
                while not self._stopped:
                    if not self._heap:
                        self._cv.wait()
                        continue
                    due, _, entry = self._heap[0]
                    if entry.cancelled:
                        heapq.heappop(self._heap)
                        continue
                    wait = due - time.monotonic()
                    if wait > 0:
                        self._cv.wait(wait)      # a newer, earlier entry notifies and rewakes
                        continue
                    heapq.heappop(self._heap)
                    break
                else:
                    return
            #  Outside the lock, and the ONLY thing this thread does with an entry: hand it to
            #  the loop. Not run it — that is the whole of the design.
            try:
                (self._on or loop()).submit(entry.callback)
            except RuntimeError as exc:      # the loop is stopped: the agent is shutting down
                log.debug("%s: %s", self.name, exc)


_process_scheduler: Scheduler | None = None
_process_lock = threading.Lock()


def scheduler() -> Scheduler:
    """The process's one scheduler — an agent is a process — built on first ask."""
    global _process_scheduler
    with _process_lock:
        if _process_scheduler is None:
            _process_scheduler = Scheduler()
        return _process_scheduler
