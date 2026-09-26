"""`refine`: a step's predicted facts, handed one level down as a want — where a rule the store
holds concludes them from other facts.

**THE HIERARCHY IS NEVER DECLARED; IT IS FOUND IN THE RULES.** A step predicts facts in its own
level's words — a hanoi Move, that a disk is on another. Where a rule of a `sh:RulesGraph`
concludes that predicate from facts of another vocabulary — a disk is on what it stands on, by
where the disks stand on the courier's grid — the step is not the level's to take: it is kept
below. So the rule is run BACKWARDS: its head is bound to the predicted fact, and its WHERE, with
those bindings, is the goal the level beneath must reach. That goal becomes a WANT, the agent's
own, whose met-test is exactly that WHERE, and it is planned like any other want, in the scope
its words fall in. Nothing is translated back: when the level beneath gets there, the rule
concludes the step's fact from the present and the executor answers the step from that revision.

This is goal regression through derived predicates, and the whole is Hierarchical Planning in
the Now's shape (Kaelbling and Lozano-Pérez, 2011), with the hierarchy found in the rules a
world combines rather than written into the actions (knowledge/domain/planning/refinement.md).

**A RULE THAT CANNOT RUN BACKWARDS IS NOT A BRIDGE.** Its head must be one triple whose subject
and object are constants or variables its WHERE binds plainly; anything else — a head of two
triples, a `BIND` into a head variable — is left out and said in the log, so a step it would
have concluded is taken as it would be with no rule at all.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime

import pyoxigraph as ox

from agent.hash_named_graph import facts_of
from agent.ontology import GRAPH_PREFIX, OREXIS, STATE, local_of
from agent.store import classify, graphs_of, instant, revisions_of, rows, update

from .ontology import PLANNING, WANT

log = logging.getLogger("refine")

RULES_GRAPH = "http://www.w3.org/ns/shacl#RulesGraph"

_RULES_Q = """
SELECT ?rule ?text WHERE { ?rule a sh:SPARQLRule ; sh:construct ?text .
                           FILTER NOT EXISTS { ?rule sh:deactivated true } } ORDER BY ?rule"""

_PREFIX = re.compile(r"^\s*PREFIX\s+(?:[A-Za-z][\w.-]*)?\s*:\s*<[^>]*>\s*$", re.I | re.M)
_TERM = r"(\?\w+|<[^>]+>|(?:[A-Za-z][\w.-]*)?:[\w.-]*|a)"
_HEAD = re.compile(rf"^\s*{_TERM}\s+{_TERM}\s+{_TERM}\s*\.?\s*$")


def refine(store: ox.Store, me: str, step: str, adds, now: datetime, retracts=()) -> str | None:
    """Mint the want that keeps the step `step` below, from the facts it predicts it `adds` and
    `retracts` (the canonical form a step's prediction is written in), in the agent `me`'s own
    want graph; the want. None where no rule the store holds concludes any fact it adds, which
    is the answer for every step of a level with nothing beneath it.

    THE GOAL IS THE WORLD THE STEP LANDS IN, NOT ITS DIFF. Every fact of a concluded predicate
    the present holds, less what the step retracts, plus what it adds — each regressed, and all
    of them to hold at once. The diff alone was measured to be too little: `disk_1 on disk_2`
    was reached below by carrying disk_2 over to disk_1, off the peg the upper plan had put it
    on, and the plan above walked on over a world it had not predicted. What the level above
    assumed of the facts a step leaves alone is what its later steps stand on, so the level
    beneath is held to keeping them — the frame, in the level above's own words."""
    rules = [parsed for rule, text in _rules(store) if (parsed := _parse(text, rule)) is not None]
    heads = [(declared, head, where, _names(declared)) for declared, head, where in rules]
    concluded = {_expand(head[1], names) for _, head, _, names in heads}
    adds = [_fact(f) for f in adds]
    if not any(f[1] in concluded for f in adds):
        return None
    gone = {_fact(f) for f in retracts}
    states = graphs_of(store, STATE)
    present = facts_of(store, *states, *revisions_of(store, *states))
    target = sorted({_fact(f) for f in present if f[1] in concluded} - gone
                    | {f for f in adds if f[1] in concluded}, key=repr)
    prefixes, conjuncts = set(), []
    for fact in target:
        branches = []
        for declared, head, where, names in heads:
            bound = _bind(head, fact, names)
            if bound is None:
                continue
            branch = where
            for var, term in bound.items():
                branch = re.sub(rf"\?{var}\b", term, branch)
            branches.append(branch)
            prefixes |= set(declared)
        if branches:
            conjuncts.append(" UNION ".join(f"{{ {b} }}" for b in branches))
    if not conjuncts:
        return None
    #  UNMET WHILE ANY FACT OF THE LANDING WORLD HAS NO WAY BELOW THAT HOLDS — one violation per
    #  such fact, so the search's met-test reads a conjunction and each fact its own union.
    goal = " UNION ".join(f"{{ FILTER NOT EXISTS {{ {c} }} }}" for c in conjuncts)
    select = ("\n".join(sorted(prefixes)) + "\n" if prefixes else "") + \
        f"SELECT $this WHERE {{ {goal} }}"
    want = f"{step}.below"
    graph = GRAPH_PREFIX + "want/refined/" + local_of(step)
    shape = f"{want}.met"
    update(store, f"""INSERT DATA {{ GRAPH <{graph}> {{
  <{me}> planning:holds <{want}> .
  <{want}> a planning:Want ; planning:metWhen <{shape}> ; planning:refines <{step}> ;
      rdfs:label "what {local_of(step)} comes to, one level down" ;
      prov:generatedAtTime {instant(now)} .
  <{shape}> a sh:NodeShape ; sh:targetNode <{me}> ;
      sh:sparql [ a sh:SPARQLConstraint ; sh:message "{local_of(step)} is not kept below yet" ;
                  sh:select {_literal(select)} ] . }} }}""")
    classify(store, graph, WANT, OREXIS + "Recorded", me)   # the agent's own act, not a desire's derivation
    log.info("refining %s into %s — %d fact(s) of the world it lands in, held below",
             local_of(step), local_of(want), len(conjuncts))
    return want


def _fact(f) -> tuple:
    """A canonical fact as nested tuples, whether it came from JSON or from the store."""
    return tuple(_fact(x) for x in f) if isinstance(f, (list, tuple)) else f


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


def _bind(head: tuple[str, str, str], fact, names: dict[str, str]) -> dict[str, str] | None:
    """The head's variables bound to one predicted fact, as the terms they are — None where the
    head does not conclude that fact."""
    s, p, o = head
    fs, fp, fo = fact
    if _expand(p, names) != fp:
        return None
    bound: dict[str, str] = {}
    for term, value in ((s, fs), (o, fo)):
        rendered = _render(value)
        if rendered is None:
            return None
        if term.startswith("?"):
            if bound.setdefault(term[1:], rendered) != rendered:
                return None
        elif _expand(term, names) != (value[1] if value[0] == "iri" else None):
            return None
    return bound


def _expand(term: str, names: dict[str, str]) -> str | None:
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
    """A canonical term back as SPARQL: an IRI, a number, a text with its language or type."""
    kind = value[0]
    if kind == "iri":
        return f"<{value[1]}>"
    if kind == "num":
        return repr(value[1])
    if kind == "lit":
        text, tag = value[1], value[2]
        return _literal(text) + (f"^^<{tag}>" if "://" in tag else (f"@{tag}" if tag else ""))
    return None


def _literal(text: str) -> str:
    return '"""' + text.replace("\\", "\\\\").replace('"', '\\"') + '"""'
