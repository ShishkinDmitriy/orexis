"""The scopes in the store, as SPARQL and nothing else.

`scoping_actions` hands the partition here and it is written as scopes; `derive_wants`
reads it back with one SELECT. This module owns the scope graph: its name for eyes
(`scopes/<agent>`), its classification with owner, and that it is replaced whole on every run,
as `judgments.py` owns the judgment graph. A reader that means the graph asks its class.
"""

from __future__ import annotations

from orexis_agent_progression.ontology import CLASSIFICATION_GRAPH
from orexis_agent_progression.store import bindings

from .ontology import DELIBERATION, scopes_graph

SCOPE_GRAPH = DELIBERATION + "ScopeGraph"

SCOPES_Q = """
SELECT ?member ?scope WHERE { ?member deliberation:inScope ?scope }"""


def save_scopes(store, agent_id: str, holder: str,
                scopes: list[tuple[str, set[str], set[str]]]) -> None:
    """Replace the agent's scopes with these — `(scope, predicates, actions)` each — and say
    what the graph is. Written whole, and classified even when empty: a store with no scope
    graph has never been scoped, which `derive_wants` refuses to guess about."""
    graph = scopes_graph(agent_id)
    blocks = []
    for scope, predicates, actions in scopes:
        members = " ".join(f"<{m}> deliberation:inScope <{scope}> ." for m in sorted(predicates | actions))
        blocks.append(f"  <{scope}> a deliberation:Scope .\n  {members}")
    store.drop_graph(graph)
    store.update(f"""
INSERT DATA {{
  GRAPH <{graph}> {{
{chr(10).join(blocks)}
  }}
  GRAPH <{CLASSIFICATION_GRAPH}> {{
    <{graph}> a deliberation:ScopeGraph ; orexis:arrivedBy orexis:Derived ;
        orexis:beliefsOf <{holder}> . }}
}}""")


def find_scopes(store) -> dict[str, str] | None:
    """Every member's scope, predicate or action, from the scope graph asked by class — or
    None where the store holds no scope graph at all, which is a store nobody scoped."""
    graphs = store.graphs_of(SCOPE_GRAPH)
    if not graphs:
        return None
    return {r["member"]: r["scope"] for r in bindings(store.query_over(SCOPES_Q, *graphs))}
