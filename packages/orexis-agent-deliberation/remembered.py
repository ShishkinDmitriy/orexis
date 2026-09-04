"""A remembered plan is a method on the want, lifted from a plan that worked (#469).

The first honest form: a plan that reached its end is lifted FILLED — its steps as they were
walked, with their predictions — into the agent's own graph, hung on the want it served with
the signature of the world it was decided in. A pursuit of that want in a world of the same
signature adopts it with no search, and the trace says so. A different world searches. A
remembered plan that fails a step is forgotten: the promotion rule's converse. Lifting to
variables, the regressed applicability and the composed effect are the seams after this.

What is kept is never a possible world — only the steps to re-try — and every use is verified
by the road #510 built: a step whose prediction fails drops the tail and the search takes over.
"""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone

from orexis_agent_progression.act import Step, predicts_from_json, predicts_json
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


def lift(agent, want: str, steps: list, world: str, cost: float | None) -> str:
    """Lift a walked plan into the agent's graph, for this want in this world."""
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
    """A plan remembered for this want in a world of this signature: `(uri, steps, cost)`,
    or None. Newest first, where several were remembered."""
    graph = remembered_graph(agent.id)
    rows = bindings(agent.beliefs.query(f"""
SELECT ?r ?cost ?at WHERE {{ GRAPH <{graph}> {{
  ?r a <{REMEMBERED_PLAN}> ; <{FOR_WANT}> <{want}> ; <{IN_WORLD}> "{world}" ; <{REMEMBERED_AT}> ?at .
  OPTIONAL {{ ?r <{MEASURED_COST}> ?cost }} }} }} ORDER BY DESC(?at) LIMIT 1"""))
    if not rows:
        return None
    uri = rows[0]["r"]
    steps = bindings(agent.beliefs.query(f"""
SELECT ?node ?first ?rest ?action ?via ?about ?quantity ?predicts WHERE {{ GRAPH <{graph}> {{
  <{uri}> <{LIFTED}> ?head . ?head <{_RDF}rest>* ?node . ?node <{_RDF}first> ?first ; <{_RDF}rest> ?rest .
  ?first <{PROGRESSION}fills> ?action .
  OPTIONAL {{ ?first <{PROGRESSION}through> ?via }}
  OPTIONAL {{ ?first <{OREXIS}about> ?about }}
  OPTIONAL {{ ?first <{PROGRESSION}quantity> ?quantity }}
  OPTIONAL {{ ?first <{PROGRESSION}predicts> ?predicts }} }} }}"""))
    by_node = {r["node"]: r for r in steps}
    head = bindings(agent.beliefs.query(f"SELECT ?h WHERE {{ GRAPH <{graph}> {{ <{uri}> <{LIFTED}> ?h }} }}"))
    out, node = [], head[0]["h"] if head else None
    while node in by_node:
        r = by_node[node]
        out.append(Step(action=r["action"], via=r.get("via") or "", want=want, about=r.get("about"),
                        quantity=float(r["quantity"]) if r.get("quantity") else None,
                        predicts=predicts_from_json(r["predicts"]) if r.get("predicts") else None))
        node = r["rest"]
    cost = float(rows[0]["cost"]) if rows[0].get("cost") else None
    return (uri, out, cost) if out else None


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
