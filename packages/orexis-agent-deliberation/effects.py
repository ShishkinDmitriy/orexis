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

import functools
import logging
import re

import pyoxigraph as ox
import rdflib
from rdflib import URIRef, Variable
from rdflib.plugins.sparql.algebra import translateQuery
from rdflib.plugins.sparql.parser import parseQuery
from rdflib.plugins.sparql.parserutils import CompValue

from orexis_agent_progression.ontology import STATE_GRAPH
from orexis_agent_progression.store import PREFIXES, Raw, bindings, bind as bind_text
from .relevance import _TOKEN, parseable

log = logging.getLogger("effects")

#  The action's effect texts, read off public knowledge like everything else — the actions
#  graph is public and the store's default graph merges the public graphs, so no `GRAPH`
#  clause names it (AGENTS.md: never wrap GRAPH around a SELECT). `?rule` is bound by
#  SUBSTITUTION (#500), the engine's own parameter, projected. An action with no construct
#  states no effect and is not returned.
_RULE_Q = """
SELECT ?rule ?construct ?available ?retracts ?lands ?costs WHERE {
  ?rule a orexis:Action ; sh:construct ?construct .
  OPTIONAL { ?rule orexis:available ?available }
  OPTIONAL { ?rule orexis:retracts ?retracts }
  OPTIONAL { ?rule orexis:landsAfter ?lands }
  OPTIONAL { ?rule orexis:costs ?costs }
} LIMIT 1"""


_DRIFTS_Q = """
SELECT ?drift ?construct ?retracts WHERE {
  ?drift a orexis:Drift ; sh:construct ?construct .
  OPTIONAL { ?drift orexis:retracts ?retracts }
}"""


def drifts_of(store) -> list[dict]:
    """Every drift the loaded packages declare — what the world does while nobody acts.

    Read off public knowledge like an action's effect, and REMEMBERED per store for the same
    reason: it is a schema only a write can change, and a pass asks it at every fork.
    """
    def fetch():
        return bindings(store.query(_DRIFTS_Q))
    return store.remember("drifts", fetch)


def drift(store, rule: dict, elapsed: float, when=None, **bind) -> tuple[list, list]:
    """What one drift makes true over `elapsed` seconds — `(added, retracted)`, as triples.

    The same shape as `apply` and deliberately: a drift is an effect with nobody taking it, so
    the machinery that computes what a lever would make true computes what the world makes true
    unaided. What differs is the parameter — `$elapsed`, the seconds the world has had — and
    that nothing here asks whether it is AVAILABLE, because nobody chooses for the world.
    """
    bind = {**bind, "elapsed": elapsed}
    return (_run(store, rule.get("construct"), bind, when),
            _run(store, rule.get("retracts"), bind, when))


def rule_for(store, action: str) -> dict | None:
    """The effect rule an action carries, or None for an action an event adopts.

    None is the answer for an action that states neither text — the market's Presenting,
    adopted by an event and never on a menu — and for nothing else: an action with a
    precondition states an effect, or the gate (`deliberable`, in `onboarding/validate.py`)
    refuses the world before an agent runs (#506).
    """
    #  REMEMBERED PER STORE (#552): the text is public knowledge and only a write can change
    #  it, yet it was fetched on every fork by `apply`, `cost_of` and `lands_after` each —
    #  three of the seven store calls a fork cost, answering the same thing every time.
    def fetch():
        rows = bindings(store.query(_RULE_Q, {"rule": action}))
        return rows[0] if rows else None
    return store.remember(("rule", action), fetch)


def apply(store, action: str, when=None, **bind) -> tuple[list, list]:
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
    #  `$state` DEFAULTS TO THE AGENT'S OWN READINGS (#500): an actuator asking about the
    #  world it stands in never named the graph, and the token it left in the text used to
    #  parse as a VARIABLE — `GRAPH $state` matching every graph in the store at once,
    #  silently. The binder refuses a leftover now, so the caller that means "here" gets
    #  here, and only a planner names another world.
    bind.setdefault("state", STATE_GRAPH)
    return (_run(store, rule.get("construct"), bind, when),
            _run(store, rule.get("retracts"), bind, when))


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
        #  A plain string stays PLAIN (found by #257's world): pyoxigraph reports xsd:string
        #  on every simple literal, and rdflib holds a plain Literal and an explicitly
        #  string-typed one as DISTINCT terms - so a triple arriving once through a
        #  serialisation parse and once through this constructor landed twice, and every
        #  asserted string in the world gate's two-road join was silently doubled. Invisible
        #  until a shape counted one: hanoi's avoided-pattern node was the first focus any
        #  maxCount here ever had.
        dt = x.datatype.value if x.datatype else None
        if dt == "http://www.w3.org/2001/XMLSchema#string" and not x.language:
            dt = None
        return rdflib.Literal(x.value, lang=x.language,
                              datatype=rdflib.URIRef(dt) if dt else None)
    return x


def lands_after(store, action: str, when=None, **bind) -> float | None:
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
    bind.setdefault("state", STATE_GRAPH)
    rule = rule_for(store, action)
    if rule is None or not rule.get("lands"):
        return None
    rows = _select(store, rule["lands"], bind, when)
    if not rows or rows[0]["seconds"] is None:
        return None
    return float(rows[0]["seconds"].value)


def cost_of(store, action: str, when=None, **bind) -> float | None:
    """What taking this act would spend, in the wallet's unit — asked, never computed.

    `orexis:landsAfter`'s twin (#466): the owning package declares the SELECT, the same
    substitution fills it, and it travels the rules' own store door so a cost read off a
    record binds exactly as a landing time does. None where the rule declines — no cost
    declared, or premises that do not hold — and every caller must read None as FREE, the
    statement an omitted declaration makes.
    """
    bind.setdefault("state", STATE_GRAPH)
    rule = rule_for(store, action)
    if rule is None or not rule.get("costs"):
        return None
    rows = _select(store, rule["costs"], bind, when)
    if not rows or rows[0]["cost"] is None:
        return None
    return float(rows[0]["cost"].value)


def precondition(store, action: str, keyed=(), **bind) -> list:
    """The facts a step's rules READ, as triples (#550): the positive patterns of the effect
    construct's WHERE and of the action's availability select, instantiated by the engine
    for this binding — `$me`, `$via`, `$about`, `$state` and the rest, exactly as `apply`
    takes them. What comes back is the step's PRECONDITION in the world it was asked about:
    the facts whose presence is what made the diff what it is. One declaration: nothing
    here is authored beside the rule, and a rule that will not run yields nothing, loudly
    in the log and quietly here, as `apply` does.

    THE ENGINE INSTANTIATES. A CONSTRUCT whose template is the WHERE's own triple patterns
    hands back, per solution, the triples those patterns matched — the same road the effect
    itself takes, no bindings read through JSON, no terms rebuilt. Patterns under
    OPTIONAL and UNION are in the template and simply drop where unbound; a pattern under
    FILTER NOT EXISTS is an ABSENCE and is left to the regression (#551), and a subtracted
    MINUS pattern is not read at all. A pattern whose predicate is a property path is
    skipped: it reads a chain, not one fact.

    The availability select is asked FOR THIS ROW — its `?via`, `?about` and `?want` held to
    the step's — so the facts are the ones that put this step on the menu, not every row
    the action could offer.

    `keyed` names the classes whose instances the signature states by KEY rather than by
    identity (`orexis:keyedBy` — an observation, keyed by feature and property). A rule
    reads such a node by its properties and never its type, and a fact about it stated
    without the type would not be the fact the prediction states; so where a pattern's
    node turns out to be one, its type is read beside it, and the signature can say it the
    way it says every other reading.
    """
    rule = rule_for(store, action)
    if rule is None:
        return []
    bind.setdefault("state", STATE_GRAPH)
    read = []
    text = _precondition_template(rule["construct"], tuple(keyed), ())
    if text:
        read += _run(store, text, bind)
    if rule.get("available"):
        text = _precondition_template(rule["available"], tuple(keyed), ("via", "about", "want"))
        if text:
            read += _run(store, text, {
                "me": bind["me"], "beliefs": bind["beliefs"], "state": bind["state"],
                "wants": Raw(f"(<{bind.get('want', 'urn:nothing')}> "
                             f"<{bind.get('about', 'urn:nothing')}>)"),
                "via": bind.get("via") or "urn:nothing", "about": bind.get("about") or "urn:nothing",
                "want": bind.get("want") or "urn:nothing"})
    return read


@functools.lru_cache(maxsize=256)
def _precondition_template(text: str, keyed: tuple, restrict: tuple) -> str | None:
    """A rule text — a CONSTRUCT or a SELECT, its `$tokens` still in it — rewritten as the
    CONSTRUCT that answers the facts its WHERE read, tokens kept so the caller binds it as
    it binds the rule; None where it states no positive pattern.

    PARSED ONCE PER TEXT. rdflib's SPARQL parser is what the precondition costs — 216 ms of 276
    for a two-step plan, measured — and a rule's text is the same for every step that takes
    the action, so the parse is cached on the text and only the binding is per step. The
    parse reads the text made parseable the way `relevance` reads it, every token a
    variable; a variable that was a token goes back into the template AS the token.
    `restrict` names the projected variables held to the step's terms, as `$` tokens too.
    """
    tokens = set(_TOKEN.findall(text))
    try:
        alg = translateQuery(parseQuery(PREFIXES + parseable(text))).algebra
    except Exception as exc:                            # noqa: BLE001 — a rule that will not parse
        log.error("a rule's premises could not be read: %s", exc)
        return None
    patterns = _positive_patterns(alg.get("p", alg))
    body = _where_body(text)
    if not patterns or body is None:
        return None

    def term(t) -> str:
        return f"${t}" if isinstance(t, Variable) and str(t) in tokens else t.n3()

    projected = {str(v) for v in (alg.get("PV") or [])}
    filters = " ".join(f"FILTER(?{name} = ${name})" for name in restrict if name in projected)
    template = [f"{term(s)} {term(p)} {term(o)} ." for s, p, o in patterns]
    types = []
    if keyed:
        classes = " ".join(f"<{c}>" for c in keyed)
        nodes = {t for s, _, o in patterns for t in (s, o)
                 if isinstance(t, Variable) and str(t) not in tokens}
        for n, v in enumerate(sorted(nodes, key=str)):
            template.append(f"{v.n3()} a ?_t{n} .")
            #  AND WHAT ELSE IT IS (#576): every class the world's own graph types a keyed
            #  node with — the bands the domain asserted — so a premise can state the
            #  reading by what it is rather than by its number.
            template.append(f"{v.n3()} a ?_u{n} .")
            #  Where the rule could have read the node's type: the default graph, or the
            #  world's own readings graph — `$state`, the one graph a possible world holds
            #  apart. Never `GRAPH ?g`: in an imaginarium that is every sibling world at once.
            #  ONLY FOR A NODE THE RULE BOUND. A variable an OPTIONAL left unbound — no
            #  standing reading, no pick — is FREE in a pattern that follows, and an
            #  `OPTIONAL { ?v a ?t }` then binds it to any node of the class; the template
            #  read that back as the rule having read it, and a missing reading came back
            #  as some other observation, typed. So the lookup asks about a stand-in that is
            #  the node where bound and nothing where not.
            types.append(f"BIND(COALESCE({v.n3()}, <urn:orexis:unbound>) AS ?_v{n}) "
                         f"OPTIONAL {{ VALUES ?_t{n} {{ {classes} }} "
                         f"{{ ?_v{n} a ?_t{n} }} UNION {{ GRAPH $state {{ ?_v{n} a ?_t{n} }} }} }} "
                         f"OPTIONAL {{ GRAPH $state {{ ?_v{n} a ?_u{n} }} FILTER(BOUND(?_t{n})) }}")
    return (f"CONSTRUCT {{ {' '.join(template)} }} "
            f"WHERE {{ {{ {body} }} {' '.join(types)} {filters} }}")


def _positive_patterns(node) -> list:
    """Every triple pattern of a WHERE that is READ — the BGPs, less what a MINUS subtracts
    and less any pattern whose predicate is a path."""
    out: list = []

    def walk(n):
        if isinstance(n, CompValue):
            if n.name == "BGP":
                out.extend((s, p, o) for s, p, o in n["triples"]
                           if isinstance(p, (URIRef, Variable)))
                return
            for key, value in n.items():
                if n.name == "Minus" and key == "p2":
                    continue
                walk(value)
        elif isinstance(n, (list, tuple)):
            for item in n:
                walk(item)
    walk(node)
    return out


def _where_body(text: str) -> str | None:
    """The inside of the query's WHERE group, as written — braces matched, strings skipped,
    and a `#` comment skipped to its line's end as the grammar skips it: a rule's comments
    are prose, and an apostrophe in one is not a string's opening quote. Read as one until
    a third apostrophe in the dosing rule's comments made every premise of a dose silently
    vanish."""
    m = re.search(r"\bWHERE\s*\{", text, re.IGNORECASE)
    if not m:
        return None
    start = m.end() - 1
    depth, quote, i = 0, None, start
    while i < len(text):
        c = text[i]
        if quote:
            if c == "\\":
                i += 1
            elif c == quote:
                quote = None
        elif c == "#":
            i = text.find("\n", i)
            if i < 0:
                return None
        elif c in "\"'":
            quote = c
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1:i]
        i += 1
    return None


def _select(store, text: str, bind: dict, when=None) -> list:
    """A rule's query that answers with BINDINGS rather than a graph. Same substitution, same
    swallowing of a rule that will not run: a package's broken query must not take an agent
    down, and what is lost is precision about waiting rather than the ability to act.

    THROUGH THE RULES' OWN DOOR (`store.construct`), and that is a correction (#472): a
    rule's SELECT must see exactly what its CONSTRUCT sees — public knowledge plus this
    agent's own records — and `store.query` reads public alone, so a landing time computed
    from an obligation RECORD (`orexis:forClaim`, `orexis:amountL`) bound nothing and every
    serve landed "immediately", silently. The rows come back as engine solutions rather
    than JSON bindings; the one consumer reads its column accordingly."""
    try:
        return store.construct(bind_text(text, **bind), at=when)
    except Exception as exc:
        log.error("timing query for this means would not run: %s", exc)
        return []


def _run(store, text: str | None, bind: dict, when=None) -> list:
    if not text:
        return []
    try:
        return list(store.construct(bind_text(text, **bind), at=when))
    except Exception as exc:
        #  A rule that will not run is a package's bug and must not take an agent down: the
        #  lever still works, and what is lost is the ability to reason about it in advance.
        log.error("effect rule for this means would not run: %s", exc)
        return []
