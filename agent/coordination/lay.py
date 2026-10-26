"""`lay`: what an agent lays of a peer's holdings as forecasts — a belief about the peer's thing over each
period, which the grounds take in where each begins (knowledge/domain/coordination/conflict.md).

**WHILE A DRAW STANDS, BOTH LAY; ONCE DECIDED, THE LOSER LAYS ALL AND THE WINNER THE STEP IN FLIGHT.** For a
standing conflict the agent lays the peer's holdings, from the peer's latest question or, where it has heard
none, its answer: undecided, so each plans as if yielding and neither enters the contested values — safety
never waits on the draw; lost, or with the peer silent, every holding the peer says, which keeps the precedence
for as long as the conflict stands; won, only what a step the peer has taken gives its thing, as the peer says
it (`coordination:taken`), which nothing a draw decides cancels — commitment is hard on the step in flight.
Yielding to the peer's next holding whether taken or not, the winner yielded every time the loser's next drive
was the contested cell, and at a crossing the loser crossed first. A conflict that does not stand lays nothing.

**OF A SILENT PEER THAT SAID NOTHING, WHERE ITS THINGS MAY BE.** A peer that says nothing says nothing of where it
is going, so the agent estimates it — one silent by its draw's restarts said its holdings, which are laid, and is
estimated nothing more: each `coordination:Reach` a world's rules ship says where a thing may be a step of its own
ahead, and asked of where the agent believes the peer's thing now, and again of each answer, as many times as the
agent's lookahead says (`coordination:lookahead`, two, and one more where the lot it drew alone this round was
lost), it gives every place the thing may stand by then, each a node of its own, laid as a forecast from now for
as many of the longest step a reach says it takes (`coordination:stepS`) — after which only the next sighting
says, and a plan may wait the window out. A place laid stands while a step of its window is left, and is laid
again where the places move or less is left: let lapse while the peer was still in sight, nothing of it would be
foreseen until the next pass, and a step taken then would have been taken blind.
One for the step the peer may take next, one more since what the agent believes of the peer may be a step behind;
and laid one node per place, so the thing's keys are never crossed into places it cannot stand. The one constraint
over the thing, the world's own, keeps the agent's plans out of every place laid, and a sighting that moves the
peer moves what is laid, which reopens a walking plan it makes impossible. No place is laid where the agent's own
step in flight lands: that step is never cancelled, so a peer foreseen there would make every world impossible.

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

from datetime import datetime, timedelta

import pyoxigraph as ox

from agent.hash_named_graph import hash_named_graph
from agent.ontology import BELIEF, FORECAST, RECEIVED, SELF_GRAPH
from agent.stance import stance
from agent.store import PREFIXES, Raw, bind, catalogue_of, entry, forget_graph, graphs_of, rows, update

from .holdings import _TEXTS_Q, Holding, _heard, _key_of, _present, holdings
from .ontology import (CONSTRAINT_GRAPH, LOOKAHEAD, LOOKING, answer_graph, conflicts_graph, laid_graph, laid_root,
                       question_graph)

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
    foreseen: dict[str, timedelta] = {}            # each place foreseen, and one step of its window
    for r in rows(store, _STANDING_Q, (), graph=Raw(f"<{conflicts_graph(me)}>")):
        won = rows(store, _WON_Q, beliefs, draw=r["draw"])
        peer, constraint = r["peer"], r["constraint"]
        theirs = _heard(store, question_graph(peer, me, constraint)) or _heard(store, answer_graph(peer, me, constraint))
        said = bool(theirs)
        if won and won[0]["w"] == me:                   # the winner lays the loser's step in flight alone
            theirs = [h for h in theirs if h.start is None or h.taken]
        if r.get("silent") == "true" and not said:      # and of a silent peer that said nothing, where its things may be
            ahead = int(stance(store, LOOKAHEAD, LOOKING)) + (1 if won and won[0]["w"] != me else 0)
            landing = [h for h in holdings(store, constraint, at) if h.taken]   # never where its own step in flight lands
            reached = [h for h in _reach(store, peer, constraint, ahead, at) if not _refused(store, h, at, landing)]
            foreseen |= {h.thing: (h.end - at) / max(ahead, 1) for h in reached if h.end is not None}
            theirs += reached
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
        held = _holding_in(store, graph) if graph in laid else None
        if held == h or (held is not None and h.thing in foreseen and held.thing == h.thing
                         and held.values == h.values and held.end is not None and held.end - at > foreseen[h.thing]):
            continue                                # a place foreseen stands while a step of its window is left
        forget_graph(store, graph)
        facts = " ".join(f"<{h.thing}> <{p}> {_rendered(v)} ." for p, v in h.values)
        update(store, f"INSERT DATA {{ GRAPH <{graph}> {{ {facts} }} {entry(store, graph, FORECAST, RECEIVED, me, h.start, h.end)} }}")
        hash_named_graph(store, graph)
        written.append(graph)
    return written


def _laid(store: ox.Store, me: str) -> dict[tuple[str, str], tuple[list[Holding], list[Holding]]]:
    """What the self `me` of `store` lays now, per peer and constraint of a conflict it holds: the holdings the
    peer said, and those it foresaw of the peer — told apart by whether the peer acts for the thing. What a
    history view is told; a conflict laying nothing answers two empty lists."""
    cat = catalogue_of(store)
    if cat is None:
        return {}
    present = {r["g"] for r in rows(store, _LAID_Q, (), cat=Raw(f"<{cat}>"), root=Raw(f'"{laid_root(me)}"'))}
    out = {}
    for r in rows(store, _ALL_Q, (), graph=Raw(f"<{conflicts_graph(me)}>")):
        peer, constraint = r["peer"], r["constraint"]
        acts = {a["t"] for a in rows(store, _ACTS_FOR_Q, graphs_of(store, BELIEF, common=True), peer=peer)}
        said, foreseen = [], []
        under = laid_graph(me, peer, constraint, 0)[:-1]
        for graph in sorted((g for g in present if g.startswith(under)), key=lambda g: int(g[len(under):])):
            if (h := _holding_in(store, graph)) is not None:
                (said if h.thing in acts else foreseen).append(h)
        out[(peer, constraint)] = (said, foreseen)
    return out


_ALL_Q = """SELECT DISTINCT ?peer ?constraint WHERE { GRAPH $graph { ?c a coordination:Conflict ; coordination:with ?peer ;
                                                                   coordination:over ?constraint } } ORDER BY ?peer ?constraint"""


#  THE THINGS A PEER ACTS FOR; WHAT THE AGENT BELIEVES EACH IS; AND EVERY REACH A WORLD'S RULES SHIP.
_ACTS_FOR_Q = "SELECT ?t WHERE { $peer orexis:actsFor ?t } ORDER BY ?t"
_REACH_Q = """SELECT ?text ?step WHERE { ?rule a coordination:Reach ; sh:construct ?text .
                                         OPTIONAL { ?rule coordination:stepS ?step }
                                         FILTER NOT EXISTS { ?rule sh:deactivated true } } ORDER BY ?rule"""
_RULES_GRAPH = "http://www.w3.org/ns/shacl#RulesGraph"
_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"


def _reach(store: ox.Store, peer: str, constraint: str, ahead: int, at: datetime) -> list[Holding]:
    """Every place a thing `peer` acts for may stand `ahead` of its steps on, as the world's reaches say: a holding
    per place, of a node standing for the thing there, with the kinds and the values on `constraint`'s key the reach
    gives it, from `at` for `ahead` of the longest step a reach says (`coordination:stepS`), for ever where one says none — the places it holds now left out, which are what sensing says. Each reach is asked over
    everything the agent believes now, the thing's own values on the key replaced by the place it is foreseen from,
    so a reach, about `$this`, the thing, may read the world — the free tools a robot may pick up — and a thing holding nothing on the key, a
    robot with free hands, is foreseen too."""
    key = _key_of(store, constraint)
    reaches = rows(store, _REACH_Q, graphs_of(store, _RULES_GRAPH))
    texts = [r["text"] for r in reaches]
    if not key or not texts:
        return []
    steps = [float(r["step"]) for r in reaches if r.get("step") is not None]
    until = at + timedelta(seconds=ahead * max(steps)) if len(steps) == len(reaches) else None
    present = _present(store, at)
    common = graphs_of(store, BELIEF, common=True)
    order = lambda pv: (pv[0], str(pv[1]))                      # noqa: E731
    out: list[Holding] = []
    for r in rows(store, _ACTS_FOR_Q, common, peer=peer):
        thing = ox.NamedNode(r["t"])
        scratch, now = ox.Store(), set()
        for graph in dict.fromkeys([*common, *present]):
            for q in store.quads_for_pattern(None, None, None, ox.NamedNode(graph)):
                if q.subject == thing and q.predicate.value in key:
                    now.add((q.predicate.value, q.object))
                else:
                    scratch.add(ox.Quad(q.subject, q.predicate, q.object, ox.DefaultGraph()))
        now = tuple(sorted(now, key=order))
        seen, frontier, places = {now}, [now], {}
        for _ in range(ahead):
            nxt = []
            for values in frontier:
                held = [ox.Quad(thing, ox.NamedNode(p), v, ox.DefaultGraph()) for p, v in values]
                scratch.extend(held)
                for text in texts:
                    found: dict = {}
                    for t in scratch.query(PREFIXES + bind(text, this=thing)):
                        found.setdefault(t.subject, []).append((t.predicate.value, t.object))
                    for node, pvs in found.items():
                        place = tuple(sorted(((p, v) for p, v in pvs if p in key), key=order))
                        if place in seen or not place:
                            continue
                        seen.add(place)
                        nxt.append(place)
                        places[node.value] = tuple(sorted(pvs, key=order))
                for q in held:
                    scratch.remove(q)
            frontier = nxt
        out += [Holding(node, values, at, until) for node, values in sorted(places.items())]
    return out


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


def _refused(store: ox.Store, held: Holding, at: datetime, landing: list[Holding] = ()) -> bool:
    """Whether a constraint the agent holds reads a violation of the peer's thing holding `held`'s values beside
    everything else the agent believes now: the present's facts, the thing's own values replaced by the holding's,
    asked of each constraint's own select — and again beside each of `landing`, a holding of the agent's own its
    step in flight lands in, that overlaps `held` in time, the agent's thing's values replaced by that holding's."""
    present = _present(store, at)
    common = graphs_of(store, BELIEF, common=True)
    base = [q for graph in dict.fromkeys([*common, *present]) for q in store.quads_for_pattern(None, None, None, ox.NamedNode(graph))]
    thing = ox.NamedNode(held.thing)
    texts = [r["text"] for c in rows(store, _HELD_Q, [*graphs_of(store, CONSTRAINT_GRAPH), *graphs_of(store, SELF_GRAPH)])
             for r in rows(store, _TEXTS_Q, [*graphs_of(store, CONSTRAINT_GRAPH), *common], constraint=c["c"])]
    beside = [held, *(m for m in landing if (held.end is None or m.start is None or m.start < held.end)
                      and (m.end is None or held.start is None or held.start < m.end))]
    for h in beside:
        replaced = {(ox.NamedNode(x.thing), p) for x in {held, h} for p, _ in x.values}
        scratch = ox.Store()
        for q in base:
            if (q.subject, q.predicate.value) not in replaced:
                scratch.add(ox.Quad(q.subject, q.predicate, q.object, ox.DefaultGraph()))
        for x in {held, h}:
            for predicate, value in x.values:
                scratch.add(ox.Quad(ox.NamedNode(x.thing), ox.NamedNode(predicate), value, ox.DefaultGraph()))
        for text in texts:
            try:
                for row in scratch.query(PREFIXES + text):
                    if any(isinstance(term, ox.NamedNode) and term == thing for term in row):
                        return True
            except (SyntaxError, ValueError):
                continue
    return False
