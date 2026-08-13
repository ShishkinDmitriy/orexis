"""market:Bidding — answer offers with a number only this agent can compute.

This is where one-process-per-agent earns itself: the bid is a function of the agent's
*private* valuation and its *own* fresh reading. No host and no peer can compute it, so it
has to be asked for. The agent hears an offer, looks at its own sensor, and answers — or
stays silent, which is a legitimate answer.

An offer therefore starts with *looking*, not with computing: the agent asks its sensor and
waits for that answer before it bids. Nudging and then reading whatever was already stored
would defeat the point — it would bid on the past while pretending to have just looked. If
the reading does not arrive before the auction closes, the agent simply misses it, which
is the honest outcome.

Two reasons it stays silent, and both are deliberate:
  - it is at or above its aim (a reflex — no need, no bid);
  - its newest reading is staler than it is willing to trust. Owning the cadence must not
    mean bidding on a comfortable old number.

The bid *number* is deterministic code (see decisions/deterministic-bid.md); an LLM would
later produce the justification, never the number.

It is no longer the capability that holds a **band**. That moved to `desire`, where it is
deduced per property from what the world states rather than picked as two decimals — and where
an agent that bids in nothing at all can still have one. Perception supplies numbers, desire
supplies verdicts, and this supplies a price.

Vocabulary: capabilities/market/ontology.ttl (protocol) + domain/water/ontology.ttl (what a
bid means here). Rules: capabilities/market/shapes.ttl, domain/water/shapes.ttl.
"""

from __future__ import annotations

from agent.market import EPS, Bid
from agent.module import Module, Timer
from agent.ontology import ONTOLOGY_GRAPH
from agent.store import bindings

from .beliefs import BIDDING_BLOCK
from .terms import BIDDING, DESIRE, PERCEPTION

# The term whose meaning this asks after is the one this package already names for its own
# beliefs, so nothing here is written twice and nothing here is a domain property. A block's
# terms are full IRIs, so this is written `<...>` rather than under an assumed prefix — which
# is what lets the denomination live in the domain's namespace and `market:aboutProperty` in
# this package's, without either being spelled twice. It hung on the target while the bidder
# held one; the denomination outlived the point, so it hangs on the deficit-to-litres term now.
_DENOMINATED = BIDDING_BLOCK.terms["litres_per_fraction"]
_ABOUT_Q = f"""
SELECT ?property WHERE {{
  <{_DENOMINATED}> market:aboutProperty ?property  }} LIMIT 1"""


def value_bid(moisture: float, aim: float, b, balance: float,
              allocated_l: float = 0.0) -> Bid | None:
    """Deterministic willingness-to-pay from a deficit. None means cede.

    - the deficit below the AIM drives both the litres wanted and the urgency (price). The aim
      arrives as an argument because it is not a market belief: it is desire's — the pick
      inside the region — and the caller asked whoever provides that family;
    - the bid is for *unmet* demand — what is already allocated is subtracted;
    - quantity is capped by what the wallet can actually pay for, so a bid is always solvent.
    """
    deficit = aim - moisture
    if deficit <= 0:
        return None  # at or above the aim — cede

    unmet_l = deficit * b.litres_per_fraction - allocated_l
    if unmet_l <= EPS:
        return None  # a prior allocation already covers it

    urgency = min(1.0, deficit / aim)
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
        self.beliefs = agent.beliefs.read(BIDDING_BLOCK)
        self.balance = self.beliefs.endowment
        self.won_l = 0.0
        self.pending: dict | None = None  # an auction I have been asked to answer
        self._deadline: Timer | None = None
        self.about = self._what_my_desire_is_about()

    def _what_my_desire_is_about(self) -> str:
        """The observable property my valuation is denominated in.

        Asked of my own desire, not of the market. A market is a LOT — 1L of water is 1L of
        water whether or not anyone's soil is dry — and a market for something no instrument
        measures has to stay expressible. What is genuinely property-shaped is the stake: my
        target is 0.55 OF something, and my bands and my litres-per-fraction are in the same
        unit. Until this link existed that number was dimensionless, and the agent got away
        with it only because it had exactly one kind of reading to compare it to.

        Read from the T-Box against the term this package already names, so no domain property
        is written here and no world has to restate it. Refused rather than defaulted: with no
        answer the only thing left is to judge whichever reading arrived last, which is the
        confusion this exists to end. An agent that will not start is a visible fault; one
        pricing water off a humidity is not.
        """
        rows = bindings(self.agent.store.query(_ABOUT_Q))
        if not rows:
            raise RuntimeError(
                f"{self.agent.id} bids, but the domain does not say what a bid is priced IN — "
                f"state market:aboutProperty on <{_DENOMINATED}> in the domain ontology")
        return rows[0]["property"]

    def _my_aim(self) -> float | None:
        """The point I am steering the priced property toward — desire's, asked for at bid time.

        Through `agent.provider`, so this package never imports desire's Python. None when
        nothing here holds desires or no aim was picked, and the caller cedes: a bid prices the
        deficit below an aim, and with no aim there is no deficit — only a number somebody would
        have had to invent.
        """
        desire = self.agent.provider(DESIRE)
        if desire is None:
            return None
        return desire.aim(self.about)

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

    # --- what I no longer make of a reading ---
    #
    # `annotate` and `urgency` used to be implemented here, and they have gone to
    # `packages/capability/desire/`. The reason is not tidiness: holding an opinion about your own
    # state was conditional on being a market participant, and an agent acting for a plant in a
    # world with no economy at all still knows when that plant is in trouble — it simply has
    # nobody to ask for help. A band is a fact about a STAKE and a bid is a fact about a market,
    # and one of those is a special case of having the other.
    #
    # Nothing here calls the desire module. It contributes through the same `annotate`/`urgency`
    # hooks this class used, so the announcement and the cadence are unchanged in shape — see
    # `agent/module.py`. What did change is that they now answer for every property the agent has
    # a region in, rather than for the one a bid happens to be priced in.

    # --- answering an offer ---

    def on_offer(self, market, offer: dict) -> None:
        """Look first. The bid is submitted when the reading comes back, not before."""
        auction_id = offer.get("auction_id")
        if not auction_id or not self.me.acts_for:
            return

        self.pending = {"auction_id": auction_id, "market": market}
        perception = self.agent.provider(PERCEPTION)
        if perception is None:
            # bidding while perceiving nothing leaves no reading to cite, so no honest bid
            self.log.info("auction %s: I perceive nothing — sitting out", auction_id)
            self.pending = None
            return

        perception.sense_now()  # a listening agent cannot, and simply does not

        # If something current is already in hand, answer now; otherwise wait for the sensor.
        reading = perception.fresh_reading(self.me.acts_for, self.about)
        if reading is not None:
            self.submit(reading.value)
            return

        # Give up when the auction closes — a bid nobody can count is not a bid.
        window = float(offer.get("closes_in_s") or 0) or 1.0
        self._deadline = Timer(window, self.give_up)
        self._deadline.start()

    def on_reading_recorded(self, subject_uri: str, observed_property: str, value: float) -> None:
        """The look I asked for came back. Now I can bid on it — if it is the one I asked for.

        Matching on the subject alone meant that on a pot with two sensors, whichever reported
        first won the race, and a temperature could be submitted as a bid on soil moisture.
        """
        if not self.pending or subject_uri != self.me.acts_for:
            return
        if observed_property != self.about:
            return
        self.submit(value)

    def give_up(self) -> None:
        if self._deadline:
            self._deadline.stop()
        if self.pending:
            self.log.info("auction %s: sitting out — %s",
                          self.pending["auction_id"], self._why_blind())
            self.pending = None

    def _why_blind(self) -> str:
        """Not knowing and being broken are different, and were reported identically.

        "my sensor did not answer in time" was said whenever an auction closed without a reading —
        including when the board was simply asleep on the cadence this agent itself set. A real
        failure then reads exactly like the ordinary case, which is how a real failure gets
        ignored.
        """
        perception = self.agent.provider(PERCEPTION)
        reading = self.agent.beliefs.current_reading(self.me.acts_for, self.about)
        if reading is None:
            return "no reading yet from my sensor"
        if perception is None:
            return "nothing here perceives"
        overdue_after = perception.stale_after_s(self.me.acts_for, self.about)
        if reading.is_fresh(overdue_after):
            return (f"my sensor is asleep and answered {reading.age_s():.0f}s ago; "
                    f"it is not due for {overdue_after}s")
        return (f"my sensor has not reported in {reading.age_s():.0f}s, past the {overdue_after}s "
                f"I allow for the cadence I set — it has gone quiet")

    def submit(self, moisture: float) -> None:
        rnd, self.pending = self.pending, None
        if self._deadline:
            self._deadline.stop()
        if rnd is None:
            return
        auction_id, market = rnd["auction_id"], rnd["market"]

        aim = self._my_aim()
        if aim is None:
            self.log.info("auction %s: I hold no aim in %s — sitting out",
                          auction_id, self.about)
            return

        bid = value_bid(moisture, aim, self.beliefs, self.balance)
        if bid is None:
            self.log.info("auction %s: moisture %.3f, aim %.2f — cede",
                          auction_id, moisture, aim)
            return

        self.log.info("auction %s: moisture %.3f -> bid %.3f L @ €%.3f",
                      auction_id, moisture, bid.max_qty_l, bid.max_price_per_l)
        self.publish(f"{market.bid_topic}/{self.me.agent_id}", {
            "auction_id": auction_id,
            "agent": self.me.agent_id,
            "max_qty_l": bid.max_qty_l,
            "max_price_per_l": bid.max_price_per_l,
            "balance": round(self.balance, 4),
        })

    # --- what came back ---

    def on_voucher(self, voucher: dict) -> None:
        amount = float(voucher.get("amount_l", 0.0))
        debit = float(voucher.get("debit", 0.0))
        self.balance -= debit
        self.won_l += amount
        self.log.info("won %.3f L for €%.2f — balance €%.2f", amount, debit, self.balance)
