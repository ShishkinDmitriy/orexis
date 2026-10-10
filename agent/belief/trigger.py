"""`trigger`: an arrival of testimony triggers every transition once, applied to the agent's own
state, order by order, within a budget (knowledge/domain/belief/transition.md,
a-transition-changes-the-state-and-an-inference-only-concludes).

**WHAT TRIGGERS, AND WHAT IS TRIGGERED.** An arrival of TESTIMONY — a graph whose catalogue row says
it arrived `orexis:Received`, an instrument's reading or a peer's word heard — triggers every
`belief:Transition` of a rules graph that is not `sh:deactivated`. A transition declares no trigger.
Nothing that arrived another way triggers one: the agent's own — a prediction or a committed step,
which it records, the very state a transition writes, which it derives — and what the sovereign
asserted trigger none, so a transition's output can never trigger it again.

**WHAT IT READS, AND SO WHAT IT IS ABOUT**: the arrival with its revisions — which have settled by the
time this is called, so a transition reads the quantity the pipeline concluded and not the raw count —
the public graphs, and the agent's own DERIVED state graphs, whatever their period: the state a
transition replaces is a premise of the one it writes, and a state ended by a silence is still the
state the next arrival is judged beside. Never another testimony: an observation received, a forecast,
a peer's word is not read beside an arrival it is not. So a WHERE asking for an observation of a
property can match only the arrival, and on any other arrival it matches nothing and changes nothing:
the rule's WHERE says what it is about.

**WHERE IT WRITES.** What an order inserts goes into a state graph of the arrival's own — the kernel's
`orexis:StateGraph`, the arrival's owner's and derived, holding over the arrival's period — so a state
lasts as long as what it was made of, and a silence ends it as it ends the arrival. What an order
deletes is taken out of whichever of the agent's own derived state graphs holds it, and one left empty
is forgotten, row and all. Testimony is never a target: a graph received or heard, a public graph, an
ontology, a revision — nothing that is not a state the agent derived — is never deleted from. The
target says no `prov:wasDerivedFrom`: a revision is derived from its source and goes with it, and this
outlives the arrival it was made of until a later transition takes its rows out.

**ONCE, IN ORDER, WITHIN A BUDGET.** The orders run ascending through the one machine
(`transition.py`): every rule of one order reads the same state, its deletions are applied before its
additions, and a later order reads what the earlier made. An order is applied whole or not at all and
costs one rule execution a rule, revision's unit; one is begun while any of `budget` is left, as
`revise` begins a group, and where the budget is spent before the last the answer says how many orders
are done, for the caller to continue from — never one applied twice for one arrival.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import pyoxigraph as ox

from agent.ontology import OREXIS, PUBLIC, STATE
from agent.store import Raw, bind, catalogue_of, entry, forget_graph, graphs_of, revisions_of, rows, update

from .ontology import REVISION_GRAPH, state_graph
from .revise import BUDGET
from .transition import applied, asked, transitions

log = logging.getLogger("trigger")

#  WHETHER THE ARRIVAL IS TESTIMONY, WHOSE IT IS AND WHEN IT HOLDS, off its row: the state graph it is
#  given has the same owner and period.
_ARRIVAL_Q = """
SELECT ?owner ?start ?end WHERE {
  GRAPH $cat { $arrival orexis:arrivedBy orexis:Received .
               OPTIONAL { $arrival orexis:beliefsOf ?owner }
               OPTIONAL { $arrival dcterms:temporal ?p .
                          OPTIONAL { ?p orexis:start ?start } OPTIONAL { ?p orexis:end ?end } } } }
LIMIT 1"""

#  EVERY STATE GRAPH THE AGENT DERIVED, of any period: its own state, which a transition reads and
#  deletes from.
_DERIVED_Q = """
SELECT ?g WHERE { GRAPH $cat { ?g a orexis:StateGraph ; orexis:arrivedBy orexis:Derived } } ORDER BY ?g"""

#  A ROW, AND ITS PERIOD, TAKEN BACK — for an arrival's state graph said again of a later arrival.
_UNDESCRIBE_U = """
DELETE { GRAPH $cat { $graph ?p ?o . ?period ?pp ?po } }
WHERE  { GRAPH $cat { $graph ?p ?o . OPTIONAL { $graph dcterms:temporal ?period . ?period ?pp ?po } } }"""


@dataclass(frozen=True)
class Triggered:
    """What applying the transitions an arrival triggers did: the rule executions it spent, how many of
    its orders are applied — those before this call included — whether that is all of them, and the
    agent's own state graphs this call changed, written into or deleted from, an emptied one too."""
    spent: int = 0
    done: int = 0
    finished: bool = True
    changed: tuple = ()


def trigger(store, arrival: str, *, budget: int = BUDGET, done: int = 0) -> Triggered:
    """Apply the transitions `arrival` triggers to the agent's own state, from its `done`th order on,
    spending at most `budget` rule executions — an order begun while any is left, and applied whole.
    An arrival that is no testimony triggers nothing, spends nothing, and is done."""
    cat = catalogue_of(store)
    if cat is None:
        return Triggered(0, done, True)
    row = next(iter(rows(store, _ARRIVAL_Q, (), cat=Raw(f"<{cat}>"), arrival=arrival)), None)
    if row is None:
        return Triggered(0, done, True)
    orders = transitions(store)
    if done >= len(orders):
        return Triggered(0, done, True)
    into = state_graph(arrival)
    spent = 0
    changed: list[str] = []
    for n in range(done, len(orders)):
        if spent >= budget:
            log.debug("the transitions %s triggers are cut short after %d of %d order(s)", arrival, n, len(orders))
            return Triggered(spent, n, False, tuple(changed))
        state = _derived(store, cat)
        #  WHAT WAS CONCLUDED OF THE ARRIVAL, whatever kind its runner revised it into: every revision is
        #  this package's `belief:RevisionGraph`, so this asks that and learns no other package's word.
        reads = list(dict.fromkeys([arrival, *revisions_of(store, arrival, kind=REVISION_GRAPH),
                                    *graphs_of(store, PUBLIC), *state]))
        change = asked(store, orders[n], reads)
        spent += change.executions
        changed += [g for g in _deleted_from(store, change, state) if g not in changed]
        emptied = applied(store, change, into, state)
        for graph in emptied:
            if graph != into or not change.added:
                forget_graph(store, graph)
        if change.added:
            _describe(store, cat, into, row)
            if into not in changed:
                changed.append(into)
        if change.added or change.deleted:
            log.debug("%s triggered order %d: %d deleted, %d added", arrival, n, len(change.deleted), len(change.added))
    return Triggered(spent, len(orders), True, tuple(changed))


def _deleted_from(store, change, targets) -> list[str]:
    """The graphs of `targets` holding something `change` deletes — what applying it will change there."""
    return [g for g in targets if any(
        ox.Quad(t.subject, t.predicate, t.object, ox.NamedNode(g)) in store for t in change.deleted)]


def _derived(store, cat: str) -> list[str]:
    """Every state graph `store` holds that the agent derived, whatever its period."""
    return [r["g"] for r in rows(store, _DERIVED_Q, (), cat=Raw(f"<{cat}>"))]


def _describe(store, cat: str, into: str, row: dict) -> None:
    """The arrival's state graph's row, said of the arrival it now holds the state of: a state graph,
    the arrival's owner's, derived, over the arrival's period — and any row it had of an earlier arrival
    taken back first, since a graph's stretch is its row's and the rows it holds are this arrival's now."""
    update(store, bind(_UNDESCRIBE_U, cat=Raw(f"<{cat}>"), graph=into))
    update(store, f"INSERT DATA {{ {entry(store, into, STATE, OREXIS + 'Derived', row.get('owner'), row.get('start'), row.get('end'))} }}")
