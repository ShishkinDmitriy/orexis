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

from . import genesis
from orexis_agent_progression.store import Store

# Re-exported, because every tool that reads a ratified world reaches for these in the same
# breath as `dataset()` and should not have to know that one lives in `genesis`.
from .genesis import world_dir, world_files, worlds  # noqa: F401


def dataset(world: str) -> rdflib.Dataset:
    """One world as an agent sees it, handed to rdflib to query.

    **The derivation is not repeated here — it is copied.** A `Store` is built and
    `refresh_public` run against it, exactly as an agent does at boot, and the resulting public
    graphs are then poured into an rdflib Dataset. So the vocabulary, the entailments and every
    package's rules are computed once, by one engine, and rdflib only ever *reads* the answer.

    This used to be a second implementation: rdflib parsed the same files and re-ran the same
    `rules.ru`, which is two engines deriving separately and hoping to agree. They did not. The
    closure was never run on this side at all, so a world whose sensor is typed as a *kind* of
    sensor derived its capabilities inside an agent and not in `orexis-compose` — the same fault
    issue #27 was opened for, surviving in the half of the system #27 did not look at.

    It also sidesteps an rdflib behaviour worth knowing: **`USING` there attempts to dereference
    the graph IRI over HTTP** rather than resolving it against the dataset, so the derivation
    rules cannot run on rdflib at all now that they span graphs. Nothing is lost — they no longer
    need to.

    `default_union=True` is the rdflib spelling of what `store.query` does with `default_graph`:
    an unqualified pattern reads everything public, so the same query means the same thing here
    as against a running agent's store.
    """
    st = Store()  # in memory: built, copied out, thrown away
    # The module-local name, not `genesis.world_dir` — a test that redirects a world redirects it
    # here, and reaching through the other module would silently ignore that.
    genesis.refresh_public(st, world_dir(world))

    ds = rdflib.Dataset(default_union=True)
    for iri in st.public_graphs():
        turtle = st.get_graph(iri)
        if turtle.strip():
            ds.graph(rdflib.URIRef(iri)).parse(data=turtle, format="turtle")
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
