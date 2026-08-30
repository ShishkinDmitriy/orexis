"""The loop: a queue of callables and one thread that runs them, forever, in order.

THIS IS THE EXECUTING THREAD. Everything the layers above want done — a timer landing, an act
handed to its actor, a sweep, a report — is enqueued here and runs here, one piece after
another. Before this file there was no such thread: each cadence and each deadline spawned a
`threading.Timer` of its own, so the society's work ran on however many threads happened to be
awake, and nothing could say what the agent was doing NOW.

WHAT AN ITEM MAY COST: milliseconds, and it must not wait. An item is a handler's work — decode
and write, take one act, close one round, sweep, report — atomic and bounded. An item that
sleeps, polls, or waits on a future holds every other clock in the agent, since there is one
thread here by design; an item that searches parks every handler behind seconds of planning,
which is the inversion layered-by-timescale-and-interruptibility forbids. A wait is a
scheduler entry (progression's); a search is the deliberation worker's; only their RESULTS
are items here.

The contract is three things, and the layer is the promise that it stays three:

- `submit(fn, *args)` — put one piece of work on the queue and get a `Future` back. The
  future is how a caller on ANOTHER thread waits for the result without ever touching this
  one; a caller on this thread must not wait on it, because the work it would wait for is
  behind it in the same queue (`is_current()` is how it knows).
- the loop runs whatever is submitted, in submission order, on one daemon thread, and an
  exception in one piece of work is logged and delivered through its future — it never stops
  the loop, because the loop stopping is every clock in the agent stopping.
- `stop()` — the loop finishes the piece in hand and exits; work submitted after it is
  refused, loudly, since a queue that silently accepts what will never run is the failure the
  empty-result trap already names.

What is NOT here, and stays not here: a delay (that is a timer, progression's), a wait (that
is a rescheduled check, progression's), a store, and any word of BDI. A layer whose contract
grows logic is the trigger a-layer-is-a-package-and-need-loads-it names for a rereading.

One loop per process is the ordinary case — an agent IS a process — and `loop()` answers with
it, started on first use so that merely importing this starts no thread. A `Loop` can also be
built by hand, which is what a test does to hold one it can stop.
"""

from __future__ import annotations

import logging
import queue
import threading
from concurrent.futures import Future

log = logging.getLogger("reactive")


class Loop:
    """A FIFO of work and the one thread that drains it."""

    def __init__(self, name: str = "reactive"):
        self.name = name
        self._work: queue.SimpleQueue = queue.SimpleQueue()
        self._thread: threading.Thread | None = None
        self._stopped = False
        self._lock = threading.Lock()

    # --- the contract -----------------------------------------------------------------------

    def submit(self, fn, *args, **kwargs) -> Future:
        """Enqueue one piece of work. The future resolves when it has run — here, not now."""
        future: Future = Future()
        with self._lock:
            if self._stopped:
                raise RuntimeError(f"{self.name}: the loop is stopped and would never run this")
            self._work.put((fn, args, kwargs, future))
            if self._thread is None:
                self._thread = threading.Thread(target=self._drain, name=self.name, daemon=True)
                self._thread.start()
        return future

    def is_current(self) -> bool:
        """Am I the thread that runs the work? A caller here must never wait on a future."""
        return threading.current_thread() is self._thread

    @property
    def pending(self) -> int:
        """How much is queued and not yet started — for a report, never for a decision."""
        return self._work.qsize()

    def stop(self, timeout: float | None = 5.0) -> None:
        """Finish the piece in hand and exit. Idempotent; a loop never started has nothing to do."""
        with self._lock:
            if self._stopped:
                return
            self._stopped = True
            thread = self._thread
        if thread is None:
            return
        self._work.put(None)               # the sentinel: drained after everything before it
        if not self.is_current():
            thread.join(timeout)

    # --- the loop ---------------------------------------------------------------------------

    def _drain(self) -> None:
        while True:
            item = self._work.get()
            if item is None:
                return
            fn, args, kwargs, future = item
            if not future.set_running_or_notify_cancel():
                continue
            try:
                future.set_result(fn(*args, **kwargs))
            except BaseException as exc:      # noqa: BLE001 — the loop outlives every failure
                log.error("%s: %s failed: %s", self.name, getattr(fn, "__qualname__", fn), exc)
                future.set_exception(exc)


_process_loop: Loop | None = None
_process_lock = threading.Lock()


def loop() -> Loop:
    """The process's one loop — an agent is a process, so this is the agent's executing thread.
    Built on first ask, so importing the layer starts nothing."""
    global _process_loop
    with _process_lock:
        if _process_loop is None:
            _process_loop = Loop()
        return _process_loop
