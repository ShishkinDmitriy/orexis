"""Weighing: judging one thing FOR ONE WANT OR DESIRE, and writing what was found.

A WORLD'S own facts — the candidate that reached it, what the path spent, when it is — are
true of it whoever is asking. Whether a want is met there, whether its search may still open
it and whether it has: those are true of the world AND the want together, and one imaginarium
holds the worlds of every want in a scope. So they hang off a node naming both, rather than
off the world as if it had only one asker. A DESIRE is weighed the same way, in every ground
the timeline laid, and its weighings carry the met-test's rows — the instances in trouble —
which is what the derivation mints wants from. A CANDIDATE the search passed over is weighed
too, saying which world its fork repeated, so a want offered nothing can be told apart from
one whose levers all led somewhere already seen.

**IT JUDGES AS WELL AS WRITES**, and takes the store and two names. The met-test is read off
the shapes in the store and compiled once per want or desire for the pass; the world it is
asked over is `world_at`; what comes back is written whole — the verdict, the rows, and for
a want whether the world is on the frontier. Nothing crosses back but the node's name.

THE ONE WRITER OF THE SHAPE, and the one reader of a met-test in this package.
"""

from __future__ import annotations

import logging
from datetime import datetime

import pyoxigraph as ox
import rdflib

from . import violation
from agent.ontology import OREXIS, RECORD, local_of
from agent.store import NAMESPACES, Raw, bind, catalogue_of, graphs_of, rdflib_view, remember, rows, update

from .ontology import DESIRE, PLANNING, SHAPES, WANT
from .world_at import world_at

#  THE CATALOGUE IS BOUND, NOT FOUND, IN THE HOT READS: `GRAPH ?cat { ?cat a
#  orexis:CatalogueGraph . … }` makes the engine evaluate the group per named graph, and with
#  a store of sixteen possible worlds each such read cost 0.5 to 1.0 ms where a read over one
#  bound graph costs 0.1 to 0.2 — measured on the two-disk bench. The name is asked of the
#  store once per pass (`catalogue_of`, remembered) and spliced as `$cat`: a reader asking
#  the store for the catalogue's name is what the rule allows; spelling it is what it refuses.

log = logging.getLogger("weigh")

_MET_WHEN = rdflib.URIRef(PLANNING + "metWhen")
_ESTIMATES = rdflib.URIRef(PLANNING + "estimates")
_DERIVED_FROM = rdflib.URIRef("http://www.w3.org/ns/prov#wasDerivedFrom")
_SELECT = rdflib.URIRef("http://www.w3.org/ns/shacl#select")

#  WHAT `about` IS, AND WHETHER IT IS A REPEAT, in one read: a candidate says the world it was
#  taken in, and the world it reached if it reached one; a world says neither. Where the
#  reached world holds what a world this want already weighed holds, by hash, `?seen` names
#  that world. Two reads before, at a tenth of a search on the two-disk bench.
_ABOUT_Q = """
SELECT ?from ?child ?seen WHERE {
  GRAPH $cat { OPTIONAL { $about planning:from ?from }
    OPTIONAL { ?child planning:by $about ; orexis:hash ?hash .
               OPTIONAL { ?x a planning:Weighing ; planning:for $for ; planning:weighs ?seen .
                          ?seen orexis:hash ?hash } } } }
ORDER BY ?seen LIMIT 1"""

#  WHOSE, AND WHETHER A WANT: who holds what is weighed for, off the graph it lives in — a
#  desire and a want are both held — and whether it is a want, since only a want's world
#  goes on the frontier.
_HELD_Q = """
SELECT ?holder ?want WHERE {
  GRAPH ?g { ?holder planning:holds $for . OPTIONAL { $for a planning:Want . BIND(true AS ?want) } } }
LIMIT 1"""

#  THE PRESENT: where the timeline begins — the earliest ground.
_PRESENT_Q = """
SELECT (MIN(?start) AS ?now) WHERE {
  GRAPH $cat { ?g a planning:GroundGraph ; dcterms:temporal/orexis:start ?start } }"""

_WEIGH_U = """
INSERT { GRAPH ?cat { $weighing a planning:Weighing ; planning:for $for ;
                      planning:weighs $about $verdict .
                      $violations } }
WHERE  { GRAPH ?cat { ?cat a orexis:CatalogueGraph } }"""


def weigh(store, for_, about: str, *, memo=None) -> str:
    """Weigh `about` — a world, a ground, or a candidate — for `for_`, a want or a desire, and
    write the weighing. Its node.

    A CANDIDATE is weighed by what it reached: nothing, where its effect changed nothing in
    the world it was taken in, so it repeats that world; a world holding what a world this
    want already weighed holds, by hash, so it repeats that one; or a new world, which is
    judged as a world is. A WORLD is judged: the met-test of `for_`, compiled once for the
    pass, asked over the world at its own instant, with what the holder's records say at the
    present. Every row is written as a `planning:violation`; none is `planning:met true`; a
    met-test that cannot be compiled or run writes no verdict at all, which the derivation
    reads as not judged and the search reads as unmet, the safe direction for each.

    ON THE FRONTIER where it is a want's and the world is unmet. A desire's weighing is never
    open: a desire is not searched, its wants are.
    """
    cat = Raw(f"<{remember(memo, ('catalogue',), lambda: catalogue_of(store))}>")
    found = next(iter(rows(store, _ABOUT_Q, (), about=about, cat=cat, **{"for": for_})), {})
    held = remember(memo, ("held", for_), lambda: next(iter(rows(store, _HELD_Q, (), **{"for": for_})), {}))
    verdict, violations = "", ""
    if found.get("from"):
        world = found.get("child")
        repeats = found["from"] if world is None else found.get("seen")
        if repeats is not None:
            verdict = f" ; planning:repeats <{repeats}>"
            world = None
    else:
        world = about
    #  NAMED FOR WHAT IT WEIGHS — the world where a candidate reached one this want had not
    #  seen, the candidate where it was passed over — and named before the rows are written,
    #  because the rows hang off the name.
    about = about if world is None else world
    node = f"{about}.for.{local_of(for_)}"
    if world is not None:
        report = _report(store, for_, world, held, memo)
        if report is not None:
            verdict = f" ; planning:met {'true' if not report else 'false'}"
            violations = "".join(_violation(node, row) for row in report)
        if held.get("want") and (report is None or report):
            verdict += " ; planning:open true"
        if held.get("want"):
            left = _remaining(store, for_, world, held, memo)
            if left is not None:
                verdict += f" ; planning:remaining {left}"
    update(store, bind(_WEIGH_U, weighing=Raw(f"<{node}>"), about=about,
                       verdict=Raw(verdict), violations=Raw(violations), **{"for": for_}))
    return node


def _report(store, for_, world: str, held: dict, memo) -> list[dict] | None:
    """The met-test's rows in `world`, or None where there is no met-test to ask or the engine
    refuses it — which is not the same as met, and is said by writing no verdict."""
    select = remember(memo, ("select", for_), lambda: _select(store, for_, memo))
    if select is None:
        return None
    graphs = _graphs(store, world, held, memo)
    try:
        found = store.query(select, prefixes=NAMESPACES,
                            default_graph=[ox.NamedNode(g) for g in graphs])
        names = [v.value for v in found.variables]
        seen = {}
        for solution in found:
            row = {n: solution[n] for n in names if solution[n] is not None}
            seen.setdefault(tuple(sorted((k, str(v)) for k, v in row.items())), row)
        return [seen[k] for k in sorted(seen)]
    except Exception as exc:                                        # noqa: BLE001
        log.error("a met-test could not be read in %s: %s", world.rsplit("/", 1)[-1], exc)
        return None


def _graphs(store, world: str, held: dict, memo) -> list[str]:
    """What a text about `world` is answered over: the world at its own instant, with the
    holder's records as they stand at the present."""
    now = remember(memo, ("present",), lambda: next(iter(rows(store, _PRESENT_Q, (), cat=Raw(
        f"<{remember(memo, ('catalogue',), lambda: catalogue_of(store))}>"))), {}).get("now"))
    return world_at(store, world, holder=held.get("holder"),
                    now=datetime.fromisoformat(now) if now else None, memo=memo)


def _remaining(store, for_, world: str, held: dict, memo) -> str | None:
    """What the want's estimate reads in `world` — how far it still is, in the unit the search
    spends — or None where the want declares none or the select refuses to run.

    THE DESIRE OWNS THE TERM AND THE PACKAGE OWNS THE MEASURE: `planning:estimates` on the want,
    or on the desire it was derived from, points at a node carrying one `sh:select` that
    binds `?estimate`; the package that declares the actions declares the node, because
    *never overstates* is a promise about the package's own costs and no world can keep it.
    Run over the same graphs as the met-test, the world at its instant, and written on the
    weighing as `planning:remaining` for the frontier to order by.

    NONE IS NOT NOUGHT. A want with no estimate is not a want that is nought away, and a
    broken declaration read as arrived would crown a plan that achieved nothing; the frontier
    reads an absent figure as nought, which is uniform-cost, the safe direction.
    """
    text = remember(memo, ("estimate", for_), lambda: _estimate(store, for_, memo))
    if text is None:
        return None
    try:
        found = store.query(text, prefixes=NAMESPACES,
                            default_graph=[ox.NamedNode(g) for g in _graphs(store, world, held, memo)])
        row = next(iter(found), None)
        return None if row is None or row["estimate"] is None else str(row["estimate"].value)
    except Exception as exc:                                        # noqa: BLE001
        log.error("the estimate of %s could not be read in %s: %s", local_of(for_),
                  world.rsplit("/", 1)[-1], exc)
        return None


def _estimate(store, for_, memo) -> str | None:
    """The `sh:select` the want's `planning:estimates` points at — the want's own, or its
    desire's — off the shapes crossed once for the pass. None where neither declares one."""
    shapes = remember(memo, ("shapes",), lambda: rdflib_view(store, *graphs_of(store, DESIRE, WANT, RECORD, SHAPES)))
    want = rdflib.URIRef(for_)
    node = shapes.value(want, _ESTIMATES)
    if node is None:
        desire = shapes.value(want, _DERIVED_FROM)
        node = shapes.value(desire, _ESTIMATES) if desire is not None else None
    text = shapes.value(node, _SELECT) if node is not None else None
    return str(text) if text is not None else None


def _select(store, for_, memo) -> str | None:
    """`for_`'s met-test compiled to the select whose rows are its violations — `?this`, the
    constraint's index, what it is about and which way it broke — off the shapes crossed once
    for the pass. None, with a word in the log, where there is no shape or the compiler
    refuses it: a shape compiled to an empty pattern would read as met for ever."""
    shapes = remember(memo, ("shapes",), lambda: rdflib_view(store, *graphs_of(store, DESIRE, WANT, RECORD, SHAPES)))
    shape = shapes.value(rdflib.URIRef(for_), _MET_WHEN)
    if shape is None:
        return None
    try:
        return violation.report_select(shapes.cbd(shape), shape)
    except violation.Unsupported as exc:
        log.warning("%s: its met-test cannot be compiled, so it is not judged: %s", local_of(for_), exc)
        return None


def _violation(node: str, row: dict) -> str:
    """One report row as the violation it is, hung off the weighing."""
    parts = [f"planning:instance {row['this']}"]
    if "_constraint" in row:
        parts.append(f"planning:constraint {row['_constraint']}")
    if "_about" in row:
        parts.append(f"planning:about {row['_about']}")
    if "_side" in row:
        parts.append(f"planning:violationIs {row['_side']}")
    return f"<{node}> planning:violation [ {' ; '.join(parts)} ] .\n"
