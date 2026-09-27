"""The metrics a pass writes: every select the loaded packages ship, run over the store it names.

HOW THE AGENT IS DOING IS MOSTLY ROWS ALREADY (a-documents-kind-says-who-reads-it, §6). A plan's
`planning:Exhausted`, the weighings a search keeps, an intention resolved `failed`, a sensor's
`sensing:silentSince`, a revision's `belief:settled false` — each is written by the package that
decides it, for its own reasons. So a package does not count: it ships a select over its own rows
in its own `metrics.ttl`, a graph of kind `orexis:MetricGraph`, and this module runs every one it
finds by that kind. **No list of them exists**, here or in the runtime: a package's metrics are
loaded where the package is (#824), and a package not loaded counts nothing.

NOT PUBLIC, and the kind says so: `orexis:MetricGraph` is beneath `orexis:Graph` alone, so no rule
reads a select as a fact of the world and `prepare_ground` copies none into a possible world.

A METRIC SAYS WHICH STORE IT IS RUN OVER, `orexis:over` a repository class, and the runtime — which
holds the stores — hands this module each class's stores: the belief base, the Planner's
imaginaria, the executor's intentions store. Said rather than defaulted, because running every
select over every store is wrong in the quiet direction: the imaginaria copy the belief base's
readings and catalogue, so a silent sensor would be counted once per scope.

A FIGURE IS A COUNT. A select's columns are its figures; its rows over every store of the
repository are SUMMED, which is right for a count and for nothing else, and the imaginaria are one
per scope. A select may read the catalogue as `$cat`, bound where the store has one. The point is
measured under the metric's local name — the document's own `<#cone>` — and the field under the
column's; an integer stays an integer, since a field that flips between integer and float is a
point the store refuses.

A SELECT THAT FAILS costs the agent nothing: said in the log, and the other metrics are written.

**AND WHAT HAPPENED, AND HOW LONG IT TOOK, IS AN EVENT** — which no select can answer, and which
must never become a row, since no plan branches on how long a search took. So an event is
contributed the way history is (§5): the package that does the work asks for the metrics sink as
it happens (`event`), and where none is loaded it computes nothing — `recording()` is asked before
anything is timed or read. A select says what state the stores are in; an event says what the
pass did.

COMPUTE TIME IS `time.perf_counter`, NEVER THE AGENT'S CLOCK. The agent's timeline runs fast in a
simulation, and a test's clock advances per read — "a read of the clock is a tick in a test" — so
a timing that read `clock.now()` would be wrong in the one and would change the other's behaviour.
Nothing here reads the clock at all: an event is stamped at the instant of the pass in progress,
which the runtime says once (`begin`), plus the real seconds since, at the clock's pace — distinct
per event, since two points of one measurement, one tag set and one instant are one point to the
store, and in the agent's timeline, where the gauges and the history are.

EVERY POINT IS TAGGED WITH THE WORLD AND THE AGENT (`identify`), told once by the runtime's `main`:
the agent's id is the one identifier the process is handed, and the world's name is the name of
the directory it was handed — the name the buckets, the compose project and the dashboards' folder
already go by. An event about a want is tagged with the DESIRE it was derived under, so a desire
reads across worlds and agents; the want's own name is a FIELD, never a tag, because a want is
minted per instance and a tag of unbounded values breaks the store's index.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta

import pyoxigraph as ox

from agent import clock
from agent.ontology import OREXIS, local_of
from agent.series import METRICS, sink
from agent.store import Raw, Unbound, answer, catalogue_of, graphs_of, rows

log = logging.getLogger("metrics")

#  WHO SPEAKS, and the pass in progress: said by the runtime, read by every point.
_who: dict[str, str] = {}
_pass: tuple[datetime, float] | None = None


def identify(world: str | None = None, agent: str | None = None) -> None:
    """Tag every metric point from here on with `world` and `agent` — or with neither, called bare."""
    _who.clear()
    _who.update({k: v for k, v in (("world", world), ("agent", agent)) if v})


def begin(at: datetime) -> None:
    """A pass begins at the agent's instant `at`: events until the next are stamped from it."""
    global _pass
    _pass = (at, time.perf_counter())


def recording() -> bool:
    """Whether a metrics sink is loaded — asked before anything is timed or read for an event."""
    return sink(METRICS) is not None


def stamp() -> datetime | None:
    """The instant an event happens at: the pass's, moved on by the real seconds since at the
    clock's pace — reading no clock. None before any pass, and the store stamps it."""
    if _pass is None:
        return None
    at, started = _pass
    return at + timedelta(seconds=(time.perf_counter() - started) * clock.pace())


def point(measurement: str, fields: dict, at: datetime | None = None, **tags) -> dict:
    """A metric point, tagged with who speaks and `tags` — a tag of None is left out."""
    return {"measurement": measurement, "fields": dict(fields), "time": at if at is not None else stamp(),
            "tags": {**_who, **{k: v for k, v in tags.items() if v is not None}}}


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


def event(measurement: str, fields: dict, **tags) -> None:
    """Contribute what just happened to the metrics sink, where one is loaded; nothing where not."""
    if (to := sink(METRICS)) is not None:
        to.write([point(measurement, fields, **tags)])

METRIC_GRAPH = OREXIS + "MetricGraph"

#  EVERY METRIC THE LOADED PACKAGES SHIP, read off the graphs of its kind and nowhere else.
_METRICS_Q = """
SELECT ?metric ?over ?select WHERE { ?metric a orexis:Metric ; orexis:over ?over ; sh:select ?select }
ORDER BY ?metric"""

_XSD = "http://www.w3.org/2001/XMLSchema#"
_INTEGERS = {_XSD + t for t in ("integer", "int", "long", "short", "byte", "nonNegativeInteger",
                                 "positiveInteger", "unsignedInt", "unsignedLong")}
_REALS = {_XSD + t for t in ("decimal", "double", "float")}


def declared(beliefs: ox.Store) -> list[dict]:
    """Every metric the belief base holds a select for, as {metric, over, select}, by its IRI."""
    return rows(beliefs, _METRICS_Q, graphs_of(beliefs, METRIC_GRAPH))


_EVENTS_Q = """SELECT ?event ?field WHERE { ?event a orexis:Event ; orexis:field ?field } ORDER BY ?event ?field"""


def events(beliefs: ox.Store) -> dict[str, list[str]]:
    """Every event the loaded packages declare, by the measurement it is written under, with the
    fields it carries — what a dashboard draws, read where the metrics are."""
    out: dict[str, list[str]] = {}
    for r in rows(beliefs, _EVENTS_Q, graphs_of(beliefs, METRIC_GRAPH)):
        out.setdefault(measurement_of(r["event"]), []).append(r["field"])
    return out


def measurement_of(metric: str) -> str:
    """The measurement a metric's point is written under: the metric's local name."""
    return local_of(metric)


def measure(beliefs: ox.Store, repositories: dict[str, list[ox.Store]], at: datetime) -> list[dict]:
    """A point per metric the belief base declares, at `at`: its select run over every store
    `repositories` holds for the class it is `orexis:over`, each column summed across them. A
    metric over a repository with no store, or whose select answers nothing, writes no point."""
    points = []
    for metric in declared(beliefs):
        fields: dict[str, int | float | bool] = {}
        for store in repositories.get(metric["over"], ()):
            try:
                found = _run(store, metric["select"])
            except Exception as exc:                               # noqa: BLE001
                log.warning("the metric %s could not be read: %s", measurement_of(metric["metric"]), exc)
                continue
            for name, value in found.items():
                fields[name] = fields.get(name, 0) + value
        if fields:
            points.append(point(measurement_of(metric["metric"]), fields, at))
    return points


def _run(store: ox.Store, select: str) -> dict[str, int | float]:
    """The columns of every row `select` answers over `store`, summed, each as the number it is.
    A column that binds nothing is not a figure, and neither is one that binds no number."""
    cat = catalogue_of(store)
    if cat is None and "$cat" in select:
        raise Unbound("the metric reads the catalogue and this store has none")
    result = answer(store, select, (), **({"cat": Raw(f"<{cat}>")} if cat is not None else {}))
    out: dict[str, int | float] = {}
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
