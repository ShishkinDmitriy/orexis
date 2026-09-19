"""`judge_desires`: every desire judged at the present and at every foreseen instant, the
judgments written to the store — the first of the road's two functions
(judge-desires-then-derive-wants), and the readers of a desire's met-test beside it: the
compiled select whose rows are its violations, and the witnesses a desire has at the present or
at the first instant it fails.

After the call, the store says what each desire read; nothing comes back and nothing is kept in
hand. `derive_wants` reads the judgment graph. `pursuit` calls the two in turn when a pass
stands on a root or a want, and the ledger when a claim arrives.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from orexis_agent_progression import clock
from orexis_agent_progression.ontology import OREXIS
from orexis_agent_progression.store import bindings

from .judgments import save_judgments

log = logging.getLogger("judge_desires")


def judge_desires(agent) -> None:
    """Judge every desire at the present and at every foreseen instant, and write the
    judgments to the store — the first of the road's two functions (judge-desires-then-
    derive-wants). After it, the store says what each desire's met-test read: met or unmet,
    and where unmet the results, one `deliberation:Judgment` per desire per instant in the
    agent's judgment graph, replaced whole. Nothing of this run is kept anywhere else — no
    object comes back — so `derive_wants` reads the store and nothing in hand.

    ONE SELECT PER DESIRE PER INSTANT, and not one union of them: the compiler measured a
    single UNION of every shape at thirteen times the cost of the selects asked one by one,
    so this iterates where the contract is the whole. The present is the door's `now`; the
    foreseen instants are every prediction's start, where the door hands the prediction
    holding then beside the present (#643). A desire whose met-test the compiler refuses is
    judged by the choir — the container's judgment of its present, where one is in hand —
    and carries no result: it derives its one want about everything it is about, as every
    want was before the road.
    """
    roots = sorted({d.uri for d in agent.desires.find_all()})
    now = clock.now()
    starts = sorted({start for _g, start, _end in agent.beliefs.prediction_windows() if start is not None})
    judged: list[tuple[str, datetime | None, bool, list[dict]]] = []
    for root in roots:
        select = unmet_select_of(agent, root)
        if select is None:
            pursuing = getattr(agent, "pursuing", None)
            row = next((d for d in pursuing() if d.uri == root), None) if pursuing is not None else None
            if row is not None:
                judged.append((root, None, row.is_met, []))
            continue
        for at in [None, *starts]:
            try:
                answer = agent.beliefs.query_at(select, at=at or now)
            except Exception as exc:                                    # noqa: BLE001
                log.error("%s: could not be judged at %s: %s", root.rsplit("#", 1)[-1], at or "now", exc)
                continue
            #  The engine's bindings as they are, one per distinct row — two predictions
            #  holding at one instant give one node two offending values, and both are told.
            rows = {tuple(sorted((k, v["value"]) for k, v in r.items())): r
                    for r in answer.get("results", {}).get("bindings", [])}
            judged.append((root, at, not rows, [rows[k] for k in sorted(rows)]))
    save_judgments(agent.beliefs, agent.id, agent.me.uri, judged)


def unmet_select_of(agent, root: str) -> str | None:
    """The root's own met-test, compiled to the select whose rows are its VIOLATIONS — `?this`,
    which constraint, and `?_about` where the constraint's block says what it is about — from
    public knowledge and the graphs the agent owns, ASKED by their classification and never
    named (a root's shape lives in the roots graph since #644, and the roots graph is
    `orexis:DesireGraph` in the classification boot writes). Cached per root on the agent: a
    root never changes while the agent runs. None where the root states no shape or the
    compiler refuses.

    THE REPORT AND NOT THE FOCUS NODES (one-road-derives-every-want): a desire universal over
    several properties fails per property, and the rows are what say which. The planner
    compiles the same shape the same way for the law it holds candidates to."""
    from rdflib import URIRef

    from orexis_agent_progression.violation import Unsupported, report_select

    from .conformance import graph_from

    cache = agent.__dict__.setdefault("_root_selects", {})
    if root in cache:
        return cache[root]
    rows = bindings(agent.desires.query_union(f"SELECT ?s WHERE {{ <{root}> orexis:metWhen ?s }} LIMIT 1"))
    select = None
    if rows:
        shape = rows[0]["s"]
        try:
            #  FROM THE GRAPHS THAT HOLD DESIRES AND WANTS, asked by class — a root's shape and
            #  its blank-node closure live in a desire graph whole, a derived want's own in its
            #  want graph (the container reads a want's crossing off that one), and the whole
            #  belief base parsed into rdflib cost half a second per shape for a closure of
            #  forty triples (#711).
            shapes = graph_from(agent.beliefs, *agent.beliefs.graphs_of(OREXIS + "DesireGraph", OREXIS + "WantGraph"))
            select = report_select(shapes.cbd(URIRef(shape)), URIRef(shape))
        except Unsupported as exc:
            log.warning("%s: its met-test cannot be compiled, so no crossing is read for it: %s",
                        root.rsplit("#", 1)[-1], exc)
    cache[root] = select
    return select


@dataclass(frozen=True)
class Witness:
    """One way a desire is failing, and when it first does: the focus node that failed, the
    constraint it failed, what that constraint is about where its block says, and the instant.
    A universal is refuted by a witness, and the want minted under it is the universal
    instantiated at that witness (one-road-derives-every-want)."""

    instance: str
    constraint: str
    about: str | None
    at: datetime


def witnesses_of(agent, root: str, *, now: bool = False) -> list[Witness]:
    """Every (instance, constraint) under which `root` reads unmet, each at the FIRST instant it
    does — the start of the earliest prediction where it fails; or, with `now`, at the PRESENT
    alone, which is a different question: what is in trouble already, not what will be.

    The root's own met-test asked through the door at each prediction's start, where the door
    hands the prediction holding then beside the present (#643). A prediction typed with the
    region band and the one below reads unmet, so the safe direction (#633) falls out of the
    bands, and no kernel line knows a rate. One select per desire is the whole of the
    decomposition: its rows ARE the instances in trouble, and `?_about` says which property
    where the desire's shape states it per block.
    """
    select = unmet_select_of(agent, root)
    if select is None:
        return []
    instants = [clock.now()] if now else [
        start for _graph, start, _end in agent.beliefs.prediction_windows() if start is not None]
    seen: dict[tuple[str, str], Witness] = {}
    for at in instants:
        try:
            rows = bindings(agent.beliefs.query_at(select, at=at))
        except Exception as exc:                                    # noqa: BLE001
            log.error("%s: the crossing could not be read at %s: %s", root.rsplit("#", 1)[-1], at, exc)
            return []
        for r in rows:
            key = (r["this"], r.get("_constraint", ""))
            if key not in seen:
                seen[key] = Witness(instance=r["this"], constraint=r.get("_constraint", ""),
                                    about=r.get("_about"), at=at)
    return sorted(seen.values(), key=lambda w: (w.at, w.instance, w.constraint))
