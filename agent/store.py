"""An agent's own belief base — an embedded quad store, private by construction.

There is no shared triplestore. Each agent holds one store containing the world as of the
version it booted with, the vocabulary, its own beliefs and its own readings. Nothing else can
reach it: it is a file inside that agent's container, not a service on a network.

That is the whole of the isolation. Before this, privacy was *enforced* — per-agent credentials
and a per-graph access registry over one shared server — and the enforcement had to be
configured, generated and reloaded, which meant a restart every time a principal was added, and
made twenty worlds depend on one process. Now an agent's store contains only what it may see,
so there is nothing left to enforce. See knowledge/decisions/where-the-belief-base-lives.md.

Two kinds of knowledge live here, and their lifetimes differ:

- **public** — the T-Box and the world. Not the agent's to keep: replaced from the ratified
  files on every start, so an agent that restarts picks up an amended world.
- **private** — its beliefs, and what it has sensed. Written at birth, and the agent's
  thereafter. Start and stop must never touch them.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Callable

import pyoxigraph as ox

# A SPARQL SELECT -> the SPARQL-JSON results dict. The seam every reader is written against,
# unchanged from when this was an HTTP client, so nothing above here knows the difference.
QueryFn = Callable[[str], dict]

# Sent with every query. This is the ONLY set a query may use — some engines silently pre-bind
# common prefixes and others do not, so relying on that works in one and fails in another.
# `test_store.py` holds the codebase to this list.
PREFIXES = """
PREFIX ag:   <http://example.org/agora#>
PREFIX sosa: <http://www.w3.org/ns/sosa/>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>
"""

DECLARED = frozenset(
    line.split()[1].rstrip(":") for line in PREFIXES.splitlines() if line.startswith("PREFIX")
)


# How many decimal places a derived number is written with. Well under the eighteen the store's
# fixed-point xsd:decimal can hold, and far more than a statistic deserves.
#
# This is not tidiness. A Python float divided out to full precision produces lexical forms like
# `0.0039920159680638745` — nineteen fractional digits — which the store accepts, returns, and
# reports the datatype of quite happily, and then FAILS TO COMPARE: every `=` and `>` against it
# raises, and a SPARQL `BIND` whose expression raises leaves its variable unbound while keeping
# the row. So a rule silently produced a solution binding nothing instead of an error, which is
# the most expensive shape a bug can take. Round on the way in and the whole class is gone.
PLACES = 6


def decimal(value: float) -> str:
    """A derived number as a SPARQL literal the store can actually do arithmetic on."""
    return f'"{value:.{PLACES}f}"^^xsd:decimal'


def bindings(results: dict) -> list[dict]:
    """The rows of a SPARQL-JSON result, flattened to {var: value-string}."""
    rows = results.get("results", {}).get("bindings", [])
    return [{k: v.get("value") for k, v in row.items()} for row in rows]


class Store:
    """One agent's quad store. Persistent when given a path, in memory when not.

    A path is the normal case: beliefs must survive a restart, or every start would be a
    partial re-birth and a belief would be configuration again. In-memory exists for tests, and
    for tools that build a world, read it and throw it away.
    """

    def __init__(self, path: str | Path | None = None):
        self.path = str(path) if path else None
        self._store = ox.Store(self.path) if self.path else ox.Store()

    # --- reading ---

    def query(self, sparql: str) -> dict:
        """Read. There is no privileged variant: it is all yours, and only yours."""
        out = io.BytesIO()
        self._store.query(PREFIXES + sparql).serialize(
            output=out, format=ox.QueryResultsFormat.JSON
        )
        return json.loads(out.getvalue())

    # Kept so callers written against the old two-door store still read: with one private store
    # per agent, the distinction it drew — "as myself" versus "as admin" — has no meaning.
    query_all = query

    def get_graph(self, graph_iri: str) -> str:
        """A graph's contents as Turtle, or empty if it does not exist yet.

        A graph nobody has written to is not an error: `:sensed` is absent until the first
        reading, and a caller should be able to say so rather than crash.
        """
        out = io.BytesIO()
        self._store.dump(
            output=out, format=ox.RdfFormat.TURTLE, from_graph=ox.NamedNode(graph_iri)
        )
        return out.getvalue().decode()

    def has_graph(self, graph_iri: str) -> bool:
        """Whether anything has been written here — how birth knows it already happened."""
        return any(self._store.quads_for_pattern(None, None, None, ox.NamedNode(graph_iri)))

    # --- writing ---

    def update(self, sparql: str) -> None:
        self._store.update(PREFIXES + sparql)

    def put_graph(self, graph_iri: str, ttl: str) -> None:
        """Replace a graph with the given Turtle. Public knowledge only — see the module note."""
        graph = ox.NamedNode(graph_iri)
        self._store.remove_graph(graph)
        self._store.load(ttl, format=ox.RdfFormat.TURTLE, to_graph=graph)

    def load_file(self, path: str | Path, graph_iri: str) -> None:
        """Read a ratified file straight into a graph, without going through a string."""
        self._store.load(path=str(path), format=ox.RdfFormat.TURTLE,
                         to_graph=ox.NamedNode(graph_iri))

    def optimize(self) -> None:
        """Compact the store. Blocking, and worth it only when something says it is needed.

        The belief base is an LSM tree, and every reading is a DELETE followed by an INSERT — so
        each one appends a new version plus a tombstone, and the old versions are reclaimed only
        by compaction. Compaction is size-triggered, and a few hundred triples never approach
        any threshold: the file grows for ever while the triple count does not move. Nothing
        reclaimed here is data, so nothing is lost by asking for it explicitly.

        See knowledge/decisions/a-belief-is-a-pick-within-a-range.md and issue #45.
        """
        self._store.optimize()

    def __len__(self) -> int:
        return len(self._store)
