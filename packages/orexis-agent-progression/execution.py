"""Execution, the doing half: hand a committed act to whoever takes it, on the loop. One road.

**This is what happens to a decision once it is made, and it is progression's.** It used to be
one file with the deciding half — `pursue` planned, committed the head and took it, and every
trigger arrived there. The split along the layers put the two halves where they belong: the
plan and the commit are the search's (`orexis_agent_deliberation.pursuit`, which calls down
into here), and what is left is the road from a committed act to its actor, which searches
nothing and may run for a committed act that nobody re-decided.

**Every act is taken on the reactive loop.** `carry_out` runs inline when the caller is
already the loop — a timer's tick, a deadline — and otherwise enqueues the take and waits for
its result on the caller's own thread, which is a transport's callback or the mind's revision
thread and never the loop. That is the one wait in this layer, and it is never the loop's.

**Nothing here names a package.** The link from a row to its code is `orexis:takenBy`, stated on
the action node beside the precondition and the effect — a fact a sovereign can query. See
knowledge/domain/executor.md, knowledge/domain/actor.md and
knowledge/decisions/an-intention-is-a-plan-committed-to.md.
"""

from __future__ import annotations

import logging

from dataclasses import replace

from orexis_agent_reactive.loop import loop

from .ontology import OREXIS, STEP_DONE
from .store import bindings

from .act import Act

log = logging.getLogger("execution")

#  Asked by NAME of the whole default graph — the T-Box is public, and which capability takes
#  a means is a fact about the vocabulary rather than about any world.
_TAKEN_BY_Q = f"SELECT ?action ?family WHERE {{ ?action <{OREXIS}takenBy> ?family }} LIMIT 1"


def taken_by(query, action: str) -> str | None:
    """The capability family that carries this means out, or None where no package says."""
    rows = bindings(query(_TAKEN_BY_Q, {"action": action}))
    return rows[0]["family"] if rows else None


def take_standing(agent, standing, desire) -> bool:
    """Carry out a step that already stands — the trigger changed, the decision did not.

    An offer arriving while an Acquire stands, a reading arriving while an Actuate does: the
    commitment was made on the tick and the actor could not act then. Nothing is re-decided;
    the standing row is rebuilt from the ledger and handed over.
    """
    #  The act is the ledger's, read whole — action, lever, quantity, window — plus what the
    #  want is ABOUT (`orexis:about`, read back off the want), which is the want's and not the act's.
    rows = bindings(agent.desires.query_union(
        f"SELECT ?about WHERE {{ <{standing.want}> <{OREXIS}about> ?about }}"))
    act = replace(standing.act, about=rows[0]["about"] if rows else None)
    return carry_out(agent, act, desire, standing.uri)


def carry_out(agent, act: Act, desire, intention: str) -> bool:
    """Hand one committed act to whoever the T-Box says takes its action. True if anyone did.

    On the loop. A caller that IS the loop takes it now; any other caller enqueues it and
    waits — the actors then run one at a time on the executing thread, whichever clock or
    message woke them, which is what makes a take atomic without an actor holding a lock.
    """
    on = loop()
    if on.is_current():
        return _take(agent, act, desire, intention)
    return on.submit(_take, agent, act, desire, intention).result()


def _take(agent, act: Act, desire, intention: str) -> bool:
    family = taken_by(agent.beliefs.query, act.action)
    if family is None:
        #  A row was shipped and no taker was stated. `tests/test_execution.py` refuses this
        #  for every means that has a row in a shipped world; reaching it at runtime is a
        #  package onboarded past that gate, and the honest thing is to say so loudly.
        log.error("nothing takes %s — its package states no orexis:takenBy, so this intention "
                  "stands with nobody to carry it out", act.action.rsplit("#", 1)[-1])
        return False
    took = False
    for actor in agent.providers(family):
        took = bool(actor.take(act, desire, intention)) or took
    if not took:
        log.info("%s through %s: no actor could take it now — standing",
                 act.action.rsplit("#", 1)[-1], (act.via or "?").rsplit("#", 1)[-1])
    #  SAID UPWARD. Deliberation may want to know a step was taken, and progression may not
    #  import it — so this is an event through the choir, on the executing thread, and
    #  whoever above fills `orexis:stepDone` hears it (#452).
    agent.tell(STEP_DONE, act, intention, took)
    return took
