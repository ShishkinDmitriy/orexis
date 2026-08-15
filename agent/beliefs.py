"""An agent's own beliefs — read per capability, from its own graph and nowhere else.

What is here is the *reader*, which is the same for every capability. What each capability
actually believes is declared in its own package (`capabilities/<name>/beliefs.py`) as a
`Block`: a dataclass and the terms that fill it. So this file does not grow when a capability
is added, and a module cannot accidentally depend on another's terms, because it never sees
them.

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
from datetime import datetime, timezone
from typing import get_type_hints

from .ontology import SENSED_GRAPH, beliefs_graph
from .store import QueryFn, bindings


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
class Block:
    """One capability's private parameters: the shape, and the terms that fill it.

    Declared next to the module that reads it. The cast for each field is taken from the
    dataclass annotation, so a block states its types once rather than twice.
    """

    capability: str  # the term, so a missing belief names the capability that wanted it
    cls: type
    # field name -> the FULL IRI of the term carrying it. Full, not a local name with `ag:`
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
                f"{self.cls.__name__} has no field for {', '.join(missing)} — the block and "
                "the dataclass disagree"
            )
        return {field: _CASTS[hints[field]] for field in self.terms}


@dataclass(frozen=True)
class Reading:
    """A sensed value plus when it was taken — the pair a decision must cite."""

    value: float
    result_time: datetime | None

    def age_s(self, now: datetime | None = None) -> float | None:
        if self.result_time is None:
            return None
        return ((now or datetime.now(timezone.utc)) - self.result_time).total_seconds()

    def is_fresh(self, max_age_s: float, now: datetime | None = None) -> bool:
        """Untimed readings are never fresh — an unstamped number can't be shown to be current."""
        age = self.age_s(now)
        return age is not None and age <= max_age_s


def _parse_datetime(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        ts = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


def _parse_reading(results: dict) -> Reading | None:
    rows = bindings(results)
    if not rows or rows[0].get("value") is None:
        return None
    return Reading(value=float(rows[0]["value"]), result_time=_parse_datetime(rows[0].get("ts")))


def _block_query(agent_uri: str, graph: str, terms: dict[str, str]) -> str:
    lines = "\n".join(
        f"  OPTIONAL {{ <{agent_uri}> <{term}> ?{var} }}" for var, term in terms.items()
    )
    return f"""
SELECT {" ".join("?" + v for v in terms)} WHERE {{ GRAPH <{graph}> {{
{lines}
}} }} LIMIT 1"""


class Beliefs:
    """Read-only view of ONE agent's private graph. It can reach no other agent's beliefs."""

    def __init__(self, query: QueryFn, agent_id: str, agent_uri: str):
        self.query = query
        self.agent_id = agent_id
        self.agent_uri = agent_uri
        self.graph = beliefs_graph(agent_id)

    def read(self, block: Block):
        """Fill one capability's block, or refuse to start and say exactly what is missing."""
        rows = bindings(self.query(_block_query(self.agent_uri, self.graph, block.terms)))
        row = rows[0] if rows else {}
        casts = block.casts()
        out, missing = {}, []
        for field, term in block.terms.items():
            raw = row.get(field)
            if raw is None:
                missing.append(term)
            else:
                out[field] = casts[field](raw)
        if missing:
            raise BeliefError(
                f"{self.agent_id} composed {block.capability} but its beliefs graph "
                f"<{self.graph}> is missing {', '.join(missing)} — run agora-validate"
            )
        return block.cls(**out)

    def read_optional(self, block: Block):
        """Fill a block, or None if the agent said nothing about it at all.

        This is NOT a relaxation of the rule above. A block that is wholly absent is a decision
        stated by omission — the same way a beliefs file with no `market:Bidding` block says this
        agent holds no stake — and the caller is expected to do nothing rather than to invent a
        value. A block that is PARTIALLY present is still an error and still refuses, because
        half an answer is an authoring slip rather than a choice.

        Only for blocks whose absence is meaningful and harmless. A capability's parameters are
        neither: an agent missing those must not start.
        """
        rows = bindings(self.query(_block_query(self.agent_uri, self.graph, block.terms)))
        row = rows[0] if rows else {}
        if not any(row.get(field) is not None for field in block.terms):
            return None
        return self.read(block)

    def current_reading(self, subject_uri: str, observed_property: str) -> Reading | None:
        """The latest observation of one property of a subject, with the time it was taken.

        The property is required rather than optional, and that is deliberate. It used to be
        absent, and a subject with two sensors returned whichever had written last — so an
        omitted argument would silently restore exactly the defect this signature exists to
        prevent. A caller that does not know which property it means does not know what it is
        asking.
        """
        # The feature may be the subject itself, or a PATCH of it (#98): an observation of a
        # sosa:Sample answers for what it samples, newest first. The sample link lives in the
        # world graph and the observation in :sensed, so the walk sits OUTSIDE the GRAPH
        # clause — inside it, the pattern would have to match entirely within :sensed and the
        # patch reading would silently vanish, which is AGENTS.md's narrowed-SELECT trap.
        # Newest-across-patches is deliberately NOT aggregation: nothing here averages, and
        # the seam one-agent-many-sensors.md leaves open is still open — this is only which
        # single witness answers when several patches testify.
        return _parse_reading(self.query(f"""
SELECT ?value ?ts WHERE {{
  {{ BIND(<{subject_uri}> AS ?foi) }} UNION {{ ?foi sosa:isSampleOf <{subject_uri}> }}
  GRAPH <{SENSED_GRAPH}> {{
    ?obs sosa:hasFeatureOfInterest ?foi ;
         sosa:observedProperty <{observed_property}> ;
         sosa:hasSimpleResult ?value .
    OPTIONAL {{ ?obs sosa:resultTime ?ts }}
  }}
}} ORDER BY DESC(?ts) LIMIT 1"""))
