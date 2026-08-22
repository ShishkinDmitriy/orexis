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
an agent that bids in nothing at all can still have one. Sensing supplies numbers, desire
supplies verdicts, and this supplies a price.

Vocabulary: capabilities/market/ontology.ttl (protocol) + domain/water/ontology.ttl (what a
bid means here). Rules: capabilities/market/shapes.ttl, domain/water/shapes.ttl.
"""

from __future__ import annotations

from datetime import datetime, timezone

from agent import signing
from agent.market import EPS, Bid
from agent.module import Module, Timer
from agent.ontology import ONTOLOGY_GRAPH
from agent.store import bindings

from .beliefs import BIDDING_BLOCK
from .terms import (ACQUIRE, APPLY, BIDDING, DELIBERATION, DESIRE, INTENTION, OBSERVE,
                    SENSING)

# What my bids are priced in, found THROUGH MY VENUE AND MY STAKE (#198) rather than by
# naming any term: the market I bid in is for a source, the source states its good (entailed
# from its class — 'the lot states its good'), the valuations of that good each carry a
# property, and MINE is the one my subject states a need in — the exact premises the
# participation rule derived my bidsIn from, asked again from the inside. Both joins are
# load-bearing: without the venue, a fern beside a fan market would price moisture in the
# wrong direction; without the stake, a fern at a water venue would inherit the DEALER's
# denomination, because one good honestly has a valuation per kind of recipient (a litre
# raises a pot's moisture and a barrel's stock, by different terms). This used to interrogate
# one fixed term — the litres-per-fraction IRI — which was right for every bidder while every
# bidder was a plant's. The term comes back beside the property because it is also the KEY to
# my own conversion belief below.
_ABOUT_Q = """
SELECT ?property ?term WHERE {
  <%s> market:bidsIn ?m ; ag:actsFor ?subject .
  ?m market:marketFor ?src .
  ?src market:supplies ?good .
  ?subject <http://www.w3.org/ns/ssn/systems/hasOperatingRange> ?range .
  ?range <http://www.w3.org/ns/ssn/systems/inCondition> ?cond .
  ?cond <http://www.w3.org/ns/ssn/forProperty> ?property .
  ?term market:ofGood ?good ; market:aboutProperty ?property } LIMIT 1"""

# My own copy of that conversion — a private BELIEF, read from my graph by the term the venue
# tie named, on beliefs.py's own pattern (a private graph is the one legitimate GRAPH clause:
# the default graph is public knowledge and my beliefs are deliberately not in it). It cannot
# ride BIDDING_BLOCK, whose terms are fixed at import: which conversion a bidder needs is a
# fact about its venue, and the block would demand litres-per-fraction of a dealer that
# converts stored litres. The physics copy on the SUBJECT stays untouched — this is the copy
# an agent that learned would revise, and being wrong about it would cost it money.
_CONV_Q = """
SELECT ?v WHERE { GRAPH <%s> { <%s> <%s> ?v } } LIMIT 1"""


def value_bid(moisture: float, aim: float, b, balance: float,
              allocated_l: float = 0.0, litres_per_unit: float | None = None) -> Bid | None:
    """Deterministic willingness-to-pay from a deficit. None means cede.

    - the deficit below the AIM drives both the litres wanted and the urgency (price). The aim
      arrives as an argument because it is not a market belief: it is desire's — the pick
      inside the region — and the caller asked whoever provides that family. So does the
      conversion (#198): how a deficit becomes litres depends on which property my venue
      prices, a fern's litres-per-fraction or a dealer's litres-per-stored-litre;
    - the bid is for *unmet* demand — what is already allocated is subtracted;
    - quantity is capped by what the wallet can actually pay for, so a bid is always solvent.
    """
    deficit = aim - moisture
    if deficit <= 0:
        return None  # at or above the aim — cede

    unmet_l = deficit * (litres_per_unit or 0.0) - allocated_l
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
        # A claim won and not yet presented (#132): the claim, held until my watch is live.
        # One at a time, like the pending auction — the keeper's patience absorbs a second
        # acquisition while one stands, so a second unpresented claim cannot normally arise;
        # if the market misbehaves and one does, the newer claim replaces the older, logged.
        self.holding: dict | None = None
        self._present_deadline: Timer | None = None
        self.about, self._valuation_term = self._what_my_bids_are_priced_in()
        self.conversion = self._my_conversion()

    def _what_my_bids_are_priced_in(self) -> tuple[str, str]:
        """The observable property my valuation is denominated in, and the term that says so.

        Asked through MY VENUE (#198): the market I bid in is for a source, the source's class
        states the good it vends, and the valuation term of that good carries the property. A
        market is still a LOT — 1L of water is 1L of water whether or not anyone's soil is dry
        — which is exactly why the property cannot be asked of the T-Box at large: the same
        litre is priced in SoilMoisture by a fern and in StoredLitres by the dealer restocking
        its barrel, and which of those MY bids mean is a fact about where I am plumbed.

        Refused rather than defaulted: with no answer the only thing left is to judge
        whichever reading arrived last, which is the confusion this exists to end. An agent
        that will not start is a visible fault; one pricing water off a humidity is not.
        """
        rows = bindings(self.agent.beliefs.query(_ABOUT_Q % self.me.uri))
        if not rows:
            raise RuntimeError(
                f"{self.agent.id} bids, but no valuation connects its venue's good to a "
                f"property its subject states a need in — the source states no "
                f"market:supplies good, no term carries market:ofGood/market:aboutProperty "
                f"for it, or the stake's ranges and the good's valuations do not meet")
        return rows[0]["property"], rows[0]["term"]

    def _my_conversion(self) -> float:
        """My own belief about how a deficit in the priced property becomes litres of the good.

        Keyed by the term the venue tie named, read from my private graph. Demanded exactly as
        a block term is — a bidder that cannot convert its deficit has no bid to compute, and
        the domain's shapes say the same thing at the gate, where the failure is cheaper.
        """
        rows = bindings(self.agent.beliefs.query(
            _CONV_Q % (self.agent.beliefs.graph, self.me.uri, self._valuation_term)))
        if not rows or rows[0].get("v") is None:
            raise RuntimeError(
                f"{self.agent.id} bids in a venue priced in <{self.about}> but holds no "
                f"<{self._valuation_term}> belief — run agora-validate")
        return float(rows[0]["v"])

    def qty_for(self, observed_property: str, value: float) -> float | None:
        """How many litres I would BID for, given where this property stands — one bid's size.

        The buying twin of `ActuationModule.dose_for`, public for the same reason and asked by
        the same caller. A planner simulating an Acquire must size it the way the bidder would
        actually size it, or it predicts a world nobody was going to reach — the single-source
        argument #238 made for an effect's magnitude, arriving at the quantity of a PURCHASE.

        Sized by `value_bid`, which is the same function `submit` runs, so the affordability cap
        is included rather than idealised away: an agent that cannot pay for the litres that
        would close its deficit would not bid for them, and a plan that assumed otherwise plans
        on money the wallet does not hold.

        None where this agent cannot size a bid at all — a property its venue does not price, no
        aim to steer toward, no stated conversion, or a deficit that `value_bid` cedes on.
        """
        # My bids are denominated in exactly one property (#198), so a question about any other
        # is not a question about buying: answering it would price a humidity in litres.
        if observed_property != self.about or self.conversion is None:
            return None
        aim = self._my_aim()
        if aim is None:
            return None
        bid = value_bid(value, aim, self.beliefs, self.balance,
                        litres_per_unit=self.conversion)
        return bid.max_qty_l if bid is not None else None

    def _next_move(self, value: float | None = None) -> str | None:
        """The WHETHER, asked of whoever deliberates — this module only carries moves out.

        The deciding used to be welded in here: an offer meant look-then-bid, and value_bid's
        cede was the whole of choosing. It is a family now, so a model can replace the reflex
        without touching this module — see packages/capability/deliberation/. An agent granted
        no deliberator keeps the old welded behaviour, which is what None falls through to at
        each call site: the seam must not change what an agent WITHOUT it does.

        ASKED ABOUT THE GOAL since #240, which is why a `None` value no longer means "look".
        It used to: `propose` read None as ignorance and answered Observe, and this module
        leaned on that when an offer arrived with no reading it trusts. But None also meant
        "the caller has no number", and one sentinel answering two questions is a sentinel
        that will eventually answer the wrong one. A desire says which of the two epistemic
        failures it is — never read, or read too long ago — so the question is asked properly
        and this module keeps the same behaviour for a better reason.

        The two call sites ask DIFFERENT questions, which is what the sentinel was hiding. With
        a reading in hand this is "what should I do about this number", and the number is the
        one just read — not one fetched back out of the store, because that would make the
        answer depend on whether the observation had been written yet, an ordering no caller
        can see. With nothing in hand it is "what should I do about not knowing", and only a
        desire can say which kind of not-knowing it is.
        """
        deliberator = self.agent.provider(DELIBERATION)
        if deliberator is None:
            return None
        if value is not None:
            return deliberator.propose(self.about, value)
        desire = next((g for g in self.agent.pursuing()
                     if not g.is_duty and g.observed_property == self.about), None)
        if desire is None:
            #  No want in this property at all: nothing to steer toward, and the old code
            #  reached the same answer through an aim it could not find.
            return None
        return deliberator.propose_for(desire)

    def _unseal(self, doc: dict) -> dict:
        """Open a sealed claim (#145), or pass a plaintext one through untouched.

        Sealed means the host found my published sealing key, which means keygen minted my
        pair, which means the private half is mounted beside my other credentials — so a seal
        I cannot open is an operator error worth a loud log, not a silent shrug: the claim
        is real, the water is mine, and I cannot read my own winnings.
        """
        if "sealed" not in doc:
            return doc
        try:
            opened = signing.unseal(signing.load_sealing_private(self.me.agent_id),
                                    doc["sealed"])
        except FileNotFoundError:
            opened = None
        if opened is None:
            self.log.error("a sealed claim arrived that I cannot open — my sealing key is "
                           "published but its private half is not mounted, or the payload was "
                           "tampered with. The claim is lost to me either way.")
            return {}
        import json as _json

        return _json.loads(opened)

    def _signed(self, payload: dict) -> dict:
        """My presentation, under my own hand (#144) — where I hold a key to sign with.

        No key means the pre-#144 era and the payload goes as it always did; the host demands
        a signature only from agents whose ROSTER entry says they have one, so the two eras
        interoperate without a flag anywhere.
        """
        try:
            key = signing.load_signing_private(self.me.agent_id)
        except FileNotFoundError:
            return payload
        return {**payload, "sig": signing.sign(key, signing.canonical(payload))}

    def _delta_of(self, amount_l: float) -> float | None:
        """How far a dose of this many litres should move my property — the act sizing its own
        effect for the met-verdict's margin (#165), through the same conversion the bid was
        priced with. None when the belief cannot say, which keeps the exact-crossing verdict."""
        lpf = self.conversion
        return (float(amount_l) / lpf) if lpf > 0 and amount_l else None

    def _keeper(self):
        """Whoever keeps my commitments, or None — and None is a complete answer.

        Everything below that touches the ledger is guarded by it: an agent granted no keeper
        behaves exactly as before there was one, because in phase 3 the ledger RECORDS what this
        module does and never gates it. What a standing intention absorbs is re-ADOPTION — one
        commitment spanning several rounds — not the acts themselves; whether to act stays with
        the reflexes here until deliberation is its own capability. See
        knowledge/decisions/an-intention-is-an-amortised-deliberation.md.
        """
        return self.agent.provider(INTENTION)

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
        if self._present_deadline:
            self._present_deadline.stop()

    def subscriptions(self) -> list[str]:
        topics = []
        for market in self.me.markets:
            topics.append(market.offer_topic)
            topics.append(f"{market.claim_topic}/{self.me.agent_id}")
        return topics

    def handle(self, topic: str, payload: bytes) -> bool:
        for market in self.me.markets:
            if topic == market.offer_topic:
                self.on_offer(market, self.parse(payload) or {})
                return True
            if topic == f"{market.claim_topic}/{self.me.agent_id}":
                self.on_claim(market, self._unseal(self.parse(payload) or {}))
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
        sensing = self.agent.provider(SENSING)
        if sensing is None:
            # bidding while perceiving nothing leaves no reading to cite, so no honest bid
            self.log.info("auction %s: I perceive nothing — sitting out", auction_id)
            self.pending = None
            return

        # A dose of my own has not answered yet (#167): while a watch is open and inside its
        # deadline, no reading I hold can prove the pot was not already watered — the dose may
        # have landed inside my sensor's sleep, and even a fresh look can race a valve that
        # dispenses over half a minute. This is the one blindness I have every means to know
        # about, and pricing a deficit my own water may have closed bought the same gap twice,
        # live (0.302 on the wire, 0.495 in the pot, 0.396 L re-bought). So the bid is DECLINED,
        # not gated: a judgment read off the ledger through the ordinary provider route, bounded
        # by the watch's own deadline — past it, an unanswered dose frees me exactly as before.
        # A stranger's water stays out of scope: no expectation records it, no clause can read
        # it, and #151 is the device-side answer to that half.
        if keeper := self._keeper():
            now = datetime.now(timezone.utc)
            if any(now < w.deadline for w in keeper.open_expectations(self.about)):
                self.log.info("auction %s: my own dose has not answered yet — ceding, and "
                              "asking for the look that would answer it", auction_id)
                sensing.sense_now()
                self.pending = None
                return

        sensing.sense_now()  # a listening agent cannot, and simply does not

        # If something current is already in hand, answer now; otherwise wait for the sensor.
        reading = sensing.fresh_reading(self.me.acts_for, self.about)
        if reading is not None:
            self.submit(reading.value)
            return

        # No reading it trusts — so ask whoever deliberates what to do about not seeing. The
        # reflex says look, which is what this module always did; the point of asking anyway is
        # that a member with more context could say otherwise, without this line changing.
        if self.agent.provider(DELIBERATION) is not None                 and self._next_move() != OBSERVE:
            self.log.info("auction %s: deliberation chose not to look — sitting out",
                          auction_id)
            self.pending = None
            return

        # Waiting on the sensor is a commitment — the state `pending` has always carried,
        # recorded now so it can outlive this process's memory of it.
        if keeper := self._keeper():
            keeper.adopt(OBSERVE, self.about,
                         f"auction {auction_id} needs a reading I do not have fresh")

        # Give up when the auction closes — a bid nobody can count is not a bid.
        window = float(offer.get("closes_in_s") or 0) or 1.0
        self._deadline = Timer(window, self.give_up)
        self._deadline.start()

    def on_reading_recorded(self, subject_uri: str, observed_property: str, value: float) -> None:
        """The look I asked for came back. Now I can bid on it — if it is the one I asked for.

        Matching on the subject alone meant that on a pot with two sensors, whichever reported
        first won the race, and a temperature could be submitted as a bid on soil moisture.
        """
        if subject_uri == self.me.acts_for and observed_property == self.about:
            self._maybe_present()  # a held claim checks its watch on every look (#132)
        if not self.pending or subject_uri != self.me.acts_for:
            return
        if observed_property != self.about:
            return
        if keeper := self._keeper():
            keeper.satisfy(OBSERVE, self.about, "the look I asked for came back")
        self.submit(value)

    def give_up(self) -> None:
        if self._deadline:
            self._deadline.stop()
        if self.pending:
            why = self._why_blind()
            self.log.info("auction %s: sitting out — %s", self.pending["auction_id"], why)
            if keeper := self._keeper():
                keeper.drop(OBSERVE, self.about, f"the auction closed first: {why}")
            self.pending = None

    def _why_blind(self) -> str:
        """Not knowing and being broken are different, and were reported identically.

        "my sensor did not answer in time" was said whenever an auction closed without a reading —
        including when the board was simply asleep on the cadence this agent itself set. A real
        failure then reads exactly like the ordinary case, which is how a real failure gets
        ignored.
        """
        sensing = self.agent.provider(SENSING)
        reading = self.agent.beliefs.current_reading(self.me.acts_for, self.about)
        if reading is None:
            return "no reading yet from my sensor"
        if sensing is None:
            return "nothing here perceives"
        overdue_after = sensing.stale_after_s(self.me.acts_for, self.about)
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

        # The WHETHER is the deliberator's. The reflex member reproduces exactly the cede this
        # module used to compute for itself — below the aim, pursue; otherwise nothing — so the
        # behaviour is unchanged and the DECIDER is replaceable. An agent with no deliberator
        # falls through to the old welded logic: value_bid still cedes at-or-above the aim.
        if self.agent.provider(DELIBERATION) is not None                 and self._next_move(moisture) != ACQUIRE:
            self.log.info("auction %s: moisture %.3f — deliberation chose not to pursue",
                          auction_id, moisture)
            return

        aim = self._my_aim()
        if aim is None:
            self.log.info("auction %s: I hold no aim in %s — sitting out",
                          auction_id, self.about)
            return

        bid = value_bid(moisture, aim, self.beliefs, self.balance,
                        litres_per_unit=self.conversion)
        if bid is None:
            self.log.info("auction %s: moisture %.3f, aim %.2f — cede",
                          auction_id, moisture, aim)
            return

        # The commitment is to the GAP, not to the round: adopted with the first bid, absorbed
        # for every further bid while it stands (that is the keeper's patience at work — one
        # commitment spanning several rounds is one intention), resolved by the claim.
        if keeper := self._keeper():
            keeper.adopt(ACQUIRE, self.about,
                         f"bid {bid.max_qty_l}L @ {bid.max_price_per_l}/L in auction "
                         f"{auction_id} to close my deficit below {aim}")

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

    def on_claim(self, market, claim: dict) -> None:
        amount = float(claim.get("amount_l", 0.0))
        debit = float(claim.get("debit", 0.0))
        self.balance -= debit
        self.won_l += amount
        self.log.info("won %.3f L for €%.2f — balance €%.2f", amount, debit, self.balance)

        keeper = self._keeper()
        acquire_uris = (keeper.satisfy(ACQUIRE, self.about,
                                       f"claim for {amount}L at a debit of {debit}")
                        if keeper is not None else [])

        # A market authored without a redeem channel keeps the old arrangement — the host
        # redeemed on issue, the dose is already flying — so the expectation opens NOW, on the
        # acquire's row, exactly as before #132.
        if not market.redeem_topic or not claim.get("jti"):
            for uri in acquire_uris:
                keeper.expect(uri, self.about,
                              f"paid {debit} for {amount}L on a market with no redeem channel "
                              f"— the host has already redeemed, so show me",
                              expected_delta=self._delta_of(amount))
            return

        # HOLD (#132): winning is not actuating. The claim stands until my watch is live —
        # a reading acknowledged at my fast cadence (#135), proof the board heard the
        # tightening — or until the bounded wait says redeem blind rather than never. The
        # keeper's standing Apply is what tightens the cadence: a held claim IS urgency.
        if self.holding is not None:
            self.log.warning("a second claim arrived while %s was held — presenting the newer",
                             self.holding.get("jti"))
        self.holding = {"jti": claim["jti"], "market": market,
                        "amount_l": amount, "debit": debit}
        if keeper is not None:
            keeper.adopt(APPLY, self.about,
                         f"holding claim {claim['jti']} ({amount}L) until my watch is "
                         f"live — never spend a dose you cannot watch land")
        if (sensing := self.agent.provider(SENSING)) is not None:
            sensing.sense_now()
            bound = sensing.stale_after_s(self.me.acts_for, self.about)
        else:
            bound = 60.0
        # The bound: one full cycle of the rhythm currently in force, after which a watch that
        # could not be confirmed is not going to be — old firmware that never acks, a listening
        # rig, a board mid-sleep on a long cadence. Redeem blind and say so, because a dose
        # delayed forever is worse than a dose unobserved.
        self._present_deadline = Timer(float(bound), self._present_blind)
        self._present_deadline.start()
        self._maybe_present()

    def _maybe_present(self) -> None:
        """Present the held claim if the watch is live. Called on every reading of my property."""
        if self.holding is None:
            return
        sensing = self.agent.provider(SENSING)
        if sensing is None or not sensing.watch_is_live(self.me.acts_for, self.about):
            return
        self._present("my watch is live — a reading arrived acknowledged at my fast cadence")

    def _present_blind(self) -> None:
        if self.holding is None:
            return
        self._present("the wait is over and the watch never confirmed live — redeeming blind, "
                      "because a dose delayed forever is worse than a dose unobserved")

    def _present(self, why: str) -> None:
        held, self.holding = self.holding, None
        if self._present_deadline:
            self._present_deadline.stop()
        if held is None:
            return
        market = held["market"]
        self.log.info("presenting claim %s: %s", held["jti"], why)
        self.publish(f"{market.redeem_topic}/{self.me.agent_id}",
                     self._signed({"jti": held["jti"], "sub": self.me.agent_id}))
        if keeper := self._keeper():
            # The dose is imminent NOW — this is when the end becomes expectable, not at the
            # claim: a baseline taken at the win would have aged the whole hold, and the
            # sense_now inside expect() lands on a board that is provably (or at least
            # plausibly) awake and fast. The watch hangs on the Apply row, because applying is
            # the act whose end the movement is.
            for uri in keeper.satisfy(APPLY, self.about,
                                      f"claim {held['jti']} presented: {why}"):
                keeper.expect(uri, self.about,
                              f"presented {held['jti']} for {held['amount_l']}L — the graph "
                              f"says this raises what I am short of, so show me",
                              expected_delta=self._delta_of(held["amount_l"]))
