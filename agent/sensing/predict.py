"""`predict`: what the drifts say one reading will be, written as predictions — graphs of
band sets holding during their windows, each starting where the classification probably
changes (the-drift-is-sensings-and-its-result-is-predictions, #642, #783).

**A DRIFT IS A PACKAGE'S RULE OVER `$elapsed`** — what the world does to a reading while
nobody acts — declared against this layer's word (`sensing:Drift`) with the horizons the
package predicts at beside it. After every reading, for one key, this runs every drift the
store holds at each horizon of the ladder past the reading's own horizon and writes one
prediction per window: `orexis:PredictionGraph`, holding during its window, carrying the
predicted node keyed exactly as the reading is and typed with every band the rule says it may
be in. The rate, the spread and the instrument's noise are inside the package's text; what
leaves it is bands, and where a rule types none the vocabulary entails the one the centre
falls in — and then the centre goes: a prediction carries no number, no instant and no
instrument, because the mind reads bands and a world that hashed a centre would be a new
world at every reading.

**THE CROSSING IS FOUND, NOT ROUNDED TO THE LADDER.** The ladder's windows are an hour, five
and a day; a prediction for the window at which the set first differs from the reading's own
bands would put the crossing at that window's START, which the drift may not reach for hours.
So the first window whose bands differ is bisected — the drift run at instants between the
last elapsed known to classify as the reading does and the first known not to — until the
change is placed within a minute or a sixty-fourth of the window, and that instant is where
the crossed prediction's period begins; what stood before it carries the reading's own bands
to that instant. A crossing the ladder placed at one o'clock and the bisection at four is the
case the suite holds (`a_widening_spread_crosses_later_than_the_ladder_says`), because a
refinement is measured before it is believed. The crossed window's set is the union of what
the drift says at the crossing and at the window's far end, since the set moves across it.

**WHAT IT RETRACTS IS SAID ON THE ROW.** A prediction is a diff, and only a ground has
applied it: the graph holds what it ADDS, and its catalogue row carries `orexis:retracts`, the
`DELETE … WHERE` naming `GRAPH $state` that takes the key's standing node out of whatever
ground the boundary is laid over — the key is this layer's, so the text is this layer's to
write. The row also says which reading the prediction was derived from, so the next reading
of the key drops the whole ladder before it writes its own.

**A KEY NO DRIFT MOVES IS PREDICTED TO STAY AS IT READS** for the first window alone — its
bands carried forward — and at no later one: a package that declares no drift has made no
claim about the world past that, and this layer invents no persistence. A key no ladder
reaches at all is predicted nowhere, and stands until its horizon.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta

import pyoxigraph as ox

from agent.entail import entail
from agent.ontology import BELIEF, DESIRE, PREDICTION, PUBLIC, RECORD, WANT, local_of
from agent.store import (Raw, bind, catalogue_of, construct, entry, forget_graph, graphs_of,
                         instant, quads, remember, rows, update)

from .ontology import (FAMILIES, FEATURE, PROPERTY, RECORDED, RESULT_WORDS, prediction_graph)

log = logging.getLogger("predict")

_RDF_TYPE = ox.NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")

#  THE READING IN HAND: the graph of readings holding this key's node, the stretch it stands
#  for, and the result beside it — asked by kind and by pattern, never by name.
_READING_Q = """
SELECT ?reading ?node ?from ?until ?value ?taken WHERE {
  GRAPH $cat { ?reading a orexis:StateGraph ; dcterms:temporal ?p . ?p orexis:start ?from .
               OPTIONAL { ?p orexis:end ?until } }
  GRAPH ?reading { ?node sosa:hasFeatureOfInterest $feature ; sosa:observedProperty $property }
  OPTIONAL { GRAPH $cat { ?result a sensing:ResultGraph }
             GRAPH ?result { ?node sosa:hasSimpleResult ?value ; sosa:resultTime ?taken } } }
ORDER BY DESC(?from) LIMIT 1"""

_RESULTS_Q = """
SELECT ?result WHERE {
  GRAPH $cat { ?result a sensing:ResultGraph }
  GRAPH ?result { $node ?p ?o } }"""

#  EVERY DRIFT THE STORE HOLDS, with the horizons its package lists beside it.
_DRIFTS_Q = """
SELECT ?drift ?construct (GROUP_CONCAT(STR(?h); SEPARATOR=" ") AS ?horizons) WHERE {
  ?drift a sensing:Drift ; sh:construct ?construct .
  OPTIONAL { ?drift sensing:atHorizon ?h }
} GROUP BY ?drift ?construct ORDER BY ?drift"""

#  THE LADDER WRITTEN FOR THIS KEY BEFORE: every prediction derived from the reading's graph.
_LADDER_Q = """
SELECT ?g WHERE { GRAPH $cat { ?g a orexis:PredictionGraph ; prov:wasDerivedFrom $reading } }"""

#  WHAT OF A NODE'S TYPES IS A BAND: the three families and every member the world minted.
_BANDS_Q = """
SELECT DISTINCT ?b ?f WHERE { VALUES ?f { $families } ?b rdfs:subClassOf+ ?f }"""

#  THE DIFF A PREDICTION MAKES: the key's standing node goes, whole.
_RETRACTS = ("DELETE { GRAPH $state { ?o ?p ?v } } "
             "WHERE { GRAPH $state { ?o sosa:hasFeatureOfInterest <%s> ; sosa:observedProperty <%s> ; ?p ?v } }")

#  THE INSTRUMENT'S WORDS OFF A PREDICTION, once the centre's band is drawn from them.
_STRIP_U = """
DELETE { GRAPH $g { ?s ?p ?o } } WHERE { GRAPH $g { ?s ?p ?o } VALUES ?p { $words } }"""

#  HOW CLOSE THE CROSSING IS PLACED: within a minute, or a sixty-fourth of the window it falls
#  in where that is coarser — a plant's day is bisected to twenty minutes, its hour to one.
_RESOLUTION_S = 60.0


def predict(store: ox.Store, me: str, subject: str, observed_property: str, *,
            sample: str | None = None, now: datetime | None = None, memo=None) -> list[str]:
    """Rewrite the ladder of predictions for one key from the reading in hand. The graphs
    written, first window first; none where no reading of the key stands or no drift's
    ladder reaches past its horizon.

    `me` is who holds the reading, `now` the present the records are read at — the reading's
    own instant where none is given.
    """
    feature = sample or subject
    cat = Raw(f"<{remember(memo, ('catalogue',), lambda: catalogue_of(store))}>")
    found = next(iter(rows(store, _READING_Q, (), cat=cat, feature=feature, property=observed_property)), None)
    if found is None:
        log.debug("nothing read of %s of %s: nothing to predict", local_of(observed_property), local_of(feature))
        return []
    reading, node = found["reading"], found["node"]
    taken = datetime.fromisoformat(found["taken"] if found.get("taken") else found["from"])
    opens = datetime.fromisoformat(found["until"]) if found.get("until") else taken
    for old in rows(store, _LADDER_Q, (), cat=cat, reading=reading):
        forget_graph(store, old["g"])
    drifts = remember(memo, ("drifts",), lambda: rows(store, _DRIFTS_Q, graphs_of(store, PUBLIC)))
    ladder = sorted({float(h) for d in drifts for h in (d.get("horizons") or "").split()
                     if taken + timedelta(seconds=float(h)) > opens})
    if not ladder:
        return []
    bands = remember(memo, ("bands",), lambda: _bands(store))
    results = [r["result"] for r in rows(store, _RESULTS_Q, (), cat=cat, node=node)]
    held = [reading, *results]
    own = _bands_of(store, reading, node, bands)
    tokens = {"me": me, "subject": subject, "about": observed_property}
    run = lambda elapsed: _run(store, drifts, tokens, held, feature, observed_property, taken, elapsed, now, memo)

    #  THE WINDOWS, one per rung of the ladder, each predicted at its far end.
    windows: list[tuple[datetime, datetime, list]] = []
    for n, h in enumerate(ladder):
        closes = taken + timedelta(seconds=h)
        start = opens if n == 0 else windows[-1][1]
        triples = run(h)
        if not triples and n == 0:
            triples = [ox.Triple(q.subject, q.predicate, q.object) for q in quads(store, reading)]
        if triples:
            windows.append((start, closes, triples))

    #  THE CROSSING: the first window whose bands differ from the reading's own, bisected.
    crossed = next((i for i, (_, _, t) in enumerate(windows) if own and _typed(t, node, bands) != own), None)
    if crossed is not None:
        start, closes, triples = windows[crossed]
        lo = (start - taken).total_seconds()
        hi = (closes - taken).total_seconds()
        tolerance = max(_RESOLUTION_S, (hi - lo) / 64)
        before = None
        while hi - lo > tolerance:
            mid = (lo + hi) / 2
            there = run(mid)
            if not there or _typed(there, node, bands) == own:
                lo, before = mid, there
            else:
                hi = mid
        at_hi = run(hi)
        crossing = taken + timedelta(seconds=math.ceil(hi))
        if crossing > start:
            kept = before if before else [ox.Triple(q.subject, q.predicate, q.object) for q in quads(store, reading)]
            windows[crossed:crossed + 1] = [(start, crossing, kept), (crossing, closes, _union(triples, at_hi))]

    written = []
    for n, (start, closes, triples) in enumerate(windows):
        graph = prediction_graph(local_of(me), feature, observed_property, n)
        update(store, f"""
INSERT DATA {{
  {entry(store, graph, PREDICTION, RECORDED, me, start=start, end=closes)}
  GRAPH <{catalogue_of(store)}> {{
    <{graph}> prov:wasDerivedFrom <{reading}> ;
              orexis:retracts {_literal(_RETRACTS % (feature, observed_property))} . }} }}""")
        store.extend(ox.Quad(t.subject, t.predicate, t.object, ox.NamedNode(graph)) for t in triples)
        entail(store, graph, of=[node], memo=memo)
        update(store, bind(_STRIP_U, g=Raw(f"<{graph}>"), words=Raw(" ".join(f"<{w}>" for w in RESULT_WORDS))))
        written.append(graph)
    log.info("predicted %s of %s in %d window(s), the first opening %s%s",
             local_of(observed_property), local_of(feature), len(written),
             windows[0][0].isoformat(timespec="seconds") if windows else "never",
             f", crossing at {windows[crossed + 1][0].isoformat(timespec='seconds')}"
             if crossed is not None and crossed + 1 < len(windows) else "")
    return written


def _run(store, drifts, tokens: dict, held: list[str], feature: str, observed_property: str,
         taken: datetime, elapsed: float, now: datetime | None, memo) -> list:
    """Every drift over the reading in hand at `elapsed` seconds past it, as the triples about
    this key's node — the world at the instant reached, and the reading whatever its period,
    since the reading in hand is what the drift is about."""
    lands = taken + timedelta(seconds=elapsed)
    known = remember(memo, ("known", lands), lambda: graphs_of(
        store, PUBLIC, BELIEF, RECORD, DESIRE, WANT, at=lands, now=now or taken))
    graphs = list(dict.fromkeys([*known, *held]))
    out = []
    for drift in drifts:
        try:
            added = construct(store, bind(drift["construct"], lands=instant(lands), elapsed=float(elapsed), **tokens), graphs)
        except Exception as exc:                                    # noqa: BLE001
            log.error("drift %s would not run for a prediction: %s", local_of(drift["drift"]), exc)
            continue
        by_node: dict = {}
        for t in added:
            by_node.setdefault(t.subject, []).append(t)
        for subject, ts in by_node.items():
            facts = {t.predicate.value: t.object for t in ts}
            if (getattr(facts.get(FEATURE), "value", None) == feature
                    and getattr(facts.get(PROPERTY), "value", None) == observed_property):
                out.extend(ts)
    return out


def _bands(store) -> dict:
    """Every band class to the family it sits beneath, a family to itself: the members asked
    of the store, the families known, since a BIND inside a UNION branch sees nothing bound
    outside it (AGENTS.md, the traps)."""
    out = {f: f for f in FAMILIES}
    for r in rows(store, _BANDS_Q, graphs_of(store, PUBLIC), families=Raw(" ".join(f"<{f}>" for f in FAMILIES))):
        out[r["b"]] = r["f"]
    return out


def _bands_of(store, graph: str, node: str, bands: dict) -> frozenset:
    return _closed((q.object.value for q in store.quads_for_pattern(
        ox.NamedNode(node), _RDF_TYPE, None, ox.NamedNode(graph))), bands)


def _typed(triples, node: str, bands: dict) -> frozenset:
    """The bands a set of triples types `node` with."""
    return _closed((t.object.value for t in triples if t.predicate == _RDF_TYPE and t.subject.value == node), bands)


def _closed(types, bands: dict) -> frozenset:
    """A set of band types with each member's family beside it — so a rule that typed the
    member alone and one that typed both classify alike, which is what the entailment writes."""
    out = set()
    for t in types:
        if t in bands:
            out.add(t)
            out.add(bands[t])
    return frozenset(out)


def _union(first, second) -> list:
    seen = {(t.subject, t.predicate, t.object) for t in first}
    return list(first) + [t for t in second if (t.subject, t.predicate, t.object) not in seen]


def _literal(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
