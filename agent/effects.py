"""What a lever would make true — reading the rules the packages ship, and running one.

A means states its effect as a SHACL-AF `sh:SPARQLRule`: `sh:condition` naming the shape that
must hold before it may run, `sh:construct` holding the query that yields the triples applying
it would ADD, and `ag:retracts` — ours, because the standard has none — holding the query that
yields the triples it REMOVES. The rules live in the effect graph, loaded from every package's
`effects.ttl` at genesis, so a model or a sovereign can read the whole tool list without a
second format existing anywhere.

**The vocabulary is SHACL-AF's; the engine is not.** pySHACL will execute `sh:SPARQLRule`, and
we measured that it does — but only with `inplace=True`, because its rules are forward-chaining
inference: apply everything applicable, to a fixpoint, mutating the graph. A plan step is one
rule against one hypothesis, which is the opposite shape, so driving that machinery would mean
fighting it. A stored `sh:construct` is just a query, and this project already has an engine
that runs queries. See knowledge/decisions/a-plan-is-a-path-of-graph-diffs.md, "take the
vocabulary and not necessarily the engine".

WHAT IS NOT HERE is the possible world and the search that would use it — that is #239. This
reads a rule and runs it, and the one caller today is the actuator asking what its own dose
will do, so that the number it predicts and the number it later verifies against cannot be two
numbers.
"""

from __future__ import annotations

import logging

from .ontology import EFFECTS_GRAPH
from .store import bindings

log = logging.getLogger("effects")

#  Which rule belongs to which means, and the two queries it carries. Asked of the effect graph
#  by NAME, because that graph is the one place rules live and a rule for a means nobody loaded
#  is a rule nothing will ever ask for.
_RULE_Q = """
SELECT ?rule ?construct ?retracts ?lands ?confirmed WHERE { GRAPH <%s> {
  ?rule <http://example.org/agora#effectOf> <%s> ;
        <http://www.w3.org/ns/shacl#construct> ?construct .
  OPTIONAL { ?rule <http://example.org/agora#retracts> ?retracts }
  OPTIONAL { ?rule <http://example.org/agora#landsAfter> ?lands }
  OPTIONAL { ?rule <http://example.org/agora#confirmedBy> ?confirmed } } } LIMIT 1"""


def rule_for(store, means: str) -> dict | None:
    """The effect rule a means carries, or None where the package shipped no `effects.ttl`.

    None is an ordinary answer and every caller must take it: most means have no effect stated
    yet, and a lever whose consequences nobody has written down is still a lever that works —
    it is only one a planner cannot reason about.
    """
    rows = bindings(store.query(_RULE_Q % (EFFECTS_GRAPH, means)))
    return rows[0] if rows else None


def apply(store, means: str, **bind) -> tuple[list, list]:
    """Run one means' effect: `(added, retracted)`, as triples, against nothing.

    Nothing is written. Both halves are CONSTRUCTs, so this asks the store two questions and
    returns their answers — which is what makes a possible world computable as
    `(beliefs - retracted) + added` without a single mutation anywhere. `ag:retracts` exists
    because SHACL-AF has no deletion, and it is not optional: the sensed graph upserts one
    observation node per (subject, property), so an effect predicting a reading that did not
    retract the node it replaces would leave two results on one node — and a shape asking
    whether ANY reading sits past an edge would then answer about a reading the plan just
    replaced.

    `bind` fills the rule's placeholders the way every other shipped query here is filled:
    `$me`, `$subject`, `$property`, `$litres`. Substitution rather than SPARQL's own binding
    because the text is a literal in the graph and the engine takes a string.
    """
    rule = rule_for(store, means)
    if rule is None:
        return [], []
    return (_run(store, rule.get("construct"), bind),
            _run(store, rule.get("retracts"), bind))


def lands_after(store, means: str, **bind) -> float | None:
    """How long after this act the world change completes, in seconds — asked, never computed.

    The figure a waiter needs and the figure a planner needs, and they must be the same one.
    `cmd.seconds + doseGraceS` is a claim about when the world should have answered; an agent
    that holds a second copy plans against one timeline and verifies against another, and the
    disagreement surfaces as a false UNMET that looks like a device lying. That is #238's
    argument for magnitude, one axis over — see `ag:landsAfter`.

    None where the rule declines: no effect stated for this means, no timing on the effect, or
    premises that do not hold (an agent whose lever does not reach this subject). Every caller
    must take None and keep whatever it did before, because a lever with no stated timing is
    still a lever that works — it is only one nobody can wait for precisely.
    """
    rule = rule_for(store, means)
    if rule is None or not rule.get("lands"):
        return None
    rows = _select(store, rule["lands"], bind)
    if not rows or rows[0].get("seconds") is None:
        return None
    return float(rows[0]["seconds"])


def confirmed_by(store, means: str) -> str | None:
    """By which route this effect becomes knowable — construction, report, observation, or not
    at all. Static, unlike the timing: it is a property of the MEANS, where whether a given
    agent can take that route is a fact about its wiring."""
    rule = rule_for(store, means)
    return rule.get("confirmed") if rule else None


def _select(store, text: str, bind: dict) -> list:
    """A rule's query that answers with BINDINGS rather than a graph. Same substitution, same
    swallowing of a rule that will not run: a package's broken query must not take an agent
    down, and what is lost is precision about waiting rather than the ability to act."""
    for name, value in bind.items():
        text = text.replace(f"${name}", value if isinstance(value, str) else repr(value))
    try:
        return bindings(store.query(text))
    except Exception as exc:
        log.error("timing query for this means would not run: %s", exc)
        return []


def _run(store, text: str | None, bind: dict) -> list:
    if not text:
        return []
    for name, value in bind.items():
        text = text.replace(f"${name}", value if isinstance(value, str) else repr(value))
    try:
        return list(store.construct(text))
    except Exception as exc:
        #  A rule that will not run is a package's bug and must not take an agent down: the
        #  lever still works, and what is lost is the ability to reason about it in advance.
        log.error("effect rule for this means would not run: %s", exc)
        return []
