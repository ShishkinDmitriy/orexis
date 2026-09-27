"""How the agent is doing, told to whoever administers it — the kernel of it, and nothing any package says.

METRICS ARE THE ADMINS' INSTRUMENTATION OF THE AGENT — code watching code, not a description of
anything — so they live in code and nowhere in the model (a-documents-kind-says-who-reads-it, its
amendment "metrics are code each package owns"). No graph declares one and no row holds one.
Each package that reports keeps everything it reports in ONE module, `agent/<package>/metrics.py`:
its GAUGES, what a store it owns holds, and its EVENTS, what happened and how long it took, called
from its acts as they happen. The runtime's own are in `agent/runtime.py`. Adding a metric is
editing that module; `orexis-dashboards` draws what the modules hold by importing them, and a
package's module is imported only where the package is loaded (#824).

A GAUGE IS SAMPLED ONCE A WINDOW, at the flush, over the stores its package's `gauges` is handed
— and which store that is is said, never defaulted: the imaginaria copy the belief base's readings
and its catalogue, so a select run over every store counted one silent sensor once per scope. A
select's figures are summed across the stores it is handed, so a select-gauge's figure is a count.

AN EVENT IS NOT A POINT. It is added to the window's TALLY for its measurement and its tags: how
many (`count`), for each VALUE its sum, mean and max (`<value>_sum`, `_mean`, `_max`, all floats,
so a field never changes type between windows), and for each FLAG how many raised it (`<flag>`,
written as nought where none did, so a rate is `<flag> / count`). A field or tag the event does not
declare is said in the log once and left out. At the end of the window the runtime samples every
gauge, and `flush` writes the gauges and the tallies, every point stamped at the flush's own
instant, and opens the next window.

REAL TIME, NEVER THE AGENT'S. A metric is about the process, which lives in real time, and the
agent's clock may run fast in a simulation and advances per read in a test, where one more read
changes what the run does. So a duration is `time.perf_counter` (`Laps`), the window is kept by a
monotonic real clock, a flush is stamped by the wall, and nothing here reads `agent.clock`. The
window's length is a deployment fact: the installation states it and onboarding writes it into
the agent's environment as `METRICS_INTERVAL_S`; sixty seconds where nothing says. A test drives
the window with `configure` — an interval of nought flushes every pass, and a monotonic clock of its
own flushes when the test says — and never sleeps.

OPTIONAL. Where no metrics sink is loaded (`agent.series`), `recording()` is False: nothing is
tallied, timed, sampled or read, and a caller asks it before computing anything for an event. The
tally is kept for ONE sink, and a sink installed in its place starts an empty window.

EVERY POINT IS TAGGED WITH THE WORLD AND THE AGENT (`identify`), told once by the runtime's `main`:
the agent's id is the one identifier the process is handed, and the world's name is the name of the
directory it was handed — the name the buckets, the compose project and the dashboards' folder
already go by. An event about a want is tagged with the DESIRE it was derived under, so a desire
reads across worlds and agents; the want's own name is on NO point, since a want is minted per
instance, a tag of unbounded values breaks the store's index, and a name cannot be aggregated —
the log names the want, and history carries it on a step.
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from datetime import datetime, timezone
from typing import Callable, Iterable

import pyoxigraph as ox

from agent.series import METRICS, sink
from agent.store import Raw, Unbound, answer, catalogue_of

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
    """Whether a metrics sink is loaded — asked before anything is timed or read for a metric."""
    return sink(METRICS) is not None


# ---------------------------------------------------------------- what a package declares


class Gauge:
    """What a store holds, sampled once a window: a `select` whose columns are the figures, summed
    across the stores its package's `gauges` is handed — or, where the figure is no select's,
    `read(stores)` answering the fields itself. `unit` is how a panel draws it."""

    def __init__(self, name: str, select: str | None = None, *,
                 read: Callable[[list[ox.Store]], dict] | None = None, unit: str = "none"):
        if (select is None) == (read is None):
            raise ValueError(f"the gauge {name} is a select or a read, and one of them")
        self.name, self.select, self.read, self.unit = name, select, read, unit

    def sample(self, stores: Iterable[ox.Store]) -> dict:
        stores = list(stores)
        return self.read(stores) if self.read is not None else counted(stores, self.select)

    def __repr__(self) -> str:
        return f"Gauge({self.name!r})"


class Event:
    """What happened, tallied in the window: `values` are aggregated as sum, mean and max, `flags`
    counted where raised, and `tags` — beside the world and the agent every point carries — are
    what a tally is kept apart by, so a tag's values must stay few."""

    def __init__(self, name: str, *, values: tuple[str, ...] = (), flags: tuple[str, ...] = (),
                 tags: tuple[str, ...] = ()):
        self.name, self.values, self.flags, self.tags = name, tuple(values), tuple(flags), tuple(tags)

    def __call__(self, fields: dict | None = None, **tags) -> None:
        """It happened: tallied where a metrics sink is loaded, and nothing where none is."""
        to = sink(METRICS)
        if to is None:
            return
        told = {k: str(v) for k, v in tags.items() if v is not None}
        for name in [k for k in told if k not in self.tags]:
            _once(f"{self.name} is tagged {name}, which it does not declare — left out")
            del told[name]
        with _lock:
            _window_for(to)
            _tallies.setdefault((self.name, tuple(sorted(told.items()))), _Tally(self)).add(fields or {})

    @property
    def written(self) -> tuple[str, ...]:
        """Every field a point of this event carries: its count, its flags, and each value's three."""
        return ("count", *self.flags, *(f"{v}_{how}" for v in self.values for how in ("sum", "mean", "max")))

    def __repr__(self) -> str:
        return f"Event({self.name!r})"


def declared(module: str) -> list[Gauge | Event]:
    """Every gauge and event the module named `module` holds, in the order it states them — what a
    package reports, read off its `metrics.py`, and what the dashboards draw."""
    return [v for v in vars(sys.modules[module]).values() if isinstance(v, (Gauge, Event))]


def sample(module: str, stores: Iterable[ox.Store]) -> list[tuple[Gauge, dict]]:
    """Every gauge of the module named `module`, sampled over `stores` — a gauge that fails costs
    the agent nothing: said in the log, and the others are sampled."""
    stores = list(stores)
    out = []
    for gauge in declared(module):
        if not isinstance(gauge, Gauge):
            continue
        try:
            out.append((gauge, gauge.sample(stores)))
        except Exception as exc:                                   # noqa: BLE001
            log.warning("the gauge %s could not be read: %s", gauge.name, exc)
    return out


# ---------------------------------------------------------------- a select's figures

_XSD = "http://www.w3.org/2001/XMLSchema#"
_INTEGERS = {_XSD + t for t in ("integer", "int", "long", "short", "byte", "nonNegativeInteger",
                                 "positiveInteger", "unsignedInt", "unsignedLong")}
_REALS = {_XSD + t for t in ("decimal", "double", "float")}


def counted(stores: Iterable[ox.Store], select: str) -> dict[str, int | float]:
    """The columns of every row `select` answers over each of `stores`, summed across them, each as
    the number it is — an integer stays one, since a field that flips between integer and float is
    a point the store refuses. A select may read the catalogue as `$cat`; a column binding no number
    is no figure."""
    out: dict[str, int | float] = {}
    for store in stores:
        cat = catalogue_of(store)
        if cat is None and "$cat" in select:
            raise Unbound("the gauge reads the catalogue and this store has none")
        result = answer(store, select, (), **({"cat": Raw(f"<{cat}>")} if cat is not None else {}))
        for row in result.get("results", {}).get("bindings", []):
            for name, term in row.items():
                value = _number(term)
                if value is not None:
                    out[name] = out.get(name, 0) + value
    return out


def _number(term: dict) -> int | float | None:
    datatype = term.get("datatype")
    if term.get("type") != "literal" or datatype is None:
        return None
    if datatype in _INTEGERS:
        return int(term["value"])
    if datatype in _REALS:
        return float(term["value"])
    return None


# ---------------------------------------------------------------- the window

class _Tally:
    """One measurement's and tag set's events in the window."""

    __slots__ = ("event", "count", "flags", "values")

    def __init__(self, event: Event):
        self.event, self.count = event, 0
        self.flags = {f: 0 for f in event.flags}
        self.values: dict[str, list[float]] = {}          # value -> [n, sum, max]

    def add(self, fields: dict) -> None:
        self.count += 1
        for name, value in fields.items():
            if name in self.flags:
                self.flags[name] += int(bool(value))
            elif name in self.event.values and isinstance(value, (int, float)) and not isinstance(value, bool):
                held = self.values.get(name)
                if held is None:
                    self.values[name] = [1, float(value), float(value)]
                else:
                    held[0] += 1
                    held[1] += value
                    held[2] = max(held[2], float(value))
            else:
                _once(f"{self.event.name} carries {name}, which it does not declare a value or a flag — left out")

    def fields(self) -> dict:
        out: dict = {"count": self.count, **self.flags}
        for name, (n, total, most) in self.values.items():
            out[f"{name}_sum"] = round(total, 6)
            out[f"{name}_mean"] = round(total / n, 6)
            out[f"{name}_max"] = round(most, 6)
        return out


_lock = threading.Lock()
_tallies: dict[tuple, _Tally] = {}
_for = None                                   # the sink the window is kept for
_opened: float | None = None                  # when it opened, on `_monotonic`
_warned: set[str] = set()


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


def flush(gauges: Iterable[tuple[Gauge, dict]] = ()) -> list[dict]:
    """Write the window: every gauge as sampled now and every tally, each point at the flush's
    instant, and open the next. The points written — none where no sink is loaded."""
    global _opened
    to = sink(METRICS)
    if to is None:
        return []
    with _lock:
        _window_for(to)
        tallies = list(_tallies.items())
        _tallies.clear()
        _opened = _monotonic()
    at = _wall()
    points = [point(gauge.name, fields, at) for gauge, fields in gauges if fields]
    points += [point(name, tally.fields(), at, **dict(tags)) for (name, tags), tally in tallies]
    to.write(points)
    return points


def point(measurement: str, fields: dict, at: datetime | None, **tags) -> dict:
    """A metric point, tagged with who speaks and `tags`."""
    return {"measurement": measurement, "fields": dict(fields), "time": at, "tags": {**_who, **tags}}


def _once(said: str) -> None:
    if said not in _warned:
        _warned.add(said)
        log.warning(said)


class Laps:
    """Real seconds spent per part of something, each lap from the last, as `<part>_s` — by
    `perf_counter`, the process's and not the agent's clock. Made only where a sink is loaded."""

    def __init__(self):
        self.spent: dict[str, float] = {}
        self._mark = time.perf_counter()

    def __call__(self, part: str) -> None:
        now = time.perf_counter()
        self.spent[f"{part}_s"] = round(self.spent.get(f"{part}_s", 0.0) + (now - self._mark), 6)
        self._mark = now
