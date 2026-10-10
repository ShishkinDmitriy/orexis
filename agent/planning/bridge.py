"""The bridges: the rules a store holds that conclude one vocabulary's facts from another's, read
as heads that can be run BACKWARDS — what `refine` regresses a step's predicted facts through, and
what the Planner asks, when it hands a plan down, of which of its steps a level beneath may keep
(knowledge/domain/planning/bridge.md).

A RULE THAT CANNOT RUN BACKWARDS IS NOT A BRIDGE. Its head must be one triple whose subject and
object are constants or variables its WHERE binds plainly; anything else is left out and said in
the log. And a TRANSITION is none: a rule typed `belief:Transition` changes a state
when something arrives, and concludes no vocabulary's facts from another's
(a-transition-changes-the-state-and-an-inference-only-concludes).
"""

from __future__ import annotations

import logging
import re

import pyoxigraph as ox

from agent.ontology import local_of
from agent.store import bind, graphs_of, quads, rows

log = logging.getLogger("bridge")

RULES_GRAPH = "http://www.w3.org/ns/shacl#RulesGraph"

_RULES_Q = """
SELECT ?rule ?text WHERE { ?rule a sh:SPARQLRule ; sh:construct ?text .
                           FILTER NOT EXISTS { ?rule sh:deactivated true }
                           FILTER NOT EXISTS { ?rule a belief:Transition } } ORDER BY ?rule"""

#  THE TWO GRAPHS A STEP PREDICTS IN, wherever its plan is (a-steps-prediction-is-two-graphs-it-names).
_PREDICTED_Q = """
SELECT ?adds ?retracts WHERE {
  OPTIONAL { GRAPH ?a { $step execution:adds ?adds } }
  OPTIONAL { GRAPH ?r { $step execution:retracts ?retracts } } } LIMIT 1"""

_PREFIX = re.compile(r"^\s*PREFIX\s+(?:[A-Za-z][\w.-]*)?\s*:\s*<[^>]*>\s*$", re.I | re.M)
_TERM = r"(\?\w+|<[^>]+>|(?:[A-Za-z][\w.-]*)?:[\w.-]*|a)"
_HEAD = re.compile(rf"^\s*{_TERM}\s+{_TERM}\s+{_TERM}\s*\.?\s*$")


def heads(store) -> list[tuple[list[str], tuple[str, str, str], str, dict[str, str]]]:
    """Every bridge the store holds as (its PREFIX lines, its head, its WHERE, its names)."""
    parsed = [p for rule, text in _rules(store) if (p := _parse(text, rule)) is not None]
    return [(declared, head, where, _names(declared)) for declared, head, where in parsed]


def keeps(store, step: str) -> bool:
    """Whether the step `step` is kept below: a bridge's head binds a fact the step predicts its
    world gains — which is what makes `refine` mint a want for it whatever the present holds."""
    found = heads(store)
    adds, _ = predicted(store, step)
    return any(binding(head, f, names) is not None for f in adds for _, head, _, names in found)


def predicted(store, step: str) -> tuple[list[tuple], list[tuple]]:
    """What the step `step` predicts, as the terms they are: the facts of the graph it
    `execution:adds` and of the one it `execution:retracts`, each a `(subject, predicate, object)`
    of the engine's own terms, sorted. Empty on a side the step does not name."""
    found = next(iter(rows(store, bind(_PREDICTED_Q, step=step))), {})
    facts = lambda g: sorted(((q.subject, q.predicate, q.object) for q in quads(store, g)), key=str) if g else []
    return facts(found.get("adds")), facts(found.get("retracts"))


def _rules(store) -> list[tuple[str, str]]:
    """Every active SPARQL rule of every rules graph, with its construct."""
    return [(r["rule"], r["text"]) for r in rows(store, _RULES_Q, graphs_of(store, RULES_GRAPH))]


def _parse(text: str, rule: str) -> tuple[list[str], tuple[str, str, str], str] | None:
    """A rule as its PREFIX lines, its one head triple and its WHERE body — or None, said in the
    log, where it cannot be run backwards."""
    declared = [m.group(0).strip() for m in _PREFIX.finditer(text)]
    body = _PREFIX.sub("", text).strip()
    m = re.match(r"(?is)CONSTRUCT\s*\{", body)
    if not m:
        return None
    head_end = _closing(body, m.end() - 1)
    template = body[m.end():head_end].strip()
    rest = body[head_end + 1:].strip()
    w = re.match(r"(?is)WHERE\s*\{", rest)
    if not w:
        return None
    where = rest[w.end():_closing(rest, w.end() - 1)].strip()
    head = _HEAD.match(template)
    if head is None:
        log.warning("%s concludes more than one triple and is not run backwards", local_of(rule))
        return None
    for var in (t for t in head.groups() if t.startswith("?")):
        if re.search(rf"\bAS\s+\{var}\b", where, re.I):
            log.warning("%s binds %s with BIND and is not run backwards", local_of(rule), var)
            return None
    return declared, head.groups(), where


def _closing(text: str, opening: int) -> int:
    """The index of the brace closing the one at `opening`, strings skipped."""
    depth, i, quote = 0, opening, None
    while i < len(text):
        c = text[i]
        if quote:
            if c == "\\":
                i += 2
                continue
            if c == quote:
                quote = None
        elif c in "\"'":
            quote = c
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise ValueError("unbalanced braces in a rule")


def _names(declared: list[str]) -> dict[str, str]:
    """The rule's own `PREFIX` lines as a map, over the store's — a domain's words are the rule's
    to declare, and the store never loaded them."""
    from agent.store import NAMESPACES
    out = dict(NAMESPACES)
    for line in declared:
        m = re.match(r"(?i)\s*PREFIX\s+([A-Za-z][\w.-]*)?\s*:\s*<([^>]*)>", line)
        if m:
            out[m.group(1) or ""] = m.group(2)
    return out


def binding(head: tuple[str, str, str], fact, names: dict[str, str]) -> dict[str, str] | None:
    """The head's variables bound to one predicted fact — a triple of the engine's terms — as
    SPARQL text; None where the head does not conclude that fact."""
    s, p, o = head
    fs, fp, fo = fact
    if expand(p, names) != fp.value:
        return None
    bound: dict[str, str] = {}
    for term, value in ((s, fs), (o, fo)):
        rendered = _render(value)
        if rendered is None:
            return None
        if term.startswith("?"):
            if bound.setdefault(term[1:], rendered) != rendered:
                return None
        elif expand(term, names) != (value.value if isinstance(value, ox.NamedNode) else None):
            return None
    return bound


def expand(term: str, names: dict[str, str]) -> str | None:
    """A head's predicate or constant as a full IRI, through the rule's prefixes."""
    if term.startswith("<"):
        return term[1:-1]
    if term == "a":
        return "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
    if ":" in term and not term.startswith("?"):
        label, local = term.split(":", 1)
        return names[label] + local if label in names else None
    return None


def _render(value) -> str | None:
    """A term as SPARQL: an IRI in angles, a literal in its N-Triples form. A blank node is
    nothing a WHERE can be bound to and is refused."""
    if isinstance(value, ox.NamedNode):
        return f"<{value.value}>"
    if isinstance(value, ox.Literal):
        return str(value)
    return None


def literal(text: str) -> str:
    return '"""' + text.replace("\\", "\\\\").replace('"', '\\"') + '"""'
