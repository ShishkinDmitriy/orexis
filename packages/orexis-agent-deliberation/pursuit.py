"""Pursuit: plan, commit the head as an intention, hand it down to be carried out. One road.

**This is what happens to a want, and it is deliberation's because the first step is the
search.** It used to be three things by trigger: the keeper's tick carried out Observe alone,
the bidder re-asked the deliberator inside `submit` when a round knocked, and the actuator
asked on its own reading — each adopting its own intention with its own reason. The search
was one road and execution was three, and a plan's `via` — WHICH lever, half of what a step
says — was dropped between the planner and the ledger.

Now every trigger arrives here and none of them decides. `pursue(agent, desire)`:

1. PLAN — `deliberator.decide(desire)`, the search, answering with rows;
2. COMMIT — every step to the keeper, the head stood at, `progression:through` the lever,
   `progression:pursues` the desire. Absorbed within patience means nothing to carry out;
3. TAKE — handed DOWN to progression's `carry_out`, which asks the T-Box who takes the action
   and runs the take on the reactive loop. False from every actor is "not now": the intention
   stands and the next trigger finds it.

**The plan is handed down whole** (#510, progression-steps-through-a-plan-on-confirmed-feedback):
every step goes to the keeper, the head is taken, and each further step is taken when the
world confirms the one before it — by feedback, with no search above it. A plan in progress
is not searched over again until it lapses or the world contradicts it; that is the
amortisation, moved from "adopt absorbs the same head" to "a standing plan is not re-decided".

This file and progression's `execution.py` were one `agent/execution.py`; the layer split cut
it at the one line where deciding stops and doing starts. See knowledge/domain/executor.md and
knowledge/decisions/an-intention-is-a-plan-committed-to.md.
"""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import datetime

from .derive_wants import derive_wants
from .judgments import witnesses_of
from .plan import SATISFIED

from orexis_agent_progression.execution import carry_out
from orexis_agent_progression.store import bindings
from orexis_agent_reactive.loop import loop
from orexis_agent_progression import clock

log = logging.getLogger("pursuit")


# --- what the search is handed (#618) ------------------------------------------------------
#
#  A DESIRE IS A ROOT AND IS NEVER PURSUED. It is the agent's for its whole life — the premise
#  of what is pursued — and what the search is handed is a WANT derived under it, with a binding
#  of its own, a lifetime and a definition of done: bound `orexis:AtEnd`, `prov:wasDerivedFrom`
#  the root, minted here the first time the root reads unmet and withdrawn when its plan
#  finishes or it reads met with nothing standing for it
#  (an-always-want-is-a-root-and-what-is-pursued-is-derived-from-it). It CARRIES the root's
#  met-test instantiated at its witness — the same shape, targeting the one instance in
#  trouble, with the blocks about what the want is about (`narrowed`) — POINTS at the root's
#  avoided state and estimate, one owner each, and restates the root's address,
#  `orexis:about`, which is what the affordances join a want by. The container presents it in
#  the root's place with the root's own measure and its own state (`Agent.pursuing`), so a
#  keeper's verdict, a bidder's lookup and a mark by either name meet the same want.


def handed(agent, judgment):
    """The want the search is handed for `desire`: itself, unless it is a ROOT — then the want
    derived under it, minted if the root reads unmet and none stands; None for a met root
    with nothing derived under it, which is nothing to pursue and runs no pass."""
    if judgment.derived_from is not None or not _is_root(agent, judgment.uri):
        #  A WANT ALREADY MINTED, or one a package speaks for: handed as it is. Its root may
        #  have gained instances since — a second claim — so the derivation tops up first; and where
        #  that re-minted THIS want — what it foresaw has arrived — the judgment in hand still
        #  carries the old instant, so it is presented again.
        if judgment.derived_from is not None:
            if judgment.uri in derived(agent):
                return next((d for d in agent.pursuing() if d.uri == judgment.uri), judgment)
        return judgment
    #  THE PASS STANDS ON THE ROOT: every desire is judged into the store and the wants derived
    #  from what the store says — a root whose met-test the compiler refused is judged by the
    #  choir there, and still derives its one want.
    derived(agent)
    child = child_of(agent, judgment.uri)
    if child is None:
        return None
    #  AS THE CONTAINER PRESENTS IT: a want met at an instant carries its instant, its
    #  time room and the state the newest prediction gives it (`Agent.pursuing`), none of
    #  which the root's row knows; an at-end want is the root's row under the derived name.
    presented = next((d for d in agent.pursuing() if d.uri == child and d.holds_at is not None), None)
    return presented if presented is not None else replace(judgment, uri=child, derived_from=judgment.uri)


def derived(agent) -> list[str]:
    """`derive_wants` over this agent's store, and the projection refreshed where it minted.

    IT IS A FUNCTION OVER THE STORE and holds no collection, so a want it writes
    announces itself to nobody — where `Wants.save` would have told the desire modality to
    rebuild. Saying so is the caller's, and this is the caller every pass goes through: one
    place, and the rebuild is paid only when something was actually minted.
    """
    minted = derive_wants(agent.beliefs.engine)
    if minted:
        agent.desires.rebuild()
    return minted


def _is_root(agent, want: str) -> bool:
    """Is this the standing kind — a desire, never handed to a search (#618)?

    BEING IN THE COLLECTION IS THE ANSWER. It read the binding, back when a want was a desire
    by entailment and only `orexis:Always` separated them; the types are disjoint now, so the
    question is simply whether the desires hold it (a-kind-is-a-type-not-a-binding).
    """
    return agent.desires.find_first_by_uri(want) is not None


def child_of(agent, root: str) -> str | None:
    """The want derived under `root` that stands now, or None.

    THROUGH THE REPOSITORY (#677): which graphs hold wants and what asks for one are `Wants`',
    and this is the question rather than the query.
    """
    found = agent.wants.find_first_by_desire(root)
    return found.uri if found else None


def crossing_of(agent, root: str) -> datetime | None:
    """When the world a DESIRE is about is judged to leave what the desire wants, or None: the
    earliest instant its judgments read unmet. The rows are `judgments.witnesses_of`.

    A desire's, never a want's. A want has no crossing — it is what a crossing produced, and
    it carries the instant it must hold at; whether it is still in trouble by then is
    `judgments.unmet_by`.
    """
    found = witnesses_of(agent.beliefs.engine, root)
    return found[0].at if found else None


def foreseen(agent, root: str) -> datetime | None:
    """The instant a want derived under `root` must hold at, or None: the predicted crossing.

    A FORESIGHT once gated this — a per-agent pick discarding a crossing further out than N
    seconds — and it is gone with the one in `derive_wants`: what bounds the lookahead is the
    horizons each drift predicts at, so a crossing there is at all is one worth a want.
    """
    return crossing_of(agent, root)


def root_of(agent, want: str) -> str | None:
    """The desire `want` was derived under, or None where it was derived from no desire.

    THROUGH THE COLLECTION THAT HOLDS THE ANSWER. It was asked of `Wants` — find the want, read
    the name it kept — which walks one collection to reach an element of another and hands back
    a field rather than a thing.
    """
    found = agent.desires.find_first_by_want(want)
    return found.uri if found else None


def withdraw(agent, child: str) -> None:
    """The want derived under a root is gone: its plan finished, or it reads met with nothing
    standing for it. A root still unmet derives it again on the next pass, so a plan that fell
    short re-plans through a fresh want rather than a stale one."""
    agent.wants.delete_by_uri(agent.id, child)
    log.info("%s withdrawn", child.rsplit("#", 1)[-1])


def pursue(agent, judgment, surprise: tuple | None = None) -> str | None:
    """Plan, commit, take. The intention that stands for the plan's head — adopted now, or
    already standing and absorbed — or None where the search proposed nothing.

    None is a decision somebody else made: the search found no step (its trace says why).
    An absorbed impulse is NOT None — the commitment stands, and the caller is told which.
    """
    #  A ROOT IS NEVER HANDED TO THE SEARCH (#618): what is pursued is the want derived under it.
    judgment = handed(agent, judgment)
    if judgment is None:
        return None
    keeper = agent.keeper
    if keeper is not None and (going := keeper.in_progress(judgment.uri)) is not None:
        #  A PLAN IN PROGRESS IS NOT RE-DECIDED (#510): its next step is taken when the world
        #  confirms the one before it, and a lapse or a surprise is what brings the question
        #  back here. A search now would re-decide what nothing has contradicted.
        return going.uri
    plan = agent.deliberator.decide(judgment, surprise=surprise)
    #  A PROMISE THE SEARCH CANNOT MEET IS REFUSED BELOW (#533): a want some step raised for
    #  this level, answered with no plan, or with a plan that does not reach it, is a promise
    #  the level beneath cannot keep — said to the keeper, which writes the refusal on the
    #  step and lapses it at once, so the level above passes the move over and decides again.
    if keeper is not None and _promised(agent, judgment.uri) and \
            (plan is None or plan.outcome != SATISFIED):
        keeper.refuse_below(judgment.uri, plan.outcome if plan is not None else "nothing to do")
        return None
    if plan is None or not plan.steps:
        return None
    #  PLACED AT THE INSTANT THE PASS STOOD AT (#619, #625): a plan found where the present's
    #  drift stands later than now has its first step held there — the keeper does the
    #  waiting — and a plan found from the present is taken now, whatever instant the want
    #  holds at; what waits for the instant then is the step the world places, a claim's
    #  presenting. Never by subtraction from the deadline.
    if plan.placed_at is not None and plan.placed_at > clock.now():
        plan = replace(plan, steps=(replace(plan.steps[0], not_before=plan.placed_at),) + plan.steps[1:])
    act = plan.steps[0]
    if keeper is None:
        return None
    #  THE PATIENCE IS `adopt`'S, whole: a commitment that STANDS within patience absorbs the
    #  impulse, and every means now stands until the world answers — an Acquire until its
    #  claim, an Actuate until its watch is judged (#353). There used to be a hook here for
    #  the one act that resolved at the command; making its intention stand to the END was
    #  the BDI-shaped fix, and the hook went with it.
    because = _because(plan, judgment)

    def commit_and_take() -> str | None:
        uri = keeper.adopt(plan.steps, judgment.uri, because)          # the WHOLE plan (#510)
        if uri is None:
            #  ABSORBED: the same commitment already stands within patience. Say WHICH, so a
            #  caller that needs to know whether anything is on its way (a bidder waiting for
            #  a look) can tell an absorbed impulse from a want nothing can serve — both used
            #  to come back as None, and the second is the only one that means "sit out".
            standing = keeper.standing(action=act.action, want=judgment.uri)
            return standing[0].uri if standing else None
        #  THE STEP THE LEDGER STANDS AT, not the plan's head as the search wrote it: an
        #  action with a method was expanded at adoption (#523), and its first step is
        #  what there is to take.
        carry_out(agent, keeper.current(uri) or act, judgment, uri)
        return uri

    #  ONLY THE RESULT CROSSES ONTO THE LOOP. The search ran on whoever called — the
    #  deliberation worker, or a test — and what it found is one act; committing it to the
    #  ledger and handing it to its actor is progression's, and runs as ONE item on the
    #  executing thread, so the ledger write and the take are atomic against every other
    #  handler and tick. A caller that IS the loop does it now; any other waits for its
    #  answer, which is the one wait a search is allowed.
    on = loop()
    if on.is_current():
        return commit_and_take()
    return on.submit(commit_and_take).result()


def pursue_for(agent, want: str, surprise: tuple | None = None) -> str | None:
    """The actors' door: something changed about this want — what now, about it?

    An actor holding a fresh reading finds the want it means by its own query — sensing's
    `want_about(property)` states the rule, an unmet epistemic want first and then the stake —
    and hands the NODE here. None where the agent is not pursuing that want at all.
    """
    #  BY EITHER NAME (#618): a mark may name the root while the want derived under it stands.
    judgment = next((d for d in agent.pursuing() if d.uri == want or d.derived_from == want), None)
    return pursue(agent, judgment, surprise=surprise) if judgment is not None else None


def _because(plan, judgment) -> str:
    """The ledger's prose: what the plan found and how far it expected to get. The want by
    its own name, which says what it is about — a debt's carries its claim."""
    what = judgment.uri.rsplit("#", 1)[-1]
    if plan.urgency_now is None or plan.urgency_after is None:
        return f"{plan.outcome} for {what}"
    return (f"{plan.outcome} for {what}: urgency {plan.urgency_now:.2f} -> "
            f"{plan.urgency_after:.2f} over {len(plan.steps)} step(s)")


def _promised(agent, want: str) -> bool:
    """Is this want a promise some step raised for this level (`progression:promisedBy`)?"""
    return bool(bindings(agent.desires.query(
        f"SELECT ?s WHERE {{ <{want}> progression:promisedBy ?s }} LIMIT 1")))
