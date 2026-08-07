"""The ratified world, read from the outside.

Every tool that provisions a world has the same first problem: it must know the world *before*
anything is running — before a broker will accept a connection, before an agent has a belief
base, before there is a store to ask. So it does what an agent does at boot and what nobody
else may do at all: parse the Turtle, merge the T-Box, run every package's `rules.ru`, and
hold the answer in memory.

That is the same derivation an agent performs on itself. Running it rather than guessing is
what lets these tools grant *exactly* what the wiring implies — a bucket for an agent that
observes, a topic for an agent that bids — instead of maintaining a second list beside the
world that would drift from it. See knowledge/decisions/capability-packages.md.

**This module is for the operator, never for a member.** An agent is handed one world and one
id, and must not learn that other worlds exist; the sovereign who provisions the infrastructure
is precisely the party who does know, and is the reason `all_worlds()` is here. Nothing under
`capabilities/` or `transports/` may import it.

See knowledge/decisions/series-and-bus-isolation.md.
"""

from __future__ import annotations

import rdflib

from . import loader
from .genesis import world_dir, world_files, worlds
from .ontology import ONTOLOGY_GRAPH, WORLD_GRAPH


def dataset(world: str) -> rdflib.Dataset:
    """One world, composed exactly as an agent composes it: T-Box, topology, derivation."""
    ds = rdflib.Dataset()
    for path in loader.ontology_files():
        ds.graph(rdflib.URIRef(ONTOLOGY_GRAPH)).parse(path, format="turtle")
    for path in world_files(world_dir(world)):
        ds.graph(rdflib.URIRef(WORLD_GRAPH)).parse(path, format="turtle")
    for rule in loader.rule_files():
        ds.update(rule.read_text())
    return ds


def rows(ds: rdflib.Dataset, sparql: str) -> list[dict]:
    """Query results as plain dicts, so callers never touch rdflib term types.

    Queries here spell IRIs out in full rather than using prefixes: this runs on rdflib, which
    silently pre-binds common ones, so a prefixed query can pass every test and then fail
    against a store that binds nothing. See backend/tests/test_store.py.
    """
    return [{str(k): str(v) for k, v in row.asdict().items()} for row in ds.query(sparql)]


def all_worlds() -> list[str]:
    """Every world on disk. The operator's view — see the note at the top of this module."""
    return worlds()
