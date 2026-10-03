"""`predict`: when the reading will change range — the rates of the drifts moving what it
observes, accumulated from the observation in hand, and a prediction written for each stretch
between crossings.

**A PREDICTION IS THE CALCULATION OF WHEN THE READING CHANGES RANGE.** Every `prediction:Drift`
that `prediction:moves` the observed property answers a RATE for the subject at an instant —
per second of the one timeline, a package's select over whatever holds then — and the drifts
ADD: drying and rain are two drifts and the value moves by their sum, which is PDDL+'s
trajectory semantics, a drift being a process (a-prediction-accumulates-rates-between-happenings).
The sum is accumulated from the observation for `HORIZON_S`, split at every HAPPENING — the
start or end of a public or belief graph holding in that stretch, since only there can what a
drift reads change, which is how a forecast hour and a step the executor committed to become
one without this package learning either word — and held for at most `SEGMENT_S` between, so a
rate that depends on the value is asked again. Within a segment the value is a straight line, and a crossing of a bound of every range
that applies to what the sensor observes (SSN-System's, `ranges_of`) is placed exactly, by
division: no scan looks for it, so a value that dips below a floor and comes back inside an hour
later is seen. A drift answering `?until` contributes nothing past it, and a segment is split
where the value reaches it, so the soil dries to nothing and not below.

**A RATE KNOWN AS A RANGE GIVES A CORRIDOR.** A drift may answer `?low` and `?high` instead of
`?rate`, and ranges add as rates do; two trajectories are accumulated, the low one by every
drift's lowest rate and the high one by every drift's highest, each asking the drifts at its own
value. The side of an instant is the corridor's worst, range by range — below where the low
trajectory is under the floor, above where the high one is over the ceiling — and the number
written is the trajectory that side was read from, so the rules conclude of it the side the
corridor has.

**WHAT IS WRITTEN IS ONE PREDICTION PER STRETCH**: from the observation's horizon to the first
crossing, crossing to crossing, and from the last to the horizon's end — each an
`orexis:PredictionGraph` holding during its stretch, carrying a predicted `sosa:Observation` in
SOSA's words with the number at the last instant of the stretch known to lie on its side. Each
says which observation it was derived from, so the next observation of the key drops them all
before its own are written, and its row carries `orexis:retracts`, the `DELETE … WHERE` naming
`GRAPH $state` that takes the key's standing node out of whatever ground the boundary is laid
over — in the form `lay_ground` reads today.

**A KEY NO DRIFT MOVES** — a store declaring no drift at all is the same case — is predicted to
stay as it reads for `CARRIED_S` past the observation alone: a package that declares no drift
has made no claim about the world past that, and this package invents no persistence.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta

import pyoxigraph as ox

from agent.ontology import BELIEF, DRIFT_GRAPH, PREDICTION, PUBLIC, RECORD, local_of
from agent.store import (PLACES, Raw, catalogue_of, entry, forget_graph, graphs_of, instant, quads,
                         remember, revisions_of, rows, update)

from .ontology import DRIFT, FEATURE, MOVES, PROPERTY, RATE, RECORDED, RESULT, prediction_graph
from .ranges import ranges_of, side

log = logging.getLogger("predict")

_XSD = "http://www.w3.org/2001/XMLSchema#"
_SOSA = "http://www.w3.org/ns/sosa/"
_RDF_TYPE = ox.NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")

#  HOW FAR PAST THE OBSERVATION THE AGENT LOOKS, in the timeline's seconds: a day.
HORIZON_S = 86400.0

#  THE LONGEST A RATE IS HELD before the drifts are asked again: an hour, so a rate that
#  depends on the value it moves is read off a value no more than an hour old.
SEGMENT_S = 3600.0

#  HOW LONG A KEY NO DRIFT MOVES IS CARRIED FORWARD as it reads: an hour past the observation.
CARRIED_S = 3600.0

#  WHERE A STRETCH'S NUMBER IS READ when its end lies across a bound: this long before the end,
#  or half the stretch where that is shorter.
_EDGE_S = 60.0

#  THE OBSERVATION IN HAND: the graph holding the node this sensor last made and the stretch it
#  stands for, asked by the kernel's kind and by SOSA's pattern, never by name and never by a word
#  of sensing's. Its key and its number are asked of the graph and its revisions together
#  (`_KEY_Q`), since what an observation is OF and its quantity are what the rules concluded of the
#  number the sensor gave — written by the time this runs, belief's part hearing a graph first.
_OBSERVATION_Q = """
SELECT ?graph ?node ?taken ?from ?until WHERE {
  GRAPH $cat { ?graph a orexis:StateGraph ; dcterms:temporal ?p . ?p orexis:start ?from .
               OPTIONAL { ?p orexis:end ?until } }
  GRAPH ?graph { ?node sosa:madeBySensor $sensor . OPTIONAL { ?node sosa:resultTime ?taken } } }
ORDER BY DESC(?from) LIMIT 1"""
_KEY_Q = """
SELECT ?feature ?property ?value WHERE {
  $node sosa:hasFeatureOfInterest ?feature ; sosa:observedProperty ?property ; sosa:hasSimpleResult ?value } LIMIT 1"""

#  EVERY DRIFT MOVING THE PROPERTY — the terms spliced as the terms they are, since no file of
#  this package binds a label for its namespace and a query needs none.
#  Read from the graphs of drifts alone (`orexis:DriftGraph`), as the planner reads actions from
#  `orexis:ActionGraph` alone: named for what it holds, and asked for, it is a term somebody reads. The
#  kind is the kernel's and not this package's, since this package's premise reads the drift rows off
#  the world before this package is loaded, and a premise reads only the kernel's and the mind's kinds.
_DRIFTS_Q = "SELECT ?drift ?rate WHERE { ?drift a $drift ; $moves $property ; $rate_of ?rate } ORDER BY ?drift"

#  THE PREDICTIONS WRITTEN FOR THIS KEY BEFORE: every one derived from the observation's graph.
_WRITTEN_Q = """
SELECT ?g WHERE { GRAPH $cat { ?g a orexis:PredictionGraph ; prov:wasDerivedFrom $graph } }"""

#  THE HAPPENINGS: every instant inside the horizon at which a public or belief graph begins or
#  stops holding — the only instants at which what a drift reads can change.
_HAPPENINGS_Q = """
SELECT DISTINCT ?t WHERE {
  GRAPH $cat { VALUES ?kind { $kinds } ?g a ?kind ; dcterms:temporal ?p .
               { ?p orexis:start ?t } UNION { ?p orexis:end ?t } }
  FILTER(?t > $from && ?t < $to) }"""

#  THE DIFF A PREDICTION MAKES: the key's standing node goes, whole.
_RETRACTS = ("DELETE { GRAPH $state { ?o ?p ?v } } "
             "WHERE { GRAPH $state { ?o sosa:hasFeatureOfInterest <%s> ; sosa:observedProperty <%s> ; ?p ?v } }")


def predict(store, me: str, sensor: str, *, now: datetime | None = None, memo=None) -> list[str]:
    """Rewrite the predictions of the key `sensor` last observed, from the observation in hand:
    one per stretch between the instants the drifts' summed rates carry the reading across a
    bound. The graphs written, first stretch first; none where no observation by the sensor
    stands or the horizon does not reach past its own.

    `me` is who holds the observation, `now` the present the records are read at — the
    observation's own instant where none is given.
    """
    cat = Raw(f"<{remember(memo, ('catalogue',), lambda: catalogue_of(store))}>")
    found = next(iter(rows(store, _OBSERVATION_Q, (), cat=cat, sensor=sensor)), None)
    if found is None:
        log.debug("nothing observed by %s: nothing to predict", local_of(sensor))
        return []
    graph, node = found["graph"], found["node"]
    believed = [graph, *revisions_of(store, graph)]
    key = next(iter(rows(store, _KEY_Q, believed, node=node)), None)
    if key is None:
        log.debug("%s's observation is of nothing the rules concluded: nothing to predict", local_of(sensor))
        return []
    feature, observed_property, reading = key["feature"], key["property"], float(key["value"])
    taken = datetime.fromisoformat(found["taken"] if found.get("taken") else found["from"])
    opens = datetime.fromisoformat(found["until"]) if found.get("until") else taken
    for old in rows(store, _WRITTEN_Q, (), cat=cat, graph=graph):
        forget_graph(store, old["g"])
    base = (opens - taken).total_seconds()
    if base >= HORIZON_S:
        return []
    drifts = remember(memo, ("drifts", observed_property), lambda: rows(
        store, _DRIFTS_Q, graphs_of(store, DRIFT_GRAPH), drift=Raw(f"<{DRIFT}>"), moves=Raw(f"<{MOVES}>"),
        rate_of=Raw(f"<{RATE}>"), property=observed_property))
    ranges = ranges_of(store, sensor, observed_property, memo)

    def rates(elapsed: float, value: float) -> list[tuple[float, float, float | None]]:
        """Every contribution the drifts answer at `elapsed` seconds past the observation, for
        the subject holding `value`: (lowest rate, highest rate, the value it stops at)."""
        at = taken + timedelta(seconds=elapsed)
        known = remember(memo, ("known", at), lambda: graphs_of(store, PUBLIC, BELIEF, RECORD, at=at, now=now or taken))
        #  THE OBSERVATION IN HAND IS READ AT EVERY INSTANT, with what the rules concluded of it —
        #  its key and its number live in its revisions — since a drift sized from the reading a
        #  committed step answers reads it past the stretch the observation holds for.
        graphs = list(dict.fromkeys([*known, *believed]))
        said = []
        for drift in drifts:
            try:
                answered = rows(store, drift["rate"], graphs, feature=feature, at=instant(at),
                                value=ox.Literal(repr(float(value)), datatype=ox.NamedNode(_XSD + "double")))
            except Exception as exc:                                    # noqa: BLE001
                log.error("drift %s would not run for a prediction: %s", local_of(drift["drift"]), exc)
                continue
            for row in answered:
                low, high = row.get("low", row.get("rate")), row.get("high", row.get("rate"))
                if low is None or high is None:
                    continue
                low, high = float(low), float(high)
                said.append((min(low, high), max(low, high), float(row["until"]) if row.get("until") else None))
        return said

    knots, moved = _accumulate(rates, reading, _happenings(store, cat, taken), memo)
    if not moved:
        #  NO DRIFT MOVES THIS KEY: it is predicted to stay as it reads, for an hour alone.
        if CARRIED_S <= base:
            return []
        stretches = [(base, CARRIED_S, None)]
    else:
        stretches = _stretches(knots, ranges, base)
    own = [ox.Triple(q.subject, q.predicate, q.object) for g in believed for q in quads(store, g)]
    written = []
    for n, (begins, closes, value) in enumerate(stretches):
        graph_n = prediction_graph(local_of(me), feature, observed_property, n)
        update(store, f"""
INSERT DATA {{
  {entry(store, graph_n, PREDICTION, RECORDED, me, start=taken + timedelta(seconds=begins), end=taken + timedelta(seconds=closes))}
  GRAPH <{catalogue_of(store)}> {{
    <{graph_n}> prov:wasDerivedFrom <{graph}> ;
                orexis:retracts {_literal(_RETRACTS % (feature, observed_property))} . }} }}""")
        triples = own if value is None else _observation(own, node, value[1], taken + timedelta(seconds=value[0]))
        store.extend(ox.Quad(t.subject, t.predicate, t.object, ox.NamedNode(graph_n)) for t in triples)
        written.append(graph_n)
    log.info("predicted %s of %s in %d stretch(es) from %s%s", local_of(observed_property), local_of(feature),
             len(written), opens.isoformat(timespec="seconds"),
             "".join(f", crossing at {(taken + timedelta(seconds=b)).isoformat(timespec='seconds')}"
                     for b, _, _ in stretches[1:]))
    return written


def _happenings(store, cat, taken: datetime) -> list[float]:
    """The seconds past the observation at which a public or belief graph begins or stops
    holding inside the horizon, earliest first, with the horizon's end."""
    found = rows(store, _HAPPENINGS_Q, (), cat=cat, kinds=Raw(f"<{PUBLIC}> <{BELIEF}>"),
                 **{"from": instant(taken), "to": instant(taken + timedelta(seconds=HORIZON_S))})
    return sorted({*((datetime.fromisoformat(r["t"]) - taken).total_seconds() for r in found), HORIZON_S})


def _accumulate(rates, reading: float, happenings: list[float], memo) -> tuple[list[tuple[float, float, float]], bool]:
    """The corridor from the observation to the horizon, as knots (elapsed, low, high) the two
    trajectories are straight between, and whether any drift moved the value at all.

    Each trajectory asks the drifts at its own value and moves by the sum of their lowest rates
    (the low one) or highest (the high one); a drift at or past its `until` in the direction it
    pushes contributes nothing, and a segment ends where the value reaches one, so the next
    asking sees the drift stopped."""
    t, lo, hi = 0.0, reading, reading
    knots, moved = [(t, lo, hi)], False
    for happening in happenings:
        while t < happening - 1e-9:
            said_lo = rates(t, lo)
            said_hi = said_lo if hi == lo else rates(t, hi)
            r_lo, stops_lo = _net(said_lo, lo, 0)
            r_hi, stops_hi = _net(said_hi, hi, 1)
            moved = moved or bool(said_lo or said_hi)
            step = min(happening - t, SEGMENT_S)
            step = min(step, _reach(lo, r_lo, stops_lo), _reach(hi, r_hi, stops_hi))
            lo, hi = _move(lo, r_lo, step, stops_lo), _move(hi, r_hi, step, stops_hi)
            t += step
            knots.append((t, min(lo, hi), max(lo, hi)))
            lo, hi = min(lo, hi), max(lo, hi)
    return knots, moved


def _net(said, value: float, end: int) -> tuple[float, list[float]]:
    """The summed rate of one trajectory — every contribution's lowest (`end` 0) or highest
    (`end` 1) — and the `until` values the contributing drifts push toward."""
    total, stops = 0.0, []
    for contribution in said:
        rate, until = contribution[end], contribution[2]
        if until is not None and ((rate < 0 and value <= until) or (rate > 0 and value >= until)):
            continue                                        # stopped where it stops
        total += rate
        if until is not None and rate != 0:
            stops.append(until)
    return total, stops


def _reach(value: float, rate: float, stops: list[float]) -> float:
    """How long until the value, moving at `rate`, reaches the nearest stop ahead of it."""
    ahead = [(s - value) / rate for s in stops if rate and (s - value) / rate > 1e-9]
    return min(ahead, default=math.inf)


def _move(value: float, rate: float, step: float, stops: list[float]) -> float:
    """The value `step` seconds on, landing on a stop exactly where it reaches one."""
    moved = value + rate * step
    for s in stops:
        if abs(moved - s) < 1e-9 or (value < s < moved) or (moved < s < value):
            return s
    return moved


def _stretches(knots, ranges, base: float) -> list[tuple[float, float, tuple[float, float]]]:
    """The stretches from `base` to the horizon between the instants the corridor's side
    changes, each with the instant its number is read at and the number: the last instant of
    the stretch whose number, as written, lies on its side — its end, a minute before where the
    end lies across a bound or rounding carries it there, or its middle."""
    crossings = sorted({c for (t0, lo0, hi0), (t1, lo1, hi1) in zip(knots, knots[1:])
                        for c in _crossed(t0, lo0, hi0, t1, lo1, hi1, ranges) if base < c < HORIZON_S})
    starts, ends = [base, *crossings], [*crossings, HORIZON_S]
    out = []
    for begins, closes in zip(starts, ends):
        sides = _sides(knots, ranges, (begins + closes) / 2)
        for at in (closes, closes - min(_EDGE_S, (closes - begins) / 2), (begins + closes) / 2):
            lo, hi = _at(knots, at)
            value = round(hi if 1 in sides and -1 not in sides else lo, PLACES)
            if tuple(side(low, high, value) for low, high in ranges) == sides:
                break                                   # the number as written reads the stretch's side
        out.append((begins, closes, (at, value)))
    return out


def _crossed(t0, lo0, hi0, t1, lo1, hi1, ranges) -> list[float]:
    """Every instant in one straight segment at which the low trajectory crosses a floor or the
    high one crosses a ceiling, to the whole second after it."""
    out = []
    for low, high in ranges:
        if (lo0 < low) != (lo1 < low):
            out.append(float(math.ceil(t0 + (low - lo0) / (lo1 - lo0) * (t1 - t0))))
        if (hi0 > high) != (hi1 > high):
            out.append(float(math.ceil(t0 + (high - hi0) / (hi1 - hi0) * (t1 - t0))))
    return out


def _sides(knots, ranges, elapsed: float) -> tuple[int, ...]:
    """The corridor's worst side of every range at `elapsed`: below where the low trajectory is
    under the floor, above where the high one is over the ceiling."""
    lo, hi = _at(knots, elapsed)
    return tuple(-1 if side(low, high, lo) < 0 else 1 if side(low, high, hi) > 0 else 0 for low, high in ranges)


def _at(knots, elapsed: float) -> tuple[float, float]:
    """The two trajectories at `elapsed`, straight between the knots."""
    for (t0, lo0, hi0), (t1, lo1, hi1) in zip(knots, knots[1:]):
        if t0 <= elapsed <= t1:
            f = 0.0 if t1 == t0 else (elapsed - t0) / (t1 - t0)
            return lo0 + (lo1 - lo0) * f, hi0 + (hi1 - hi0) * f
    return knots[-1][1], knots[-1][2]


def _observation(own, node: str, value: float, at: datetime) -> list:
    """The predicted observation: the one in hand's key and sensor, with `value` at `at`."""
    subject = ox.NamedNode(node)
    kept = {FEATURE, PROPERTY, _SOSA + "madeBySensor"}
    out = [ox.Triple(subject, _RDF_TYPE, ox.NamedNode(_SOSA + "Observation"))]
    out += [t for t in own if t.subject == subject and t.predicate.value in kept]
    number = f"{round(value, PLACES) + 0.0:.{PLACES}f}".rstrip("0")
    out.append(ox.Triple(subject, ox.NamedNode(RESULT), ox.Literal(number + ("0" if number.endswith(".") else ""),
                                                                  datatype=ox.NamedNode(_XSD + "decimal"))))
    out.append(ox.Triple(subject, ox.NamedNode(_SOSA + "resultTime"),
                         ox.Literal(at.isoformat(), datatype=ox.NamedNode(_XSD + "dateTime"))))
    return out


def _literal(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
