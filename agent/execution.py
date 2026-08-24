"""Execution: plan, commit the head as an intention, hand it to its actor. One road.

**This is what happens to a decision, and it is the kernel's.** It used to be three things by
trigger: the keeper's tick carried out Observe alone, the bidder re-asked the deliberator inside
`submit` when a round knocked, and the actuator asked on its own reading — each adopting its own
intention with its own reason. The search was one road and execution was three, and a plan's
`via` — WHICH lever, half of what a step says — was dropped between the planner and the ledger.

Now every trigger arrives here and none of them decides. `pursue(agent, desire)`:

1. PLAN — `deliberator.decide(desire)`, the search as it was, answering with rows;
2. COMMIT — the head row to the keeper, `ag:by` the means, `ag:through` the lever,
   `ag:pursues` the desire. Absorbed within patience means nothing to carry out;
3. TAKE — the means' `ag:takenBy` family asked of the T-Box, `agent.providers` asked for
   whoever is loaded, and each handed the row. False from all of them is "not now": the
   intention stands and the next trigger finds it.

**Only the head is committed**, and that is not a shortcut: the plan is re-derived every pass
because the world moves, so a committed tail would be a promise about a future nobody has seen.
The tail is in the trace for a reader.

**Nothing here names a package.** The link from a row to its code is `ag:takenBy`, stated on the action node beside
the precondition and the effect — a fact a sovereign can query, where `planner._dose` still
spells the two SIZING families by hand because a bid and a dose are sized by different names. See knowledge/domain/execution.md,
knowledge/domain/actor.md and knowledge/decisions/an-intention-is-a-plan-committed-to.md.
"""

from __future__ import annotations

import logging

from .ontology import AG
from .store import bindings

log = logging.getLogger("execution")

#  Asked by NAME of the whole default graph — the T-Box is public, and which capability takes
#  a means is a fact about the vocabulary rather than about any world.
_TAKEN_BY_Q = (f"SELECT ?family WHERE {{ ?action <{AG}means> <%s> ; "
               f"<{AG}takenBy> ?family }} LIMIT 1")


def taken_by(query, means: str) -> str | None:
    """The capability family that carries this means out, or None where no package says."""
    rows = bindings(query(_TAKEN_BY_Q % means))
    return rows[0]["family"] if rows else None


def pursue(agent, desire) -> str | None:
    """Plan, commit, take. The intention that stands for the plan's head — adopted now, or
    already standing and absorbed — or None where the search proposed nothing.

    None is a decision somebody else made: the search found no step (its trace says why).
    An absorbed impulse is NOT None — the commitment stands, and the caller is told which.
    """
    plan = agent.deliberator.decide(desire)
    if plan is None or not plan.steps:
        return None
    row = plan.steps[0]
    keeper = agent.keeper
    if keeper is None:
        return None
    #  THE PATIENCE IS `adopt`'S, whole: a commitment that STANDS within patience absorbs the
    #  impulse, and every means now stands until the world answers — an Acquire until its
    #  claim, an Actuate until its watch is judged (#353). There used to be a hook here for
    #  the one act that resolved at the command; making its intention stand to the END was
    #  the BDI-shaped fix, and the hook went with it.
    uri = keeper.adopt(row.means, row.observed_property,
                       _because(plan, desire), desire=desire.uri, via=row.via)
    if uri is None:
        #  ABSORBED: the same commitment already stands within patience. Say WHICH, so a
        #  caller that needs to know whether anything is on its way (a bidder waiting for a
        #  look) can tell an absorbed impulse from a want nothing can serve — both used to
        #  come back as None, and the second is the only one that means "sit out".
        standing = keeper.standing(means=row.means, observed_property=row.observed_property,
                                   desire=desire.uri)
        return standing[0].uri if standing else None
    carry_out(agent, row, desire, uri)
    return uri


def pursue_about(agent, observed_property: str) -> str | None:
    """The actors' door: a fresh reading of this property is in hand — what now, about it?

    Which of the property's wants is pursued is the deliberator's rule (an unmet epistemic
    want first, then the stake), stated once in `desire_about` and asked here rather than
    restated. None where nothing is wanted about the property at all.
    """
    desire = agent.deliberator.desire_about(observed_property)
    return pursue(agent, desire) if desire is not None else None


def take_standing(agent, standing, desire) -> bool:
    """Carry out a step that already stands — the trigger changed, the decision did not.

    An offer arriving while an Acquire stands, a reading arriving while an Actuate does: the
    commitment was made on the tick and the actor could not act then. Nothing is re-decided;
    the standing row is rebuilt from the ledger and handed over.
    """
    from .menu import Affordance

    row = Affordance(means=standing.means, observed_property=standing.observed_property,
                     via=standing.via or "")
    return carry_out(agent, row, desire, standing.uri)


def carry_out(agent, row, desire, intention: str) -> bool:
    """Hand one committed row to whoever the T-Box says takes its means. True if anyone did."""
    family = taken_by(agent.beliefs.query, row.means)
    if family is None:
        #  A row was shipped and no taker was stated. `tests/test_execution.py` refuses this
        #  for every means that has a row in a shipped world; reaching it at runtime is a
        #  package onboarded past that gate, and the honest thing is to say so loudly.
        log.error("nothing takes %s — its package states no ag:takenBy, so this intention "
                  "stands with nobody to carry it out", row.means.rsplit("#", 1)[-1])
        return False
    took = False
    for actor in agent.providers(family):
        took = bool(actor.take(row, desire, intention)) or took
    if not took:
        log.info("%s through %s: no actor could take it now — standing",
                 row.means.rsplit("#", 1)[-1], (row.via or "?").rsplit("#", 1)[-1])
    return took


def _because(plan, desire) -> str:
    """The ledger's prose: what the plan found and how far it expected to get."""
    what = (desire.observed_property.rsplit("#", 1)[-1] if desire.observed_property
            else f"a duty to {desire.owed_to.rsplit('#', 1)[-1]}" if desire.is_duty
            else desire.uri.rsplit("#", 1)[-1])
    if plan.urgency_now is None or plan.urgency_after is None:
        return f"{plan.outcome} for {what}"
    return (f"{plan.outcome} for {what}: urgency {plan.urgency_now:.2f} -> "
            f"{plan.urgency_after:.2f} over {len(plan.steps)} step(s)")
