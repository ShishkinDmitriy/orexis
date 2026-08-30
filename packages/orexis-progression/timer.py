"""A cancellable timer — a CADENCE that repeats, or a DEADLINE that fires once. Landing is an
ENQUEUE, never a run.

This is the seam between the two lowest layers, and the whole reason the reactive layer is a
package. `fn` runs on the reactive loop, in the order the clocks went off, and NEVER on the
thread that kept the time: the scheduler (`scheduler.py`) sleeps until the deadline and does
one thing when it lands — `loop.submit(fn)`. So a slow `fn` delays the next one on the loop,
which is visible and measurable, and never delays a deadline being NOTICED, which was not.

Before this file `_fire` ran `fn` on the `threading.Timer` thread that woke it, so eight
callers (the deliberator's tick, upkeep, reporting's interval, the watchdog's look, actuation's
sweep, and the market's three deadlines) were eight threads doing the agent's work at once,
and nothing could be pointed at as "the executing thread".

The two kinds are not the same thing and this class used to offer only the first, which every
deadline in the market then had to pretend was what it wanted. It is not: a deadline that
rearms is a deadline that fires again for a round that has already closed.

What that cost, measured on the bench before this parameter existed. `hosting.announce`
assigns a fresh timer per round and never stopped the outgoing one, so an overlapping
announce orphaned it — still pending, still repeating, and its `fn` is `close`, which
closes whatever round is open when it lands rather than the one it was started for. The
orphan then rearmed itself in `_fire`, because `close` stops `self._timer`, which by then
is a DIFFERENT object. One overlap therefore bought a permanent heartbeat closing rounds
early, and overlaps accumulate: in six hours the simulation world opened 654 auctions and
cleared 3, with a window announced as 3s closing at a median of 1.05s — once at -0.00s,
an auction closed by an orphan at the instant it opened. Every bid arrived after the
close, so the market looked like it had no bidders when it had two bidding well.

`repeat=True` stays the default because five of the eight callers really are cadences and a
deadline is the exception that must say so. A cadence REARMS AFTER `fn` HAS RUN on the loop,
not when the clock lands — so a slow tick never queues a second copy of itself behind the
first, and the interval is a gap between runs rather than between starts, as it always was.
"""

from __future__ import annotations

from .scheduler import Entry, Scheduler, scheduler


class Timer:
    """A cadence or a deadline. Same API as it always had; what changed is where `fn` runs."""

    def __init__(self, interval_s: float, fn, repeat: bool = True, by: Scheduler | None = None):
        self.interval_s = interval_s
        self.fn = fn
        self.repeat = repeat
        #  `by` is the scheduler that keeps this timer's time, and through it the loop `fn`
        #  lands on — the process's unless a caller holds its own, which is a test that wants
        #  to stop them or a reader measuring what one loop serialises.
        self._by = by
        self._entry: Entry | None = None
        self._stopped = False

    def start(self) -> None:
        if self._stopped:
            return
        self._entry = (self._by or scheduler()).at(self.interval_s, self._run)

    def _run(self) -> None:
        """ON THE LOOP. A stop that arrived while this was queued is honoured here, so a
        deadline stopped by the round it belonged to never lands on the next one."""
        if self._stopped:
            return
        try:
            self.fn()
        finally:
            #  A deadline is spent once it lands. Rearming here is what let an orphan outlive
            #  the round it belonged to — and `stop()` from inside `fn` cannot save it, because
            #  the attribute it stops may already point at a newer timer.
            if self.repeat and not self._stopped:
                self.start()

    def stop(self) -> None:
        self._stopped = True
        if self._entry:
            self._entry.cancel()
