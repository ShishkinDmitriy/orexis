"""A transition: rules that change a state rather than conclude of it, and the one machine that applies
them (knowledge/domain/belief/transition.md, a-transition-changes-the-state-and-an-inference-only-concludes).

**ONE TEXT, AND THE RUNNER SAYS WHERE.** A rule is a `belief:Transition` whose `belief:update` is one
SPARQL update — `DELETE { … } INSERT { … } WHERE { … }`, either template alone over its WHERE, or
`DELETE WHERE { … }` — its delete template what it takes out, whatever stands in the place it
changes, which nobody can name in advance, and its insert template what it adds, both over the one
WHERE (#951). Rules are grouped by `sh:order`, an absent order nought as SHACL says. Every rule of
one order reads the same state: each template is asked as the `CONSTRUCT` it and the WHERE spell
(`templates`) before any of the order is applied, and then its deletions are taken out and its
additions put in, deletions first, so a later order reads what the earlier made. No rule names a
graph: what it reads is the list its caller hands, and what it changes the graphs its caller names
(a-rule-does-not-say-which-world-it-reads).

**THREE RUNNERS, ONE MACHINE.** Planning applies an action's effect through it in the possible world a
step makes, reading that world and changing it alone (`agent/planning/take.py`). The belief package
applies an arrival's transition through it to the agent's own state, each arrival of testimony
triggering every `belief:Transition` of a rules graph once (`trigger`). And planning applies the same
transitions in a ground it lays, each predicted observation arriving there triggering every one once,
reading the ground's own state and changing the ground alone (`agent/planning/lay_ground.py`, #944).
An effect is a transition the agent causes; an arrival's, an observation received or predicted, is
one the world causes. None runs to a fixpoint: an order is applied once. `transitions` answers the
rules every runner of an arrival's transition applies, so the present and a ground are changed by the
same ones.

**A RULE THAT WILL NOT RUN CHANGES NOTHING, LOUDLY.** A text the update grammar refuses, one that names
its own graphs (`WITH`, `USING`, `GRAPH`) or chains a second operation with `;`, one that is no
`DELETE`/`INSERT … WHERE`, one that will not bind, and one the engine refuses are a package's bug and
must not take an agent down: said in the log, naming the rule, and what that rule would have changed
is left as it was — the whole of it, since its two templates are one text.

**THE TEXT IS READ BY RDFLIB'S UPDATE GRAMMAR, NEVER BY A PATTERN OVER ITS CHARACTERS.** `parseUpdate`
says what the text is — how many operations, of which kind, naming which graphs — and the same
grammar's own productions, each wrapped to keep the text it matched, say where its prologue, its
templates and its WHERE stand, so each CONSTRUCT is the text's own words, its `$tokens` and its
prefixes as written. Parsed once per text and remembered: the text is a document's, and a search asks
it on every fork. A `$token` therefore stands where a variable may, which is every place a shipped
text puts one.

**THE VOCABULARY IS SHACL'S AND THE ENGINE IS NOT.** pySHACL runs `sh:SPARQLRule` only as inference
to a fixpoint, the opposite shape, and executes no bare `sh:Rule`, which is what a transition is
beneath; a stored update is just a text, and this project has an engine that runs queries
(a-plan-is-a-path-of-graph-diffs).
"""

from __future__ import annotations

import functools
import logging
from dataclasses import dataclass, field

import pyoxigraph as ox
from pyparsing import CaselessKeyword, Optional, original_text_for
from rdflib.plugins.sparql import parser as grammar
from rdflib.plugins.sparql.parserutils import CompValue

from agent.store import add_quads, bind, construct, graphs_of, rows

from .ontology import RULES_GRAPH

log = logging.getLogger("transition")

#  EVERY TRANSITION, over the rules graphs: each active one, with its order and its update.
_TRANSITIONS_Q = """
SELECT DISTINCT ?rule ?order ?update WHERE {
  ?rule a belief:Transition .
  FILTER NOT EXISTS { ?rule sh:deactivated true }
  OPTIONAL { ?rule sh:order ?o } OPTIONAL { ?rule belief:update ?update }
  BIND(COALESCE(?o, 0) AS ?order) }
ORDER BY ?order ?rule"""


@dataclass(frozen=True)
class Rule:
    """One rule of a transition: its order, its update text, and its name for the log."""
    order: float = 0.0
    update: str | None = None
    name: str | None = None

    @property
    def deletes(self) -> bool:
        """Whether the rule's text states a delete template — whatever it comes to match."""
        try:
            return self.update is not None and templates(self.update).delete is not None
        except Refused:
            return False


@dataclass(frozen=True)
class Templates:
    """An update text as its runner asks it: each template a `CONSTRUCT` over the text's one WHERE,
    with the text's prologue at its head — None for a template the text does not state."""
    delete: str | None
    insert: str | None


class Refused(ValueError):
    """An update text the runner will not run, and why — said in the log by whoever asked."""


@dataclass(frozen=True)
class Change:
    """What one order changes, asked of the state every rule of it reads: the triples it adds, the
    triples it takes out, and the rule executions asking cost — one a rule, whatever it states."""
    added: list = field(default_factory=list)
    deleted: list = field(default_factory=list)
    executions: int = 0


def transitions(store) -> list[list[Rule]]:
    """Every active `belief:Transition` of the rules graphs `store` holds, in the orders they are
    applied in — what an arrival of testimony triggers in the present, and a predicted observation
    arriving in a ground triggers there."""
    found = rows(store, _TRANSITIONS_Q, graphs_of(store, RULES_GRAPH))
    return ordered(Rule(float(r["order"]), r.get("update"), r["rule"]) for r in found)


def ordered(rules) -> list[list[Rule]]:
    """`rules` grouped by order, ascending — the orders a transition is applied in."""
    groups: dict[float, list[Rule]] = {}
    for rule in rules:
        groups.setdefault(float(rule.order), []).append(rule)
    return [groups[order] for order in sorted(groups)]


def asked(store, rules, graphs, tokens: dict | None = None) -> Change:
    """What the rules of ONE order change, every one of them reading `graphs` as they stand: each
    rule's delete template and insert template asked, before anything is applied. `tokens` are the
    `$tokens` a text takes — an effect's parameters; none for an arrival's transition."""
    added, deleted = [], []
    for rule in rules:
        if not rule.update:
            log.error("%s: a transition states no belief:update, so it changes nothing", _named(rule))
            continue
        try:
            parts = templates(rule.update)
            #  BOTH TEMPLATES OR NEITHER: one text is one change, and half of it — a state taken out
            #  with nothing put in its place — is a state no rule said.
            taken = _run(store, parts.delete, tokens, graphs) if parts.delete else []
            made = _run(store, parts.insert, tokens, graphs) if parts.insert else []
        except Refused as exc:
            log.error("%s: %s, so it changes nothing", _named(rule), exc)
            continue
        except Exception as exc:                                    # noqa: BLE001
            #  A rule that will not run is a package's bug and must not take an agent down: what is
            #  lost is what it would have changed, and the log says which.
            log.error("%s: its update would not run, so it changes nothing: %s", _named(rule), exc)
            continue
        deleted += taken
        added += made
    return Change(added, deleted, len(rules))


def applied(store, change: Change, into: str, targets) -> list[str]:
    """`change` applied: what it deletes taken out of every graph of `targets` that holds it, then
    what it adds put into `into`. The targets the deletions left empty, as they stood BEFORE the
    additions — for a caller that forgets an emptied graph, which an effect's world never is."""
    targets = list(dict.fromkeys(targets))
    touched = set()
    for t in change.deleted:
        for graph in targets:
            quad = ox.Quad(t.subject, t.predicate, t.object, ox.NamedNode(graph))
            if quad in store:
                store.remove(quad)
                touched.add(graph)
    emptied = [g for g in targets if g in touched
               and next(iter(store.quads_for_pattern(None, None, None, ox.NamedNode(g))), None) is None]
    add_quads(store, (ox.Quad(t.subject, t.predicate, t.object, ox.NamedNode(into)) for t in change.added))
    return emptied


# --- the text, read by the update grammar -----------------------------------------------------------

#  WHERE THE PARTS OF ONE `DELETE`/`INSERT … WHERE` STAND, in rdflib's own productions: each wrapped
#  to keep the text it matched, so a part is the text's words and not a reprinting of its parse. The
#  grammar is rdflib's — the prologue, a template's braces and a group graph pattern — and only the
#  keywords between them are spelled here, as SPARQL spells them; a comment is skipped as rdflib's
#  own update grammar skips it, by the same expression, so rdflib's elements are not touched.
_TEMPLATE = lambda: original_text_for(grammar.QuadPattern)    # noqa: E731
_PARTS = (original_text_for(grammar.Prologue)("prologue")
          + ((CaselessKeyword("DELETE") + CaselessKeyword("WHERE") + _TEMPLATE()("pattern"))
             | (Optional(CaselessKeyword("DELETE") + _TEMPLATE()("delete"))
                + Optional(CaselessKeyword("INSERT") + _TEMPLATE()("insert"))
                + CaselessKeyword("WHERE") + original_text_for(grammar.GroupGraphPattern)("where"))))
_PARTS.ignore(grammar.UpdateUnit.ignoreExprs[0])

#  WHAT NAMES A GRAPH inside a template or a WHERE, by the parse tree's own names.
_NAMING = {"QuadsNotTriples", "GraphGraphPattern"}


def templates(text: str) -> Templates:
    """`text`, a transition's update, as the two `CONSTRUCT`s its runner asks over its one WHERE —
    raising `Refused`, saying why, where the runner will not run it."""
    found = _templates(text)
    if isinstance(found, str):
        raise Refused(found)
    return found


@functools.lru_cache(maxsize=1024)
def _templates(text: str) -> Templates | str:
    """`templates`, remembered per text — a refusal as the reason, so it is remembered too. The
    escapes `\\u…` are expanded first, as SPARQL says and rdflib's own `parseUpdate` does."""
    text = grammar.expandUnicodeEscapes(text)
    try:
        parsed = grammar.parseUpdate(text)
    except Exception as exc:                                        # noqa: BLE001 — a refusal, said
        return f"its update will not parse: {str(exc).splitlines()[0]}"
    operations = list(parsed.get("request") or [])
    if len(operations) != 1 or len(parsed["prologue"]) != 1:
        return "its update chains operations with `;`, and a transition is one"
    [operation] = operations
    if operation.name not in ("Modify", "DeleteWhere"):
        return f"its update is {operation.name}, no DELETE/INSERT … WHERE"
    if "withClause" in operation or "using" in operation or _NAMING & _names(operation):
        return "its update names its own graphs, and the runner says them"
    try:
        parts = _PARTS.parse_string(text, parse_all=True)
    except Exception as exc:                                        # noqa: BLE001 — the grammar's own
        return f"its update's parts could not be found: {str(exc).splitlines()[0]}"
    head = parts.get("prologue") or ""
    asked_as = lambda template, where: f"{head}\nCONSTRUCT {template}\nWHERE {where}"
    if parts.get("pattern") is not None:
        return Templates(asked_as(parts["pattern"], parts["pattern"]), None)
    where = parts["where"]
    return Templates(asked_as(parts["delete"], where) if parts.get("delete") is not None else None,
                     asked_as(parts["insert"], where) if parts.get("insert") is not None else None)


def _names(node, out: set | None = None) -> set:
    """Every production name under a parsed update."""
    out = set() if out is None else out
    if isinstance(node, CompValue):
        out.add(node.name)
        for value in node.values():
            _names(value, out)
    elif isinstance(node, (list, tuple)) or hasattr(node, "as_list"):
        for value in node:
            _names(value, out)
    return out


def _run(store, text: str, tokens: dict | None, graphs) -> list:
    return list(construct(store, bind(text, **(tokens or {})), graphs))


def _named(rule: Rule) -> str:
    return rule.name or "a rule"
