"""The deliberator: the belief package's pass, sequenced the way the planner and the executor
sequence theirs.

**WHAT IT OWNS IS A QUEUE.** A writer that wrote a graph says so, `changed(source)`, and
nothing happens there; `deliberate()` is the pass, which revises every source in the queue in
turn, spending at most a budget of rule executions across them, and answers what it spent. A
source whose rules settled leaves the queue; one the budget cut short stays, its revision
graph's row saying `belief:settled false`, and the next pass continues it from what is held —
a pass cut short is finished by the passes after, as a search cut short is. Who calls the pass
and when is the container's, as it is for the planner and the executor; there is no thread
here.

**A CUT SURVIVES A RESTART.** At construction the deliberator re-queues every revision graph
whose row says its rules did not settle, read off the catalogue, so what a pass left
half-concluded is not left there because the process came back.

**DELIBERATION, IN THE B OF BDI**, is the process by which facts follow from facts; the search
that finds a plan is the planner's and is not this. The 0.1.0 tree's deliberator was the
search, and `knowledge/domain/belief/deliberator.md` says which is which.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime

import pyoxigraph as ox

from agent import clock
from agent.lifecycle import Signal
from agent.ontology import KNOWN
from agent.stance import stance
from agent.store import Raw, catalogue_of, graphs_of, rows

from .events import Revised, RevisionsHeld
from .ontology import BUDGET_TERM, REVISION_GRAPH, SETTLED
from .revise import BUDGET as PER_SOURCE, revise

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


class Deliberator:
    """The pass over what was written since the last one, within a budget."""

    def __init__(self, beliefs: ox.Store, agent_id: str, *, budget: int | None = None):
        """The beliefs and the one identifier a process is told. The budget is the agent's stance,
        read off its self graph, `BUDGET` where it states none — or the caller's, where one sizes it."""
        self.beliefs = beliefs
        self.id = agent_id
        self.budget = budget if budget is not None else stance(beliefs, BUDGET_TERM, BUDGET)
        #  SOURCE TO WHAT STANDS BESIDE IT, in the order changes arrived; None means the
        #  beliefs holding at the pass's instant, which is what a reading is revised beside.
        self.queue: dict[str, tuple | None] = {}
        for source in self._unsettled():
            self.queue[source] = None
        #  WHAT IT SAYS HAPPENED (`events.py`): `revised`, what a pass revised, for whoever is
        #  interested in the present changing — the executor, whose steps the world answers there;
        #  and, made only where heard, `revisions_held`, what the catalogue describes after it.
        self.revised = Signal("revised")
        self.revisions_held = Signal("revisions_held")

    def changed(self, source: str, read=None) -> None:
        """A graph was written: revise it on the next pass, beside `read` where the writer
        says what stands, else beside the beliefs holding then."""
        self.queue[source] = tuple(read) if read is not None else None

    @property
    def pending(self) -> list[str]:
        """What the next pass will revise, in order."""
        return list(self.queue)

    def deliberate(self, now: datetime | None = None) -> int:
        """Revise every queued source in turn, spending at most the budget across them. What
        the pass spent. A source that settled leaves the queue; one cut short stays for the
        next pass, which continues it from what is held."""
        at = now or clock.now()
        left = self.budget
        spent = 0
        started = time.perf_counter()
        revised = len(self.queue)
        done = []
        for source in list(self.queue):
            if left <= 0:
                break
            read = self.queue[source]
            if read is None:
                read = tuple(graphs_of(self.beliefs, *KNOWN, at=at, now=at))
            used = revise(self.beliefs, source, read=read, budget=min(left, PER_SOURCE))
            done.append(source)
            spent += used
            left -= used
            if source in self._unsettled():
                self.queue[source] = read
                continue
            del self.queue[source]
        if spent:
            log.debug("%s: %d execution(s) over %d source(s), %d pending", self.id, spent,
                      len(self.queue), len(self.queue))
        #  WHAT THE PASS REVISED AND SPENT: the sources, how many it was handed, the rule executions,
        #  how many were left cut short for the next pass, and the real seconds.
        if revised:
            self.revised.emit(Revised(tuple(done), sources=revised, executions=spent, cut=len(self.queue),
                                      duration_s=round(time.perf_counter() - started, 6)))
            if self.revisions_held.connected:
                self.revisions_held.emit(self._held())
        return spent

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
