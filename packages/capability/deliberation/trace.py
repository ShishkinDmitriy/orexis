"""What the planner considered, written down so somebody can read it.

A `Plan` carries the outcome, the steps and the urgency on both sides, and every bit of it used
to die in-process as one log line. The material was never missing — the exposure was, and it
could not be added from outside: pyoxigraph holds an exclusive lock on the belief base, so
nothing else can open the store to re-run the search and see what it saw. That is the same fact
`agora-ask` exists for, arriving at the planner.

**This is the record's one exception, taken on purpose.** Possible worlds are computed and
dropped, because a stored conclusion can outlive the premise it came from — except where a
reader outside the process needs one, and then: its own graph class, cleared at the start of
every pass, carrying PROV to what generated it, never public and never in belief. All four hold
here, and the fourth is the one worth watching: nothing reads this back. Cycle detection stays
inside the search, in a set that lives as long as the pass, where it can be reasoned about. A
trace that became memory would be a conclusion feeding a conclusion.

See knowledge/decisions/a-plan-is-a-path-of-graph-diffs.md, "Possible worlds are computed, not
kept", and knowledge/domain/deliberation.md for what to ask it.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from urllib.parse import quote

from agent.ontology import DELIBERATION_GRAPH

log = logging.getLogger("trace")

KERNEL = "http://example.org/agora#"

#  Why a candidate did not become the plan — the same six-answers-instead-of-two argument the
#  pass's own outcome makes, one scale down. "Worse" and "already seen" are different findings:
#  the first says this lever does not help from here, the second says the search has been here
#  before and expanding it again would spend the depth budget going nowhere.
MET = "meets the goal"
BETTER = "better than standing still"
WORSE = "no better than standing still"
SEEN = "a world already reached"
UNSIMULATED = "could not be simulated"


def _uri(agent_id: str, goal_uri: str) -> str:
    """One node per (agent, goal), so planning the same goal twice replaces rather than adds.

    Minted from the goal's own IRI on the channel precedent — a derived instance computed from
    a given string, so a second pass lands on the same node and the DELETE below finds it.

    DETERMINISTIC ACROSS PROCESSES, which `hash()` is not: Python salts it per interpreter, so
    a node minted in one run would be unfindable in the next, the clear would match nothing,
    and every restart would orphan a trace that outlived the pass it described — the one thing
    this graph must never do. The goal's local name is already unique per agent (a want is
    minted per agent and property), and quoting the whole IRI covers a goal shaped otherwise.
    """
    tail = goal_uri.rsplit("#", 1)[-1] if "#" in goal_uri else quote(goal_uri, safe="")
    return f"{KERNEL}deliberation.{agent_id}.{quote(tail, safe='')}"


def clear(store, agent_id: str, goal_uri: str) -> None:
    """Drop the previous pass for this goal, at the START of the next one.

    At the start and not the end, which is the difference between a graph that holds one pass
    and a graph that holds two. Clearing when a pass finishes would leave the trace of a goal
    whose planning crashed sitting beside beliefs it can contradict — and the crash is exactly
    the case somebody would be reading the trace to understand.
    """
    node = _uri(agent_id, goal_uri)
    store.update(f"""
        DELETE {{ GRAPH <{DELIBERATION_GRAPH}> {{ ?c ?cp ?co . <{node}> ?p ?o }} }}
        WHERE  {{ GRAPH <{DELIBERATION_GRAPH}> {{
                    <{node}> ?p ?o .
                    OPTIONAL {{ <{node}> <{KERNEL}considered> ?c . ?c ?cp ?co }} }} }}""")


def write(store, agent_id: str, goal, plan, considered, stands_at: float) -> None:
    """Record one pass: what was weighed, what each would have reached, and what was taken.

    Never raises. A planner that fell over because its debugging aid did would be a poor trade
    for being able to watch it — so a failure here is logged and the decision stands, which is
    the same posture `reporting` takes towards the series store.
    """
    try:
        _write(store, agent_id, goal, plan, considered, stands_at)
    except Exception as exc:                      # noqa: BLE001 - see the docstring
        log.warning("could not record what was considered: %s", exc)


def _write(store, agent_id: str, goal, plan, considered, stands_at: float) -> None:
    node = _uri(agent_id, goal.uri)
    chosen = plan.steps[0].means if plan.steps else None
    rows = []
    for i, (depth, row, urgency, verdict) in enumerate(considered):
        candidate = f"{node}.{i}"
        reached = "" if urgency is None else \
            f'        <{KERNEL}wouldReach> {urgency:.6f} ;\n'
        rows.append(
            f'    <{node}> <{KERNEL}considered> <{candidate}> .\n'
            f'    <{candidate}> a <{KERNEL}Candidate> ;\n'
            f'        <{KERNEL}wouldTake> <{row.means}> ;\n'
            f'        <{KERNEL}through> <{row.via}> ;\n'
            f'        <{KERNEL}atDepth> {depth} ;\n'
            f'{reached}'
            f'        <{KERNEL}verdict> "{verdict}" .\n')
    #  The chosen candidate is named rather than duplicated: a reader joining `ag:chose` to the
    #  candidate gets its depth, its lever and the world it would reach, and the trace never
    #  says the same number twice in two places where they could drift apart.
    took = ""
    if chosen is not None:
        for i, (_, row, _, _) in enumerate(considered):
            if row.means == chosen:
                took = f'        <{KERNEL}chose> <{node}.{i}> ;\n'
                break
    store.update(f"""INSERT DATA {{ GRAPH <{DELIBERATION_GRAPH}> {{
    <{node}> a <{KERNEL}Deliberation> ;
        <{KERNEL}deliberatedOn> <{goal.uri}> ;
        <{KERNEL}verdict> "{plan.outcome}" ;
        <{KERNEL}standsAt> {stands_at:.6f} ;
        <{KERNEL}blind> {"true" if plan.partial else "false"} ;
{took}        <{KERNEL}asOf> "{datetime.now(timezone.utc).isoformat()}"^^<http://www.w3.org/2001/XMLSchema#dateTime> .
{"".join(rows)}}} }}""")


def outcomes(query) -> dict[str, int]:
    """How many goals ended in each verdict on their last pass — the aggregate, for the series.

    Read from the trace rather than counted in the module, so the number a dashboard shows and
    the answer a sovereign gets are the same fact. This is a READER, which is the one thing
    this graph is for; it is not the planner consulting its own past thinking.
    """
    from agent.store import bindings

    rows = bindings(query(f"""
SELECT ?verdict (COUNT(?d) AS ?n) WHERE {{ GRAPH <{DELIBERATION_GRAPH}> {{
  ?d a <{KERNEL}Deliberation> ; <{KERNEL}verdict> ?verdict }} }} GROUP BY ?verdict"""))
    return {r["verdict"]: int(r["n"]) for r in rows}
