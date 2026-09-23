"""Reading the store's scopes — which scope each predicate and each action is in.

`scope_actions` writes the partition; this reads it back, asking the scope graphs by class. A
store holding none at all answers None, which is a store nobody scoped and which the
derivation refuses to guess about; a scoped store with nothing in it answers an empty map.
"""

from __future__ import annotations

import pyoxigraph as ox

from orexis.agent.store import rows

SCOPES_Q = """
SELECT ?member ?scope WHERE { ?member planning:inScope ?scope }"""

#  EVERY STANDING SCOPE GRAPH, asked of the catalogue by class — what a run replaces, whatever
#  each is called, including a per-agent one a volume was left with before the partition
#  became the store's.
STANDING_Q = """
SELECT ?g WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a planning:ScopeGraph } }
ORDER BY ?g"""


def find_scopes(store: ox.Store) -> dict[str, str] | None:
    """Every member's scope, predicate or action, from the scope graphs asked by class — or
    None where the store holds none at all, which is a store nobody scoped."""
    graphs = [row["g"] for row in rows(store, STANDING_Q)]
    if not graphs:
        return None
    return {r["member"]: r["scope"] for r in rows(store, SCOPES_Q, graphs)}
