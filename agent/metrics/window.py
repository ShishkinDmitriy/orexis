"""The window: every reported event tallied in memory, and written once a window with every level
as it last stood — the metrics part's machinery, reading an event only through its class's marks
(`model.py`), so nothing here names a package's word.

AN EVENT IS NOT A POINT. A counted event is added to the window's TALLY for its measurement and its
tags: how many (`count`), for each VALUE its sum, mean and max (`<value>_sum`, `_mean`, `_max`, all
floats, so a field never changes type between windows), and for each FLAG how many raised it
(`<flag>`, written as nought where none did, so a rate is `<flag> / count`). A LEVEL is kept as it
last stood in the window, under the same measurement and tags, and written as it is; a window in
which nobody reported a level writes none, since a level nobody says is a level nobody knows. At
the end of the window `flush` writes the tallies and the levels, every point stamped at the flush's
own instant, and opens the next.

REAL TIME, NEVER THE AGENT'S. A metric is about the process, which lives in real time, and the
agent's clock may run fast in a simulation and advances per read in a test, where one more read
changes what the run does. So the window is kept by a monotonic real clock, a flush is stamped by
the wall, and nothing here reads `agent.clock`. The window's length is a deployment fact: the
installation states it and onboarding writes it into the agent's environment as
`METRICS_INTERVAL_S`; sixty seconds where nothing says. A test drives the window with `configure` —
an interval of nought flushes every pass, and a monotonic clock of its own flushes when the test
says — and never sleeps.

OPTIONAL. Where no metrics sink is loaded (`agent.series`), nothing is tallied, and the metrics
part is not created at all, so no signal is heard for it and no event is made for it. The tally is
kept for ONE sink, and a sink installed in its place starts an empty window.

EVERY POINT IS TAGGED WITH THE WORLD AND THE AGENT (`identify`), told once by the runtime's `main`:
the agent's id is the one identifier the process is handed, and the world's name is the name of the
directory it was handed — the name the buckets, the compose project and the dashboards' folder
already go by.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from datetime import datetime, timezone
from typing import Callable

from agent.series import METRICS, sink

from .model import FLAG, LEVEL, TAG, VALUE, counted, fields_of, measurement

log = logging.getLogger("metrics")

#  THE WINDOW'S LENGTH WHERE THE ENVIRONMENT SAYS NONE, and the key it is said under.
INTERVAL_S = 60.0
INTERVAL_KEY = "METRICS_INTERVAL_S"

#  WHO SPEAKS, said by the runtime and read by every point.
_who: dict[str, str] = {}


def identify(world: str | None = None, agent: str | None = None) -> None:
    """Tag every metric point from here on with `world` and `agent` — or with neither, called bare."""
    _who.clear()
    _who.update({k: v for k, v in (("world", world), ("agent", agent)) if v})


def recording() -> bool:
    """Whether a metrics sink is loaded."""
    return sink(METRICS) is not None


def tally(event) -> None:
    """Add `event` to the window where its class reports it and a metrics sink is loaded: counted,
    its values and flags aggregated, its levels kept as they last stood — under its measurement and
    the tags it carries."""
    cls = type(event)
    name = measurement(cls)
    to = sink(METRICS)
    if name is None or to is None:
        return
    tags = tuple(sorted((t, str(v)) for t in fields_of(cls, TAG) if (v := getattr(event, t)) is not None))
    levels = {f: float(v) for f in fields_of(cls, LEVEL) if (v := getattr(event, f)) is not None}
    with _lock:
        _window_for(to)
        if counted(cls):
            _tallies.setdefault((name, tags), _Tally(fields_of(cls, VALUE), fields_of(cls, FLAG))).add(event)
        if levels:
            _levels.setdefault((name, tags), {}).update(levels)


# ---------------------------------------------------------------- the window

class _Tally:
    """One measurement's and tag set's counted events in the window."""

    __slots__ = ("names", "count", "flags", "values")

    def __init__(self, values: tuple[str, ...], flags: tuple[str, ...]):
        self.names, self.count = values, 0
        self.flags = {f: 0 for f in flags}
        self.values: dict[str, list[float]] = {}          # value -> [n, sum, max]

    def add(self, event) -> None:
        self.count += 1
        for name in self.flags:
            self.flags[name] += int(bool(getattr(event, name)))
        for name in self.names:
            value = getattr(event, name)
            if value is None or isinstance(value, bool):
                continue
            held = self.values.get(name)
            if held is None:
                self.values[name] = [1, float(value), float(value)]
            else:
                held[0] += 1
                held[1] += value
                held[2] = max(held[2], float(value))

    def fields(self) -> dict:
        out: dict = {"count": self.count, **self.flags}
        for name, (n, total, most) in self.values.items():
            out[f"{name}_sum"] = round(total, 6)
            out[f"{name}_mean"] = round(total / n, 6)
            out[f"{name}_max"] = round(most, 6)
        return out


_lock = threading.Lock()
_tallies: dict[tuple, _Tally] = {}
_levels: dict[tuple, dict[str, float]] = {}
_for = None                                   # the sink the window is kept for
_opened: float | None = None                  # when it opened, on `_monotonic`


def _now() -> datetime:
    return datetime.now(timezone.utc)


_interval_s = INTERVAL_S
_monotonic: Callable[[], float] = time.monotonic
_wall: Callable[[], datetime] = _now


def configure(*, interval_s: float | None = None, monotonic: Callable[[], float] | None = None,
              wall: Callable[[], datetime] | None = None) -> None:
    """How long a window is, and the real clocks it is kept and stamped by — each left as it is
    where not given. A test hands its own clocks and so never sleeps."""
    global _interval_s, _monotonic, _wall, _opened
    with _lock:
        if interval_s is not None:
            _interval_s = float(interval_s)
        if monotonic is not None:
            _monotonic, _opened = monotonic, None
        if wall is not None:
            _wall = wall


def reset() -> None:
    """The window's length and clocks as a process starts with them, and no tally — for a test."""
    global _interval_s, _monotonic, _wall, _for, _opened
    with _lock:
        _tallies.clear()
        _levels.clear()
        _for, _opened = None, None
        _interval_s, _monotonic, _wall = INTERVAL_S, time.monotonic, _now


def load(environ=None) -> float:
    """The window's length as the environment says it (`METRICS_INTERVAL_S`), or sixty seconds where
    it says none — a value that is no positive number is said in the log and the default kept."""
    env = os.environ if environ is None else environ
    told = env.get(INTERVAL_KEY)
    interval = INTERVAL_S
    if told:
        try:
            interval = float(told)
            if interval <= 0:
                raise ValueError(told)
        except ValueError:
            log.warning("%s=%r is no positive number of seconds — the window is %gs", INTERVAL_KEY, told, INTERVAL_S)
            interval = INTERVAL_S
    configure(interval_s=interval)
    return interval


def _window_for(to) -> None:
    """Keep the window for `to`: a sink other than the one it was kept for starts it empty. Held."""
    global _for, _opened
    if to is not _for:
        _tallies.clear()
        _levels.clear()
        _for, _opened = to, _monotonic()
    elif _opened is None:
        _opened = _monotonic()


def due() -> bool:
    """Whether the window is over, on the real monotonic clock — never where no sink is loaded."""
    to = sink(METRICS)
    if to is None:
        return False
    with _lock:
        _window_for(to)
        return _monotonic() - _opened >= _interval_s


def flush() -> list[dict]:
    """Write the window: every tally and every level as it last stood, a point per measurement and
    tag set, each at the flush's instant, and open the next. The points written — none where no sink
    is loaded, or nothing was reported."""
    global _opened
    to = sink(METRICS)
    if to is None:
        return []
    with _lock:
        _window_for(to)
        held = {key: tally.fields() for key, tally in _tallies.items()}
        for key, levels in _levels.items():
            held[key] = {**held.get(key, {}), **{k: round(v, 6) for k, v in levels.items()}}
        _tallies.clear()
        _levels.clear()
        _opened = _monotonic()
    at = _wall()
    points = [point(name, fields, at, **dict(tags)) for (name, tags), fields in held.items()]
    if points:
        to.write(points)
    return points


def point(measurement: str, fields: dict, at: datetime | None, **tags) -> dict:
    """A metric point, tagged with who speaks and `tags`."""
    return {"measurement": measurement, "fields": dict(fields), "time": at, "tags": {**_who, **tags}}
