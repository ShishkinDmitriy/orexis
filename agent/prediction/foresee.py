"""`foresee`: what moves from a ground — the flows integrated from each ground as the planner lays
them, every key of the agent advancing together, and a crossing of a range bound answered as the
place the next ground is laid (a-flow-is-integrated-where-the-ground-is-laid, #1000).

**THE FLOWS ARE INTEGRATED FROM EACH GROUND.** A ground is the state the agent foresees at an instant,
with the beliefs and forecasts holding then beside it; the flows are its derivative. Every
`prediction:Flow` that `prediction:moves` a key's property answers a RATE for the subject at an instant
— per second of the one timeline, a package's select over whatever holds then — and the flows ADD:
drying and rain are two flows and the value moves by their sum, PDDL+'s trajectory semantics, a flow
being a process (a-prediction-accumulates-rates-between-happenings). What a flow READS is the ground
the planner hands this, every graph holding at the instant asked beside it — a forecast hour or a
committed step by the period its row states, so a flow sees it exactly while it holds — and the keys'
current numbers, kept in a working graph of this package's own (`NUMBERS`), so a flow of one key reads
another's as it stands at that instant; and `$value`, the one number a flow is owed of its own key.
Between two grounds the rates are asked at every HAPPENING — the start or end of a belief holding
inside the stretch, since only there can what a flow reads change — and held for at most `SEGMENT_S`
between, so a rate that depends on the value is asked again. Within a segment the value is a straight
line, and a crossing of a bound of every range that applies to what the sensor observes
(SSN-System's, `ranges_of`) is placed exactly, by division. A flow answering `?until` contributes
nothing past it, and a segment is split where the value reaches it.

**EVERY KEY ADVANCES TOGETHER.** At each segment every flow of every key is asked at the same
instant, reading the same ground and the same numbers, and every key moves by its own sum: soil
reading air and air reading soil are two coupled flows, not a cycle, and nothing orders the keys.

**A RATE KNOWN AS A RANGE GIVES A CORRIDOR.** A flow may answer `?low` and `?high` instead of
`?rate`, and ranges add as rates do; two trajectories are accumulated, the low one by every flow's
lowest rate and the high one by every flow's highest, each asking the flows at its own value. The side
of an instant is the corridor's worst, range by range, and the number handed on is the trajectory that
side was read from, so the rules conclude of it the side the corridor has.

**WHAT IS ANSWERED IS THE NEXT KNOT, WITH THE PREDICTED OBSERVATION TO LAY THERE.** `advance`
integrates from one instant to the next boundary the planner knows of and answers the earliest instant
at which any key the caller lays crosses a bound — with, for each key crossing there, a predicted
`sosa:Observation` in SOSA's words, ONE node per key, carrying the number at the far end of the stretch
the crossing opens, the last instant known to lie on the new side — or the hour's end, where a key it
lays has moved by then, with the number it then stands at, since a state the transitions hold past its
bound by a margin this package does not read is judged again within the hour; or nothing, having
advanced every key to the boundary. The planner lays a ground at the crossing, the observation arrives in it and the
domain's transitions judge it there, beside the state the ground before held and with the margin the
range states; this package writes no forecast and no state (#944). The numbers stay here, between the
grounds, and nothing of the mind reads them.

**THE KEYS ARE READ OFF THE BELIEF BASE ONCE.** `foresee` takes each sensor's latest percept
(`sensing:ObservationGraph`, sensing's kind, the one word of sensing's this package speaks from above
it, #944) with what the rules concluded of it — its key and its number — and the flows moving its
property, off the flow graphs alone (`orexis:FlowGraph`); a key no flow moves is foreseen nothing,
since a package that declares no flow has made no claim about the world (#989). The agent looks as far
as `prediction:horizonS`, a stance in its self graph, a day where it states none.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import pyoxigraph as ox

from agent.ontology import FLOW_GRAPH, local_of
from agent.stance import stance
from agent.store import PLACES, Raw, add_quads, catalogue_of, clear_graph, graphs_of, instant, revisions_of, rows

from .ontology import FLOW, FEATURE, HORIZON_TERM, MOVES, OBSERVATION_GRAPH, PROPERTY, RATE, RESULT, predicted_of
from .ranges import ranges_of, side

log = logging.getLogger("foresee")

_XSD = "http://www.w3.org/2001/XMLSchema#"
_SOSA = "http://www.w3.org/ns/sosa/"
_RDF_TYPE = ox.NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
_DOUBLE = ox.NamedNode(_XSD + "double")

#  HOW FAR PAST THE OBSERVATION THE AGENT LOOKS, in the timeline's seconds, where its self graph
#  states no `prediction:horizonS`: a day. A stance, since how far ahead the agent sees is which
#  foreseen crossings it mints a want for, and so which plans it selects now
#  (knowledge/domain/kernel/stance.md).
HORIZON_S = 86400.0

#  THE LONGEST A RATE IS HELD before the flows are asked again: an hour, so a rate that
#  depends on the value it moves is read off a value no more than an hour old.
SEGMENT_S = 3600.0

#  WHERE A STRETCH'S NUMBER IS READ when its end lies across a bound: this long before the end,
#  or half the stretch where that is shorter.
_EDGE_S = 60.0

#  THE KEYS' CURRENT NUMBERS, as the flows read them: a working graph of this package's own in the store
#  the grounds are laid in, rewritten at every instant the flows are asked at and taken away when the
#  laying is done. Not a belief and classified as nothing, so no reader of the mind is handed it; its
#  name is for eyes.
NUMBERS = "http://example.org/orexis/graph/ground/foreseen-numbers"

#  EVERY SENSOR WITH A PERCEPT IN HAND, by sensing's kind and SOSA's pattern.
_SENSORS_Q = """
SELECT DISTINCT ?sensor WHERE {
  GRAPH $cat { ?g a sensing:ObservationGraph }
  GRAPH ?g { ?o sosa:madeBySensor ?sensor } }
ORDER BY ?sensor"""

#  THE OBSERVATION IN HAND: the percept holding the node this sensor last made, asked by sensing's kind
#  and by SOSA's pattern, never by name — the pattern also passes over a revision, which is of the same
#  kind and holds no `sosa:madeBySensor`. THE LATEST is the one begun last — a percept's period runs to
#  the next one's instant, so no two of a sensor's begin at once unless it read twice in one instant,
#  and then the one still holding, whose end is the later or none, is it (#944). Its key and its number
#  are asked of the graph and its revisions together (`_KEY_Q`), since what an observation is OF and its
#  quantity are what the rules concluded of the number the sensor gave.
_OBSERVATION_Q = """
SELECT ?graph ?node ?taken ?from WHERE {
  GRAPH $cat { ?graph a sensing:ObservationGraph ; dcterms:temporal ?p . ?p orexis:start ?from .
               OPTIONAL { ?p orexis:end ?until } }
  GRAPH ?graph { ?node sosa:madeBySensor $sensor . OPTIONAL { ?node sosa:resultTime ?taken } } }
ORDER BY DESC(?from) ASC(BOUND(?until)) DESC(?until) LIMIT 1"""
_KEY_Q = """
SELECT ?feature ?property ?value WHERE {
  $node sosa:hasFeatureOfInterest ?feature ; sosa:observedProperty ?property ; sosa:hasSimpleResult ?value } LIMIT 1"""

#  EVERY FLOW MOVING THE PROPERTY — the terms spliced as the terms they are, since no file of this
#  package binds a label for its namespace and a query needs none. Read from the graphs of flows alone
#  (`orexis:FlowGraph`), as the planner reads actions from `orexis:ActionGraph` alone: named for what it
#  holds, and asked for, it is a term somebody reads. The kind is the kernel's and not this package's: a
#  domain ships flows whether or not any of its agents is a predictor.
_FLOWS_Q = "SELECT ?flow ?rate WHERE { ?flow a $flow ; $moves $property ; $rate_of ?rate } ORDER BY ?flow"

#  THE HAPPENINGS: every instant inside a stretch at which a belief begins or stops holding — the only
#  instants, between two grounds, at which what a flow reads can change.
_HAPPENINGS_Q = """
SELECT DISTINCT ?t WHERE {
  GRAPH $cat { ?g a orexis:BeliefGraph ; dcterms:temporal ?p . { ?p orexis:start ?t } UNION { ?p orexis:end ?t } }
  FILTER(?t > $from && ?t < $to) }"""


@dataclass
class _Key:
    """One key the agent foresees: the sensor, what it observes, the corridor as it stands and the
    knots of the last stretch integrated, in seconds past the integration's origin."""
    sensor: str
    feature: str
    property: str
    taken: float                     # when the reading in hand was taken, seconds past the origin
    horizon: float                   # how far this key is looked at, seconds past the origin
    ranges: list[tuple[float, float]]
    flows: list[dict]
    laid: bool                       # whether a crossing of this key is the caller's to lay
    lo: float
    hi: float
    knots: list[tuple[float, float, float]] = field(default_factory=list)


class Foresight:
    """The integration of every key of the agent, carried from ground to ground: `advance` to the next
    boundary, answering the earliest crossing, and `finish` when the grounds are laid. Made by `foresee`
    and nothing else; what it reads of a store is what the caller's `graphs_at` hands it."""

    def __init__(self, origin: datetime, keys: list[_Key]):
        self.origin = origin
        self.keys = keys
        self.t: float | None = None                 # where the integration stands, past the origin

    @property
    def horizon(self) -> datetime:
        """The last instant any key is looked at."""
        return self.origin + timedelta(seconds=max(k.horizon for k in self.keys))

    def advance(self, store, at: datetime, until: datetime, graphs_at) -> tuple[datetime, list[ox.Triple]] | None:
        """Integrate every key from `at` to `until`, reading `graphs_at(instant)` — the ground the planner
        stands in and every graph holding at the instant beside it — and answer the earliest instant in
        `(at, until]` at which a key the caller lays crosses a range bound, with the predicted observation
        of each key crossing there; None where none does, every key then standing at `until`. Asked first
        at `at`, each key is carried from its reading's instant to `at` reading what holds at `at`."""
        t0, t1 = self._s(at), self._s(min(until, self.horizon))
        if self.t is None:
            self._catch_up(store, t0, graphs_at)
        if t1 <= self.t + 1e-9:
            self.t = max(self.t, t1)
            return None
        t0 = self.t
        self._integrate(store, t0, t1, graphs_at)
        #  THE NEXT KNOT: the earliest crossing of any key the caller lays, or the hour's end where a key it
        #  lays has moved by then — a state held past its bound by a margin this package does not read is
        #  judged again within the hour, and a key standing still is judged nothing.
        crossings = {key.sensor: _crossings(key.knots, key.ranges, t0, t1) for key in self.keys if key.laid}
        first = min((c[0] for c in crossings.values() if c), default=math.inf)
        cap = t0 + SEGMENT_S
        moved = {key.sensor for key in self.keys if key.laid and _at(key.knots, min(cap, t1)) != _at(key.knots, t0)}
        if cap <= t1 + 1e-9 and cap < first and moved:
            first = cap
        if first == math.inf:
            self._stand_at(store, t1)
            return None
        arrival: list[ox.Triple] = []
        for key in self.keys:
            found = crossings.get(key.sensor, [])
            if found and abs(found[0] - first) < 1e-9:
                #  THE NUMBER LAID AT A CROSSING IS READ AT THE FAR END OF THE STRETCH IT OPENS — the next
                #  crossing, the hour's end or the boundary, whichever comes first — the last instant known to
                #  lie on the new side, so the side as written is the stretch's and not the bound's edge.
                far = min([*(c for c in found if c > first + 1e-9), first + SEGMENT_S, t1])
                when, value = _number_on_its_side(key.knots, key.ranges, first, far)
                arrival += _observation(key, value, self.origin + timedelta(seconds=when))
            elif key.laid and key.sensor in moved and first == cap:
                key.lo, key.hi = _at(key.knots, first)
                arrival += _observation(key, _worst(key), self.origin + timedelta(seconds=first))
        self._stand_at(store, first)
        return self.origin + timedelta(seconds=first), arrival

    def finish(self, store) -> None:
        """Take the working graph away: the grounds are laid, and nothing reads the numbers after."""
        clear_graph(store, NUMBERS)

    # --- the integration ------------------------------------------------------------------------

    def _s(self, at: datetime) -> float:
        return (at - self.origin).total_seconds()

    def _catch_up(self, store, t0: float, graphs_at) -> None:
        """Carry each key from the instant its reading was taken to `t0`, reading what holds at `t0`:
        the present is where the reading is judged, and the stretch behind it is read as the present."""
        for key in self.keys:
            t = key.taken
            while t < t0 - 1e-9:
                self._numbers(store, t)
                graphs = [NUMBERS, *graphs_at(self.origin + timedelta(seconds=t0))]
                r_lo, stops_lo = _net(self._rates(store, key, key.lo, t, graphs), key.lo, 0)
                r_hi, stops_hi = _net(self._rates(store, key, key.hi, t, graphs), key.hi, 1)
                step = min(t0 - t, SEGMENT_S, _reach(key.lo, r_lo, stops_lo), _reach(key.hi, r_hi, stops_hi))
                key.lo, key.hi = sorted((_move(key.lo, r_lo, step, stops_lo), _move(key.hi, r_hi, step, stops_hi)))
                t += step
        self.t = t0

    def _integrate(self, store, t0: float, t1: float, graphs_at) -> None:
        """Every key from `t0` to `t1`, together: at each segment every key's flows are asked at the same
        instant over the same graphs and the same numbers, and every key moves by its own sum. The
        knots of each key are left on it, `t0` first."""
        cat = Raw(f"<{catalogue_of(store)}>")
        happenings = {datetime.fromisoformat(r["t"]) for r in rows(
            store, _HAPPENINGS_Q, (), cat=cat, **{"from": self._at(t0), "to": self._at(t1)})}
        marks = sorted({*(self._s(h) for h in happenings), *(k.horizon for k in self.keys if t0 < k.horizon < t1), t1})
        for key in self.keys:
            key.knots = [(t0, key.lo, key.hi)]
        t = t0
        for mark in marks:
            while t < mark - 1e-9:
                self._numbers(store, t)
                graphs = [NUMBERS, *graphs_at(self.origin + timedelta(seconds=t))]
                plans = {}
                for key in self.keys:
                    if t >= key.horizon - 1e-9:
                        continue                        # looked at no further: it stands
                    said_lo = self._rates(store, key, key.lo, t, graphs)
                    said_hi = said_lo if key.hi == key.lo else self._rates(store, key, key.hi, t, graphs)
                    plans[key.sensor] = (*_net(said_lo, key.lo, 0), *_net(said_hi, key.hi, 1))
                step = min(mark - t, SEGMENT_S)
                for key in self.keys:
                    if key.sensor in plans:
                        r_lo, stops_lo, r_hi, stops_hi = plans[key.sensor]
                        step = min(step, _reach(key.lo, r_lo, stops_lo), _reach(key.hi, r_hi, stops_hi))
                for key in self.keys:
                    if key.sensor in plans:
                        r_lo, stops_lo, r_hi, stops_hi = plans[key.sensor]
                        key.lo, key.hi = sorted((_move(key.lo, r_lo, step, stops_lo), _move(key.hi, r_hi, step, stops_hi)))
                    key.knots.append((t + step, key.lo, key.hi))
                t += step

    def _rates(self, store, key: _Key, value: float, t: float, graphs) -> list[tuple[float, float, float | None]]:
        """Every contribution the key's flows answer at `t` for the subject holding `value`: (lowest
        rate, highest rate, the value it stops at)."""
        said = []
        for flow in key.flows:
            try:
                answered = rows(store, flow["rate"], graphs, feature=key.feature, at=self._at(t),
                                value=ox.Literal(repr(float(value)), datatype=_DOUBLE))
            except Exception as exc:                                    # noqa: BLE001
                log.error("flow %s would not run for a prediction: %s", local_of(flow["flow"]), exc)
                continue
            for row in answered:
                low, high = row.get("low", row.get("rate")), row.get("high", row.get("rate"))
                if low is None or high is None:
                    continue
                low, high = float(low), float(high)
                said.append((min(low, high), max(low, high), float(row["until"]) if row.get("until") else None))
        return said

    def _stand_at(self, store, t: float) -> None:
        """Every key as it stands at `t`, read off its knots, and the numbers rewritten there — rounded
        past any float's error, so a knot laid at the whole second after a crossing stands on the bound
        or past it and never a hair short, which would cross it again a second later."""
        for key in self.keys:
            key.lo, key.hi = (round(v, 12) for v in _at(key.knots, t))
        self.t = t
        self._numbers(store, t)

    def _numbers(self, store, t: float) -> None:
        """The working graph rewritten with every key's number at `t`: the trajectory its worst side is
        read from, or the corridor's middle where it is inside every range."""
        clear_graph(store, NUMBERS)
        at = self.origin + timedelta(seconds=t)
        add_quads(store, [ox.Quad(tr.subject, tr.predicate, tr.object, ox.NamedNode(NUMBERS))
                          for key in self.keys for tr in _observation(key, _worst(key), at)])

    def _at(self, t: float) -> ox.Literal:
        return instant(self.origin + timedelta(seconds=t))


def foresee(beliefs, now: datetime, *, placed=None, memo=None) -> Foresight | None:
    """The agent's foresight from `now`: every key some flow moves, read off the belief base — each
    sensor's latest percept with what the rules concluded of it, the flows moving its property, the
    ranges that apply to it and the horizon the agent looks to — ready to be advanced ground by ground.
    None where no key is moved by any flow.

    `placed` says, of a key's feature and property, whether a crossing of it is the caller's to lay —
    the scope's readings, as the planner places them; None lays every key. Every key is advanced
    either way, since a flow of the caller's may read another's number.
    """
    cat = catalogue_of(beliefs)
    if cat is None:
        return None
    horizon = stance(beliefs, HORIZON_TERM, HORIZON_S, memo)
    flow_graphs = graphs_of(beliefs, FLOW_GRAPH)
    keys = []
    for sensor in (r["sensor"] for r in rows(beliefs, _SENSORS_Q, (), cat=Raw(f"<{cat}>"))):
        found = next(iter(rows(beliefs, _OBSERVATION_Q, (), cat=Raw(f"<{cat}>"), sensor=sensor)), None)
        if found is None:
            continue
        graph, node = found["graph"], found["node"]
        believed = [graph, *revisions_of(beliefs, graph, kind=OBSERVATION_GRAPH)]
        key = next(iter(rows(beliefs, _KEY_Q, believed, node=node)), None)
        if key is None:
            log.debug("%s's observation is of nothing the rules concluded: foreseen nothing", local_of(sensor))
            continue
        flows = rows(beliefs, _FLOWS_Q, flow_graphs, flow=Raw(f"<{FLOW}>"), moves=Raw(f"<{MOVES}>"),
                     rate_of=Raw(f"<{RATE}>"), property=key["property"])
        if not flows:
            log.debug("no flow moves %s of %s: foreseen nothing", local_of(key["property"]), local_of(key["feature"]))
            continue
        taken = datetime.fromisoformat(found["taken"] if found.get("taken") else found["from"])
        if taken + timedelta(seconds=horizon) <= now:
            continue
        reading = float(key["value"])
        keys.append(_Key(sensor, key["feature"], key["property"], (taken - now).total_seconds(),
                         (taken - now).total_seconds() + horizon,
                         ranges_of(beliefs, sensor, key["property"], memo), flows,
                         placed is None or bool(placed(key["feature"], key["property"])), reading, reading))
    if not keys:
        return None
    log.debug("foreseeing %d key(s): %s", len(keys), ", ".join(local_of(k.sensor) for k in keys))
    return Foresight(now, keys)


# --- the arithmetic, on knots -------------------------------------------------------------------

def _net(said, value: float, end: int) -> tuple[float, list[float]]:
    """The summed rate of one trajectory — every contribution's lowest (`end` 0) or highest
    (`end` 1) — and the stops ahead of it: a contribution at or past its `until` in the direction
    it pushes adds nothing."""
    total, stops = 0.0, []
    for contribution in said:
        rate, until = contribution[end], contribution[2]
        if until is not None and ((rate < 0 and value <= until) or (rate > 0 and value >= until)):
            continue
        total += rate
        if until is not None and rate != 0:
            stops.append(until)
    return total, stops


def _reach(value: float, rate: float, stops: list[float]) -> float:
    """How long until the value, moving at `rate`, reaches the nearest stop ahead of it."""
    ahead = [(s - value) / rate for s in stops if rate and (s - value) / rate > 1e-9]
    return min(ahead) if ahead else math.inf


def _move(value: float, rate: float, step: float, stops: list[float]) -> float:
    """The value `step` seconds on at `rate`, held at a stop it would pass."""
    moved = value + rate * step
    for s in stops:
        if (rate > 0 and value < s < moved) or (rate < 0 and moved < s < value) or abs(moved - s) < 1e-12:
            moved = s
    return moved


def _crossings(knots, ranges, after: float, before: float) -> list[float]:
    """Every instant in `(after, before]` at which the corridor's low trajectory crosses a floor or its
    high one a ceiling, earliest first, each to the whole second after it."""
    found = sorted({c for n, ((t0, lo0, hi0), (t1, lo1, hi1)) in enumerate(zip(knots, knots[1:]))
                    for c in _crossed(t0, lo0, hi0, t1, lo1, hi1, ranges, opening=n == 0) if after < c <= before})
    return found


def _crossed(t0, lo0, hi0, t1, lo1, hi1, ranges, opening: bool = False) -> list[float]:
    """Every instant in one straight segment at which the low trajectory crosses a floor or the
    high one crosses a ceiling, to the whole second after it — a bound itself is inside, as `side` reads
    it. In the segment OPENING a stretch, a trajectory standing on the bound has crossed it: a knot is
    laid at the whole second after a crossing and may stand exactly on the bound, and read as inside it
    would cross the same bound again a second later."""
    out = []
    for low, high in ranges:
        if lo1 != lo0 and ((lo0 <= low) if opening else (lo0 < low)) != (lo1 < low):
            out.append(float(math.ceil(t0 + (low - lo0) / (lo1 - lo0) * (t1 - t0))))
        if hi1 != hi0 and ((hi0 >= high) if opening else (hi0 > high)) != (hi1 > high):
            out.append(float(math.ceil(t0 + (high - hi0) / (hi1 - hi0) * (t1 - t0))))
    return out


def _number_on_its_side(knots, ranges, begins: float, closes: float) -> tuple[float, float]:
    """The number laid for the stretch from `begins` to `closes`, and the instant it is read at: the
    last instant of the stretch whose number, as written, lies on the stretch's side — its end, a
    minute before where the end lies across a bound or rounding carries it there, or its middle."""
    sides = _sides(knots, ranges, (begins + closes) / 2)
    at, value = closes, 0.0
    for at in (closes, closes - min(_EDGE_S, (closes - begins) / 2), (begins + closes) / 2):
        lo, hi = _at(knots, at)
        value = round(hi if 1 in sides and -1 not in sides else lo, PLACES)
        if tuple(side(low, high, value) for low, high in ranges) == sides:
            break                                   # the number as written reads the stretch's side
    return at, value


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


def _worst(key: _Key) -> float:
    """The number a key stands at for the flows: the trajectory its worst side is read from, or the
    corridor's middle where it lies inside every range."""
    sides = tuple(-1 if side(low, high, key.lo) < 0 else 1 if side(low, high, key.hi) > 0 else 0 for low, high in key.ranges)
    return key.lo if -1 in sides else key.hi if 1 in sides else (key.lo + key.hi) / 2


def _observation(key: _Key, value: float, at: datetime) -> list[ox.Triple]:
    """The predicted observation of `key`: a node of its own, one per key as a fluent is, with the key's
    feature, property and sensor, the `value` and the instant — never the percept, which is what a
    sensor said and crosses into no ground (#944)."""
    subject = ox.NamedNode(predicted_of(key.feature, key.property))
    number = f"{round(value, PLACES) + 0.0:.{PLACES}f}".rstrip("0")
    return [ox.Triple(subject, _RDF_TYPE, ox.NamedNode(_SOSA + "Observation")),
            ox.Triple(subject, ox.NamedNode(FEATURE), ox.NamedNode(key.feature)),
            ox.Triple(subject, ox.NamedNode(PROPERTY), ox.NamedNode(key.property)),
            ox.Triple(subject, ox.NamedNode(_SOSA + "madeBySensor"), ox.NamedNode(key.sensor)),
            ox.Triple(subject, ox.NamedNode(RESULT), ox.Literal(number + ("0" if number.endswith(".") else ""),
                                                                datatype=ox.NamedNode(_XSD + "decimal"))),
            ox.Triple(subject, ox.NamedNode(_SOSA + "resultTime"),
                      ox.Literal(at.isoformat(), datatype=ox.NamedNode(_XSD + "dateTime")))]
