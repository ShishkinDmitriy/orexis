"""Everything planning reports of how it is doing — its gauges and its events — and nowhere else.

Instrumentation, not model (`agent/metrics.py`): the admins' view of the search, which no plan
branches on. Adding a figure is editing this module, and the dashboards draw what it holds.

THE GAUGES ARE OVER THE IMAGINARIA, one per scope, and never over the belief base — a plan, a
possible world and a weighing are written there and nowhere else, and the imaginaria copy the
beliefs' readings, so the two may not be mixed. A figure is what the imaginaria HOLD at the flush,
not what a pass added: a kept cone is counted again, and a want reached takes its worlds with it.

THE EVENTS ARE CALLED FROM THE ACTS as they happen — the Planner per pass, per search and per
adoption, `reroot` per scope — having asked `agent.metrics.recording()`, so nothing is read for
them where no metrics sink is loaded. What an event must remember between passes — when a want was
first searched, in how many passes — is memory in the Planner, never a row.
"""

from __future__ import annotations

import time
from typing import Iterable

import pyoxigraph as ox

from agent.metrics import Event, Gauge, sample
from agent.ontology import local_of
from agent.store import Raw, catalogue_of, rows

#  THE PLANS the imaginaria hold, by why each search ended. `exhausted` is the one to watch: a
#  budget that keeps cutting searches short is a budget too small for the problem, and `noCandidate`
#  is a want nothing this agent holds points at.
PLANS = Gauge("plans", """
SELECT (SUM(IF(?outcome = planning:Satisfied, 1, 0)) AS ?satisfied)
       (SUM(IF(?outcome = planning:Exhausted, 1, 0)) AS ?exhausted)
       (SUM(IF(?outcome = planning:NoCandidate, 1, 0)) AS ?noCandidate)
WHERE { GRAPH ?plan { ?p a planning:Plan ; planning:outcome ?outcome } }""")

#  THE CONE: the possible worlds kept and the weighings of them, and of those how many are on a
#  frontier and how many met their want. What a search costs in memory, window after window.
#
#  Counted by OPTIONAL rows inside the catalogue and not by `EXISTS` in the aggregate: an EXISTS in
#  a projected expression is evaluated against the DEFAULT graph, which a gauge is handed empty,
#  and it answered no met weighing on a greenhouse imaginarium holding one — measured, 2026-09-27.
CONE = Gauge("cone", """
SELECT ?worlds ?weighings ?open ?met WHERE {
  { SELECT (COUNT(?w) AS ?worlds) WHERE { GRAPH $cat { ?w a planning:PossibleGraph } } }
  { SELECT (COUNT(?x) AS ?weighings) (COUNT(?o) AS ?open) (COUNT(?m) AS ?met) WHERE {
      GRAPH $cat { ?x a planning:Weighing .
                   OPTIONAL { ?x planning:open true BIND(?x AS ?o) }
                   OPTIONAL { ?x planning:met true BIND(?x AS ?m) } } } } }""")

#  A PASS OF THE PLANNER, in real seconds per part — laying the ground and finding the present in
#  it, weighing the desires, deriving and withdrawing the wants, searching, handing the plans down —
#  and how many wants it searched.
PLANNER = Event("planner", values=("ground_s", "weigh_s", "derive_s", "search_s", "publish_s", "wants"))

#  ONE WANT'S SEARCH IN ONE PASS, tagged by the desire, the scope and how it ended: its real
#  seconds, the budget it had and the candidates it weighed.
SEARCH = Event("search", values=("duration_s", "budget", "weighed"), tags=("desire", "scope", "outcome"))

#  A PLAN THE EXECUTOR ADOPTED: in how many passes its want was searched and what was weighed for it
#  in all, the real seconds since it was first searched, the estimate at the present ground against
#  what the plan spent — how honest the estimate is — and whether an intention pursued it before.
ADOPTED = Event("adopted", values=("passes", "weighed", "wall_s", "estimate", "cost"), flags=("replan",),
                tags=("desire", "scope"))

#  WHICH WORLD THE PRESENT WAS FOUND TO BE — first, ground, child or surprise — and what of the cone
#  was kept and dropped. A surprise is the one a pass names.
REROOT = Event("reroot", values=("kept", "dropped"), tags=("present",))


def gauges(imaginaria: Iterable[ox.Store]) -> list:
    """Planning's gauges, sampled over the imaginaria and summed across them."""
    return sample(__name__, imaginaria)


#  WHAT THE EVENTS READ, asked only where a metrics sink is loaded: the want's plan and how it ended,
#  the desire it was derived under, what its estimate said at the present ground, and — off the
#  intentions — which want an intention pursues and how many have pursued it.
_PLAN_OF_Q = """
SELECT ?outcome ?spent WHERE { GRAPH ?g { ?p a planning:Plan ; planning:for $want ; planning:outcome ?outcome .
  OPTIONAL { ?p planning:spent ?spent } } } LIMIT 1"""
_DESIRE_OF_Q = """SELECT ?d WHERE { GRAPH ?g { $want a planning:Want ; prov:wasDerivedFrom ?d } } LIMIT 1"""
_ESTIMATE_Q = """
SELECT ?remaining WHERE { GRAPH $cat { ?x planning:weighs $ground ; planning:for $want ; planning:remaining ?remaining } } LIMIT 1"""
_PURSUES_Q = """SELECT ?want WHERE { GRAPH ?g { $intention execution:pursues ?want } } LIMIT 1"""
_PURSUERS_Q = """SELECT (COUNT(DISTINCT ?i) AS ?n) WHERE { GRAPH ?g { ?i a execution:Intention ; execution:pursues $want } }"""


def desire_of(store: ox.Store, want: str) -> str | None:
    """The local name of the desire `want` was derived under in `store`, or None — for a want the
    world authored, or a step kept below."""
    found = rows(store, _DESIRE_OF_Q, (), want=want)
    return local_of(found[0]["d"]) if found else None


def pursued_by(intentions: ox.Store, intention: str) -> str | None:
    """The want `intention` pursues, off the intentions store, or None."""
    found = rows(intentions, _PURSUES_Q, (), intention=intention)
    return found[0]["want"] if found else None


def report_search(store: ox.Store, want: str, *, took: float, budget: int, weighed: int,
                  scope: str | None) -> None:
    """Say one want's search in one pass, as it ends: tagged by the desire, the scope and how it
    ended, read off the plan it wrote."""
    plan = next(iter(rows(store, _PLAN_OF_Q, (), want=want)), {})
    SEARCH({"duration_s": round(took, 6), "budget": budget, "weighed": weighed},
           desire=desire_of(store, want), scope=local_of(scope) if scope else None,
           outcome=local_of(plan["outcome"]) if plan.get("outcome") else None)


def report_adoption(store: ox.Store, intentions: ox.Store, want: str, *, first: float | None, passes: int,
                    weighed: int, present: str, scope: str) -> None:
    """Say a plan the executor adopted for `want` from `store`: in how many passes it was searched
    and what they weighed, the real seconds since `first` — its first search, on `perf_counter` —
    what the want's estimate said was left at the `present` ground against what the plan spent, and
    whether an intention pursued the want before, a replan."""
    plan = next(iter(rows(store, _PLAN_OF_Q, (), want=want)), {})
    root = next(iter(rows(store, _ESTIMATE_Q, (), want=want, ground=present,
                          cat=Raw(f"<{catalogue_of(store)}>"))), {})
    pursued = int(rows(intentions, _PURSUERS_Q, (), want=want)[0]["n"])
    fields = {"passes": passes, "weighed": weighed, "replan": pursued > 1}
    if first is not None:
        fields["wall_s"] = round(time.perf_counter() - first, 6)
    if plan.get("spent") is not None:
        fields["cost"] = float(plan["spent"])
    if root.get("remaining") is not None:
        fields["estimate"] = float(root["remaining"])
    ADOPTED(fields, desire=desire_of(store, want), scope=local_of(scope))
