"""A remembered plan is a method on the want, lifted from a plan that worked (#469).

The first honest form: a plan that reached its end is lifted FILLED — its steps as they were
walked, with their predictions and their preconditions — into the agent's own graph, hung on the
want it served. KEYED BY ITS REGRESSED PRECONDITION since #551: what the chain's rules read
that the plan did not itself produce — step n's precondition less what steps 1 to n−1 add — asked
of the present as one query, never stored and never hashed. A pursuit of that want in a world
where those facts hold, and where the first step is on the menu now, adopts it with no search,
and the trace says so; where a fact is absent the trace names it. A remembered plan that fails
a step is forgotten: the promotion rule's converse.

What replaced the whole-world hash, and why: the hash keyed a plan to every canonical fact of
four graphs, so a reading on an unrelated sensor changed the key and the plan was never seen
again, and a miss could say nothing. The regressed precondition keys a plan to what its rules
read, which is what a plan depends on; a keyed reading is asked by class and key and never by
its value, since the value is what the actor re-sizes against at execution and what the world
verifies step by step — the same discipline that lets a plan be adopted on the world's word.

The second form (the composed-effect seam, closed): a remembered plan whose precondition holds
but was not adopted outright — a search entered by another path — is a candidate on the menu,
walked in the imaginarium at the root as one step and settled like any step. Lifting to
variables is the seam after this.

What is kept is never a possible world — only the steps to re-try — and every use is verified
by the path #510 built: a step whose prediction fails drops the tail and the search takes over.
"""
from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone

from orexis_agent_progression.act import (Step, predicts_from_json, predicts_json, precondition_from_json,
                                          precondition_json)
from orexis_agent_progression.ontology import OREXIS, PROGRESSION, STATE_GRAPH, picks_graph
from orexis_agent_progression.store import bindings

from .ontology import DELIBERATION



from .ontology import (FOR_WANT, LIFTED, MEASURED_COST, REMEMBERED_AT, REMEMBERED_PLAN,
                       remembered_graph)
from orexis_agent_progression import clock
from orexis_agent_progression.ontology import PUBLIC
from orexis_agent_progression.ontology import KNOWN

log = logging.getLogger("remembered")
_RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
_XSD = "http://www.w3.org/2001/XMLSchema#"


def _literal(text: str) -> str:
    return '"%s"' % text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def regressed(steps) -> frozenset | None:
    """The plan's precondition: every step's own less what the steps before it add —
    the facts the plan reads of the world and does not itself produce. None where a step
    carries no precondition (lifted before #550), which is a plan whose applicability nobody
    can say. A premise states a reading by what it IS (#576) and a prediction carries the
    number beside the class, so what a step adds is restated by class before it is
    subtracted."""
    from . import signature
    out, produced = set(), set()
    for step in steps:
        if step.precondition is None:
            return None
        out |= set(step.precondition) - produced
        if step.predicts is not None:
            adds, _ = step.predicts
            produced |= set(signature.by_class(frozenset(adds)))
    return frozenset(out)


def missing(agent, facts) -> list:
    """The facts among `facts` that do NOT hold in the present — empty where the pattern
    holds. Asked of the belief base as ONE query first (the whole pattern, LIMIT 1), and
    only on a miss fact by fact, so the report names what is absent and the common case
    costs one select. A keyed fact — a reading — is asked by class and key, never by value."""
    graphs = agent.beliefs.graphs_of(*KNOWN, at=clock.now())

    def holds(subset) -> bool:
        text = _pattern_select(subset)
        return text is None or bool(bindings(agent.beliefs.query_over(text, *graphs)))
    if holds(facts):
        return []
    return [f for f in sorted(facts, key=repr) if not holds([f])]


def applicable(agent, want: str, desires) -> tuple | None:
    """The newest plan remembered for `want` whose regressed precondition holds in the present
    AND whose first step is on the menu now — `(uri, steps, cost)`, or None. The menu check
    is what the walk made at its first step and what carries what a fact set cannot: the
    availability's own filters, a direction among them. A plan lifted before a precondition was
    carried is forgotten here, since nothing can say when it applies."""
    for uri, steps, cost in remembered_for(agent, want):
        facts = regressed(steps)
        if facts is None:
            forget(agent, uri, "lifted before its steps carried a precondition — nothing says when it applies")
            continue
        if missing(agent, facts):
            continue
        if not on_menu_now(agent, steps[0], desires):
            continue
        return uri, steps, cost
    return None


def on_menu_now(agent, step, desires) -> bool:
    """Whether the present's menu offers this very step: the action through the lever about
    the thing — the availability select's own answer, filters and all."""
    return any(
        r.is_own and r.via == step.via and (r.about or None) == (step.about or None)
        for r in agent.afforder.offered(only=frozenset({step.action})))


_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


class _Patterns:
    """Canonical facts as the triple patterns that hold exactly where they are true — an
    IRI is itself, a number is asked within the signature's rounding, a string by its text,
    a blank node by its content, a reading by its class and key."""

    def __init__(self):
        self.parts, self.vars = [], {}

    def var(self, label) -> str:
        key = repr(label)
        if key not in self.vars:
            self.vars[key] = f"?n{len(self.vars)}"
            v = self.vars[key]
            if label[0] == "obs":
                self.parts.append(f"{v} a <{label[1]}> .")
                self.parts += [f"{v} <{p}> {self.term(o)} ." for p, o in label[2]]
            elif label[0] == "bnode":
                self.parts += [f"{v} <{p}> {self.term(o)} ." for p, o in label[1]]
                self.parts += [f"{self.term(s)} <{p}> {v} ." for s, p in label[2]]
        return self.vars[key]

    def term(self, x) -> str:
        if isinstance(x, tuple):
            return self.var(x) if x[0] in ("obs", "bnode") else self.literal(repr(x))
        if isinstance(x, bool) or not isinstance(x, (int, float, str)):
            return self.literal(str(x))
        if isinstance(x, (int, float)):
            v = f"?l{len(self.parts)}"
            self.parts.append(f"FILTER(ABS({v} - {x!r}) < 0.000001)")
            return v
        return f"<{x}>" if _SCHEME.match(x) and " " not in x else self.literal(x)

    def literal(self, text: str) -> str:
        v = f"?l{len(self.parts)}"
        self.parts.append(f"FILTER(STR({v}) = {_literal(text)})")
        return v

    def fact(self, f) -> None:
        if f[0] == "keyed":
            _, cls, key, carried, value = f
            v = self.var(("obs", cls, key))
            if carried == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type":
                #  A reading by what it IS (#576): the band the domain asserted on it, one
                #  triple — the precondition says "moisture below the region", statable and
                #  queryable, never a number.
                self.parts.append(f"{v} a <{value}> .")
            return
        s, p, o = f
        #  The object is rendered first where it is a literal, so its FILTER follows the
        #  pattern that binds it.
        subject, obj = self.term(s), None
        parts_before = len(self.parts)
        obj = self.term(o)
        pattern = f"{subject} <{p}> {obj} ."
        self.parts.insert(parts_before, pattern)


def _pattern_select(facts) -> str | None:
    """One select that binds exactly where every fact holds, or None for no facts."""
    facts = list(facts)
    if not facts:
        return None
    ps = _Patterns()
    for f in facts:
        ps.fact(f)
    return "SELECT * WHERE { " + " ".join(ps.parts) + " } LIMIT 1"


def shape_of(steps) -> tuple:
    """A plan's steps as what is compared between plans: which action, through which lever,
    about what — in order. Quantity and prediction are how a step was FILLED here, not what
    the plan is, so two walks of one route through different readings are one plan."""
    return tuple((s.action, s.via or "", s.about or "") for s in steps)


def lift(agent, want: str, steps: list, cost: float | None) -> str:
    """Lift a walked plan into the agent's graph, for this want in this world.

    ONCE: a route already remembered for this want — the same steps in the same order — is
    not lifted again, whichever world it was first lifted in and whichever way found it
    this time, the search or the walk of the remembered plan itself. The one already kept is
    answered, so a caller may hold it as the plan's memory."""
    for uri, kept, _ in remembered_for(agent, want):
        if shape_of(kept) == shape_of(steps):
            log.info("%s: the plan for %s is already remembered as %s", agent.id,
                     want.rsplit("#", 1)[-1], uri.rsplit("#", 1)[-1])
            return uri
    graph = remembered_graph(agent.id)
    agent.beliefs.classify(graph, DELIBERATION + "RememberedGraph", OREXIS + "Recorded", agent.me.uri)
    uri = f"{OREXIS}remembered_{agent.id}_{uuid.uuid4().hex[:8]}"
    nodes = [f"{uri}_{n}" for n in range(len(steps))]
    blocks = []
    for node, step in zip(nodes, steps):
        facts = [f'<{PROGRESSION}fills> <{step.action}>']
        if step.via:
            facts.append(f'<{PROGRESSION}through> <{step.via}>')
        if step.about:
            facts.append(f'<{OREXIS}about> <{step.about}>')
        if step.quantity is not None:
            facts.append(f'<{PROGRESSION}quantity> "{step.quantity}"^^<{_XSD}decimal>')
        if step.predicts is not None:
            facts.append(f'<{PROGRESSION}predicts> {_literal(predicts_json(step.predicts))}')
        if step.precondition is not None:
            facts.append(f'<{PROGRESSION}precondition> {_literal(precondition_json(step.precondition))}')
        blocks.append(f"  <{node}> {' ; '.join(facts)} .")
    listed = "( " + " ".join(f"<{n}>" for n in nodes) + " )"
    measured = f' ; <{MEASURED_COST}> "{cost}"^^<{_XSD}decimal>' if cost is not None else ""
    agent.beliefs.update(f"""
INSERT DATA {{ GRAPH <{graph}> {{
  <{uri}> a <{REMEMBERED_PLAN}> ; <{FOR_WANT}> <{want}> ;
      <{LIFTED}> {listed} ;
      <{REMEMBERED_AT}> "{clock.now().isoformat()}"^^<{_XSD}dateTime>{measured} .
{chr(10).join(blocks)}
}} }}""")
    log.info("%s: remembered a plan of %d step(s) for %s", agent.id, len(steps),
             want.rsplit("#", 1)[-1])
    return uri


def remembered_for(agent, want: str) -> list:
    """Every plan remembered for this want, newest first: `(uri, steps, cost)`, the steps
    carrying their predictions and preconditions. What `applicable` keys by and what the search
    weighs as candidates."""
    graph = remembered_graph(agent.id)
    rows = bindings(agent.beliefs.query(f"""
SELECT ?r ?cost ?at WHERE {{ GRAPH <{graph}> {{
  ?r a <{REMEMBERED_PLAN}> ; <{FOR_WANT}> <{want}> ; <{REMEMBERED_AT}> ?at .
  OPTIONAL {{ ?r <{MEASURED_COST}> ?cost }} }} }} ORDER BY DESC(?at)""", agent.beliefs.graphs_of(PUBLIC)))
    out = []
    for row in rows:
        steps = _steps_of(agent, row["r"], want)
        if steps:
            out.append((row["r"], steps, float(row["cost"]) if row.get("cost") else None))
    return out


def _steps_of(agent, uri: str, want: str) -> list:
    graph = remembered_graph(agent.id)
    steps = bindings(agent.beliefs.query(f"""
SELECT ?node ?first ?rest ?action ?via ?about ?quantity ?predicts ?precondition WHERE {{ GRAPH <{graph}> {{
  <{uri}> <{LIFTED}> ?head . ?head <{_RDF}rest>* ?node . ?node <{_RDF}first> ?first ; <{_RDF}rest> ?rest .
  ?first <{PROGRESSION}fills> ?action .
  OPTIONAL {{ ?first <{PROGRESSION}through> ?via }}
  OPTIONAL {{ ?first <{OREXIS}about> ?about }}
  OPTIONAL {{ ?first <{PROGRESSION}quantity> ?quantity }}
  OPTIONAL {{ ?first <{PROGRESSION}predicts> ?predicts }}
  OPTIONAL {{ ?first <{PROGRESSION}precondition> ?precondition }} }} }}""", agent.beliefs.graphs_of(PUBLIC)))
    by_node = {r["node"]: r for r in steps}
    head = bindings(agent.beliefs.query(f"SELECT ?h WHERE {{ GRAPH <{graph}> {{ <{uri}> <{LIFTED}> ?h }} }}", agent.beliefs.graphs_of(PUBLIC)))
    out, node = [], head[0]["h"] if head else None
    while node in by_node:
        r = by_node[node]
        out.append(Step(action=r["action"], via=r.get("via") or "", want=want, about=r.get("about"),
                        quantity=float(r["quantity"]) if r.get("quantity") else None,
                        predicts=predicts_from_json(r["predicts"]) if r.get("predicts") else None,
                        precondition=precondition_from_json(r["precondition"]) if r.get("precondition") else None))
        node = r["rest"]
    return out


def forget(agent, uri: str, because: str) -> None:
    """A remembered plan that failed a step is forgotten — the promotion rule's converse."""
    graph = remembered_graph(agent.id)
    agent.beliefs.update(f"""
DELETE {{ GRAPH <{graph}> {{ ?s ?p ?o }} }}
WHERE  {{ GRAPH <{graph}> {{
  {{ <{uri}> ?p ?o . BIND(<{uri}> AS ?s) }}
  UNION {{ <{uri}> <{LIFTED}> ?head . ?head <{_RDF}rest>* ?s . ?s ?p ?o }}
  UNION {{ <{uri}> <{LIFTED}> ?head . ?head <{_RDF}rest>* ?n . ?n <{_RDF}first> ?s . ?s ?p ?o }} }} }}""")
    log.info("%s: forgot %s — %s", agent.id, uri.rsplit("#", 1)[-1], because)


def forget_matching(agent, want: str, steps, because: str) -> list:
    """Forget every plan remembered for this want that IS this route — the same steps in the
    same order — whichever way adopted it: the exact hit, or the walk that weighed it as a
    candidate and won. Answers what was forgotten."""
    gone = []
    for uri, kept, _ in remembered_for(agent, want):
        if shape_of(kept) == shape_of(steps):
            forget(agent, uri, because)
            gone.append(uri)
    return gone
