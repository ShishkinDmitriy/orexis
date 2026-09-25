"""THE CLOCK: one timeline, and it may run fast
(the-agent-keeps-one-timeline-and-its-clock-may-run-fast).

An agent writes instants — a reading's `resultTime`, a period's start and end, a want's
`holdsAt`, a step's `notBefore`, a debt's expiry — and keeps stretches — a cadence, a grace, a
patience, a landing, the `$elapsed` a drift is handed — and every one of them is in ONE
timeline. A day is eighty-six thousand four hundred of its seconds wherever the agent runs, and
a rule may say so: the literal is the timeline's own arithmetic, never a unit the mind learned.

A compressed world is not a fact the rules read; it is this clock running fast. Progression
is the layer that keeps time, so the clock is its: `now()` is what every layer and package
reads instead of the wall clock, and the one conversion is at the sleep — a delay of so many
of the agent's seconds is that many real seconds over the PACE (`real_delay`). The pace is a
deployment fact, environment and never a belief (rule 5): `OREXIS_TIME_PACE`, world seconds
per real second, handed by compose to every process of a world alike — the agents' clocks
and the stand-ins' physics, ticks and pours — from the pace the world states. The mind
cannot ask for it. The timeline's origin is fixed with the pace, `OREXIS_TIME_EPOCH`, so a
restarted agent's `now()` lands where the world's clock stands and every instant it wrote
before still means what it meant; a paced clock with no epoch stated starts its timeline at
the process's own start, which is a bench convenience and a restart's discontinuity.

What stays real: how long a pass took to compute, how long a sweep ran, the process's uptime
— resources, not the world's time — and the socket's own timeouts, which are the transport's.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone

_pace: float = 1.0
_epoch: datetime | None = None          # the instant the timeline is measured from
_epoch_real: float | None = None        # the same instant, on the real clock


def configure(pace: float | None = None, epoch: datetime | str | None = None) -> None:
    """Set the pace and the epoch — from the environment where a caller says nothing, which
    is what the process does at import. A test that runs an agent on a fast clock calls this
    and calls it again with a pace of one when it is done."""
    global _pace, _epoch, _epoch_real
    if pace is None:
        pace = float(os.environ.get("OREXIS_TIME_PACE", "1") or 1)
    if pace <= 0:
        raise ValueError(f"a clock's pace is positive, not {pace}")
    if epoch is None:
        epoch = os.environ.get("OREXIS_TIME_EPOCH") or None
    if isinstance(epoch, str):
        epoch = datetime.fromisoformat(epoch)
        if epoch.tzinfo is None:
            epoch = epoch.replace(tzinfo=timezone.utc)
    real = datetime.now(timezone.utc)
    _pace = float(pace)
    _epoch = epoch if epoch is not None else real
    _epoch_real = real.timestamp() if epoch is None else _epoch.timestamp()


def pace() -> float:
    """World seconds per real second. One, unless the world this process runs in says otherwise."""
    return _pace


def now() -> datetime:
    """The agent's instant. The wall clock at a pace of one; past the epoch at the pace otherwise."""
    real = datetime.now(timezone.utc)
    if _pace == 1.0:
        return real
    return _epoch + (real - datetime.fromtimestamp(_epoch_real, tz=timezone.utc)) * _pace


def real_delay(seconds: float) -> float:
    """How long to actually sleep for `seconds` of the agent's time — the one conversion."""
    return max(0.0, float(seconds)) / _pace


def monotonic() -> float:
    """A stretch-keeper in the agent's seconds, for code that measures an age or a deadline
    against a monotonic reading rather than an instant."""
    return time.monotonic() * _pace


configure()
