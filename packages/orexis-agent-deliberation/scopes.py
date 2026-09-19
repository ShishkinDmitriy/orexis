"""The scopes in the store, as SPARQL and nothing else.

`scope_actions` hands the partition here and it is written as scopes; `derive_wants` reads it
back with one SELECT. This module owns the scope graph: its name for eyes (`scopes`), its
classification, and that it is replaced whole on every run, as `judgments.py` owns the
judgment graph. A reader that means the graph asks its class.

ONE GRAPH FOR THE STORE, and not one per agent. The partition is a function of the actions the
store holds and the derivations loaded, and neither is anyone's in particular: every agent
reading one store would compute the same clustering from the same rows. It was written per
agent because `scope_actions` was handed an agent; handed the engine, there is nobody to name
it after, and a graph saying no owner is anyone's — which is what it always meant.
"""

from __future__ import annotations

import pyoxigraph as ox

from orexis_agent_progression.ontology import OREXIS
from orexis_agent_progression.store import NAMESPACES, rows

from .ontology import DELIBERATION, scopes_graph

SCOPE_GRAPH = DELIBERATION + "ScopeGraph"

SCOPES_Q = """
SELECT ?member ?scope WHERE { ?member deliberation:inScope ?scope }"""

#  EVERY STANDING SCOPE GRAPH, asked of the catalogue by class — what a run replaces, whatever
#  each is called, including a per-agent one a volume was left with before the partition
#  became the store's.
_STANDING_Q = """
SELECT ?g WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a deliberation:ScopeGraph } }
ORDER BY ?g"""


def scope_name(n: int) -> str:
    """The name of the nth scope in the partition, largest first — the graph's own, suffixed,
    so the same actions write the same text. This module names both the graph and what is in
    it; `scope_actions` decides the partition and asks for the names."""
    return f"{scopes_graph()}/{n}"


def save_scopes(engine: ox.Store, scopes: list[tuple[str, set[str], set[str]]]) -> None:
    """Replace the store's scopes with these — `(scope, predicates, actions)` each — and say
    what the graph is. Written whole, and classified even when empty: a store with no scope
    graph has never been scoped, which `derive_wants` refuses to guess about.

    ONE UPDATE OVER THE ENGINE: every standing scope graph asked of the catalogue by class and
    dropped, then the graph and its catalogue row together, the catalogue found by its own row
    and every kind the vocabulary puts a scope graph beneath written from one
    `rdfs:subClassOf` step — the closure is materialised at genesis, so one step is every step.
    """
    standing = [row["g"] for row in rows(engine, _STANDING_Q)]
    graph = scopes_graph()
    blocks = []
    for scope, predicates, actions in scopes:
        members = " ".join(f"<{m}> deliberation:inScope <{scope}> ." for m in sorted(predicates | actions))
        blocks.append(f"  <{scope}> a deliberation:Scope .\n  {members}")
    dropped = "".join(
        f"DROP SILENT GRAPH <{g}> ;\n"
        f"DELETE {{ GRAPH ?cat {{ <{g}> ?p ?o }} }} WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph . <{g}> ?p ?o }} }} ;\n"
        for g in standing)
    engine.update(dropped + f"""
INSERT {{
  GRAPH <{graph}> {{
{chr(10).join(blocks)}
  }}
  GRAPH ?cat {{ <{graph}> a deliberation:ScopeGraph ; orexis:arrivedBy <{OREXIS + "Derived"}> . }} }}
WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph }} }} ;
INSERT {{ GRAPH ?cat {{ <{graph}> a ?kind }} }}
WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph . ?vocabulary a orexis:OntologyGraph }}
        GRAPH ?vocabulary {{ deliberation:ScopeGraph rdfs:subClassOf ?kind }} }}""",
                  prefixes=NAMESPACES)


def find_scopes(engine: ox.Store) -> dict[str, str] | None:
    """Every member's scope, predicate or action, from the scope graphs asked by class — or
    None where the store holds none at all, which is a store nobody scoped."""
    graphs = [row["g"] for row in rows(engine, _STANDING_Q)]
    if not graphs:
        return None
    return {r["member"]: r["scope"] for r in rows(engine, SCOPES_Q, graphs)}
