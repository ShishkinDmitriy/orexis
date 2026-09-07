"""A reading's identity is its cell — the partition every reader already implies (#573).

Between two neighbouring thresholds some rule compares a property against, no rule can tell
two values apart, so neither the world nor a plan can behave differently: 0.25 and 0.27 are
one world, and so are 0.30 and 0.31, the drift that used to kill a plant's cone. Deliberation
reasons over cells; progression keeps the numbers — the actor sizes the dose against the live
reading and the keeper holds the world to the step's predicted number, both untouched.

THE THRESHOLDS ARE READ, NEVER AUTHORED. Per property: the bounds of every shape that
constrains a reading of it — a want's region, the survival envelope, a law — and the constants
a select compares the reading's variable against, walked by the same parser relevance uses. A
property whose readers are not all readable — a select comparing its reading against a
VARIABLE, which the parser cannot resolve to a number — stays point-valued, the discipline
relevance keeps applied to values: a boundary the parser cannot see would collapse two worlds
a rule tells apart, quietly, and that is this repository's signature way of being wrong.

A cell is written into a canonical fact as `("cell", lo, hi)`, its bounds rather than an index,
so a premise kept before a region was re-picked matches nothing rather than the wrong cell.
"""

from __future__ import annotations

import logging
import math

import rdflib
from rdflib import Literal, URIRef, Variable
from rdflib.plugins.sparql.algebra import translateQuery
from rdflib.plugins.sparql.parser import parseQuery
from rdflib.plugins.sparql.parserutils import CompValue

from orexis_agent_progression.store import PREFIXES

from .relevance import parseable

log = logging.getLogger("partition")

SOSA = "http://www.w3.org/ns/sosa/"
_SH = rdflib.Namespace("http://www.w3.org/ns/shacl#")
_RESULT = URIRef(SOSA + "hasSimpleResult")
_PROPERTY = URIRef(SOSA + "observedProperty")
_BOUNDS = (_SH.minExclusive, _SH.maxExclusive, _SH.minInclusive, _SH.maxInclusive)


def thresholds_of(shapes: rdflib.Graph) -> dict[str, set[float]]:
    """Per property, the numbers the shapes in `shapes` compare a reading of it against: a
    property shape on `sosa:hasSimpleResult` carrying a bound, inside a node shape that pins
    `sosa:observedProperty` by `sh:hasValue` — the form every derived region, envelope and
    law here takes."""
    out: dict[str, set[float]] = {}
    for prop_shape in shapes.subjects(_SH.path, _RESULT):
        bounds = [o for p in _BOUNDS for o in shapes.objects(prop_shape, p)]
        if not bounds:
            continue
        for node in shapes.subjects(_SH.property, prop_shape):
            for sibling in shapes.objects(node, _SH.property):
                if (sibling, _SH.path, _PROPERTY) in shapes:
                    for prop in shapes.objects(sibling, _SH.hasValue):
                        for b in bounds:
                            try:
                                out.setdefault(str(prop), set()).add(float(b))
                            except (TypeError, ValueError):
                                pass
    return out


def readers_of(texts, about: str | None = None) -> tuple[dict[str, set[float]], set[str]]:
    """Per property, the constants the selects in `texts` compare a reading of it against, and
    the properties some select compares UNREADABLY — against a variable rather than a number.
    A reading is recognised as `?o sosa:observedProperty P ; sosa:hasSimpleResult ?v`, with P
    a constant or `$about`, which is `about`."""
    found: dict[str, set[float]] = {}
    unreadable: set[str] = set()
    for text in texts:
        if not text:
            continue
        try:
            alg = translateQuery(parseQuery(PREFIXES + parseable(text))).algebra
        except Exception as exc:                        # noqa: BLE001 — unreadable is a finding
            log.debug("could not parse a select for the partition: %s", exc)
            continue
        by_obs: dict = {}                               # ?o -> property IRI
        by_var: dict = {}                               # ?v -> property IRI
        comparisons: list = []                          # (var, other)

        def walk(n):
            if isinstance(n, CompValue):
                if n.name == "BGP":
                    for s, p, o in n["triples"]:
                        if p == _PROPERTY:
                            prop = str(o) if isinstance(o, URIRef) else (
                                about if isinstance(o, Variable) and str(o) == "about" else None)
                            if prop:
                                by_obs[s] = prop
                    for s, p, o in n["triples"]:
                        if p == _RESULT and isinstance(o, Variable) and s in by_obs:
                            by_var[o] = by_obs[s]
                elif n.name == "RelationalExpression":
                    a, b = n["expr"], n["other"]
                    if isinstance(a, Variable):
                        comparisons.append((a, b))
                    if isinstance(b, Variable):
                        comparisons.append((b, a))
                for key, value in n.items():
                    if key != "_vars":
                        walk(value)
            elif isinstance(n, (list, tuple)):
                for item in n:
                    walk(item)
        walk(alg.get("p", alg))
        for var, other in comparisons:
            prop = by_var.get(var)
            if prop is None:
                continue
            if isinstance(other, Literal):
                try:
                    found.setdefault(prop, set()).add(float(other))
                except (TypeError, ValueError):
                    unreadable.add(prop)
            else:
                unreadable.add(prop)
    return found, unreadable


def cells_of(shapes_graphs, texts, about: str | None = None) -> dict[str, tuple]:
    """The partition: property -> its sorted thresholds, for every property whose readers
    are all readable; a property some select compares against a variable is left out and
    stays point-valued."""
    thresholds: dict[str, set[float]] = {}
    for g in shapes_graphs:
        if g is None:
            continue
        for prop, bounds in thresholds_of(g).items():
            thresholds.setdefault(prop, set()).update(bounds)
    found, unreadable = readers_of(texts, about)
    for prop, bounds in found.items():
        thresholds.setdefault(prop, set()).update(bounds)
    for prop in unreadable:
        thresholds.pop(prop, None)
    return {prop: tuple(sorted(b)) for prop, b in thresholds.items() if b}


def cell_of(value, thresholds: tuple) -> tuple:
    """The cell `value` falls in: `("cell", lo, hi)`, lo inclusive, hi exclusive, None at
    either open end. A value that is not a number is its own cell."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return ("cell", value, value)
    if math.isnan(v):
        return ("cell", None, None)
    lo = max((t for t in thresholds if t <= v), default=None)
    hi = min((t for t in thresholds if t > v), default=None)
    return ("cell", lo, hi)
