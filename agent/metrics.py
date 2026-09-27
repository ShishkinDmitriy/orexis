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
"""

from __future__ import annotations

import logging
from datetime import datetime

import pyoxigraph as ox

from agent.ontology import OREXIS, local_of
from agent.store import Raw, Unbound, answer, catalogue_of, graphs_of, rows

log = logging.getLogger("metrics")

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
            points.append({"measurement": measurement_of(metric["metric"]), "tags": {},
                           "fields": fields, "time": at})
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
