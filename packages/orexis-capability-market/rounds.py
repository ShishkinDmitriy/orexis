"""A round as a fact — the one writer host and bidder share, each into its own graph.

An open round used to be `open_auction` on the host and `pending` on the bidder: two dicts,
gone with the process, invisible to `orexis-ask`, and unreadable by any rule — so the buying
action's precondition could only say "I could buy here". A round is a belief now, and the
walk `?venue market:hasRound ?r` is the whole of "a round is open", on either side: THE ROW'S
PRESENCE IS THE OPENNESS (#599). It carried `FILTER(?t > NOW())` until the host began
declaring the close, because a bidder that lost was told nothing and had to end the round by
its own arithmetic — which made a fact about the venue something each bidder computed
privately, with its own clock, inside every rule that asked. See
knowledge/decisions/a-round-is-a-fact-and-offering-is-an-action.md.

WHAT IS NEVER WRITTEN: the host's `bidWindowS` and `roundCooldownS`. Those are private for a
reason — a venue that published its schedule would let a bidder time its arrival — and the
row carries `closesAt`, the instant the offer already states, never the window it came from.
`tests/test_rounds.py` scans the row for both terms.

The row lives in a graph OF ITS OWN, one per round, classified as this agent's — what THIS
agent was told or announced: a bidder's row and the host's row for one round are two facts
held by two minds, and neither reads the other's — AND HOLDING DURING ITS PERIOD (#620,
a-graph-holds-during-a-stretch): from the offer to `closesAt`, said of the graph in the periods
table, so the door hands the round to a reader asking about an instant inside it and to nobody
asking about one past it. A search standing at a future instant — a want met at a predicted
crossing — therefore never plans a bid into a round that will have closed. The retrofit the
period record deferred until measured; the measurement is on #620. What ends the row is still
the host's word (`close_round` drops the graph); the sweep drops what outlived its period. The
cooling row stays in the agent's own beliefs graph: it is a state, not a stretch.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from orexis_agent_progression.ontology import CLASSIFICATION_GRAPH, GRAPH_PREFIX, PERIODS_GRAPH
from orexis_agent_progression.store import bindings

from .terms import (CLOSES_AT, COOLING_UNTIL, HAS_ROUND, LOT_L, NS, RESERVE_PER_L,
                    ROUND, ROUND_ID)
from orexis_agent_progression import clock

_XSD = "http://www.w3.org/2001/XMLSchema#"


@dataclass(frozen=True)
class Round:
    uri: str
    venue: str
    auction_id: str
    lot_l: float
    reserve_per_l: float
    closes_at: datetime

    def is_open(self, now: datetime | None = None) -> bool:
        return (now or clock.now()) < self.closes_at


def _uri(auction_id: str) -> str:
    #  Minted from the one identifier the wire hands over, as the keeper mints an intention
    #  from its id — deterministic, so a close can find the row an announce wrote.
    return f"{NS}round_{auction_id}"


_ROUNDS = GRAPH_PREFIX + "round/"
RECEIVED = "http://example.org/orexis#Received"
RECORDED = "http://example.org/orexis#Recorded"


def round_graph(agent_id: str, auction_id: str) -> str:
    """ONE round's graph in ONE agent's store — the unit a period is said of."""
    return f"{_ROUNDS}{agent_id}/{auction_id}"


def open_round(agent, venue_uri: str, auction_id: str, lot_l: float,
               reserve_per_l: float, closes_at: datetime, arrival: str = RECEIVED,
               opened_at: datetime | None = None) -> str:
    """Write the fact that a round is open on this venue: its own graph, classified as this
    agent's — `arrival` says how it came, received from the host or recorded by it — and
    holding from now to `closes_at`. Returns the row's IRI."""
    uri = _uri(auction_id)
    graph = round_graph(agent.id, auction_id)
    since = (opened_at or clock.now()).isoformat()
    agent.beliefs.update(f"""
INSERT DATA {{
  GRAPH <{graph}> {{
    <{venue_uri}> <{HAS_ROUND}> <{uri}> .
    <{uri}> a <{ROUND}> ;
      <{ROUND_ID}> "{auction_id}" ;
      <{LOT_L}> "{float(lot_l)}"^^<{_XSD}decimal> ;
      <{RESERVE_PER_L}> "{float(reserve_per_l)}"^^<{_XSD}decimal> ;
      <{CLOSES_AT}> "{closes_at.isoformat()}"^^<{_XSD}dateTime> . }}
  GRAPH <{CLASSIFICATION_GRAPH}> {{
    <{graph}> a orexis:BeliefGraph ; orexis:arrivedBy <{arrival}> . }}
  GRAPH <{PERIODS_GRAPH}> {{
    <{graph}> dcterms:temporal [ a dcterms:PeriodOfTime ;
      orexis:start "{since}"^^<{_XSD}dateTime> ;
      orexis:end "{closes_at.isoformat()}"^^<{_XSD}dateTime> ] . }}
}}""")
    return uri


def close_round(agent, auction_id: str) -> None:
    """Retract the round — it is over for this agent, whatever the wire says next: the graph,
    its classification and its period all go."""
    agent.beliefs.drop_graph(round_graph(agent.id, auction_id))


def cooling_graph(agent_id: str, venue_uri: str) -> str:
    """ONE venue's cooling in ONE agent's store — the unit a period is said of (#645)."""
    return f"{GRAPH_PREFIX}cooling/{agent_id}/{venue_uri.rsplit('#', 1)[-1]}"


def rounds_of(agent, venue_uri: str | None = None, at: datetime | None = None) -> list[Round]:
    """Every round this agent holds at `at` — now, by default: a round is a graph holding during
    its period, and the door hands back only those. `is_open` still answers for a caller
    holding a row from earlier."""
    venue = f"FILTER(?v = <{venue_uri}>)" if venue_uri else ""
    rows = bindings(agent.beliefs.query_at(f"""
SELECT ?r ?v ?id ?lot ?reserve ?closes WHERE {{
  ?v <{HAS_ROUND}> ?r .
  ?r <{ROUND_ID}> ?id ; <{LOT_L}> ?lot ; <{RESERVE_PER_L}> ?reserve ; <{CLOSES_AT}> ?closes .
  {venue} }}""", at=at))
    return [Round(uri=r["r"], venue=r["v"], auction_id=r["id"], lot_l=float(r["lot"]),
                  reserve_per_l=float(r["reserve"]),
                  closes_at=datetime.fromisoformat(r["closes"])) for r in rows]


def convened(agent, venue_uri: str, cooldown_s: float, now: datetime | None = None) -> None:
    """A round just closed on this venue: the venue is COOLING until the cooldown runs out.

    The cooldown is a private belief and stays one; what reaches the graph is the fact that
    this venue is cooling, carrying the instant it stops as its horizon. The Offering action's
    precondition asks whether the row is there and compares nothing (#598) — it read
    `?may <= NOW()` while the term named the instant instead of the state. A GRAPH HOLDING
    DURING ITS PERIOD (#645): from the close to the horizon, so the door hands the row to
    nobody once the cooldown ran out, with no timer and no sweep of this package's own.
    """
    since = now or clock.now()
    until = since + timedelta(seconds=float(cooldown_s))
    graph = cooling_graph(agent.id, venue_uri)
    agent.beliefs.drop_graph(graph)
    agent.beliefs.update(f"""
INSERT DATA {{
  GRAPH <{graph}> {{ <{venue_uri}> <{COOLING_UNTIL}> "{until.isoformat()}"^^<{_XSD}dateTime> . }}
  GRAPH <{CLASSIFICATION_GRAPH}> {{ <{graph}> a orexis:BeliefGraph ; orexis:arrivedBy <{RECORDED}> . }}
  GRAPH <{PERIODS_GRAPH}> {{
    <{graph}> dcterms:temporal [ a dcterms:PeriodOfTime ;
      orexis:start "{since.isoformat()}"^^<{_XSD}dateTime> ;
      orexis:end "{until.isoformat()}"^^<{_XSD}dateTime> ] . }}
}}""")
