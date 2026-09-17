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
from datetime import datetime, timedelta, timezone

from .want import Want
from .plan import SATISFIED

from orexis_agent_progression.execution import carry_out
from orexis_agent_progression.store import bindings
from orexis_agent_reactive.loop import loop
from orexis_agent_progression import clock

log = logging.getLogger("pursuit")


# --- what the search is handed (#618) ------------------------------------------------------
#
#  AN `orexis:Always` DESIRE IS A ROOT AND IS NEVER PURSUED. It is the agent's for its whole
#  life — the premise of what is — and what the search is handed is a
#  want DERIVED under it with a binding of its own, a lifetime and a definition of done: bound
#  TYPED BOTH, and that is materialised entailment rather than a second statement: the closure
#  `orexis:Want rdfs:subClassOf orexis:Desire` is computed ONCE, at genesis, over what the store
#  held then — and a want is minted long after, so nothing would ever entail the supertype for
#  it and every `?d a orexis:Desire` in the tree would stop finding what it pursues.
#  `orexis:AtEnd`, `prov:wasDerivedFrom` the root, minted here the first time the root reads
#  unmet and withdrawn when its plan finishes or it reads met with nothing standing for it
#  (an-always-want-is-a-root-and-what-is-pursued-is-derived-from-it). It POINTS at the root's
#  met-test, avoided state and estimate — one owner each — and restates only the root's
#  address, `orexis:about`, which is what the menu joins a want by. The container presents it
#  in the root's place with the root's own measure (`Agent.pursuing`), so a keeper's verdict,
#  a bidder's lookup and a mark by either name meet the same want.


def handed(agent, judgment):
    """The want the search is handed for `desire`: itself, unless it is a ROOT — then the want
    derived under it, minted if the root reads unmet and none stands; None for a met root
    with nothing derived under it, which is nothing to pursue and runs no pass."""
    if judgment.derived_from is not None or judgment.is_obligation or not _is_root(agent, judgment.uri):
        return judgment
    child = child_of(agent, judgment.uri)
    if child is None:
        if judgment.is_met:
            #  MET NOW, AND PREDICTED NOT TO BE (#619): a crossing the root foresees derives a
            #  want that must hold AT that instant; nothing foreseen is nothing to pursue.
            instant = foreseen(agent, judgment.uri)
            if instant is None:
                return None
            child = mint(agent, judgment.uri, holds_at=instant)
        else:
            child = mint(agent, judgment.uri)
        if child is None:
            return judgment
    #  AS THE CONTAINER PRESENTS IT: a want met at an instant carries its instant, its
    #  time room and the state the newest prediction gives it (`Agent.pursuing`), none of
    #  which the root's row knows; an at-end want is the root's row under the derived name.
    presented = next((d for d in agent.pursuing() if d.uri == child and d.holds_at is not None), None)
    return presented if presented is not None else replace(judgment, uri=child, derived_from=judgment.uri)


def _is_root(agent, want: str) -> bool:
    """Is this the DECLARED kind — a standing rule, never handed to a search (#618)? Asked of
    the collection that holds them, whose answer's binding says which kind came back."""
    found = agent.desires.find_first_by_uri(want)
    return found is not None and found.binds.endswith("Always")


def child_of(agent, root: str) -> str | None:
    """The want derived under `root` that stands now, or None.

    THROUGH THE REPOSITORY (#677): which graphs hold wants and what asks for one are `Wants`',
    and this is the question rather than the query.
    """
    found = agent.wants.find_first_by_desire(root)
    return found.uri if found else None


def crossing_of(agent, root: str) -> datetime | None:
    """The earliest predicted crossing for `root`, or None — see `crossing_row_of`."""
    found = crossing_row_of(agent, root)
    return found[0] if found else None


def _unmet_select_of(agent, root: str) -> str | None:
    """The root's own met-test, compiled to the select whose rows are its violations — the
    same compile the planner does in `_begin` — from public knowledge and the agent's roots
    graph, where a root's shape lives since #644. Cached per root on the agent: a root never
    changes while the agent runs. None where the root states no shape or the compiler refuses."""
    from rdflib import URIRef

    from orexis_agent_progression.ontology import roots_graph
    from orexis_agent_progression.violation import Unsupported, unmet_select

    from .conformance import graph_from

    cache = agent.__dict__.setdefault("_root_selects", {})
    if root in cache:
        return cache[root]
    rows = bindings(agent.desires.query_union(f"SELECT ?s WHERE {{ <{root}> orexis:metWhen ?s }} LIMIT 1"))
    select = None
    if rows:
        shape = rows[0]["s"]
        try:
            shapes = graph_from(agent.beliefs, *agent.beliefs.public_graphs(), roots_graph(agent.id))
            select = unmet_select(shapes.cbd(URIRef(shape)), URIRef(shape))
        except Unsupported as exc:
            log.warning("%s: its met-test cannot be compiled, so no crossing is read for it: %s",
                        root.rsplit("#", 1)[-1], exc)
    cache[root] = select
    return select


def crossing_row_of(agent, root: str) -> tuple[datetime, datetime] | None:
    """When the world a root is about is PREDICTED to leave what the root wants, or None
    (#643, the-drift-is-sensings-and-its-result-is-predictions): the start of the earliest
    prediction at which the root reads UNMET — its own met-test asked through the door at each
    prediction's start, where the door hands the prediction holding then beside the present.
    A prediction typed with the region band and the one below reads unmet, so the safe
    direction (#633) falls out of the bands, and no kernel line knows a rate. The second
    instant is the same start: what a pass for the derived want is clocked from."""
    select = _unmet_select_of(agent, root)
    if select is None:
        return None
    for graph, start, end in agent.beliefs.prediction_windows():
        if start is None:
            continue
        try:
            rows = bindings(agent.beliefs.query_at(select, at=start))
        except Exception as exc:                                    # noqa: BLE001
            log.error("%s: the crossing could not be read at %s: %s", root.rsplit("#", 1)[-1], start, exc)
            return None
        if rows:
            return start, start
    return None


def foresees_of(agent, root: str) -> float | None:
    """How far ahead this root derives a want from a prediction, in seconds, or None.

    ASKED OF THE CHOIR (#644): a root authored at genesis states no foresight, because the
    belief that says how far the agent looks ahead is a pick, and a root is not a function of
    the agent's state — whoever holds that belief answers `orexis:foresight` at the moment a
    child is derived, so a re-pick reaches the next derivation with no rebuild. An asserted want
    may still state `orexis:foresees`, read where no voice answers."""
    from orexis_agent_progression.ontology import FORESIGHT

    for answer in agent.ask(FORESIGHT, root):
        if answer is not None:
            return float(answer)
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
    if (crossing - clock.now()).total_seconds() > ahead:
        return None
    return crossing


def root_of(agent, want: str) -> str | None:
    """The desire `want` was derived under, or None where it was derived from no desire.

    THROUGH THE COLLECTION THAT HOLDS THE ANSWER. It was asked of `Wants` — find the want, read
    the name it kept — which walks one collection to reach an element of another and hands back
    a field rather than a thing.
    """
    found = agent.desires.find_first_by_want(want)
    return found.uri if found else None


def mint(agent, root: str, holds_at: datetime | None = None) -> str | None:
    """Derive the want pursued under `root` and write it to the pursued graph. Its name is the
    root's, suffixed, so a second episode of the same root pursues the same node and everything
    keyed by it — the planner, a remembered plan, the trace — finds what it kept. None, and the
    root stays the goal, where the root states its met-test inline: a blank node has no name
    another graph could point at, and copying it would make a second owner of the claim."""
    child = root + ".pursued"
    points_said = []
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
        points_said.append(sol)
    labels = bindings(agent.desires.query_union(
        f"SELECT ?l WHERE {{ <{root}> rdfs:label ?l }} LIMIT 1"))
    label = "pursued: " + (labels[0]["l"] if labels else root.rsplit("#", 1)[-1])
    #  AT AN INSTANT (#619): bound `orexis:At`, holding at the crossing, its room opening now.
    binding = "orexis:AtEnd"
    if holds_at is not None:
        binding = "orexis:At"
        label = f"foreseen: {label[len('pursued: '):]} at {holds_at.isoformat(timespec='minutes')}"
    #  IT HOLDS FROM ITS DERIVATION to the instant it must hold at plus the patience its plan
    #  is given after it — the last step is placed AT the instant and its verdict comes after —
    #  and is open for a want met at its plan's end (#645).
    #  THE WANT, AND THE REPOSITORY WRITES IT (#677). What is derived is decided here — the
    #  binding, the label, what it points at — and where a want is kept, how its graph is
    #  classified and what period it holds during are `Wants`'.
    ends = None
    if holds_at is not None:
        patience = float(getattr(getattr(agent.keeper, "beliefs", None), "patience_s", 0) or 0)
        ends = (holds_at + timedelta(seconds=patience)).isoformat()
    agent.wants.save(Want(
        uri=child, desire=root, binds=binding, label=label, ends=ends,
        holds_at=holds_at.isoformat() if holds_at is not None else None,
        derived_at=clock.now().isoformat() if holds_at is not None else None,
        points=tuple((sol["p"]["value"], sol["o"]["value"]) for sol in points_said)))
    log.info("%s reads unmet: pursuing %s", root.rsplit("#", 1)[-1], child.rsplit("#", 1)[-1])
    return child


def withdraw(agent, child: str) -> None:
    """The want derived under a root is gone: its plan finished, or it reads met with nothing
    standing for it. A root still unmet derives it again on the next pass, so a plan that fell
    short re-plans through a fresh want rather than a stale one."""
    agent.wants.delete_by_uri(child)
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
    """The ledger's prose: what the plan found and how far it expected to get."""
    what = (f"an obligation to {judgment.owed_to.rsplit('#', 1)[-1]}" if judgment.is_obligation
            else judgment.uri.rsplit("#", 1)[-1])
    if plan.urgency_now is None or plan.urgency_after is None:
        return f"{plan.outcome} for {what}"
    return (f"{plan.outcome} for {what}: urgency {plan.urgency_now:.2f} -> "
            f"{plan.urgency_after:.2f} over {len(plan.steps)} step(s)")


def _promised(agent, want: str) -> bool:
    """Is this want a promise some step raised for this level (`progression:promisedBy`)?"""
    from orexis_agent_progression.store import bindings
    return bool(bindings(agent.desires.query_union(
        f"SELECT ?s WHERE {{ <{want}> progression:promisedBy ?s }} LIMIT 1")))
