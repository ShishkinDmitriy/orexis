"""What the planner considered, written down so somebody can read it.

A `Plan` carries the outcome, the steps and the urgency on both sides, and every bit of it used
to die in-process as one log line. The material was never missing — the exposure was, and it
could not be added from outside: pyoxigraph holds an exclusive lock on the belief base, so
nothing else can open the store to re-run the search and see what it saw. That is the same fact
`orexis-ask` exists for, arriving at the planner.

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

import pyoxigraph as ox

from orexis_agent_progression.ontology import DELIBERATION_GRAPH

log = logging.getLogger("trace")

KERNEL = "http://example.org/orexis#"

#  Why a candidate did not become the plan — the same six-answers-instead-of-two argument the
#  pass's own outcome makes, one scale down. "Worse" and "already seen" are different findings:
#  the first says this lever does not help from here, the second says the search has been here
#  before and expanding it again would spend the depth budget going nowhere.
MET = "meets the desire"
BETTER = "better than standing still"
WORSE = "no better than standing still"
SEEN = "a world already reached"
UNSIMULATED = "could not be simulated"
LATE = "lands after the want expires"
FORBIDDEN = "newly enters a state the society refuses"
COSTLY = "costs more than a plan already found"
SPENT = "the budget was spent before this was simulated"
IRRELEVANT = "touches nothing this want reads"
REFUSED = "refused below lately — the level beneath found no way to keep its promise"
UNAVAILABLE = "a remembered step is not on the menu here"
INAPPLICABLE = "a remembered plan's precondition does not hold here"

#  HOW A WANT WAS JUDGED in every world the pass weighed (#502) — the road, always said, and
#  the text where the road is a text. The compiled select lives nowhere else: computed once per
#  pass by the rule that what the interpreter already knows is never asserted, which is right
#  for the store and wrong for the person asking "why did this want read as unmet" — so the
#  trace, the record's one sanctioned exception, shows it.
COMPILED = "the select compiled from its shape"
AUTHORED = "the pattern it authors"
RECORD = "the record of what was discharged"
MEASURE = "a module's measure"
UNJUDGED = "nothing — a remembered plan was adopted on its precondition"

#  What each verdict is called in the series, declared HERE beside the verdict it names so the
#  two cannot drift — the same one-definition-two-readers argument `gap.rq` and `urgency` make.
#  The prose is what a sovereign reads in the trace; these are what a dashboard can put on an
#  axis, and a field name that was a sentence would be neither.
FIELD = {
    MET: "met",
    BETTER: "better",
    WORSE: "worse",
    SEEN: "cycles",
    UNSIMULATED: "unsimulated",
    LATE: "late",
    FORBIDDEN: "forbidden",
    COSTLY: "costly",
    SPENT: "spent",
    IRRELEVANT: "irrelevant",
    REFUSED: "refused",
    UNAVAILABLE: "unavailable",
    INAPPLICABLE: "inapplicable",
}


def _quoted(text: str) -> str:
    return '"%s"' % text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def _uri(agent_id: str, desire_uri: str) -> str:
    """One node per (agent, desire), so planning the same desire twice replaces rather than adds.

    Minted from the desire's own IRI on the channel precedent — a derived instance computed from
    a given string, so a second pass lands on the same node and the DELETE below finds it.

    DETERMINISTIC ACROSS PROCESSES, which `hash()` is not: Python salts it per interpreter, so
    a node minted in one run would be unfindable in the next, the clear would match nothing,
    and every restart would orphan a trace that outlived the pass it described — the one thing
    this graph must never do. The desire's local name is already unique per agent (a want is
    minted per agent and property), and quoting the whole IRI covers a desire shaped otherwise.
    """
    tail = desire_uri.rsplit("#", 1)[-1] if "#" in desire_uri else quote(desire_uri, safe="")
    return f"{KERNEL}deliberation.{agent_id}.{quote(tail, safe='')}"


def clear(store, agent_id: str, desire_uri: str) -> None:
    """Drop the previous pass for this desire, at the START of the next one.

    At the start and not the end, which is the difference between a graph that holds one pass
    and a graph that holds two. Clearing when a pass finishes would leave the trace of a desire
    whose planning crashed sitting beside beliefs it can contradict — and the crash is exactly
    the case somebody would be reading the trace to understand.
    """
    node = _uri(agent_id, desire_uri)
    store.update(f"""
        DELETE {{ GRAPH <{DELIBERATION_GRAPH}> {{ ?c ?cp ?co . <{node}> ?p ?o }} }}
        WHERE  {{ GRAPH <{DELIBERATION_GRAPH}> {{
                    <{node}> ?p ?o .
                    OPTIONAL {{ <{node}> deliberation:considered ?c . ?c ?cp ?co }} }} }}""")


def write(store, agent_id: str, desire, plan, considered, stands_at: float,
          took_s: float = 0.0, judged: tuple[str, str | None] = (UNJUDGED, None)) -> None:
    """Record one pass: what was weighed, what each would have reached, and what was taken.

    Never raises. A planner that fell over because its debugging aid did would be a poor trade
    for being able to watch it — so a failure here is logged and the decision stands, which is
    the same posture `reporting` takes towards the series store.
    """
    try:
        _write(store, agent_id, desire, plan, considered, stands_at, took_s, judged)
    except Exception as exc:                      # noqa: BLE001 - see the docstring
        log.warning("could not record what was considered: %s", exc)


def _write(store, agent_id: str, desire, plan, considered, stands_at: float,
           took_s: float, judged: tuple[str, str | None]) -> None:
    node = _uri(agent_id, desire.uri)
    #  The candidate the plan came THROUGH — a remembered route walked as one candidate is
    #  named as the route, not as the first of its steps (#469).
    chosen = getattr(plan, "origin", None) or (plan.steps[0].action if plan.steps else None)
    rows = []
    for i, entry in enumerate(considered):
        depth, row, urgency, verdict = entry[:4]
        #  WHAT WAS MISSING, where the verdict is that a remembered plan's precondition does
        #  not hold (#551): the fact, as the signature states it, so the reader is told
        #  which fact and not only that one was.
        missing = entry[4] if len(entry) > 4 and entry[4] is not None else None
        candidate = f"{node}.{i}"
        reached = "" if urgency is None else \
            f'        deliberation:wouldReach {urgency:.6f} ;\n'
        absent = "" if missing is None else \
            f'        deliberation:missing {_quoted(repr(missing))} ;\n'
        rows.append(
            f'    <{node}> deliberation:considered <{candidate}> .\n'
            f'    <{candidate}> a deliberation:Candidate ;\n'
            f'        deliberation:wouldTake <{row.action}> ;\n'
            f'        progression:through <{row.via}> ;\n'
            f'        deliberation:atDepth {depth} ;\n'
            f'{reached}{absent}'
            f'        deliberation:verdict "{verdict}" .\n')
    #  The chosen candidate is named rather than duplicated: a reader joining `deliberation:chose` to the
    #  candidate gets its depth, its lever and the world it would reach, and the trace never
    #  says the same number twice in two places where they could drift apart.
    took = ""
    if chosen is not None:
        for i, entry in enumerate(considered):
            if entry[1].action == chosen:
                took = f'        deliberation:chose <{node}.{i}> ;\n'
                break
    #  The select as a LITERAL, escaped by the engine's own writer: a compiled text carries
    #  quotes, backslashes and newlines, and a hand-quoted f-string would be the injection the
    #  binder exists to refuse (#500).
    road, text = judged
    by = "" if text is None else \
        f'        deliberation:judgedBy {ox.Literal(text)} ;\n'
    store.update(f"""INSERT DATA {{ GRAPH <{DELIBERATION_GRAPH}> {{
    <{node}> a deliberation:Deliberation ;
        deliberation:deliberatedOn <{desire.uri}> ;
        deliberation:verdict "{plan.outcome}" ;
        deliberation:judgedThrough {ox.Literal(road)} ;
{by}        deliberation:standsAt {stands_at:.6f} ;
        deliberation:tookSeconds {took_s:.6f} ;
{took}        deliberation:asOf "{datetime.now(timezone.utc).isoformat()}"^^xsd:dateTime .
{"".join(rows)}}} }}""")


def outcomes(query) -> dict[str, int]:
    """How many desires ended in each verdict on their last pass — the aggregate, for the series.

    Read from the trace rather than counted in the module, so the number a dashboard shows and
    the answer a sovereign gets are the same fact. This is a READER, which is the one thing
    this graph is for; it is not the planner consulting its own past thinking.
    """
    from orexis_agent_progression.store import bindings

    rows = bindings(query(f"""
SELECT ?verdict (COUNT(?d) AS ?n) WHERE {{ GRAPH <{DELIBERATION_GRAPH}> {{
  ?d a deliberation:Deliberation ; deliberation:verdict ?verdict }} }} GROUP BY ?verdict"""))
    return {r["verdict"]: int(r["n"]) for r in rows}


def effort(query) -> dict[str, float]:
    """What the last pass over every desire COST, and what the search did with each lever.

    Read from the trace for the same reason `outcomes` is: the pass already happened, and
    re-running it to gather figures would double the cost the figures report. Everything here
    is a projection of what was written down a moment ago.

    Each field is diagnostic of something recorded and otherwise invisible, which is the whole
    reason to have them rather than a general count:

    - `seconds` is what a reporting tick's planning costs, summed over desires. `series()` calls
      `pursued()`, which re-plans every desire, so this is the price of being asked what you want
      — and if it dominates an agent's cost then the instrumentation is the workload.
    - `deepest` is how many steps the longest path considered had. **Pinned at 1 was the
      signature of two recorded limits at once** — a rule's CONSTRUCTs running against the
      store rather than the world (#254), and a cycle signature that was only the desire's own
      value, so a step that moved nothing else was discarded as somewhere already reached
      (#258). Both are closed; if it pins again, look at what the menu offers before what the
      machinery allows.
    - `worlds` is how many simulations were built: the cost driver, and what to divide
      `seconds` by before blaming the shape checker.
    - `cycles` climbing while `deepest` stays at 1 says the search keeps arriving back where it
      started rather than being unable to go further.
    - `unsimulated` counts levers whose rule raised — an error, not a shrug.
    """
    from orexis_agent_progression.store import bindings

    #  `?c a deliberation:Candidate` is load-bearing, not tidiness: `deliberation:verdict` is deliberately declared
    #  with NO domain because a pass and a candidate both carry one, so a query that forgot to
    #  say which it meant would count the six pass outcomes among the five candidate ones.
    counted = bindings(query(f"""
SELECT ?verdict (COUNT(?c) AS ?n) WHERE {{ GRAPH <{DELIBERATION_GRAPH}> {{
  ?c a deliberation:Candidate ; deliberation:verdict ?verdict }} }} GROUP BY ?verdict"""))

    out = {name: 0.0 for name in FIELD.values()}
    for row in counted:
        if (name := FIELD.get(row["verdict"])) is not None:
            out[name] = float(row["n"])

    #  ONE query for the four scalars rather than four, and the reason is measured: this runs
    #  inside `series()` on every reporting tick, and four separate asks cost 15ms of the 430ms
    #  a tick already spends — a debugging aid taking three per cent of the thing it observes.
    #  A union of aggregate subqueries asks once and costs a third of that.
    scalars = bindings(query(f"""
SELECT ?k ?v WHERE {{
  {{ SELECT ("seconds" AS ?k) (SUM(?s) AS ?v)
     WHERE {{ GRAPH <{DELIBERATION_GRAPH}> {{ ?d deliberation:tookSeconds ?s }} }} }}
  UNION
  {{ SELECT ("worlds" AS ?k) (COUNT(?c) AS ?v)
     WHERE {{ GRAPH <{DELIBERATION_GRAPH}> {{ ?c deliberation:wouldReach ?u }} }} }}
  UNION
  {{ SELECT ("deepest" AS ?k) (MAX(?depth) AS ?v)
     WHERE {{ GRAPH <{DELIBERATION_GRAPH}> {{ ?c deliberation:atDepth ?depth }} }} }}
}}"""))
    got = {r["k"]: r["v"] for r in scalars if r.get("v") not in (None, "")}

    out["seconds"] = float(got.get("seconds", 0.0))
    #  A world was BUILT wherever an urgency was reached — the one candidate kind that never
    #  has one is the lever whose rule raised, which is counted as `unsimulated` above.
    out["worlds"] = float(got.get("worlds", 0.0))
    #  `atDepth` is the loop's own counter and starts at zero, so a candidate at depth 0 is a
    #  ONE-step path. Reported as steps, because "depth 0" reads as "no planning happened" to
    #  everyone except the person who wrote the loop, and a pass that weighed nothing reports
    #  0 rather than 1 — no path was considered at all.
    out["deepest"] = float(got["deepest"]) + 1.0 if "deepest" in got else 0.0
    return out
