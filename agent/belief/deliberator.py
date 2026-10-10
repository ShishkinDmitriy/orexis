"""The deliberator: the belief package's pass, sequenced the way the planner and the executor
sequence theirs.

**WHAT IT OWNS IS A QUEUE.** A writer that wrote a graph says so, `changed(source)`, and
nothing happens there; `deliberate()` is the pass, which takes every source in the queue in
turn, spending at most a budget of rule executions across them, and answers what it spent. A
source is an ARRIVAL, and an arrival is concluded on before it is transitioned on: it is revised
(`revise`) until its rules settle, so a transition reads the quantity the pipeline concluded and
not the raw count, and then the transitions it triggers are applied to the agent's own state
(`trigger`), once, in their orders. One done with both leaves the queue; one the budget cut short
stays, its revision graph's row saying `belief:settled false`, and the next pass continues it
from where it stood — a pass cut short is finished by the passes after, as a search cut short is.
Who calls the pass and when is the container's, as it is for the planner and the executor; there
is no thread here.

**ARRIVALS ARE TRANSITIONED ON IN TURN.** A later arrival may be revised while an earlier one is
cut short, since a revision reads its own source; but its transitions wait until every arrival
queued before it has had its own, so the readings one message carries change the state oldest
first, and a state one arrival made is never replaced by an earlier arrival's finished late.

**A CUT SURVIVES A RESTART.** At construction the deliberator re-queues every revision graph
whose row says its rules did not settle, read off the catalogue, so what a pass left
half-concluded is not left there because the process came back. Where an arrival's transitions
waited or were cut, its row says the same, and a restart revises it again — concluding nothing new
— and applies its transitions from the first order. That is exact for an arrival whose transitions
are one order, every one shipped; one cut between two orders and restarted would apply the first
again, which is the seam `knowledge/domain/belief/transition.md` names.

**DELIBERATION, IN THE B OF BDI**, is the process by which facts follow from facts; the search
that finds a plan is the planner's and is not this. The 0.1.0 tree's deliberator was the
search, and `knowledge/domain/belief/deliberator.md` says which is which.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime

import pyoxigraph as ox

from agent import clock
from agent.lifecycle import Signal
from agent.ontology import BELIEF, KNOWN
from agent.stance import stance
from agent.store import Raw, bind, catalogue_of, graphs_of, rows, update

from .events import Revised, RevisionsHeld
from .ontology import BUDGET_TERM, REVISION_GRAPH, SETTLED, revision_graph
from .revise import BUDGET as PER_SOURCE, revise
from .trigger import trigger

log = logging.getLogger("deliberator")

#  RULE EXECUTIONS one pass may spend, across every source it revises, where the agent's self graph
#  states no `belief:budget` (knowledge/domain/kernel/stance.md).
BUDGET = 256

#  EVERY SOURCE WHOSE RULES DID NOT SETTLE, off the revision graphs' rows.
_UNSETTLED_Q = """
SELECT ?source WHERE { GRAPH $cat { ?g $settled false ; prov:wasDerivedFrom ?source } } ORDER BY ?source"""


#  THE REVISIONS AND HOW MANY A BUDGET CUT SHORT, off the catalogue, where `revise` describes every
#  revision graph it writes. The words are spelled from `ontology.py`, since the store's dictionary
#  binds no label to this package's.
_HELD_Q = f"""
SELECT (COUNT(?g) AS ?revisions) (SUM(IF(?settled, 0, 1)) AS ?unsettled)
WHERE {{ GRAPH $cat {{ ?g a <{REVISION_GRAPH}> ; <{SETTLED}> ?settled }} }}"""

#  WHETHER A REVISION GRAPH'S ARRIVAL IS DONE, said again on its row where one stands: false while its
#  transitions wait or were cut, true once they have run.
_SETTLE_U = """
DELETE { GRAPH $cat { $graph $settled ?was } }
INSERT { GRAPH $cat { $graph $settled $flag } }
WHERE  { GRAPH $cat { $graph $settled ?was } }"""


@dataclass
class _Arrival:
    """A source queued: what stands beside it — kept as it was handed, so a revision the budget cuts
    short is continued beside what it was begun beside; None for the beliefs holding at the pass's
    instant, which is what one re-queued at a restart is revised beside — whether its revision has
    settled, how many of the orders of transitions it triggers are applied, and the kind its revisions
    are, as its writer handed it: a belief's are beliefs. One re-queued at a restart is continued, and
    a revision continued keeps the row it was first described with, so the kind is not needed again."""
    read: tuple | None = None
    revised: bool = False
    done: int = 0
    said: bool = False                  # whether its row was said unsettled for its transitions
    kind: str = BELIEF


class Deliberator:
    """The pass over what was written since the last one, within a budget."""

    def __init__(self, beliefs: ox.Store, agent_id: str, *, budget: int | None = None):
        """The beliefs and the one identifier a process is told. The budget is the agent's stance,
        read off its self graph, `BUDGET` where it states none — or the caller's, where one sizes it."""
        self.beliefs = beliefs
        self.id = agent_id
        self.budget = budget if budget is not None else stance(beliefs, BUDGET_TERM, BUDGET)
        #  SOURCE TO WHERE IT STANDS (`_Arrival`), in the order changes arrived.
        self.queue: dict[str, _Arrival] = {}
        for source in self._unsettled():
            self.queue[source] = _Arrival()
        #  WHAT IT SAYS HAPPENED (`events.py`): `revised`, what a pass revised or transitioned on, for
        #  whoever is interested in the present changing — the executor, whose steps the world answers
        #  there; and, made only where heard, `revisions_held`, what the catalogue describes after it.
        self.revised = Signal("revised")
        self.revisions_held = Signal("revisions_held")

    def changed(self, source: str, read=None, kind: str = BELIEF) -> None:
        """A graph was written: take it on the next pass — revised beside `read` where the writer
        says what stands, else beside the beliefs holding then, its revisions classified `kind`, and
        the transitions it triggers applied. Written again before it was done, it is a new arrival: it
        starts again, and takes its turn after everything that arrived before it, since the readings a
        message carries must change the state oldest first."""
        self.queue.pop(source, None)
        self.queue[source] = _Arrival(tuple(read) if read is not None else None, kind=kind)

    @property
    def pending(self) -> list[str]:
        """What the next pass will take, in order."""
        return list(self.queue)

    def deliberate(self, now: datetime | None = None) -> int:
        """Take every queued source in turn — revise it, then apply the transitions it triggers —
        spending at most the budget across them. What the pass spent. A source done with both
        leaves the queue; one cut short stays for the next pass, which continues it where it stood,
        and the transitions of every source queued after it wait for it."""
        at = now or clock.now()
        left = self.budget
        spent = 0
        started = time.perf_counter()
        revised = len(self.queue)
        done = []
        changed: list[str] = []         # the agent's own state graphs the transitions changed
        waiting = False                 # an arrival before this one is not done: its transitions go first
        for source in list(self.queue):
            if left <= 0:
                break
            arrival = self.queue[source]
            if not arrival.revised:
                read = arrival.read if arrival.read is not None else tuple(graphs_of(self.beliefs, *KNOWN, at=at, now=at))
                used = revise(self.beliefs, source, read=read, budget=min(left, PER_SOURCE), kind=arrival.kind)
                done.append(source)
                spent += used
                left -= used
                if source in self._unsettled():
                    #  CUT IN ITS REVISION: the arrivals after it wait for its transitions — where it
                    #  triggers any. One that triggers none changes no state, so nothing after it waits on
                    #  it: a prediction rewritten every pass and cut every pass would otherwise hold every
                    #  reading's transitions for ever.
                    arrival.read = read
                    waiting = waiting or not trigger(self.beliefs, source, budget=0, done=arrival.done).finished
                    continue
                arrival.revised = True
            #  WAITING, OR NOTHING LEFT, IS A BUDGET OF NOUGHT: an arrival triggering nothing is done all
            #  the same, and one triggering something stays for its turn.
            triggered = trigger(self.beliefs, source, budget=0 if waiting else max(left, 0), done=arrival.done)
            spent += triggered.spent
            left -= triggered.spent
            if triggered.spent and source not in done:
                done.append(source)
            changed += [g for g in triggered.changed if g not in changed]
            if not triggered.finished:
                arrival.done = triggered.done
                self._say(source, arrival, settled=False)
                waiting = True
                continue
            if arrival.said:
                self._say(source, arrival, settled=True)
            del self.queue[source]
        if spent:
            log.debug("%s: %d execution(s) over %d source(s), %d pending", self.id, spent,
                      len(self.queue), len(self.queue))
        #  WHAT THE PASS REVISED AND SPENT: the sources, the state graphs their transitions changed, how
        #  many it was handed, the rule executions, how many were left cut short for the next pass, and
        #  the real seconds.
        if revised:
            self.revised.emit(Revised(tuple(done), changed=tuple(changed), sources=revised, executions=spent,
                                      cut=len(self.queue), duration_s=round(time.perf_counter() - started, 6)))
            if self.revisions_held.connected:
                self.revisions_held.emit(self._held())
        return spent

    def _say(self, source: str, arrival: _Arrival, *, settled: bool) -> None:
        """Say on the source's revision row whether it is done, so a restart continues an arrival
        whose transitions waited or were cut — where a row stands; a source nothing was concluded of
        has none, and its transitions are this process's alone to finish."""
        if arrival.said != settled:
            return
        cat = catalogue_of(self.beliefs)
        if cat is not None:
            update(self.beliefs, bind(_SETTLE_U, cat=Raw(f"<{cat}>"), graph=revision_graph(source),
                                      settled=SETTLED, flag=Raw("true" if settled else "false")))
        arrival.said = not settled

    def _held(self) -> RevisionsHeld:
        """The revisions the catalogue describes now, and how many are unsettled."""
        cat = catalogue_of(self.beliefs)
        found = next(iter(rows(self.beliefs, _HELD_Q, (), cat=Raw(f"<{cat}>")))) if cat else {}
        return RevisionsHeld(revisions=int(found.get("revisions") or 0), unsettled=int(found.get("unsettled") or 0))

    def _unsettled(self) -> list[str]:
        cat = catalogue_of(self.beliefs)
        if cat is None:
            return []
        return [r["source"] for r in rows(self.beliefs, _UNSETTLED_Q, (), cat=Raw(f"<{cat}>"), settled=SETTLED)]
