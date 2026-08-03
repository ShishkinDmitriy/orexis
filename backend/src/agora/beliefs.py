"""An agent's own beliefs — read per capability, from its own graph and nowhere else.

Each code module asks for exactly the block its ontology module defines: the polling module
asks for `PollingBeliefs`, the bidding module for `BiddingBeliefs`. A module cannot
accidentally depend on another's terms, because it never sees them.

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

from .ontology import SENSED_GRAPH, beliefs_graph
from .store import QueryFn, bindings


class BeliefError(RuntimeError):
    """A capability was composed onto an agent without the beliefs it needs to run."""


@dataclass(frozen=True)
class PollingBeliefs:
    """ag:Polling — how closely this agent watches, and how stale it lets a reading get."""

    fast_sleep_s: int
    slow_sleep_s: int
    max_age_s: int


@dataclass(frozen=True)
class ListeningBeliefs:
    """ag:Listening — only the freshness rule. There is no cadence to hold: the hardware
    pushes on its own clock, so requiring a cadence would be requiring a fiction."""

    max_age_s: int


@dataclass(frozen=True)
class BiddingBeliefs:
    """ag:Bidding — its wallet, its desire, its limits, and its private value curve."""

    endowment: float
    target: float
    low: float
    high: float
    litres_per_fraction: float
    max_value_per_l: float


@dataclass(frozen=True)
class HostingBeliefs:
    """ag:Hosting — the seller's terms and the shape of a round."""

    quantity_l: float
    reserve_price_per_l: float
    bid_window_s: int
    cooldown_s: int


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


# Each entry: local name -> the ontology term that carries it. The module's whole contract.
_POLLING_TERMS = {
    "fast_sleep_s": "fastSleepS",
    "slow_sleep_s": "slowSleepS",
    "max_age_s": "maxReadingAgeS",
}
_LISTENING_TERMS = {"max_age_s": "maxReadingAgeS"}
_BIDDING_TERMS = {
    "endowment": "hasEndowment",
    "target": "hasTarget",
    "low": "bandLow",
    "high": "bandHigh",
    "litres_per_fraction": "litresPerFraction",
    "max_value_per_l": "maxValuePerL",
}
_HOSTING_TERMS = {
    "quantity_l": "offerQuantityL",
    "reserve_price_per_l": "reservePricePerL",
    "bid_window_s": "bidWindowS",
    "cooldown_s": "roundCooldownS",
}


def _block_query(agent_uri: str, graph: str, terms: dict[str, str]) -> str:
    lines = "\n".join(
        f"  OPTIONAL {{ <{agent_uri}> ag:{term} ?{var} }}" for var, term in terms.items()
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

    def _block(self, capability: str, terms: dict[str, str], cast: dict) -> dict:
        rows = bindings(self.query(_block_query(self.agent_uri, self.graph, terms)))
        row = rows[0] if rows else {}
        out, missing = {}, []
        for var, term in terms.items():
            raw = row.get(var)
            if raw is None:
                missing.append(f"ag:{term}")
            else:
                out[var] = cast[var](raw)
        if missing:
            raise BeliefError(
                f"{self.agent_id} composed {capability} but its beliefs graph <{self.graph}> "
                f"is missing {', '.join(missing)} — run agora-validate"
            )
        return out

    def polling(self) -> PollingBeliefs:
        cast = {k: (lambda x: int(float(x))) for k in _POLLING_TERMS}
        return PollingBeliefs(**self._block("ag:Polling", _POLLING_TERMS, cast))

    def listening(self) -> ListeningBeliefs:
        cast = {"max_age_s": lambda x: int(float(x))}
        return ListeningBeliefs(**self._block("ag:Listening", _LISTENING_TERMS, cast))

    def bidding(self) -> BiddingBeliefs:
        cast = {k: float for k in _BIDDING_TERMS}
        return BiddingBeliefs(**self._block("ag:Bidding", _BIDDING_TERMS, cast))

    def hosting(self) -> HostingBeliefs:
        cast = {k: float for k in _HOSTING_TERMS}
        cast["bid_window_s"] = cast["cooldown_s"] = lambda x: int(float(x))
        return HostingBeliefs(**self._block("ag:Hosting", _HOSTING_TERMS, cast))

    def current_reading(self, subject_uri: str) -> Reading | None:
        """The latest observation of a subject, with the time it was taken."""
        return _parse_reading(self.query(f"""
SELECT ?value ?ts WHERE {{ GRAPH <{SENSED_GRAPH}> {{
  ?obs sosa:hasFeatureOfInterest <{subject_uri}> ;
       sosa:hasSimpleResult ?value .
  OPTIONAL {{ ?obs sosa:resultTime ?ts }}
}} }} ORDER BY DESC(?ts) LIMIT 1"""))
