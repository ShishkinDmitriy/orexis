"""A transition: rules that change a state rather than conclude of it, and the one machine that applies
them (knowledge/domain/belief/transition.md, a-transition-changes-the-state-and-an-inference-only-concludes).

**THE SHAPE IS AN EFFECT'S, AND THE RUNNER SAYS WHERE.** A rule is a `sh:SPARQLRule` whose
`sh:construct` is what applying it ADDS, or whose `belief:delete` is a `DELETE … WHERE` taking out
whatever stands in the place it changes, which nobody can name in advance — or both. Rules are
grouped by `sh:order`, an absent order nought as SHACL says. Every rule of one order reads the same
state: its constructs are asked and its deletes' WHERE matched before any of the order is applied —
the delete asked as the `CONSTRUCT` its template and pattern spell — and then its deletions are
taken out and its additions put in, deletions first, so a later order reads what the earlier made.
No rule names a graph: what it reads is the list its caller hands, and what it changes the graphs
its caller names (a-rule-does-not-say-which-world-it-reads).

**TWO CALLERS, ONE MACHINE.** Planning applies an action's effect through it in the possible world a
step makes, reading that world and changing it alone (`agent/planning/take.py`). The belief package
applies a percept's transition through it to the agent's own state, each arrival of testimony
triggering every `belief:Transition` once (`trigger`). An effect is a transition the agent
causes; a percept's is one the world causes. Neither runs to a fixpoint: an order is applied once.

**A RULE THAT WILL NOT RUN CHANGES NOTHING, LOUDLY.** A text that will not bind, a delete that names
its own graphs or is no `DELETE … WHERE`, and a text the engine refuses are a package's bug and must
not take an agent down: said in the log, and what that rule would have changed is left as it was.

**THE VOCABULARY IS SHACL'S AND THE ENGINE IS NOT.** pySHACL runs `sh:SPARQLRule` only as inference
to a fixpoint, the opposite shape; a stored construct is just a query, and this project has an engine
that runs queries (a-plan-is-a-path-of-graph-diffs).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

import pyoxigraph as ox

from agent.store import add_quads, bind, construct

log = logging.getLogger("transition")

#  `PREFIX name: <iri>` at the head of a text, the empty name included — kept where it stands.
_PREFIX_LINE = re.compile(r"^\s*PREFIX\s+([A-Za-z][\w.\-]*)?\s*:\s*<([^>]*)>[ \t]*\n?", re.I | re.M)


@dataclass(frozen=True)
class Rule:
    """One rule of a transition: its order, what it adds, what it deletes, and its name for the log."""
    order: float = 0.0
    construct: str | None = None
    delete: str | None = None
    name: str | None = None


@dataclass(frozen=True)
class Change:
    """What one order changes, asked of the state every rule of it reads: the triples it adds, the
    triples it takes out, and the rule executions asking cost — one a rule, whatever it states."""
    added: list = field(default_factory=list)
    deleted: list = field(default_factory=list)
    executions: int = 0


def ordered(rules) -> list[list[Rule]]:
    """`rules` grouped by order, ascending — the orders a transition is applied in."""
    groups: dict[float, list[Rule]] = {}
    for rule in rules:
        groups.setdefault(float(rule.order), []).append(rule)
    return [groups[order] for order in sorted(groups)]


def asked(store, rules, graphs, tokens: dict | None = None) -> Change:
    """What the rules of ONE order change, every one of them reading `graphs` as they stand: each
    construct asked, and each delete's WHERE matched, before anything is applied. `tokens` are the
    `$tokens` a text takes — an effect's parameters; none for a percept's transition."""
    added, deleted = [], []
    for rule in rules:
        if rule.construct:
            added += _run(store, rule.construct, tokens, graphs, rule, "construct")
        if rule.delete:
            text = _as_construct(rule.delete, rule)
            if text is not None:
                deleted += _run(store, text, tokens, graphs, rule, "delete")
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


def _as_construct(text: str, rule: Rule) -> str | None:
    """A delete as the `CONSTRUCT` that asks what it matches — its template, or its pattern for a
    `DELETE WHERE`, over the same WHERE — with its prologue kept; None, said in the log, where it is
    no `DELETE … WHERE` or says its own graphs, which are the runner's to say."""
    body = _PREFIX_LINE.sub("", text)
    head = "".join(m.group(0) for m in _PREFIX_LINE.finditer(text))
    body = body.strip()
    if re.match(r"(?i)(WITH|USING)\b", body) or re.search(r"(?i)\bUSING\s*(NAMED\s*)?<", body):
        log.error("%s: a delete says its own graphs, and the runner says them; it deletes nothing", _named(rule))
        return None
    if not re.match(r"(?i)DELETE\b", body):
        log.error("%s: a delete is no DELETE … WHERE, so it deletes nothing", _named(rule))
        return None
    return head + "CONSTRUCT" + body[len("DELETE"):]


def _run(store, text: str, tokens: dict | None, graphs, rule: Rule, what: str) -> list:
    try:
        return list(construct(store, bind(text, **(tokens or {})), graphs))
    except Exception as exc:                                        # noqa: BLE001
        #  A rule that will not run is a package's bug and must not take an agent down: what is lost
        #  is what it would have changed, and the log says which.
        log.error("%s: a %s would not run, so it %s nothing: %s", _named(rule), what,
                  "adds" if what == "construct" else "deletes", exc)
        return []


def _named(rule: Rule) -> str:
    return rule.name or "a rule"
