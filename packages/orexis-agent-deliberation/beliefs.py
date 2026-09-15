"""An agent's own beliefs — read per capability, from its own graph and nowhere else.

What is here is the *reader*, which is the same for every capability. What each capability
runs on is declared in its own package as `Picks` — a dataclass and the terms that fill it,
one entry per pick (knowledge/domain/pick.md): a point the agent chose inside its mandate,
which #297 sorted as a want. So this file does not grow when a capability is added, and a
module cannot accidentally depend on another's terms, because it never sees them.

**There are no defaults.** If a belief is missing the agent refuses to start, naming the term
and the graph. A silent fallback would be a policy decision made in code — exactly what this
whole design removes — and it would mask a genesis error until the moment it mattered. The
SHACL module for each capability is what makes this failure impossible in a validated world.

Also here: reading `:sensed`, since a reading is the other thing an agent believes. Readings
carry their `resultTime` because under agent-driven sensing the agent owns the cadence, and
could otherwise decide when to look at a comfortable number.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import get_type_hints

from orexis_agent_progression.ontology import beliefs_graph
from orexis_agent_progression.store import bindings


class BeliefError(RuntimeError):
    """A capability was composed onto an agent without the beliefs it needs to run."""


# How a literal off the wire becomes the type the dataclass declared. Integers come through
# SPARQL as decimals often enough that int("30.0") would be the wrong kind of strict.
_CASTS = {
    int: lambda x: int(float(x)),
    float: float,
    str: str,
    bool: lambda x: str(x).lower() in ("1", "true", "yes"),
}


@dataclass(frozen=True)
class Picks:
    """One capability's private parameters: the shape, and the terms that fill it.

    Declared next to the module that reads it. The cast for each field is taken from the
    dataclass annotation, so the picks state their types once rather than twice.
    """

    capability: str  # the term, so a missing belief names the capability that wanted it
    cls: type
    # field name -> the FULL IRI of the term carrying it. Full, not a local name with `orexis:`
    # assumed around it: a belief term belongs to the package that declares it, and since
    # `capabilities/market` took a namespace of its own there is no one prefix to assume.
    # Each package builds these with its own `term()`, so this reader never learns where any
    # of them live. See knowledge/decisions/a-package-owns-its-namespace.md.
    terms: dict[str, str]

    def casts(self) -> dict:
        hints = get_type_hints(self.cls)
        missing = [f for f in self.terms if f not in hints]
        if missing:
            raise BeliefError(
                f"{self.cls.__name__} has no field for {', '.join(missing)} — the picks and "
                "the dataclass disagree"
            )
        return {field: _CASTS[hints[field]] for field in self.terms}


def _picks_query(agent_uri: str, graph: str, terms: dict[str, str]) -> str:
    lines = "\n".join(
        f"  OPTIONAL {{ <{agent_uri}> <{term}> ?{var} }}" for var, term in terms.items()
    )
    return f"""
SELECT {" ".join("?" + v for v in terms)} WHERE {{ GRAPH <{graph}> {{
{lines}
}} }} LIMIT 1"""


class Beliefs:
    """The belief modality: ONE agent's belief base, owned — the store, and the typed reads.

    A modality is a class that owns its store, and the agent never learns what kind
    (a-store-is-a-modality). This one's choices: the store genesis built into the agent's
    volume, WRITABLE at runtime — believing is recording and receiving, so update stays on
    the surface — and the PREMISE store the desire modality derives from: the world, the
    records, the readings. The whole store surface is forwarded, because the belief base
    still fronts every graph that has no store of its own (deliberation's trace, review's
    evidence, the records); what this class
    adds of its own is the typed reads below, and the isolation stands as it always did: the
    store is this process's alone, so no other agent's beliefs are reachable to forward.

    The constructor takes the store and the ONE identifier a process is legitimately handed —
    its own local id, rule 1's single stated exception — and discovers everything else,
    URI included, from the store: the world says `?a orexis:localId "<id>"`, and the URI is the
    answer, not an argument. An empty volume at birth is why the id cannot be discovered too;
    by the time this class exists, birth has run and the lookup cannot miss.
    """

    def __init__(self, store, agent_id: str):
        self._store = store
        self.agent_id = agent_id
        self.graph = beliefs_graph(agent_id)
        #  `a orexis:Agent` is load-bearing, not decoration: a plant, a sensor and a valve carry
        #  `orexis:localId` too, and a world names its subject after its agent — so the bare
        #  pattern matches two things and LIMIT 1 picks by the store's internal order, which
        #  a change to load order silently flips. It did: every pick read asked the PLANT.
        rows = bindings(store.query(
            f'SELECT ?a WHERE {{ ?a a orexis:Agent ; orexis:localId "{agent_id}" }} LIMIT 1'))
        if not rows:
            raise BeliefError(
                f"no agent with localId '{agent_id}' in this store — "
                "was the world loaded before the modality was built?")
        self.agent_uri = rows[0]["a"]

    def __getattr__(self, name):
        return getattr(self._store, name)

    def __len__(self) -> int:
        return len(self._store)

    def read(self, picks: Picks):
        """Fill one capability's picks, or refuse to start and say exactly what is missing.

        Kept on the belief modality although a parameter is a PICK — a want, by #297's sort —
        because the belief base is the pick RECORD: what was authored at birth and what review
        has since re-picked, persistent in the volume. The desire modality serves the same
        picks from its rebuilt copy, and modules read THERE; this reader remains for the
        record's own consumers — validation, review's revert — and as the machinery both
        share.
        """
        return read_picks(self.query, self.agent_uri, self.graph, self.agent_id, picks)

    def read_optional(self, picks: Picks):
        """The picks, or None if the agent said nothing about it at all.

        This is NOT a relaxation of the rule above. Picks wholly absent are is a decision
        stated by omission — the same way a beliefs file with no `market:Bidding` entries says this
        agent holds no stake — and the caller is expected to do nothing rather than to invent a
        value. Picks PARTIALLY present are still an error and still refuse, because
        half an answer is an authoring slip rather than a choice.

        Only for picks whose absence is meaningful and harmless. A capability's parameters are
        neither: an agent missing those must not start.
        """
        return read_picks_optional(self.query, self.agent_uri, self.graph,
                                   self.agent_id, picks)


def read_picks(query, agent_uri: str, graph: str, agent_id: str, picks: Picks):
    """The picks machinery both modalities share: fill a dataclass or name what is missing."""
    rows = bindings(query(_picks_query(agent_uri, graph, picks.terms)))
    row = rows[0] if rows else {}
    casts = picks.casts()
    out, missing = {}, []
    for field, term in picks.terms.items():
        raw = row.get(field)
        if raw is None:
            missing.append(term)
        else:
            out[field] = casts[field](raw)
    if missing:
        raise BeliefError(
            f"{agent_id} composed {picks.capability} but its beliefs graph "
            f"<{graph}> is missing {', '.join(missing)} — run orexis-validate"
        )
    return picks.cls(**out)


def read_picks_optional(query, agent_uri: str, graph: str, agent_id: str, picks: Picks):
    """A block, or None where the agent said nothing about it at all — see
    `Beliefs.read_optional` for why partial presence still refuses."""
    rows = bindings(query(_picks_query(agent_uri, graph, picks.terms)))
    row = rows[0] if rows else {}
    if not any(row.get(field) is not None for field in picks.terms):
        return None
    return read_picks(query, agent_uri, graph, agent_id, picks)
