"""What a lever would make true — reading the rules the packages ship, and running one.

An action states its effect in SHACL-AF's words: `sh:construct` holding the query that yields
the triples applying it would ADD, and `orexis:retracts` — ours, because the standard has none — holding the query that
yields the triples it REMOVES. The actions live in the action graph, loaded from every package's
`actions.ttl` at genesis, so a model or a sovereign can read the whole tool list without a
second format existing anywhere.

**The vocabulary is SHACL-AF's; the engine is not.** pySHACL will execute `sh:SPARQLRule`, and
we measured that it does — but only with `inplace=True`, because its rules are forward-chaining
inference: apply everything applicable, to a fixpoint, mutating the graph. A plan step is one
rule against one hypothesis, which is the opposite shape, so driving that machinery would mean
fighting it. A stored `sh:construct` is just a query, and this project already has an engine
that runs queries. See knowledge/decisions/a-plan-is-a-path-of-graph-diffs.md, "take the
vocabulary and not necessarily the engine".

WHAT IS NOT HERE is the SEARCH — that is `packages/capability/deliberation`. This reads a rule
and runs it against a dataset it is handed, and the two callers ask about different worlds: the
actuator asks about the one it is standing in, so that the number it predicts and the number it
later verifies against cannot be two numbers, and the planner asks about one nobody is in yet.
Which of them a rule is answering about is `store`, and nothing else here.
"""

from __future__ import annotations

import logging

import pyoxigraph as ox
import rdflib

from orexis_agent_progression.ontology import ACTIONS_GRAPH
from orexis_agent_progression.store import bindings

log = logging.getLogger("effects")

#  Which ACTION carries this action, and the two queries it carries as its effect. Asked of the
#  action graph by NAME, because that graph is the one place actions live and an action for a
#  means nobody loaded is one nothing will ever ask for. An action with no construct states no
#  effect and is not returned — the gate refuses a world whose menu offers one.
_RULE_Q = """
SELECT ?rule ?construct ?retracts ?lands WHERE { GRAPH <%s> {
  BIND(<%s> AS ?rule)
  ?rule a <http://example.org/orexis#Action> ;
        <http://www.w3.org/ns/shacl#construct> ?construct .
  OPTIONAL { ?rule <http://example.org/orexis#retracts> ?retracts }
  OPTIONAL { ?rule <http://example.org/orexis#landsAfter> ?lands }
  } } LIMIT 1"""


def rule_for(store, action: str) -> dict | None:
    """The effect rule a means carries, or None where the package shipped no `effects.ttl`.

    None is an ordinary answer and every caller must take it: most means have no effect stated
    yet, and a lever whose consequences nobody has written down is still a lever that works —
    it is only one a planner cannot reason about.
    """
    rows = bindings(store.query(_RULE_Q % (ACTIONS_GRAPH, action)))
    return rows[0] if rows else None


def apply(store, action: str, **bind) -> tuple[list, list]:
    """Run one means' effect: `(added, retracted)`, as triples, against nothing.

    **`store` is whichever dataset the question is being asked ABOUT, and that is the whole of
    what #254 changed here.** An actuator asks about the world it is standing in and passes its
    own belief base; a planner asks about a world nobody is in yet and passes its
    `imaginarium.Imaginarium`, where `$state` names the readings that node's path
    reached. Nothing in this file distinguishes them, and nothing should: a rule already asks
    about *whichever graph it is pointed at*, and being bound to the store was an accident of
    what the caller happened to hand over. The retraction is the half that made it visible —
    re-asked of the belief base, it finds the observation still on disk and never sees what the
    previous step added, so `(beliefs − retracts) + adds` was true for the first step and false
    for every step after it. See
    knowledge/decisions/a-rule-is-asked-about-a-world-not-about-a-store.md.

    Nothing is written. Both halves are CONSTRUCTs, so this asks the dataset two questions and
    returns their answers — which is what makes a possible world computable as
    `(beliefs - retracted) + added` without a single mutation anywhere. `orexis:retracts` exists
    because SHACL-AF has no deletion, and it is not optional: the sensed graph upserts one
    observation node per (subject, property), so an effect predicting a reading that did not
    retract the node it replaces would leave two results on one node — and a shape asking
    whether ANY reading sits past an edge would then answer about a reading the plan just
    replaced.

    `bind` fills the rule's placeholders the way every other shipped query here is filled:
    `$me`, `$subject`, `$property`, `$litres`. Substitution rather than SPARQL's own binding
    because the text is a literal in the graph and the engine takes a string.
    """
    rule = rule_for(store, action)
    if rule is None:
        return [], []
    return (_run(store, rule.get("construct"), bind),
            _run(store, rule.get("retracts"), bind))


def world_after(base, store, action: str, /, **bind):
    """The world as it WOULD be, had this means been taken: `(base − retracted) + added`.

    The two halves are separately callable and the search calls them separately, because it
    needs the diff twice: once to fork the node's readings inside the imaginarium, where the
    NEXT step's rule will read them, and once to build the flat rdflib view pySHACL validates.
    This composed form states the equation, and is what a caller asking about a single step
    wants.

    The three are POSITIONAL-ONLY, and that is load-bearing rather than tidy: everything after
    them is a binding for the rule, and a rule is free to have a placeholder called `$base` —
    Actuate's does, since #247 made the reading it predicts from a parameter. Without the `/`
    the caller's world and the rule's baseline collide on the name, which Python reports as
    "multiple values for argument" and which would otherwise have been fixed by renaming one of
    them and waiting for the next collision.

    A new graph every time and nothing written anywhere, which is what makes a hypothesis safe
    to hold: the store never learns that anyone imagined this. Possible worlds are computed and
    dropped for the reason affordance rows are never stored — what is kept is premises, and a
    world is a conclusion from beliefs plus an effect, so keeping one would be keeping something
    that can outlive what it was concluded from.

    Retraction before addition, and the order is not arbitrary. The sensed graph upserts one
    observation node per (subject, property), so an effect that predicts a reading retracts the
    node it replaces and then adds its own — done the other way round, the addition would be
    removed by the retraction that was meant to precede it, and the possible world would come
    back holding neither reading.
    """
    added, retracted = apply(store, action, **bind)
    return applied(base, added, retracted)


def applied(base, added, retracted):
    """One step's diff, as an rdflib graph: `(base − retracted) + added`, base untouched."""
    world = rdflib.Graph()
    for triple in base:
        world.add(triple)
    for triple in retracted:
        world.remove(_triple(triple))
    for triple in added:
        world.add(_triple(triple))
    return world


def _triple(t):
    """One of the store's triples as the three terms rdflib wants.

    Term by term, and NOT through `str()`. A pyoxigraph term stringifies to its N-Triples form
    — `<http://…>` with the angle brackets, a literal with its quotes and datatype — so a
    conversion that went through text would hand rdflib a URIRef whose value included the
    brackets. It would compare unequal to the same IRI everywhere else, silently: no exception,
    no empty result, just a possible world whose triples never match the ones they replace.
    The same trap caught the effect reader itself in #238, from the other direction.
    """
    return tuple(_term(x) for x in (t[0], t[1], t[2]))


def _term(x):
    """A pyoxigraph term as an rdflib one, keeping what makes it that term.

    A literal's datatype and language are not decoration: a predicted reading compared against
    a shape's `sh:minExclusive` is a decimal against a decimal, and the same digits typed as a
    string would simply fail to match — which reads exactly like a plan that does not work.
    """
    if isinstance(x, ox.NamedNode):
        return rdflib.URIRef(x.value)
    if isinstance(x, ox.BlankNode):
        return rdflib.BNode(x.value)
    if isinstance(x, ox.Literal):
        return rdflib.Literal(x.value, lang=x.language,
                              datatype=rdflib.URIRef(x.datatype.value) if x.datatype else None)
    return x


def lands_after(store, action: str, **bind) -> float | None:
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
    rule = rule_for(store, action)
    if rule is None or not rule.get("lands"):
        return None
    rows = _select(store, rule["lands"], bind)
    if not rows or rows[0].get("seconds") is None:
        return None
    return float(rows[0]["seconds"])


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
