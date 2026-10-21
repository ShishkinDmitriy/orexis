"""`lay`: what an agent lays of a peer's holdings as forecasts — a belief about the peer's thing over each
period, which the grounds take in where each begins (knowledge/domain/coordination/conflict.md).

**WHILE A DRAW STANDS, BOTH LAY; ONCE DECIDED, THE LOSER LAYS ALL AND THE WINNER THE STEP IN FLIGHT.** For a
standing conflict the agent lays the peer's holdings, from the peer's latest question or, where it has heard
none, its answer: undecided, so each plans as if yielding and neither enters the contested values — safety
never waits on the draw; lost, or with the peer silent, every holding the peer says, which keeps the precedence
for as long as the conflict stands; won, only the peer's next holding, the change of a step the peer may have
taken before the draw reached it, which nothing a draw decides cancels — commitment is hard on the step in
flight. A conflict that does not stand lays nothing.

**ONLY WHAT THE AGENT'S OWN CONSTRAINTS ADMIT.** A peer's plan goes where the peer believes it can, and this
agent may see what the peer has not — a hedge its radar shows and the peer's does not yet. Laid there, the
peer's thing would stand on it in every ground from then on, and every world forked from those grounds would be
impossible: no plan at all. So a holding the agent's own constraints refuse beside what it believes now is not
laid; the peer finds the hedge, says new holdings, and those are.

**AT EACH INSTANT, EVERYTHING THE PEER MAY HOLD, BEGUN OR NOT.** A step lands somewhere in its band, so between
its earliest landing and its latest the peer's thing may stand at its old values or its new: both are laid, from
each instant something changes to the next (`_timeline`), and yielding means entering neither. One that has begun
is a step the peer took whose change sensing may not show yet — the van still between cells — so it is laid into
the present beside what sensing says; before the peer's first change, what it holds is sensing's alone; and what
ended is taken back.

WRITTEN WHERE IT CHANGED: a forecast of the agent's own, received, per holding laid, stamped; and forgotten
when nothing lays it any more.
"""

from __future__ import annotations

from datetime import datetime

import pyoxigraph as ox

from agent.hash_named_graph import hash_named_graph
from agent.ontology import BELIEF, FORECAST, RECEIVED, SELF_GRAPH
from agent.store import PREFIXES, Raw, catalogue_of, entry, forget_graph, graphs_of, rows, update

from .holdings import _TEXTS_Q, Holding, _heard, _present
from .ontology import CONSTRAINT_GRAPH, answer_graph, conflicts_graph, laid_graph, laid_root, question_graph

_STANDING_Q = """
SELECT ?c ?peer ?constraint ?draw ?silent WHERE { GRAPH $graph {
  ?c a coordination:Conflict ; coordination:with ?peer ; coordination:over ?constraint ; coordination:draw ?draw ;
     coordination:standing true . OPTIONAL { ?c coordination:silent ?silent } } }"""
_WON_Q = "SELECT ?w WHERE { $draw coordination:wonBy ?w } LIMIT 1"
#  EVERY GRAPH THE AGENT LAID BEFORE: its own forecasts, named under its laid root.
_LAID_Q = """SELECT ?g WHERE { GRAPH $cat { ?g a orexis:ForecastGraph . FILTER(STRSTARTS(STR(?g), $root)) } }"""


def lay(store: ox.Store, me: str, at: datetime) -> list[str]:
    """Lay, as forecasts, the peers' holdings the self `me` of `store` yields to at `at`, and take back what it
    laid and yields to no more; every graph written or forgotten."""
    cat = catalogue_of(store)
    if cat is None:
        return []
    beliefs = graphs_of(store, BELIEF)
    wanted: dict[str, Holding] = {}
    for r in rows(store, _STANDING_Q, (), graph=Raw(f"<{conflicts_graph(me)}>")):
        won = rows(store, _WON_Q, beliefs, draw=r["draw"])
        peer, constraint = r["peer"], r["constraint"]
        theirs = _heard(store, question_graph(peer, me, constraint)) or _heard(store, answer_graph(peer, me, constraint))
        if won and won[0]["w"] == me:                   # the winner lays the loser's step in flight alone
            theirs = [h for h in theirs if h.start is None or h.start == min(
                (o.start for o in theirs if o.thing == h.thing and o.start is not None), default=None)]
        theirs = [h for h in theirs if h.start is None or not _refused(store, h, at)]
        for n, h in enumerate(_timeline(theirs)):
            if h.end is None or h.end > at:
                wanted[laid_graph(me, peer, constraint, n)] = h
    laid = {r["g"] for r in rows(store, _LAID_Q, (), cat=Raw(f"<{cat}>"), root=Raw(f'"{laid_root(me)}"'))}
    written = []
    for graph in sorted(laid - set(wanted)):
        forget_graph(store, graph)
        written.append(graph)
    for graph, h in sorted(wanted.items()):
        if graph in laid and _holding_in(store, graph) == h:
            continue
        forget_graph(store, graph)
        facts = " ".join(f"<{h.thing}> <{p}> {_rendered(v)} ." for p, v in h.values)
        update(store, f"INSERT DATA {{ GRAPH <{graph}> {{ {facts} }} {entry(store, graph, FORECAST, RECEIVED, me, h.start, h.end)} }}")
        hash_named_graph(store, graph)
        written.append(graph)
    return written


def _timeline(held: list[Holding]) -> list[Holding]:
    """What a peer's thing may hold at each instant its holdings say anything changes: every value of every holding
    whose period holds then, from each start or end to the next. A step lands somewhere in its band, so the old
    values hold until its latest landing and the new from its earliest, and in between the thing may stand at
    either: laid one after the other, the later would take the earlier's key out where it begins, as a forecast
    does, and the band would be the peer's earliest landing alone. Nothing is laid before the first change, which
    is sensing's."""
    out: list[Holding] = []
    for thing in sorted({h.thing for h in held}):
        mine = [h for h in held if h.thing == thing]
        cuts = sorted({h.start for h in mine if h.start is not None} | {h.end for h in mine if h.end is not None})
        for n, t in enumerate(cuts):
            values = tuple(sorted({v for h in mine if (h.start is None or h.start <= t) and (h.end is None or h.end > t)
                                   for v in h.values}, key=lambda pv: (pv[0], str(pv[1]))))
            end = cuts[n + 1] if n + 1 < len(cuts) else None
            if not values:
                continue
            if out and out[-1].thing == thing and out[-1].values == values and out[-1].end == t:
                out[-1] = out[-1]._replace(end=end)
            else:
                out.append(Holding(thing, values, t, end))
    return out


_PERIOD_Q = """
SELECT ?start ?end WHERE { GRAPH $cat { $graph dcterms:temporal ?p . OPTIONAL { ?p orexis:start ?start } OPTIONAL { ?p orexis:end ?end } } } LIMIT 1"""


def _holding_in(store: ox.Store, graph: str) -> Holding | None:
    """What a laid forecast holds, as the holding it was laid of."""
    quads = list(store.quads_for_pattern(None, None, None, ox.NamedNode(graph)))
    if not quads:
        return None
    r = next(iter(rows(store, _PERIOD_Q, (), cat=Raw(f"<{catalogue_of(store)}>"), graph=Raw(f"<{graph}>"))), {})
    return Holding(quads[0].subject.value, tuple(sorted(((q.predicate.value, q.object) for q in quads), key=lambda pv: (pv[0], str(pv[1])))),
                   datetime.fromisoformat(r["start"]) if r.get("start") else None,
                   datetime.fromisoformat(r["end"]) if r.get("end") else None)


def _rendered(term: ox.Term) -> str:
    return str(term)


_HELD_Q = "SELECT ?c WHERE { ?me a orexis:Self ; planning:holds ?c . ?c a planning:Constraint }"


def _refused(store: ox.Store, held: Holding, at: datetime) -> bool:
    """Whether a constraint the agent holds reads a violation of the peer's thing holding `held`'s values beside
    everything else the agent believes now: the present's facts, the thing's own values replaced by the holding's,
    asked of each constraint's own select."""
    present = _present(store, at)
    common = graphs_of(store, BELIEF, common=True)
    scratch = ox.Store()
    thing = ox.NamedNode(held.thing)
    keys = {p for p, _ in held.values}
    for graph in dict.fromkeys([*common, *present]):
        for q in store.quads_for_pattern(None, None, None, ox.NamedNode(graph)):
            if q.subject == thing and q.predicate.value in keys:
                continue
            scratch.add(ox.Quad(q.subject, q.predicate, q.object, ox.DefaultGraph()))
    for predicate, value in held.values:
        scratch.add(ox.Quad(thing, ox.NamedNode(predicate), value, ox.DefaultGraph()))
    for c in rows(store, _HELD_Q, [*graphs_of(store, CONSTRAINT_GRAPH), *graphs_of(store, SELF_GRAPH)]):
        for r in rows(store, _TEXTS_Q, [*graphs_of(store, CONSTRAINT_GRAPH), *common], constraint=c["c"]):
            try:
                for row in scratch.query(PREFIXES + r["text"]):
                    if any(isinstance(term, ox.NamedNode) and term == thing for term in row):
                        return True
            except (SyntaxError, ValueError):
                continue
    return False
