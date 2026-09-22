"""What a lever would make true — reading the rules the packages ship, and running one.

**FIVE FUNCTIONS OVER (store, action), and the store is whichever dataset the question is
being asked ABOUT.** `rule_for` is the action's row; `adds` is what taking it makes true here;
`retraction` is the act that takes away what it replaces; `cost_of` is what it is scored to
spend; `lands_after` is how long until it lands. Each is handed the engine, the action's IRI
and the graphs the question is over — an actuator passes its own belief base, a search passes
the imaginarium where `$state` names the world a node's path reached, and nothing here
distinguishes them.

An action states its effect in two halves that are not the same KIND of thing. `sh:construct`
is SHACL-AF's and holds a query yielding the triples applying it would ADD, asked of the world
the step is taken in. `orexis:retracts` is ours, because the standard has none, and holds a
`DELETE … WHERE` naming `GRAPH $state` — an ACT, run against the world the step makes. The
asymmetry is the domain's: what an effect adds is concrete, and what it takes away is whatever
is standing in that place, which nobody can name in advance. The actions live in the action graph, loaded from every package's
`actions.ttl` at genesis, so a model or a sovereign can read the whole tool list without a
second format existing anywhere.

**The vocabulary is SHACL-AF's; the engine is not.** pySHACL will execute `sh:SPARQLRule`, and
we measured that it does — but only with `inplace=True`, because its rules are forward-chaining
inference: apply everything applicable, to a fixpoint, mutating the graph. A plan step is one
rule against one hypothesis, which is the opposite shape, so driving that machinery would mean
fighting it. A stored `sh:construct` is just a query, and this project already has an engine
that runs queries. See knowledge/decisions/a-plan-is-a-path-of-graph-diffs.md, "take the
vocabulary and not necessarily the engine".

**WHAT IS HERE IS WHAT CAN BE ASKED, AND NOTHING THAT WRITES.** Three questions over
`(store, action)`: `rule_for` is the action's row, memoised because a template costs more to
re-read than a pass can afford and can change only by a write a pass does not make;
`cost_of` is what taking it would spend; `lands_after` is how long until it lands. The ACT —
running the effect into a world — is `apply_effects.py` beside this, because the order its two
halves go in and the graph each is bound to are facts about what an effect IS rather than
about what can be read off an action.

The two callers ask about different worlds: an actuator asks about the one it is standing in,
so that the number it predicts and the number it later verifies against cannot be two numbers,
and a planner asks about one nobody is in yet. Which of them a rule is answering about is
`store`, and nothing else here.
"""

from __future__ import annotations

import logging

from orexis.agent import clock
from orexis.agent.ontology import KNOWN, PUBLIC
from orexis.agent.store import (bindings, bind as bind_text, construct, graphs_of, query,
                                           remember)

log = logging.getLogger("effects")

#  The action's effect texts, read off public knowledge like everything else — the actions
#  graph is public and the store's default graph merges the public graphs, so no `GRAPH`
#  clause names it (AGENTS.md: never wrap GRAPH around a SELECT). `?rule` is bound by
#  SUBSTITUTION (#500), the engine's own parameter, projected. An action with no construct
#  states no effect and is not returned.
#  `STR(?takes)` because GROUP_CONCAT over an IRI binds nothing in this engine.
_RULE_Q = """
SELECT ?rule ?construct ?available ?retracts ?lands ?costs (GROUP_CONCAT(DISTINCT STR(?p); separator=" ") AS ?takes) WHERE {
  ?rule a orexis:Action ; sh:construct ?construct .
  OPTIONAL { ?rule orexis:takes ?p }
  OPTIONAL { ?rule orexis:available ?available }
  OPTIONAL { ?rule orexis:retracts ?retracts }
  OPTIONAL { ?rule orexis:landsAfter ?lands }
  OPTIONAL { ?rule orexis:costs ?costs }
} GROUP BY ?rule ?construct ?available ?retracts ?lands ?costs LIMIT 1"""


def rule_for(store, action: str, memo=None) -> dict | None:
    """The effect rule an action carries, or None for an action an event adopts.

    None is the answer for an action that states neither text — the market's Presenting,
    adopted by an event and never on a menu — and for nothing else: an action with a
    precondition states an effect, or the gate (`deliberable`, in `onboarding/validate.py`)
    refuses the world before an agent runs (#506).
    """
    #  REMEMBERED FOR THE PASS (#552): the text is public knowledge and only a write can
    #  change it, yet it was fetched on every fork by `apply`, `cost_of` and `lands_after`
    #  each — three of the seven store calls a fork cost, answering the same thing every time.
    #  The memo is the caller's, because the caller is what knows how long its answers hold.
    def fetch():
        rows = bindings(query(store, _RULE_Q, graphs_of(store, PUBLIC), {"rule": action}))
        return rows[0] if rows else None
    return remember(memo, ("rule", action), fetch)


def lands_after(store, action: str, graphs=None, *, memo=None, **bind) -> float | None:
    """How long after this act the world change completes, in seconds — asked, never computed.

    The figure a waiter needs and the figure a planner needs, and they must be the same one.
    `cmd.seconds + doseGraceS` is a claim about when the world should have answered; an agent
    that holds a second copy plans against one timeline and verifies against another, and the
    disagreement surfaces as a false UNMET that looks like a device lying. That is #238's
    argument for magnitude, one axis over — see `orexis:landsAfter`.

    None where the rule declines: no effect stated for this action, no timing on the effect, or
    premises that do not hold (an agent whose lever does not reach this subject). Every caller
    must take None and keep whatever it did before, because a lever with no stated timing is
    still a lever that works — it is only one nobody can wait for precisely.
    """
    rule = rule_for(store, action, memo)
    if rule is None or not rule.get("lands"):
        return None
    rows = _select(store, rule["lands"], bind, graphs)
    if not rows or rows[0]["seconds"] is None:
        return None
    return float(rows[0]["seconds"].value)


def cost_of(store, action: str, graphs=None, *, memo=None, **bind) -> float | None:
    """What taking this act would spend, in the wallet's unit — asked, never computed.

    `orexis:landsAfter`'s twin (#466): the owning package declares the SELECT, the same
    substitution fills it, and it travels the rules' own store door so a cost read off a
    record binds exactly as a landing time does. None where the rule declines — no cost
    declared, or premises that do not hold — and every caller must read None as FREE, the
    statement an omitted declaration makes.
    """
    rule = rule_for(store, action, memo)
    if rule is None or not rule.get("costs"):
        return None
    rows = _select(store, rule["costs"], bind, graphs)
    if not rows or rows[0]["cost"] is None:
        return None
    return float(rows[0]["cost"].value)


def _select(store, text: str, bind: dict, graphs=None) -> list:
    """A rule's query that answers with BINDINGS rather than a graph. Same substitution, same
    swallowing of a rule that will not run: a package's broken query must not take an agent
    down, and what is lost is precision about waiting rather than the ability to act.

    THROUGH THE RULES' OWN DOOR (`construct`), and that is a correction (#472): a rule's
    SELECT must see exactly what its CONSTRUCT sees — public knowledge plus this agent's own
    records — and a read of public alone meant a landing time computed
    from an obligation RECORD (the ledger's claim and amount) bound nothing and every
    serve landed "immediately", silently. The rows come back as engine solutions rather
    than JSON bindings; the one consumer reads its column accordingly."""
    try:
        return construct(store, bind_text(text, **bind), over(store, graphs))
    except Exception as exc:
        log.error("timing query for this means would not run: %s", exc)
        return []


def over(store, graphs) -> list[str]:
    """What a rule is answered over: the list the caller built — the search, for an imagined
    world at an instant — or, where none is handed in, the kinds a rule reads as they hold
    now: an actuator standing in the present, a test. Stated here, once, for the rules this
    module runs; no store decides it."""
    return graphs if graphs is not None else graphs_of(store, *KNOWN, at=clock.now())


