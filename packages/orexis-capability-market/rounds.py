"""A round as a fact — the one writer host and bidder share, each into its own graph.

An open round used to be `open_auction` on the host and `pending` on the bidder: two dicts,
gone with the process, invisible to `orexis-ask`, and unreadable by any rule — so the buying
action's precondition could only say "I could buy here". A round is a belief now, and the
walk `?venue market:hasRound ?r . ?r market:closesAt ?t FILTER(?t > NOW())` is the whole of
"a round is open", on either side. See
knowledge/decisions/a-round-is-a-fact-and-offering-is-an-action.md.

WHAT IS NEVER WRITTEN: the host's `bidWindowS` and `roundCooldownS`. Those are private for a
reason — a venue that published its schedule would let a bidder time its arrival — and the
row carries `closesAt`, the instant the offer already states, never the window it came from.
`tests/test_rounds.py` scans the row for both terms.

The row lives in the agent's OWN graph (`beliefs_graph`), because it is what THIS agent was
told or announced: a bidder's row and the host's row for one round are two facts held by two
minds, and neither reads the other's.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from modality.ontology import beliefs_graph
from modality.store import bindings

from .terms import (CLOSES_AT, HAS_ROUND, LOT_L, MAY_CONVENE_AT, NS, RESERVE_PER_L,
                    ROUND, ROUND_ID)

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
        return (now or datetime.now(timezone.utc)) < self.closes_at


def _uri(auction_id: str) -> str:
    #  Minted from the one identifier the wire hands over, as the keeper mints an intention
    #  from its id — deterministic, so a close can find the row an announce wrote.
    return f"{NS}round_{auction_id}"


def open_round(agent, venue_uri: str, auction_id: str, lot_l: float,
               reserve_per_l: float, closes_at: datetime) -> str:
    """Write the fact that a round is open on this venue. Returns the row's IRI."""
    uri = _uri(auction_id)
    agent.beliefs.update(f"""
INSERT DATA {{ GRAPH <{beliefs_graph(agent.id)}> {{
  <{venue_uri}> <{HAS_ROUND}> <{uri}> .
  <{uri}> a <{ROUND}> ;
    <{ROUND_ID}> "{auction_id}" ;
    <{LOT_L}> "{float(lot_l)}"^^<{_XSD}decimal> ;
    <{RESERVE_PER_L}> "{float(reserve_per_l)}"^^<{_XSD}decimal> ;
    <{CLOSES_AT}> "{closes_at.isoformat()}"^^<{_XSD}dateTime> .
}} }}""")
    return uri


def close_round(agent, auction_id: str) -> None:
    """Retract the round — it is over for this agent, whatever the wire says next."""
    uri = _uri(auction_id)
    agent.beliefs.update(f"""
DELETE {{ GRAPH <{beliefs_graph(agent.id)}> {{ ?v <{HAS_ROUND}> <{uri}> . <{uri}> ?p ?o }} }}
WHERE  {{ GRAPH <{beliefs_graph(agent.id)}> {{ <{uri}> ?p ?o . OPTIONAL {{ ?v <{HAS_ROUND}> <{uri}> }} }} }}""")


def sweep_expired(agent, now: datetime | None = None) -> int:
    """Retract every round past its closesAt — a bidder is never told a round closed, it is
    told the outcome or nothing, so the clock is what ends the row. Returns how many went."""
    gone = [r for r in rounds_of(agent) if not r.is_open(now)]
    for r in gone:
        close_round(agent, r.auction_id)
    return len(gone)


def rounds_of(agent, venue_uri: str | None = None) -> list[Round]:
    """Every round this agent holds a row for, open or not — the caller asks `is_open`."""
    venue = f"FILTER(?v = <{venue_uri}>)" if venue_uri else ""
    rows = bindings(agent.beliefs.query(f"""
SELECT ?r ?v ?id ?lot ?reserve ?closes WHERE {{ GRAPH <{beliefs_graph(agent.id)}> {{
  ?v <{HAS_ROUND}> ?r .
  ?r <{ROUND_ID}> ?id ; <{LOT_L}> ?lot ; <{RESERVE_PER_L}> ?reserve ; <{CLOSES_AT}> ?closes .
  {venue} }} }}"""))
    return [Round(uri=r["r"], venue=r["v"], auction_id=r["id"], lot_l=float(r["lot"]),
                  reserve_per_l=float(r["reserve"]),
                  closes_at=datetime.fromisoformat(r["closes"])) for r in rows]


def convened(agent, venue_uri: str, cooldown_s: float, now: datetime | None = None) -> None:
    """A round just closed on this venue: write when the host may convene the next one.

    The cooldown is a private belief and stays one; what reaches the graph is the INSTANT it
    runs out, so the Offering action's precondition can compare it to NOW() without the
    duration ever sitting on a row. Replaced, never accumulated.
    """
    until = (now or datetime.now(timezone.utc)) + timedelta(seconds=float(cooldown_s))
    agent.beliefs.update(f"""
DELETE {{ GRAPH <{beliefs_graph(agent.id)}> {{ <{venue_uri}> <{MAY_CONVENE_AT}> ?was }} }}
WHERE  {{ GRAPH <{beliefs_graph(agent.id)}> {{ <{venue_uri}> <{MAY_CONVENE_AT}> ?was }} }} ;
INSERT DATA {{ GRAPH <{beliefs_graph(agent.id)}> {{
  <{venue_uri}> <{MAY_CONVENE_AT}> "{until.isoformat()}"^^<{_XSD}dateTime> }} }}""")
