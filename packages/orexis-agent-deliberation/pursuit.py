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

import json
import logging
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from .ontology import pursued_graph
from .planner import SATISFIED

from orexis_agent_progression.execution import carry_out
from orexis_agent_progression.ontology import STATE_GRAPH
from orexis_agent_progression.store import bind, bindings
from orexis_agent_reactive.loop import loop

log = logging.getLogger("pursuit")


# --- what the search is handed (#618) ------------------------------------------------------
#
#  AN `orexis:Always` WANT IS A ROOT AND IS NEVER PURSUED. It is the agent's for its whole
#  life — the premise of what is — and what the search is handed is a
#  want DERIVED under it with a binding of its own, a lifetime and a definition of done: bound
#  `orexis:AtEnd`, `prov:wasDerivedFrom` the root, minted here the first time the root reads
#  unmet and withdrawn when its plan finishes or it reads met with nothing standing for it
#  (an-always-want-is-a-root-and-what-is-pursued-is-derived-from-it). It POINTS at the root's
#  met-test, avoided state and estimate — one owner each — and restates only the root's
#  address, `orexis:about`, which is what the menu joins a want by. The container presents it
#  in the root's place with the root's own measure (`Agent.pursuing`), so a keeper's verdict,
#  a bidder's lookup and a mark by either name meet the same want.


def handed(agent, desire):
    """The want the search is handed for `desire`: itself, unless it is a ROOT — then the want
    derived under it, minted if the root reads unmet and none stands; None for a met root
    with nothing derived under it, which is nothing to pursue and runs no pass."""
    if desire.derived_from is not None or desire.is_obligation or not _is_root(agent, desire.uri):
        return desire
    child = child_of(agent, desire.uri)
    if child is None:
        if desire.is_met:
            #  MET NOW, AND PREDICTED NOT TO BE (#619): a crossing the root foresees derives a
            #  want that must hold AT that instant; nothing foreseen is nothing to pursue.
            instant = foreseen(agent, desire.uri)
            if instant is None:
                return None
            child = mint(agent, desire.uri, holds_at=instant)
        else:
            child = mint(agent, desire.uri)
        if child is None:
            return desire
    #  AS THE CONTAINER PRESENTS IT: a want met at an instant carries its instant, its
    #  time room and the state the newest prediction gives it (`Agent.pursuing`), none of
    #  which the root's row knows; an at-end want is the root's row under the derived name.
    presented = next((d for d in agent.pursuing() if d.uri == child and d.holds_at is not None), None)
    return presented if presented is not None else replace(desire, uri=child, derived_from=desire.uri)


def _is_root(agent, want: str) -> bool:
    return bool(bindings(agent.desires.query_union(
        f"SELECT ?b WHERE {{ <{want}> orexis:bindsWhen orexis:Always }} LIMIT 1")))


def child_of(agent, root: str) -> str | None:
    """The want derived under `root` that stands now, or None."""
    rows = bindings(agent.desires.query_union(
        f"SELECT ?c WHERE {{ ?c prov:wasDerivedFrom <{root}> ; a orexis:Desire ; "
        f"orexis:bindsWhen ?b . FILTER(?b IN (orexis:AtEnd, orexis:At)) }} LIMIT 1"))
    return rows[0]["c"] if rows else None


def crossing_of(agent, root: str) -> datetime | None:
    """When the reading a root is about is predicted to leave its band, or None: the
    earliest instant any declared drift's `orexis:crossesAfter` states for the subject this
    agent acts for and a property the root is about, read at the belief base. The drift's
    package owns the arithmetic; this reads the rows."""
    from . import effects
    abouts = {r["a"] for r in bindings(agent.desires.query_union(
        f"SELECT ?a WHERE {{ <{root}> orexis:about ?a }}"))}
    subject = getattr(agent.me, "acts_for", None)
    if not abouts or subject is None:
        return None
    earliest = None
    for rule in effects.drifts_of(agent.beliefs):
        text = rule.get("crosses")
        if not text:
            continue
        try:
            rows = bindings(agent.beliefs.query(bind(text, state=STATE_GRAPH)))
        except Exception as exc:                        # a package's select, not the mind's problem
            log.error("crossesAfter of %s will not run: %s", rule.get("drift"), exc)
            continue
        for r in rows:
            if r.get("subject") != subject or r.get("property") not in abouts:
                continue
            if not r.get("at") or r.get("seconds") is None:
                continue
            when = datetime.fromisoformat(r["at"]) + timedelta(seconds=float(r["seconds"]))
            if earliest is None or when < earliest:
                earliest = when
    return earliest


def foresees_of(agent, root: str) -> float | None:
    """How far ahead this root derives a want from a prediction, in seconds, or None."""
    rows = bindings(agent.desires.query_union(
        f"SELECT ?f WHERE {{ <{root}> orexis:foresees ?f }} LIMIT 1"))
    return float(rows[0]["f"]) if rows else None


def foreseen(agent, root: str) -> datetime | None:
    """The instant a want derived under `root` must hold at, or None: the predicted
    crossing, where the root foresees that far ahead."""
    ahead = foresees_of(agent, root)
    if ahead is None:
        return None
    crossing = crossing_of(agent, root)
    if crossing is None:
        return None
    if (crossing - datetime.now(timezone.utc)).total_seconds() > ahead:
        return None
    return crossing


def root_of(agent, want: str) -> str | None:
    """The root `want` is derived under, or None where it is not derived from a want."""
    rows = bindings(agent.desires.query_union(
        f"SELECT ?r WHERE {{ <{want}> prov:wasDerivedFrom ?r . ?r a orexis:Desire ; "
        f"orexis:bindsWhen orexis:Always }} LIMIT 1"))
    return rows[0]["r"] if rows else None


def mint(agent, root: str, holds_at: datetime | None = None) -> str | None:
    """Derive the want pursued under `root` and write it to the pursued graph. Its name is the
    root's, suffixed, so a second episode of the same root pursues the same node and everything
    keyed by it — the planner, a remembered plan, the trace — finds what it kept. None, and the
    root stays the goal, where the root states its met-test inline: a blank node has no name
    another graph could point at, and copying it would make a second owner of the claim."""
    child = root + ".pursued"
    pointed = []
    #  The raw SPARQL-JSON rows, because the TYPE of the object matters here and
    #  `bindings` flattens it away: a blank node cannot be pointed at from another graph.
    said = agent.desires.query_union(f"""
SELECT ?p ?o WHERE {{ <{root}> ?p ?o .
  FILTER(?p IN (orexis:metWhen, orexis:unmetWhen, orexis:estimates, orexis:about)) }}""")
    for sol in said.get("results", {}).get("bindings", []):
        if sol["o"]["type"] == "bnode":
            log.warning("%s states its %s inline; it is pursued itself", root.rsplit("#", 1)[-1],
                        sol["p"]["value"].rsplit("#", 1)[-1])
            return None
        pointed.append(f"<{child}> <{sol['p']['value']}> <{sol['o']['value']}> .")
    labels = bindings(agent.desires.query_union(
        f"SELECT ?l WHERE {{ <{root}> rdfs:label ?l }} LIMIT 1"))
    label = "pursued: " + (labels[0]["l"] if labels else root.rsplit("#", 1)[-1])
    #  AT AN INSTANT (#619): bound `orexis:At`, holding at the crossing, its room opening now.
    binding, timed = "orexis:AtEnd", ""
    if holds_at is not None:
        binding = "orexis:At"
        timed = (f' ; orexis:holdsAt "{holds_at.isoformat()}"^^xsd:dateTime'
                 f' ; prov:generatedAtTime "{datetime.now(timezone.utc).isoformat()}"^^xsd:dateTime')
        label = f"foreseen: {label[len('pursued: '):]} at {holds_at.isoformat(timespec='minutes')}"
    agent.beliefs.update(f"""
INSERT DATA {{ GRAPH <{pursued_graph(agent.id)}> {{
  <{agent.me.uri}> orexis:holds <{child}> .
  <{child}> a orexis:Desire ; orexis:bindsWhen {binding} ; prov:wasDerivedFrom <{root}>{timed} ;
      rdfs:label {json.dumps(label)} .
  {' '.join(pointed)}
}} }}""")
    agent.desires.rebuild()
    log.info("%s reads unmet: pursuing %s", root.rsplit("#", 1)[-1], child.rsplit("#", 1)[-1])
    return child


def withdraw(agent, child: str) -> None:
    """The want derived under a root is gone: its plan finished, or it reads met with nothing
    standing for it. A root still unmet derives it again on the next pass, so a plan that fell
    short re-plans through a fresh want rather than a stale one."""
    graph = pursued_graph(agent.id)
    agent.beliefs.update(f"""
DELETE {{ GRAPH <{graph}> {{ ?s ?p ?o }} }}
WHERE  {{ GRAPH <{graph}> {{ ?s ?p ?o . FILTER(?s = <{child}> || ?o = <{child}>) }} }}""")
    agent.desires.rebuild()
    log.info("%s withdrawn", child.rsplit("#", 1)[-1])


def pursue(agent, desire) -> str | None:
    """Plan, commit, take. The intention that stands for the plan's head — adopted now, or
    already standing and absorbed — or None where the search proposed nothing.

    None is a decision somebody else made: the search found no step (its trace says why).
    An absorbed impulse is NOT None — the commitment stands, and the caller is told which.
    """
    #  A ROOT IS NEVER HANDED TO THE SEARCH (#618): what is pursued is the want derived under it.
    desire = handed(agent, desire)
    if desire is None:
        return None
    keeper = agent.keeper
    if keeper is not None and (going := keeper.in_progress(desire.uri)) is not None:
        #  A PLAN IN PROGRESS IS NOT RE-DECIDED (#510): its next step is taken when the world
        #  confirms the one before it, and a lapse or a surprise is what brings the question
        #  back here. A search now would re-decide what nothing has contradicted.
        return going.uri
    plan = agent.deliberator.decide(desire)
    #  A PROMISE THE SEARCH CANNOT MEET IS REFUSED BELOW (#533): a want some step raised for
    #  this level, answered with no plan, or with a plan that does not reach it, is a promise
    #  the level beneath cannot keep — said to the keeper, which writes the refusal on the
    #  step and lapses it at once, so the level above passes the move over and decides again.
    if keeper is not None and _promised(agent, desire.uri) and \
            (plan is None or plan.outcome != SATISFIED):
        keeper.refuse_below(desire.uri, plan.outcome if plan is not None else "nothing to do")
        return None
    if plan is None or not plan.steps:
        return None
    #  PLACED, NOT IMMEDIATE (#619): a want met at an instant is served by a plan whose first
    #  step is taken at the instant less the plan's own duration — the keeper holds it there.
    if desire.holds_at is not None and plan.landing is not None:
        start = desire.holds_at - timedelta(seconds=plan.landing)
        if start > datetime.now(timezone.utc):
            plan = replace(plan, steps=(replace(plan.steps[0], not_before=start),) + plan.steps[1:])
    act = plan.steps[0]
    if keeper is None:
        return None
    #  THE PATIENCE IS `adopt`'S, whole: a commitment that STANDS within patience absorbs the
    #  impulse, and every means now stands until the world answers — an Acquire until its
    #  claim, an Actuate until its watch is judged (#353). There used to be a hook here for
    #  the one act that resolved at the command; making its intention stand to the END was
    #  the BDI-shaped fix, and the hook went with it.
    because = _because(plan, desire)

    def commit_and_take() -> str | None:
        uri = keeper.adopt(plan.steps, desire.uri, because)          # the WHOLE plan (#510)
        if uri is None:
            #  ABSORBED: the same commitment already stands within patience. Say WHICH, so a
            #  caller that needs to know whether anything is on its way (a bidder waiting for
            #  a look) can tell an absorbed impulse from a want nothing can serve — both used
            #  to come back as None, and the second is the only one that means "sit out".
            standing = keeper.standing(action=act.action, want=desire.uri)
            return standing[0].uri if standing else None
        #  THE STEP THE LEDGER STANDS AT, not the plan's head as the search wrote it: an
        #  action with a method was expanded at adoption (#523), and its first step is
        #  what there is to take.
        carry_out(agent, keeper.current(uri) or act, desire, uri)
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


def pursue_for(agent, want: str) -> str | None:
    """The actors' door: something changed about this want — what now, about it?

    An actor holding a fresh reading finds the want it means by its own query — sensing's
    `want_about(property)` states the rule, an unmet epistemic want first and then the stake —
    and hands the NODE here. None where the agent is not pursuing that want at all.
    """
    #  BY EITHER NAME (#618): a mark may name the root while the want derived under it stands.
    desire = next((d for d in agent.pursuing() if d.uri == want or d.derived_from == want), None)
    return pursue(agent, desire) if desire is not None else None


def _because(plan, desire) -> str:
    """The ledger's prose: what the plan found and how far it expected to get."""
    what = (f"an obligation to {desire.owed_to.rsplit('#', 1)[-1]}" if desire.is_obligation
            else desire.uri.rsplit("#", 1)[-1])
    if plan.urgency_now is None or plan.urgency_after is None:
        return f"{plan.outcome} for {what}"
    return (f"{plan.outcome} for {what}: urgency {plan.urgency_now:.2f} -> "
            f"{plan.urgency_after:.2f} over {len(plan.steps)} step(s)")


def _promised(agent, want: str) -> bool:
    """Is this want a promise some step raised for this level (`progression:promisedBy`)?"""
    from orexis_agent_progression.store import bindings
    return bool(bindings(agent.desires.query_union(
        f"SELECT ?s WHERE {{ <{want}> progression:promisedBy ?s }} LIMIT 1")))
