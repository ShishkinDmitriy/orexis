"""market:Hosting — run auctions in a market: announce, collect, match, clear, issue.

This module exists in this shape *because* each agent is its own process. The host cannot
compute anyone's bid — the valuation is private and lives in another process entirely — so an
auction is a conversation rather than a calculation:

    participant announces it is in trouble (its own judgment, voluntarily disclosed)
        -> host announces an offer with a deadline          [market:offerTopic]
        -> each bidder answers with a number only it can compute   [market:bidTopic/<agent>]
        -> host matches, clearing validates, vouchers go back  [market:voucherTopic/<agent>]
        -> actuation redeems them against the hardware

The host proposes; clearing disposes. `auction.py`, `clearing.py` and `market.py` are pure —
this module is only the choreography around them. **How bids become an allocation is not part
of the choreography**: it is matching, `market:BidMatchingCapability`, asked for by family exactly as
actuation is, so this package does not know that pay-as-bid is implemented in Python at all. See
knowledge/domain/bid-matching.md and knowledge/decisions/bid-matching-is-a-capability.md.

Vocabulary: capabilities/market/ontology.ttl. Rules: capabilities/market/shapes.ttl.
See knowledge/domain/auction.md, knowledge/domain/round.md,
knowledge/decisions/clearing-as-validator.md.
"""

from __future__ import annotations

import time
import uuid

from agent.auction import run_auction
from agent.market import Bid, Limits, MarketState, Offer
from agent.module import Module, Timer
from agent.ontology import WORLD_GRAPH
from agent.store import bindings
from agent.world import participants

from .beliefs import HOSTING_BLOCK
from .terms import ACTUATION, HOSTING, BID_MATCHING


def _event_topics_q(market_uri: str) -> str:
    """Where my participants announce what they notice. Public, like the rest of the wiring."""
    return f"""
SELECT ?agentId ?eventTopic WHERE {{ 
  ?agent market:bidsIn <{market_uri}> ; ag:localId ?agentId ; mqtt:eventTopic ?eventTopic  }}"""


class HostingModule(Module):
    CAPABILITY = HOSTING
    name = "hosting"

    def __init__(self, agent):
        super().__init__(agent)
        self.beliefs = agent.beliefs.read(HOSTING_BLOCK)
        self.markets = self.me.hosted_markets
        self.participants = {
            m.uri: participants(agent.store.query, m) for m in self.markets
        }
        self.event_topics = {}  # topic -> market
        for market in self.markets:
            for row in bindings(agent.store.query(_event_topics_q(market.uri))):
                self.event_topics[row["eventTopic"]] = market

        self.open_auction: dict | None = None
        self.last_auction_at = 0.0
        self._timer: Timer | None = None

    def subscriptions(self) -> list[str]:
        topics = list(self.event_topics)
        for market in self.markets:
            topics.append(f"{market.bid_topic}/+")
        return topics

    def stop(self) -> None:
        if self._timer:
            self._timer.stop()

    # --- what opens an auction ---

    def handle(self, topic: str, payload: bytes) -> bool:
        market = self.event_topics.get(topic)
        if market is not None:
            self.on_participant_event(market, self.parse(payload) or {})
            return True
        for m in self.markets:
            if topic.startswith(m.bid_topic + "/"):
                self.on_bid(m, self.parse(payload) or {})
                return True
        return False

    def on_participant_event(self, market, event: dict) -> None:
        """A participant said it is in trouble. Scarcity is what condenses an auction."""
        if event.get("band") != "LOW":
            return
        now = time.monotonic()
        if now - self.last_auction_at < self.beliefs.cooldown_s:
            return  # a flapping participant must not be able to spam the market
        if self.open_auction is not None:
            return
        self.announce(market, trigger=event.get("agent", "?"))

    def matcher(self):
        """Whichever of my capabilities can turn bids into an allocation, or None.

        Asked for by family, so this package does not know that pay-as-bid is implemented in
        Python at all — the same way `redeem` asks for whoever can actuate. A host that names
        a way of matching nothing implements gets None here, which is the honest outcome of
        declaring a member ahead of its module.
        """
        return self.agent.provider(BID_MATCHING)

    def announce(self, market, trigger: str) -> None:
        auction_id = uuid.uuid4().hex[:8]
        self.last_auction_at = time.monotonic()
        self.open_auction = {"auction_id": auction_id, "market": market, "bids": {}}
        matcher = self.matcher()
        self.log.info("auction %s opened on %s (%s is LOW) — %.2f L, reserve €%.2f, %ss to bid",
                      auction_id, market.local_id, trigger, self.beliefs.quantity_l,
                      self.beliefs.reserve_price_per_l, self.beliefs.bid_window_s)
        self.publish(market.offer_topic, {
            "auction_id": auction_id,
            "host": self.me.agent_id,
            "quantity_l": self.beliefs.quantity_l,
            "reserve_price_per_l": self.beliefs.reserve_price_per_l,
            "closes_in_s": self.beliefs.bid_window_s,
            # The matching travels with the invitation, as a real auction announces its terms
            # when it opens. A bidder cannot bid well against terms it does not know — under
            # pay-as-bid a winner pays what it offered, so the honest strategy is to shade,
            # and under a uniform price it does not. Read off the provider rather than from a
            # belief, so what is announced is necessarily what will run.
            "matches_by": matcher.CAPABILITY if matcher else None,
        })
        self._timer = Timer(self.beliefs.bid_window_s, self.close)
        self._timer.start()

    # --- collecting ---

    def on_bid(self, market, bid: dict) -> None:
        rnd = self.open_auction
        if rnd is None or bid.get("auction_id") != rnd["auction_id"]:
            return  # late, or for an auction that is not mine
        agent = bid.get("agent")
        if agent not in self.participants[market.uri]:
            self.log.warning("bid from %s, who does not bid in this market — ignored", agent)
            return
        rnd["bids"][agent] = bid

    # --- closing ---

    def close(self) -> None:
        if self._timer:
            self._timer.stop()
        rnd, self.open_auction = self.open_auction, None
        if rnd is None:
            return
        market, auction_id = rnd["market"], rnd["auction_id"]

        if not rnd["bids"]:
            self.log.info("auction %s closed with no bids", auction_id)
            return

        bids = [
            Bid(agent=a, max_qty_l=float(b["max_qty_l"]),
                max_price_per_l=float(b["max_price_per_l"]))
            for a, b in sorted(rnd["bids"].items())
        ]
        # Balances are SELF-REPORTED by the bidders and therefore untrusted. Clearing is
        # supposed to check solvency against its own ledger; that ledger does not exist yet
        # (see decisions/agent-centric-epistemics.md §4), and this is the honest stand-in
        # until it does — recorded rather than hidden.
        wallets = {a: float(b.get("balance", 0.0)) for a, b in rnd["bids"].items()}

        state = MarketState(
            bids={b.agent: b for b in bids},
            wallets=wallets,
            certified=frozenset({self.me.agent_id, *self.participants[market.uri]}),
            limits=Limits(tank_capacity_l=market.capacity_l, rot_headroom_l={}),
        )
        offer = Offer(
            supplier=self.me.agent_id,
            quantity_l=self.beliefs.quantity_l,
            reserve_price_per_l=self.beliefs.reserve_price_per_l,
        )

        matcher = self.matcher()
        if matcher is None:
            # Nothing to allocate the bids with. Checked here as well as by the shape, because a
            # world can be amended between validation and an auction, and losing its bids in
            # silence is worse than saying so — every bidder is waiting on a voucher.
            self.log.error("auction %s cannot be matched — this host has no matching capability, "
                           "so the bids are discarded. Check its market:matchesBy.", auction_id)
            return

        result = run_auction(offer, bids, state, auction_id=auction_id, match=matcher.propose_match)
        if not result.validation.ok:
            self.log.warning("auction %s RED — clearing rejected: %s",
                             auction_id, result.validation.violations)
            return
        if not result.vouchers:
            self.log.info("auction %s closed — nothing cleared the reserve", auction_id)
            return

        self.log.info("auction %s GREEN — %.3f L allocated to %d",
                      auction_id, result.trade.total_qty_l, len(result.vouchers))
        for voucher in result.vouchers:
            self.publish(f"{market.voucher_topic}/{voucher.sub}", {
                "auction_id": auction_id, "jti": voucher.jti, "sub": voucher.sub,
                "scope": voucher.scope, "amount_l": voucher.amount_l, "debit": voucher.debit,
            })
        self.redeem(result.vouchers)

    def redeem(self, vouchers) -> None:
        """Hand the vouchers to whichever of my capabilities can touch the hardware.

        Winning is not the same as being able to open a valve: the resource owner redeems.
        Asked for by term, so this package does not know that actuation is implemented in
        Python at all — a host in a build without it simply issues paper.
        """
        actuation = self.agent.provider(ACTUATION)
        if actuation is None:
            self.log.info("no actuation capability — vouchers issued but not redeemed")
            return
        actuation.redeem_all(vouchers)
