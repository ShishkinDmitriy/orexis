"""My venues, from the world — the market's own wiring, loaded by the market.

See sensing's `wiring.py` for why this left `agent/world.py`. A venue is loaded twice over,
by relation: the ones I bid in, and the ones I host.
"""

from __future__ import annotations

from dataclasses import dataclass

from orexis_modality_graph.store import bindings


@dataclass(frozen=True)
class Market:
    """A venue and its three channels."""

    uri: str
    local_id: str
    resource: str  # URI of what is allocated
    offer_topic: str
    bid_topic: str
    claim_topic: str
    redeem_topic: str | None = None  # absent in a world authored before #132 — paper, unspendable
    capacity_l: float = 0.0  # physical ceiling of the resource — the allocation limit
    #  How long this venue holds a winner's claim. None where the world authored no window,
    #  which is the same era as no redeem channel: the host redeemed on issue and no winner
    #  ever waited. A stated window is what puts an expiry on every claim the venue issues.
    redeem_window_s: float | None = None




def _markets_q(agent_uri: str, relation: str) -> str:
    return f"""
SELECT ?market ?localId ?resource ?offerTopic ?bidTopic ?claimTopic ?redeemTopic ?window ?capacity
WHERE {{ 
  <{agent_uri}> market:{relation} ?market .
  ?market ag:localId ?localId ; market:marketFor ?resource ;
          market:offerTopic ?offerTopic ; market:bidTopic ?bidTopic ; market:claimTopic ?claimTopic .
  OPTIONAL {{ ?market market:redeemTopic ?redeemTopic }}
  OPTIONAL {{ ?market market:redeemWindowS ?window }}
  OPTIONAL {{ ?resource market:lotCapacity ?capacity }}
 }}"""


# What each participant may be allocated at most, in one trade. A DOMAIN derives this — the
# span of what its subject survives, in litres — and states it in the market's word, exactly as
# a domain states `market:lotCapacity` for the total. This reads the conclusion and names no
# domain. See packages/orexis-plant-water/rules.ru and #270.
def _ceilings_q(market_uri: str) -> str:
    return f"""
SELECT ?agentId ?ceiling WHERE {{
  ?agent market:bidsIn <{market_uri}> ; ag:localId ?agentId ;
         market:allocationCeilingL ?ceiling }}"""


# Everyone entitled to bid here — the host needs this to know who may answer an offer.
def _participants_q(market_uri: str) -> str:
    return f"""
SELECT ?agentId WHERE {{ 
  ?agent market:bidsIn <{market_uri}> ; ag:localId ?agentId  }}"""


def _market_from(row: dict) -> Market:
    return Market(
        uri=row["market"], local_id=row["localId"], resource=row["resource"],
        offer_topic=row["offerTopic"], bid_topic=row["bidTopic"],
        claim_topic=row["claimTopic"], redeem_topic=row.get("redeemTopic"),
        redeem_window_s=float(row["window"]) if row.get("window") else None,
        capacity_l=float(row["capacity"]) if row.get("capacity") else 0.0,
    )




def bidding_markets_of(query, agent_uri: str) -> tuple[Market, ...]:
    return tuple(_market_from(r) for r in bindings(query(_markets_q(agent_uri, "bidsIn"))))


def hosted_markets_of(query, agent_uri: str) -> tuple[Market, ...]:
    return tuple(_market_from(r) for r in bindings(query(_markets_q(agent_uri, "hosts"))))


def participants(query, market: Market) -> frozenset[str]:
    """Who may bid here. Public — a host must know who its counterparties are."""
    return frozenset(r["agentId"] for r in bindings(query(_participants_q(market.uri))))


def allocation_ceilings(query, market: Market) -> dict[str, float]:
    """The most each participant may be allocated in one trade, for whoever has one.

    A participant is ABSENT rather than zero when its subject states no survival range — a
    ceiling of 0.0 would refuse every trade it is in, and `world/sensing`'s agents are exactly
    that case. Clearing treats absent as unchecked, which is the honest answer: nothing in the
    world says what too much would be.
    """
    return {r["agentId"]: float(r["ceiling"])
            for r in bindings(query(_ceilings_q(market.uri)))}


def node_of(query, agent_id: str) -> str | None:
    """A participant's node, from the one thing a bid or a claim carries: its id. Public
    wiring, so an act names an agent the world declares and never a string somebody sent."""
    rows = bindings(query(
        f'SELECT ?a WHERE {{ ?a a <http://example.org/orexis#Agent> ; '
        f'<http://example.org/orexis#localId> "{agent_id}" }}'))
    return rows[0]["a"] if rows else None
