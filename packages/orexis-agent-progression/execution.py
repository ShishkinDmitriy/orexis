"""Execution, the doing half: hand a committed act to whoever takes it, on the loop. One path.

**This is what happens to a decision once it is made, and it is progression's.** It used to be
one file with the deciding half — `pursue` planned, committed the head and took it, and every
trigger arrived there. The split along the layers put the two halves where they belong: the
plan and the commit are the search's (`orexis_agent_deliberation.pursuit`, which calls down
into here), and what is left is the path from a committed act to its actor, which searches
nothing and may run for a committed act that nobody re-decided.

**Every act is taken on the reactive loop.** `carry_out` runs inline when the caller is
already the loop — a timer's tick, a deadline — and otherwise enqueues the take and waits for
its result on the caller's own thread, which is a transport's callback or the mind's revision
thread and never the loop. That is the one wait in this layer, and it is never the loop's.

**Nothing here names a package.** The link from a step to its code is the action itself: every
action is an extension point, and the module that carries it out is `@contributes(<action>)`
(#523) — the choir is asked by the action and whoever contributes it answers. See
knowledge/domain/executor.md, knowledge/domain/actor.md and
knowledge/decisions/an-intention-is-a-plan-committed-to.md.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from dataclasses import replace

from orexis_agent_reactive.loop import loop

from .ontology import OREXIS, STEP_DONE
from .store import bindings

from .act import Step

log = logging.getLogger("execution")

#  Asked by NAME of the whole default graph — the T-Box is public, and which capability takes
#  a means is a fact about the vocabulary rather than about any world.
def take_standing(agent, standing, judgment) -> bool:
    """Carry out a step that already stands — the trigger changed, the decision did not.

    An offer arriving while an Acquire stands, a reading arriving while an Actuate does: the
    commitment was made on the tick and the actor could not act then. Nothing is re-decided;
    the standing row is rebuilt from the ledger and handed over.
    """
    #  The act is the ledger's, read whole — action, lever, quantity, window — plus what the
    #  want is ABOUT (`orexis:about`, read back off the want), which is the want's and not the act's.
    rows = bindings(agent.desires.query(
        f"SELECT ?about WHERE {{ <{standing.want}> orexis:about ?about }}"))
    act = replace(standing.step, about=rows[0]["about"] if rows else None)
    return carry_out(agent, act, judgment, standing.uri)


def carry_out(agent, act: Step, judgment, intention: str) -> bool:
    """Hand one committed act to whoever the T-Box says takes its action. True if anyone did.

    On the loop. A caller that IS the loop takes it now; any other caller enqueues it and
    waits — the actors then run one at a time on the executing thread, whichever clock or
    message woke them, which is what makes a take atomic without an actor holding a lock.
    """
    on = loop()
    if on.is_current():
        return _take(agent, act, judgment, intention)
    return on.submit(_take, agent, act, judgment, intention).result()


def _take(agent, act: Step, judgment, intention: str) -> bool:
    #  BY THE ACTION'S OWN POINT (#523): every action is an extension point, and the module
    #  that carries it out contributes the method — asking the choir by the action reaches
    #  exactly its takers, every member of a family of two, and nobody else. An action nobody
    #  declared, or one no module of mine contributes, stands with nobody to carry it out —
    #  said loudly, since onboarding and boot refuse the ordinary cases before this is reached.
    from assembly import loader
    if act.action not in loader.extensions() or not any(m.answer(act.action) for m in agent.modules):
        #  A PROMISE THE LEVEL BENEATH KEEPS (#523): an action nobody takes, with a bridge
        #  declared for it, is planned below — its predicted fact becomes a want the taken
        #  actions can bring about, and the step waits on that fact.
        keeper = getattr(agent, "keeper", None)
        if keeper is not None and keeper.promise(intention):
            return False
        log.error("nothing takes %s — no module of mine contributes it and no bridge refines it, "
                  "so this intention stands with nobody to carry it out", act.action.rsplit("#", 1)[-1])
        return False
    #  READINESS IS THE KEEPER'S (#523): a step whose action says what it waits for is held
    #  rather than handed out, and comes back here when the wait is over.
    keeper = getattr(agent, "keeper", None)
    if keeper is not None and not keeper.ready(intention):
        return False
    took = any(bool(answer) for answer in agent.ask(act.action, act, judgment, intention))
    if took and keeper is not None:
        keeper.after_take(intention)
    if not took:
        log.info("%s through %s: no actor could take it now — standing",
                 act.action.rsplit("#", 1)[-1], (act.via or "?").rsplit("#", 1)[-1])
    #  SAID UPWARD. Deliberation may want to know a step was taken, and progression may not
    #  import it — so this is an event through the choir, on the executing thread, and
    #  whoever above fills `orexis:stepDone` hears it (#452).
    agent.tell(STEP_DONE, act, intention, took)
    return took
