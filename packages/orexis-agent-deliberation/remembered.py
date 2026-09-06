"""A remembered plan is a method on the want, lifted from a plan that worked (#469).

The first honest form: a plan that reached its end is lifted FILLED — its steps as they were
walked, with their predictions — into the agent's own graph, hung on the want it served with
the signature of the world it was decided in. A pursuit of that want in a world of the same
signature adopts it with no search, and the trace says so. A remembered plan that fails a
step is forgotten: the promotion rule's converse.

The second form (the composed-effect seam, closed): in a world of ANOTHER signature every plan
remembered for the want is a candidate on the menu — walked in the imaginarium at the root as
one step, each of its steps re-simulated in order and each on the menu of the world the one
before reached, and settled like any step: dear, late, forbidden, seen or met. Its composed
effect is the world the walk reaches, its applicability is that every step was on its menu,
and where it achieves the want its cost seeds the bound the rest of the pass is refused by.
Lifting to variables and the regressed applicability are the seams after this.

What is kept is never a possible world — only the steps to re-try — and every use is verified
by the road #510 built: a step whose prediction fails drops the tail and the search takes over.
"""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone

from orexis_agent_progression.act import (Step, predicts_from_json, predicts_json, premises_from_json,
                                          premises_json)
from orexis_agent_progression.ontology import OREXIS, PROGRESSION
from orexis_agent_progression.store import bindings

from . import signature
from .ontology import (FOR_WANT, IN_WORLD, LIFTED, MEASURED_COST, REMEMBERED_AT,
                       REMEMBERED_PLAN, remembered_graph)

log = logging.getLogger("remembered")
_RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
_XSD = "http://www.w3.org/2001/XMLSchema#"


def world_signature(agent) -> str:
    """The world the agent stands in, as the same canonical facts the search's signature is
    made of, hashed — what a remembered plan is keyed by."""
    #  THE WORLD AND THE STATE, and nothing the agent writes about itself: the ledger, the
    #  trace and this very graph change with every pass, and a signature over them would never
    #  see the same world twice. What a plan depends on is what its rules read — the topology
    #  and the readings — and that is what is hashed.
    from orexis_agent_progression.ontology import (STATE_GRAPH, WORLD_DERIVED_GRAPH,
                                                    WORLD_ENTAILED_GRAPH, WORLD_GRAPH)
    store = agent.beliefs
    keys = signature.keys_of(store.query)
    facts = signature.facts((q for iri in (WORLD_GRAPH, WORLD_DERIVED_GRAPH, WORLD_ENTAILED_GRAPH, STATE_GRAPH)
                             for q in store.quads(iri)), keys)
    return hashlib.sha256(json.dumps(sorted(map(repr, facts))).encode()).hexdigest()[:24]


def _literal(text: str) -> str:
    return '"%s"' % text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def shape_of(steps) -> tuple:
    """A plan's steps as what is compared between plans: which action, through which lever,
    about what — in order. Quantity and prediction are how a step was FILLED here, not what
    the plan is, so two walks of one route through different readings are one plan."""
    return tuple((s.action, s.via or "", s.about or "") for s in steps)


def lift(agent, want: str, steps: list, world: str, cost: float | None) -> str:
    """Lift a walked plan into the agent's graph, for this want in this world.

    ONCE: a route already remembered for this want — the same steps in the same order — is
    not lifted again, whichever world it was first lifted in and whichever road found it
    this time, the search or the walk of the remembered plan itself. The one already kept is
    answered, so a caller may hold it as the plan's memory."""
    for uri, kept, _, _ in remembered_for(agent, want):
        if shape_of(kept) == shape_of(steps):
            log.info("%s: the plan for %s is already remembered as %s", agent.id,
                     want.rsplit("#", 1)[-1], uri.rsplit("#", 1)[-1])
            return uri
    graph = remembered_graph(agent.id)
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
        if step.premises is not None:
            facts.append(f'<{PROGRESSION}premises> {_literal(premises_json(step.premises))}')
        blocks.append(f"  <{node}> {' ; '.join(facts)} .")
    listed = "( " + " ".join(f"<{n}>" for n in nodes) + " )"
    measured = f' ; <{MEASURED_COST}> "{cost}"^^<{_XSD}decimal>' if cost is not None else ""
    agent.beliefs.update(f"""
INSERT DATA {{ GRAPH <{graph}> {{
  <{uri}> a <{REMEMBERED_PLAN}> ; <{FOR_WANT}> <{want}> ; <{IN_WORLD}> "{world}" ;
      <{LIFTED}> {listed} ;
      <{REMEMBERED_AT}> "{datetime.now(timezone.utc).isoformat()}"^^<{_XSD}dateTime>{measured} .
{chr(10).join(blocks)}
}} }}""")
    log.info("%s: remembered a plan of %d step(s) for %s in world %s", agent.id, len(steps),
             want.rsplit("#", 1)[-1], world[:8])
    return uri


def remembered(agent, want: str, world: str):
    """A plan remembered for this want in a world of THIS signature: `(uri, steps, cost)`,
    or None. Newest first, where several were remembered. The exact hit — adopted with no
    search, since the pass that lifted it already searched this very world."""
    for uri, steps, cost, kept_in in remembered_for(agent, want):
        if kept_in == world:
            return uri, steps, cost
    return None


def remembered_for(agent, want: str) -> list:
    """Every plan remembered for this want, newest first: `(uri, steps, cost, world)` — the
    world being the signature it was lifted in. What the search weighs as candidates where
    the world it stands in is none of those."""
    graph = remembered_graph(agent.id)
    rows = bindings(agent.beliefs.query(f"""
SELECT ?r ?cost ?at ?world WHERE {{ GRAPH <{graph}> {{
  ?r a <{REMEMBERED_PLAN}> ; <{FOR_WANT}> <{want}> ; <{IN_WORLD}> ?world ; <{REMEMBERED_AT}> ?at .
  OPTIONAL {{ ?r <{MEASURED_COST}> ?cost }} }} }} ORDER BY DESC(?at)"""))
    out = []
    for row in rows:
        steps = _steps_of(agent, row["r"], want)
        if steps:
            out.append((row["r"], steps, float(row["cost"]) if row.get("cost") else None,
                        row["world"]))
    return out


def _steps_of(agent, uri: str, want: str) -> list:
    graph = remembered_graph(agent.id)
    steps = bindings(agent.beliefs.query(f"""
SELECT ?node ?first ?rest ?action ?via ?about ?quantity ?predicts ?premises WHERE {{ GRAPH <{graph}> {{
  <{uri}> <{LIFTED}> ?head . ?head <{_RDF}rest>* ?node . ?node <{_RDF}first> ?first ; <{_RDF}rest> ?rest .
  ?first <{PROGRESSION}fills> ?action .
  OPTIONAL {{ ?first <{PROGRESSION}through> ?via }}
  OPTIONAL {{ ?first <{OREXIS}about> ?about }}
  OPTIONAL {{ ?first <{PROGRESSION}quantity> ?quantity }}
  OPTIONAL {{ ?first <{PROGRESSION}predicts> ?predicts }}
  OPTIONAL {{ ?first <{PROGRESSION}premises> ?premises }} }} }}"""))
    by_node = {r["node"]: r for r in steps}
    head = bindings(agent.beliefs.query(f"SELECT ?h WHERE {{ GRAPH <{graph}> {{ <{uri}> <{LIFTED}> ?h }} }}"))
    out, node = [], head[0]["h"] if head else None
    while node in by_node:
        r = by_node[node]
        out.append(Step(action=r["action"], via=r.get("via") or "", want=want, about=r.get("about"),
                        quantity=float(r["quantity"]) if r.get("quantity") else None,
                        predicts=predicts_from_json(r["predicts"]) if r.get("predicts") else None,
                        premises=premises_from_json(r["premises"]) if r.get("premises") else None))
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
    same order — whichever road adopted it: the exact hit, or the walk that weighed it as a
    candidate and won. Answers what was forgotten."""
    gone = []
    for uri, kept, _, _ in remembered_for(agent, want):
        if shape_of(kept) == shape_of(steps):
            forget(agent, uri, because)
            gone.append(uri)
    return gone
