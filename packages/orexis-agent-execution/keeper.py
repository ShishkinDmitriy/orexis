"""The keeper: the ledger of what this agent is committed to.

**The kernel's, and granted by nothing.** Commitment is not plug-in-able — every agent keeps a
ledger, and the store that holds one was always built for every agent regardless. This writes
it, and it is the only thing that does.

**Nothing here decides.** Whoever found a plan decided; this keeps the record honest. What it
owns is the COMMITMENT itself: that a plan standing for a want is not committed to twice
within the agent's patience, which is the amortisation — inside your patience, a second
impulse to do the same thing is absorbed rather than re-decided
(an-intention-is-an-amortised-deliberation).

**It existed before it had a name, as module state.** A bid awaiting its claim was an
intention to acquire, living in a Python attribute that died with the process and answered to
nothing. They are rows in a graph now, with an adoption time, a resolution and a reason — so
an operator can ask what an agent thought it was doing.

**WHAT THE PREDECESSOR'S KEEPER HAD AND THIS DOES NOT** — it was 1,736 lines and this is a
tenth of that, and every absence is a thing that will come back attached to whatever needs it
(an-agent-is-four-things):

- **the expectation watch** — a baseline, a predicted value, an observed one, a verdict and a
  deadline per step, plus the suspicion count that decided a counterparty was unreliable. The
  whole of it reads a world this agent is not yet observing.
- **held conditions** — `until` and `untilNot`, a step waiting on a shape that compiles to a
  select re-asked on every write. The store emitted an `on_write` event for exactly this and
  emits none now.
- **methods and bridges** — expanding an abstract action into the steps its package says it
  comes to, and translating a taker-less step's promise into the level beneath.
- **refusals** — remembering that a level below could not keep a promise, so the same move is
  passed over while the refusal is younger than the patience.

What is here is what a ledger is: adopt, what stands, resolve, and the patience that makes
adopting mean something.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

import pyoxigraph as ox

from . import clock
from .ontology import EXECUTION, PATIENCE_S, intentions_graph, picks_graph
from .plans import ADOPTED_AT, BY, INTENTION, OUTCOME, PURSUES, RESOLVED_AT, copy_plan
from .store import Raw, bind, rows, update

log = logging.getLogger("keeper")

#  HOW LONG A COMMITMENT IS GIVEN where the agent states none. A figure and not a policy: an
#  agent whose world gives it room says its own, and this is what a bare store falls back to
#  so that the absence of a belief is not the absence of a patience.
DEFAULT_PATIENCE_S = 60.0

_STANDING_Q = """
SELECT ?intention ?want ?at ?adopted WHERE {
  GRAPH $ledger {
    ?intention a execution:Intention ;
               execution:pursues ?want ;
               execution:adoptedAt ?adopted .
    OPTIONAL { ?intention execution:by ?at }
    FILTER NOT EXISTS { ?intention execution:resolvedAt ?done } } }
ORDER BY ?adopted"""

#  THE PICK ITSELF, out of the graph the agent's picks live in — named, because a writer
#  reading back what it wrote names its graph and this is the one read that does.
_PATIENCE_Q = """
SELECT ?s WHERE { GRAPH $picks { $me <$patience> ?s } }"""


class Standing:
    """One commitment that has not been resolved: what it pursues, where it has got to, and
    when it was adopted."""

    __slots__ = ("uri", "want", "at", "adopted")

    def __init__(self, uri: str, want: str, at: str | None, adopted: datetime):
        self.uri, self.want, self.at, self.adopted = uri, want, at, adopted

    def age_s(self, now: datetime | None = None) -> float:
        """How long this has been standing, in the agent's seconds."""
        return ((now or clock.now()) - self.adopted).total_seconds()

    def __repr__(self) -> str:
        return f"Standing({self.uri.rsplit('#', 1)[-1]} for {self.want.rsplit('#', 1)[-1]})"


class Keeper:
    """One agent's ledger, over the intentions store.

    Handed the two engines and the one identifier a process is told. It holds no beliefs of
    its own: the patience is a PICK, read off the beliefs store where the agent's picks are,
    because how stubborn to be is the agent's own belief and not the ledger's constant.
    """

    def __init__(self, intentions: ox.Store, beliefs: ox.Store, agent_id: str,
                 holder: str | None = None):
        self.intentions = intentions
        self.beliefs = beliefs
        self.id = agent_id
        self.holder = holder
        self.graph = intentions_graph(agent_id)

    # --- committing ---------------------------------------------------------------------------

    def commit(self, source: ox.Store, graph: str, want: str) -> str | None:
        """Copy a found plan into the ledger — unless one for this want is already standing
        and younger than the patience, which is the absorption this class exists for.

        None means nothing was committed, and the two reasons are told apart in the log: an
        empty plan (nothing to do) and an absorbed one (already doing it).
        """
        if (held := self.standing_for(want)) is not None:
            age = held.age_s()
            if age < self.patience_s:
                log.debug("%s: absorbed a second plan for %s — %s stands, %.0fs of %.0fs",
                          self.id, want.rsplit("#", 1)[-1], held, age, self.patience_s)
                return None
            #  PAST THE PATIENCE, a new adoption SUPERSEDES the old, and the old is recorded
            #  as dropped with the reason. A commitment abandoned without a reason is
            #  indistinguishable from one forgotten.
            self.resolve(held.uri, "superseded")
        return copy_plan(source, graph, self.intentions, self.id, want)

    # --- what stands --------------------------------------------------------------------------

    def standing(self) -> list[Standing]:
        """Every commitment adopted and not resolved, oldest first."""
        return [Standing(r["intention"], r["want"], r.get("at"),
                         datetime.fromisoformat(r["adopted"]))
                for r in rows(self.intentions, bind(_STANDING_Q, ledger=Raw(f"<{self.graph}>")))]

    def standing_for(self, want: str) -> Standing | None:
        """The commitment standing for this want, or None. One or none: a second plan for one
        want while the first stands is the thing `commit` absorbs."""
        return next((s for s in self.standing() if s.want == want), None)

    # --- resolving ----------------------------------------------------------------------------

    def resolve(self, intention: str, outcome: str) -> None:
        """Say this commitment has ended, and how.

        THE LIFECYCLE IS TWO TIMESTAMPS AND AN OUTCOME, not a state machine: standing is an
        adoption with no resolution, and how it ended is a word. A resolved intention STAYS —
        every one does, with its outcome — because a ledger that forgot its resolutions could
        not answer the only question an operator brings to it, which is what this agent
        thought it was doing and why it stopped.
        """
        update(self.intentions, f"""
INSERT DATA {{ GRAPH <{self.graph}> {{
  <{intention}> <{RESOLVED_AT}> "{clock.now().isoformat()}"^^xsd:dateTime ;
                <{OUTCOME}> "{outcome}" . }} }}""")
        log.info("%s: %s — %s", self.id, intention.rsplit("#", 1)[-1], outcome)

    # --- the one figure -----------------------------------------------------------------------

    @property
    def patience_s(self) -> float:
        """How long a standing commitment blocks re-adoption of one for the same want.

        An OPINION, so it is the agent's own belief and a review may move it inside whatever
        room its world leaves. Read fresh rather than cached: a review that moved it between
        two passes moved it, and a keeper holding the old number would be the wrapper problem
        this layer exists without.
        """
        if self.holder is None:
            return DEFAULT_PATIENCE_S
        found = rows(self.beliefs, bind(_PATIENCE_Q, picks=Raw(f"<{picks_graph(self.id)}>"),
                                        me=Raw(f"<{self.holder}>"),
                                        patience=Raw(PATIENCE_S)))
        try:
            return float(found[0]["s"])
        except (IndexError, KeyError, TypeError, ValueError):
            return DEFAULT_PATIENCE_S

    def __len__(self) -> int:
        return len(self.standing())
