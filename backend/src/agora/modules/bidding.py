"""ag:Bidding — answer offers with a number only this agent can compute.

This is where one-process-per-agent earns itself: the bid is a function of the agent's
*private* valuation and its *own* fresh reading. No host and no peer can compute it, so it
has to be asked for. The agent hears an offer, looks at its own sensor, and answers — or
stays silent, which is a legitimate answer.

An offer therefore starts with *looking*, not with computing: the agent asks its sensor and
waits for that answer before it bids. Nudging and then reading whatever was already stored
would defeat the point — it would bid on the past while pretending to have just looked. If
the reading does not arrive before the round closes, the agent simply misses the round, which
is the honest outcome.

Two reasons it stays silent, and both are deliberate:
  - it is at or above its target (a reflex — no need, no bid);
  - its newest reading is staler than it is willing to trust. Owning the cadence must not
    mean bidding on a comfortable old number.

The bid *number* is deterministic code (see decisions/deterministic-bid.md); an LLM would
later produce the justification, never the number.

Vocabulary: ontology/market.ttl (protocol) + ontology/water.ttl (what a bid means here).
Rules: shapes/market.ttl, shapes/water.ttl.
"""

from __future__ import annotations

from ..market import EPS, Bid
from ..ontology import BIDDING
from .base import Module, Timer


def value_bid(moisture: float, b, balance: float, allocated_l: float = 0.0) -> Bid | None:
    """Deterministic willingness-to-pay from a deficit. None means cede.

    - the deficit below target drives both the litres wanted and the urgency (price);
    - the bid is for *unmet* demand — what is already allocated is subtracted;
    - quantity is capped by what the wallet can actually pay for, so a bid is always solvent.
    """
    deficit = b.target - moisture
    if deficit <= 0:
        return None  # at or above target — cede

    unmet_l = deficit * b.litres_per_fraction - allocated_l
    if unmet_l <= EPS:
        return None  # a prior allocation already covers it

    urgency = min(1.0, deficit / b.target)
    price = b.max_value_per_l * urgency
    if price <= EPS or balance <= EPS:
        return None  # broke, or the water is worth nothing to me right now

    qty = min(unmet_l, balance / price)
    return None if qty <= EPS else Bid(
        agent="", max_qty_l=round(qty, 3), max_price_per_l=round(price, 3)
    )


class BiddingModule(Module):
    CAPABILITY = BIDDING
    name = "bidding"

    def __init__(self, agent):
        super().__init__(agent)
        self.beliefs = agent.beliefs.bidding()
        self.balance = self.beliefs.endowment
        self.won_l = 0.0
        self.pending: dict | None = None  # a round I have been asked to answer
        self._deadline: Timer | None = None

    def stop(self) -> None:
        if self._deadline:
            self._deadline.stop()

    def subscriptions(self) -> list[str]:
        topics = []
        for market in self.me.markets:
            topics.append(market.offer_topic)
            topics.append(f"{market.voucher_topic}/{self.me.agent_id}")
        return topics

    def handle(self, topic: str, payload: bytes) -> bool:
        for market in self.me.markets:
            if topic == market.offer_topic:
                self.on_offer(market, self.parse(payload) or {})
                return True
            if topic == f"{market.voucher_topic}/{self.me.agent_id}":
                self.on_voucher(self.parse(payload) or {})
                return True
        return False

    # --- answering an offer ---

    def on_offer(self, market, offer: dict) -> None:
        """Look first. The bid is submitted when the reading comes back, not before."""
        round_id = offer.get("round_id")
        if not round_id or not self.me.acts_for:
            return

        self.pending = {"round_id": round_id, "market": market}
        perception = self.perception()
        if perception is None:
            # bidding while perceiving nothing leaves no reading to cite, so no honest bid
            self.log.info("round %s: I perceive nothing — sitting out", round_id)
            self.pending = None
            return

        perception.sense_now()  # a listening agent cannot, and simply does not

        # If something current is already in hand, answer now; otherwise wait for the sensor.
        reading = perception.fresh_reading(self.me.acts_for)
        if reading is not None:
            self.submit(reading.value)
            return

        # Give up when the round closes — a bid nobody can count is not a bid.
        window = float(offer.get("closes_in_s") or 0) or 1.0
        self._deadline = Timer(window, self.give_up)
        self._deadline.start()

    def on_reading_recorded(self, subject_uri: str, value: float) -> None:
        """The look I asked for came back. Now I can bid on it."""
        if self.pending and subject_uri == self.me.acts_for:
            self.submit(value)

    def give_up(self) -> None:
        if self._deadline:
            self._deadline.stop()
        if self.pending:
            self.log.info("round %s: my sensor did not answer in time — sitting out",
                          self.pending["round_id"])
            self.pending = None

    def submit(self, moisture: float) -> None:
        rnd, self.pending = self.pending, None
        if self._deadline:
            self._deadline.stop()
        if rnd is None:
            return
        round_id, market = rnd["round_id"], rnd["market"]

        bid = value_bid(moisture, self.beliefs, self.balance)
        if bid is None:
            self.log.info("round %s: moisture %.3f, target %.2f — cede",
                          round_id, moisture, self.beliefs.target)
            return

        self.log.info("round %s: moisture %.3f -> bid %.3f L @ €%.3f",
                      round_id, moisture, bid.max_qty_l, bid.max_price_per_l)
        self.publish(f"{market.bid_topic}/{self.me.agent_id}", {
            "round_id": round_id,
            "agent": self.me.agent_id,
            "max_qty_l": bid.max_qty_l,
            "max_price_per_l": bid.max_price_per_l,
            "balance": round(self.balance, 4),
        })

    def perception(self):
        """Whichever perception capability this agent got from its hardware, if any."""
        from .perception import PerceptionModule

        return next((m for m in self.agent.modules if isinstance(m, PerceptionModule)), None)

    # --- what came back ---

    def on_voucher(self, voucher: dict) -> None:
        amount = float(voucher.get("amount_l", 0.0))
        debit = float(voucher.get("debit", 0.0))
        self.balance -= debit
        self.won_l += amount
        self.log.info("won %.3f L for €%.2f — balance €%.2f", amount, debit, self.balance)
