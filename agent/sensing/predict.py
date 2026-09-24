"""`predict`: when the reading will change range — the domain's drifts run over the observation
in hand, and a prediction written for each stretch between crossings.

**A PREDICTION IS THE CALCULATION OF WHEN THE READING CHANGES RANGE.** Every `sensing:Drift`
the domain declares — a package's rule over `$elapsed`, what the world does to a reading while
nobody acts — is run over the observation at the instants of the LADDER, `LADDER_S`, each rung
past the observation's own horizon; the ladder is the scan, not the answer, and it is this
layer's: a drift declares no horizon, since the bisection places a crossing wherever it falls
and a rung only bounds how far the scan looks. Against every range that applies to what the
sensor observes (SSN-System's operating and survival ranges, `ranges_of`),
wherever the drift's number lies on one side of a bound at one rung and the other side at the
next, the crossing is bisected between them, within a minute or a sixty-fourth of the rung, and
the scan goes on from it — so a rung that crosses two bounds yields two crossings. A comparison
to a bound is arithmetic this layer does on numbers; the SIDE as a fact the mind reads is the
rules', concluded over what is written here.

**WHAT IS WRITTEN IS ONE PREDICTION PER STRETCH**: from the horizon to the first crossing,
crossing to crossing, and from the last to the ladder's end — each an `orexis:PredictionGraph`
holding during its stretch, carrying a predicted `sosa:Observation` in SOSA's words with the
number the drift gives at the last instant of that stretch the bisection knows to lie on its
side, so the rules classify every stretch as the side it is. Each says which observation it
was derived from, so the next observation of the key drops the whole ladder before its own is
written, and its row carries `orexis:retracts`, the `DELETE … WHERE` naming `GRAPH $state` that
takes the key's standing node out of whatever ground the boundary is laid over — the key is
this layer's, so the text is this layer's to write, in the form `lay_ground` reads today.

**A KEY NO DRIFT MOVES** — a store declaring no drift at all is the same case — is predicted
to stay as it reads for the first rung alone: a package that declares no drift has made no
claim about the world past that, and this layer invents no persistence. A key that crosses
nothing has one prediction to the ladder's end.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta

import pyoxigraph as ox

from agent.ontology import BELIEF, DESIRE, PREDICTION, PUBLIC, RECORD, WANT, local_of
from agent.store import (Raw, bind, catalogue_of, construct, entry, forget_graph, graphs_of,
                         instant, quads, remember, rows, update)

from .ontology import FEATURE, PROPERTY, RECORDED, RESULT, prediction_graph
from .ranges import ranges_of, side

log = logging.getLogger("predict")

_RESULT = ox.NamedNode(RESULT)

#  THE OBSERVATION IN HAND: the graph holding the node this sensor last made, its key, the
#  stretch it stands for and its number — asked by kind and by pattern, never by name.
_OBSERVATION_Q = """
SELECT ?graph ?node ?feature ?property ?value ?taken ?from ?until WHERE {
  GRAPH $cat { ?graph a sensing:ObservationGraph ; dcterms:temporal ?p . ?p orexis:start ?from .
               OPTIONAL { ?p orexis:end ?until } }
  GRAPH ?graph { ?node sosa:madeBySensor $sensor ; sosa:hasFeatureOfInterest ?feature ;
                 sosa:observedProperty ?property ; sosa:hasSimpleResult ?value .
                 OPTIONAL { ?node sosa:resultTime ?taken } } }
ORDER BY DESC(?from) LIMIT 1"""

#  EVERY DRIFT THE STORE HOLDS.
_DRIFTS_Q = "SELECT ?drift ?construct WHERE { ?drift a sensing:Drift ; sh:construct ?construct } ORDER BY ?drift"

#  THE LADDER: how far past the observation's horizon the drifts are asked, in the timeline's
#  seconds — an hour, five and a day. The scan, not the answer: a crossing inside a rung is
#  bisected to the minute, and a rung only says how far ahead the agent looks.
LADDER_S = (3600.0, 18000.0, 86400.0)

#  THE LADDER WRITTEN FOR THIS KEY BEFORE: every prediction derived from the observation's graph.
_LADDER_Q = """
SELECT ?g WHERE { GRAPH $cat { ?g a orexis:PredictionGraph ; prov:wasDerivedFrom $graph } }"""

#  THE DIFF A PREDICTION MAKES: the key's standing node goes, whole.
_RETRACTS = ("DELETE { GRAPH $state { ?o ?p ?v } } "
             "WHERE { GRAPH $state { ?o sosa:hasFeatureOfInterest <%s> ; sosa:observedProperty <%s> ; ?p ?v } }")

#  HOW CLOSE THE CROSSING IS PLACED: within a minute, or a sixty-fourth of the rung it falls
#  in where that is coarser — a plant's day is bisected to twenty minutes, its hour to one.
_RESOLUTION_S = 60.0


def predict(store, me: str, sensor: str, *, now: datetime | None = None, memo=None) -> list[str]:
    """Rewrite the predictions of the key `sensor` last observed, from the observation in hand:
    one per stretch between the instants the drifts say the reading changes range. The graphs
    written, first stretch first; none where no observation by the sensor stands or the ladder
    does not reach past its horizon.

    `me` is who holds the observation, `now` the present the records are read at — the
    observation's own instant where none is given.
    """
    cat = Raw(f"<{remember(memo, ('catalogue',), lambda: catalogue_of(store))}>")
    found = next(iter(rows(store, _OBSERVATION_Q, (), cat=cat, sensor=sensor)), None)
    if found is None:
        log.debug("nothing observed by %s: nothing to predict", local_of(sensor))
        return []
    graph, node, feature, observed_property = found["graph"], found["node"], found["feature"], found["property"]
    reading = float(found["value"])
    taken = datetime.fromisoformat(found["taken"] if found.get("taken") else found["from"])
    opens = datetime.fromisoformat(found["until"]) if found.get("until") else taken
    for old in rows(store, _LADDER_Q, (), cat=cat, graph=graph):
        forget_graph(store, old["g"])
    drifts = remember(memo, ("drifts",), lambda: rows(store, _DRIFTS_Q, graphs_of(store, PUBLIC)))
    ladder = [h for h in LADDER_S if taken + timedelta(seconds=h) > opens]
    if not ladder:
        return []
    ranges = ranges_of(store, sensor, observed_property, memo)
    tokens = {"me": me, "about": observed_property}
    own = [ox.Triple(q.subject, q.predicate, q.object) for q in quads(store, graph)]
    base = (opens - taken).total_seconds()

    def at(elapsed: float) -> list:
        """The drifts' triples about the key at `elapsed` seconds past the observation — the
        observation's own where the drifts say nothing, which at the horizon they may not."""
        said = _run(store, drifts, tokens, graph, feature, observed_property, taken, elapsed, now, memo)
        return said if said else (own if elapsed <= base else [])

    def sides(elapsed: float):
        value = _value(at(elapsed), node)
        return None if value is None else tuple(side(low, high, value) for low, high in ranges)

    #  THE SCAN, rung by rung, and every crossing within a rung bisected in turn.
    crossings: list[tuple[float, float]] = []       # (last elapsed on the old side, first on the new)
    rungs = [base, *ladder]
    for lo_end, hi_end in zip(rungs, rungs[1:]):
        start, far = lo_end, sides(hi_end)
        if far is None:
            continue
        while sides(start) is not None and sides(start) != far:
            lo, hi, before = start, hi_end, sides(start)
            tolerance = max(_RESOLUTION_S, (hi_end - lo_end) / 64)
            while hi - lo > tolerance:
                mid = (lo + hi) / 2
                if sides(mid) in (None, before):
                    lo = mid
                else:
                    hi = mid
            crossings.append((math.floor(lo), math.ceil(hi)))
            start = hi

    #  THE STRETCHES: the horizon to the first crossing, crossing to crossing, the last to the
    #  ladder's end — each carrying the number at the last instant known to lie on its side.
    ends = [*(hi for _, hi in crossings), ladder[-1]]
    knowns = [*(lo for lo, _ in crossings), ladder[-1]]
    starts = [base, *(hi for _, hi in crossings)]
    if not any(_run(store, drifts, tokens, graph, feature, observed_property, taken, h, now, memo) for h in ladder):
        #  NO DRIFT MOVES THIS KEY: it is predicted to stay as it reads, for the first rung alone.
        ends, knowns, starts = [ladder[0]], [base], [base]
    written = []
    for n, (begins, closes, known) in enumerate(zip(starts, ends, knowns)):
        triples = at(known) or own
        graph_n = prediction_graph(local_of(me), feature, observed_property, n)
        update(store, f"""
INSERT DATA {{
  {entry(store, graph_n, PREDICTION, RECORDED, me, start=taken + timedelta(seconds=begins), end=taken + timedelta(seconds=closes))}
  GRAPH <{catalogue_of(store)}> {{
    <{graph_n}> prov:wasDerivedFrom <{graph}> ;
                orexis:retracts {_literal(_RETRACTS % (feature, observed_property))} . }} }}""")
        store.extend(ox.Quad(t.subject, t.predicate, t.object, ox.NamedNode(graph_n)) for t in triples)
        written.append(graph_n)
    log.info("predicted %s of %s in %d stretch(es) from %s%s", local_of(observed_property), local_of(feature),
             len(written), (taken + timedelta(seconds=base)).isoformat(timespec="seconds"),
             "".join(f", crossing at {(taken + timedelta(seconds=hi)).isoformat(timespec='seconds')}" for _, hi in crossings))
    return written


def _run(store, drifts, tokens: dict, graph: str, feature: str, observed_property: str,
         taken: datetime, elapsed: float, now: datetime | None, memo) -> list:
    """Every drift over the observation in hand at `elapsed` seconds past it, as the triples
    about this key's node — the world at the instant reached, and the observation whatever
    its period, since the observation in hand is what the drift is about."""
    lands = taken + timedelta(seconds=elapsed)
    known = remember(memo, ("known", lands), lambda: graphs_of(
        store, PUBLIC, BELIEF, RECORD, DESIRE, WANT, at=lands, now=now or taken))
    graphs = list(dict.fromkeys([*known, graph]))
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


def _value(triples, node: str) -> float | None:
    """The number a set of triples gives `node`, or None where it gives none."""
    for t in triples:
        if t.predicate == _RESULT and t.subject.value == node:
            try:
                return float(t.object.value)
            except (TypeError, ValueError):
                return None
    return None


def _literal(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
