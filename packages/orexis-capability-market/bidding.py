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

import uuid

from datetime import datetime, timedelta, timezone

from agent import signing
from .trade import EPS, Bid
from agent.module import Module, contributes
from orexis_agent_progression.timer import Timer
from orexis_agent_progression.ontology import HANDLE, SUBSCRIPTIONS

SENSING_URGENCY = "http://example.org/orexis/sensing#urgency"       # sensing's hook, spelled as every cross-package reference is
READING_RECORDED = "http://example.org/orexis/sensing#readingRecorded"
from orexis_agent_progression.ontology import (CLASSIFICATION_GRAPH, GRAPH_PREFIX, ONTOLOGY_GRAPH,
                                               PERIODS_GRAPH, beliefs_graph)
from orexis_agent_progression.store import bindings
from assembly.contribute import contributes

from . import rounds, wallet
from .wiring import bidding_markets_of
from .beliefs import BIDDING_PICKS
from .terms import (BIDDING, CLAIM, CLAIMED_AT, CLAIM_DEBIT, CLAIM_ID, CLAIM_L, HOLDS_CLAIM, NS,
                    ON_VENUE, PRESENTED_AT, PRESENTING, SENSING, TENDERING, USABLE_FROM, USABLE_UNTIL)
from orexis_agent_progression import clock

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
  <%s> market:bidsIn ?m ; orexis:actsFor ?subject .
  ?m market:marketFor ?src .
  ?src market:supplies ?good .
  ?subject <http://www.w3.org/ns/ssn/systems/hasOperatingRange> ?range .
  ?range <http://www.w3.org/ns/ssn/systems/inCondition> ?cond .
  ?cond <http://www.w3.org/ns/ssn/forProperty> ?property .
  ?term market:ofGood ?good ; market:aboutProperty ?property } LIMIT 1"""

# My own copy of that conversion — a private BELIEF, read from my graph by the term the venue
# tie named, on beliefs.py's own pattern (a private graph is the one legitimate GRAPH clause:
# the default graph is public knowledge and my beliefs are deliberately not in it). It cannot
# ride BIDDING_PICKS, whose terms are fixed at import: which conversion a bidder needs is a
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


def claim_graph(agent_id: str, jti: str) -> str:
    """ONE held claim's graph in ONE agent's store — the unit a period is said of (#645)."""
    return f"{GRAPH_PREFIX}claim/{agent_id}/{jti}"


class BiddingModule(Module):
    CAPABILITY = BIDDING
    name = "bidding"

    def __init__(self, agent):
        super().__init__(agent)
        self.markets = bidding_markets_of(agent.beliefs.query, self.me.uri)
        self._asked: set = set()          # (want, instant) asked for ahead (#627)
        self.beliefs = agent.desires.read(BIDDING_PICKS)
        #  THE WALLET IS A BELIEF (#395): what is left lives in this agent's own graph, so a
        #  restart resumes with what it has rather than with what it was given.
        self.won_l = 0.0
        self.pending: dict | None = None  # an auction I have been asked to answer
        self._deadline: Timer | None = None
        # A claim won and not yet presented (#132): the claim, held until my watch is live.
        # One at a time, like the pending auction — the keeper's patience absorbs a second
        # acquisition while one stands, so a second unpresented claim cannot normally arise;
        # if the market misbehaves and one does, the newer claim replaces the older, logged.
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

    def _baseline(self):
        """The reading I hold of my property — the before a watch leaves from."""
        sensing = self.agent.provider(SENSING)
        return sensing.current_reading(self.me.acts_for, self.about) if sensing else None

    def _seeing_s(self) -> float | None:
        """How long a reading of my property may take to arrive — the cadence my sensing keeps."""
        sensing = self.agent.provider(SENSING)
        try:
            return float(sensing.stale_after_s(self.me.acts_for, self.about)) if sensing else None
        except Exception:
            return None

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
                f"<{self._valuation_term}> belief — run orexis-validate")
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

    def _next_move(self) -> str | None:
        """The WHETHER, asked of whoever deliberates — this module only carries moves out.

        The deciding used to be welded in here: an offer meant look-then-bid, and value_bid's
        cede was the whole of choosing. It moved out so that a model can answer instead without
        this module changing — the property `tests/test_deliberation.py` pins by silencing the
        deliberator and watching a thirsty bidder submit nothing.

        ASKED ABOUT THE GOAL since #240, which is why a `None` value never meant "look". It
        used to: the old bare-value door read None as ignorance and answered Observe, and this
        module leaned on that when an offer arrived with no reading it trusts. But None also
        meant "the caller has no number", and one sentinel answering two questions is a
        sentinel that will eventually answer the wrong one. A desire says which of the two
        epistemic failures it is — never read, or read too long ago.

        ONE QUESTION NOW, where there were two. The value-carrying half went with the reflex:
        both call sites here ask *what should I do about this property*, and the answer comes
        from a search over what the agent believes rather than from a number this module is
        holding. The store is not behind the caller — `Observations.record` writes before it
        announces — and where it is (a write that failed), the want reads unmeasured and the
        answer is a look, which is the honest move for an agent that lost its own reading.
        """
        want = self._want()
        return self.agent.deliberator.propose_for(want) if want is not None else None

    #  WHICH WANT my bids serve: the stake about the property they are priced in, asked of
    #  sensing, which is where a property means anything (the-stake-is-sensings-want). The
    #  ledger keys on the want, so every row this module writes or reads names it.
    @property
    def balance(self) -> float:
        """What I have left to bid with — read, never remembered."""
        return wallet.balance_of(self.agent)

    def _stake(self):
        sensing = self.agent.provider(SENSING)
        return sensing.stake_about(self.about) if sensing is not None else None

    def _stake_uri(self) -> str | None:
        stake = self._stake()
        return stake.uri if stake is not None else None

    def _want(self):
        """The want to act on about my property NOW — sensing's rule: knowing first."""
        sensing = self.agent.provider(SENSING)
        return sensing.want_about(self.about) if sensing is not None else None

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

    def _keeper(self):
        """Whoever keeps my commitments, or None — and None is a complete answer.

        Everything below that touches the ledger is guarded by it: an agent granted no keeper
        behaves exactly as before there was one, because in phase 3 the ledger RECORDS what this
        module does and never gates it. What a standing intention absorbs is re-ADOPTION — one
        commitment spanning several rounds — not the acts themselves; whether to act stays with
        the reflexes here until deliberation is its own capability. See
        knowledge/decisions/an-intention-is-an-amortised-deliberation.md.
        """
        return self.agent.keeper

    def _my_aim(self) -> float | None:
        """The point I am steering the priced property toward — desire's, asked for at bid time.

        Through `agent.provider`, so this package never imports sensing's Python. None when
        nothing here senses or no aim was picked, and the caller cedes: a bid prices the
        deficit below an aim, and with no aim there is no deficit — only a number somebody would
        have had to invent.
        """
        sensing = self.agent.provider(SENSING)
        if sensing is None:
            return None
        return sensing.aim(self.about)

    def stop(self) -> None:
        if self._deadline:
            self._deadline.stop()

    @contributes(SUBSCRIPTIONS)
    def subscriptions(self) -> list[str]:
        topics = []
        for market in self.markets:
            topics.append(market.offer_topic)
            topics.append(f"{market.claim_topic}/{self.me.agent_id}")
        return topics

    @contributes(HANDLE)
    def handle(self, topic: str, payload: bytes) -> bool:
        for market in self.markets:
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
        if offer.get("closed"):
            self.on_close(auction_id)
            return

        self.pending = {"auction_id": auction_id, "market": market}
        #  Swept here too, and only as an optimisation: an offer is the event a bidder
        #  usually gets, and starting a round with yesterday's rows still standing would read
        #  oddly in a trace. What GUARANTEES they go is the housekeeping tick's `sweep` —
        #  an agent that stops bidding stops getting this event (#398).
        self.agent.upkeep.sweep()   # a round I bid in that closed with no claim is gone by now (#523, #645)
        from datetime import timedelta

        rounds.open_round(self.agent, market.uri, auction_id,
                          float(offer.get("quantity_l") or 0.0),
                          float(offer.get("reserve_price_per_l") or 0.0),
                          clock.now()
                          + timedelta(seconds=float(offer.get("closes_in_s") or 0) or 1.0))
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
            now = clock.now()
            if any(now < w.deadline for w in keeper.open_expectations(self._stake_uri())):
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

        #  No reading it trusts — so the LOOK is asked for the way everything is now: the
        #  want about knowing this property goes through execution, which plans, commits and
        #  hands the look to whoever takes it. None means no plan for it — deliberation chose
        #  not to look — and a look already standing is on its way (execution says which by
        #  returning the standing intention). This module names no Observe: the look is
        #  sensing's word and sensing's act; waiting for it is `pending`, the bidder's own.
        from orexis_agent_deliberation import reviser

        #  MARKED, not asked (#392): what the search decides is not this handler's to wait
        #  for. If it proposes nothing, the give-up below says so — at the round's close
        #  rather than at once, which is also the more honest moment: a reading arriving
        #  mid-round can change the answer.
        if (want := self._want()) is not None:
            reviser.wake(self.agent, want.uri)

        #  THE WINDOW IS THE ACT'S — a bid not after the round closes — and the ACTOR writes
        #  it when it takes the act, from the round row it reads there. What stays here is the
        #  give-up: the close the offer itself states.
        window = float(offer.get("closes_in_s") or 0) or 1.0
        #  A DEADLINE, spent once it lands (see Timer). It used to repeat, and `give_up` stops
        #  `self._deadline` — which by the next round is a different object, so a deadline left
        #  over from an earlier round went on giving up on rounds it was never started for.
        if self._deadline:
            self._deadline.stop()
        self._deadline = Timer(window, self.give_up, repeat=False)
        self._deadline.start()

    @contributes(READING_RECORDED)
    def on_reading_recorded(self, subject_uri: str, observed_property: str, value: float) -> None:
        """The look I asked for came back. Now I can bid on it — if it is the one I asked for.

        Matching on the subject alone meant that on a pot with two sensors, whichever reported
        first won the race, and a temperature could be submitted as a bid on soil moisture.
        """
        if subject_uri == self.me.acts_for and observed_property == self.about:
            self._ask_ahead(value)
        if not self.pending or subject_uri != self.me.acts_for:
            return
        if observed_property != self.about:
            return
        self.submit(value)

    def _ask_ahead(self, value: float) -> None:
        """A crossing foreseen is a dose ASKED for at an instant (#627, a-claim-is-water-at-a-time):
        where the want about my property is one met AT an instant — derived under my stake
        from a predicted crossing — announce it where I announce being low, with the litres a
        bid would be sized to and the instant I intend to present; once per want and instant.
        The host answers with a claim where its stock covers the ask at that instant, or
        convenes a round where it does not; either is what my tender is then done by."""
        want = self._want()
        holds_at = getattr(want, "holds_at", None)
        if want is None or holds_at is None:
            return
        key = (want.uri, holds_at.isoformat(timespec="seconds"))
        if key in self._asked:
            return
        litres = self.qty_for(self.about, value)
        if not litres:
            return
        topic = next((r["t"] for r in bindings(self.agent.beliefs.query(
            f"SELECT ?t WHERE {{ <{self.me.uri}> mqtt:eventTopic ?t }} LIMIT 1"))), None)
        if not topic:
            return
        for market in self.markets:
            wanted = self._presenting_instant(holds_at, market, litres)
            self.log.info("asking for %.3f L at %s — foreseen for %s", litres,
                          wanted.isoformat(timespec="seconds"), want.uri.rsplit("#", 1)[-1])
            self.publish(topic, {"agent": self.me.agent_id, "subject": self.me.acts_for,
                                 "property": self.about, "asks": litres,
                                 "wanted_at": wanted.isoformat()})
        self._asked.add(key)

    def on_close(self, auction_id: str) -> None:
        """The host says its round is over (#599), and that ends it for me.

        A round is a fact THIS agent holds, written when the host announced it. What ends it
        used to be arithmetic — my own clock against the `closesAt` I computed from the window
        the offer stated — because a bidder that lost was told nothing. Now the venue says so,
        and the fact is retracted by the same road it arrived on: something another agent DID,
        through translation and the belief-revision seam.

        The clock is not gone, it is the BACKSTOP: a message can be lost and a host can die,
        so `sweep` still retracts a row whose close has passed, and the give-up timer still
        lands for a round this bidder is waiting on. What changed is which of them is the
        mechanism.
        """
        if self.pending and self.pending.get("auction_id") == auction_id:
            #  Exactly what the deadline landing does, and earlier: the tender is dropped, the
            #  look stays owed, and `pending` is cleared. Reused rather than repeated, so the
            #  two roads out of a round cannot drift apart.
            self.give_up()
            return
        rounds.close_round(self.agent, auction_id)

    def give_up(self) -> None:
        if self._deadline:
            self._deadline.stop()
        if self.pending:
            why = self._why_blind()
            self.log.info("auction %s: sitting out — %s", self.pending["auction_id"], why)
            rounds.close_round(self.agent, self.pending["auction_id"])
            #  The look stays wanted and stays committed — a reading is still owed, round or
            #  no round — so only the Acquire is dropped; sensing resolves the look when it lands.
            if keeper := self._keeper():
                keeper.drop(TENDERING, self._stake_uri(), f"the auction closed first: {why}")
            self.pending = None

    def _why_blind(self) -> str:
        """Not knowing and being broken are different, and were reported identically.

        "my sensor did not answer in time" was said whenever an auction closed without a reading —
        including when the board was simply asleep on the cadence this agent itself set. A real
        failure then reads exactly like the ordinary case, which is how a real failure gets
        ignored.
        """
        sensing = self.agent.provider(SENSING)
        reading = sensing.current_reading(self.me.acts_for, self.about) if sensing else None
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
        """A round is open and I hold a fresh reading: EXECUTE, do not decide.

        The whether used to be asked here — a search inside the actor, on every round, over
        the same world the keeper's tick had already searched. Now an `Acquire` that stands is
        a commitment spanning rounds (that was always its documented meaning), so this hands
        it straight to `take`; only a round arriving with nothing standing asks execution to
        plan once and commit. `value_bid` still cedes at or above the aim inside `_bid`, so
        the sizing agrees with the deciding without either being the other's authority.
        """
        from orexis_agent_deliberation import reviser
        from orexis_agent_progression import execution

        if self.pending is None:
            return
        auction_id = self.pending["auction_id"]
        if self._deadline:
            self._deadline.stop()
        keeper = self._keeper()
        stake = self._stake()
        standing = (keeper.standing(TENDERING, stake.uri)
                    if keeper is not None and stake is not None else [])
        if standing and stake is not None:
            execution.take_standing(self.agent, standing[0], stake)
        elif stake is not None:
            #  MARKED, and nothing is concluded from it (#392): what the search decides is
            #  not this module's to wait for. This branch used to read the mark's `None` as
            #  "deliberation chose not to pursue" and clear `pending` — which said the round
            #  had passed while the pass that would bid was still to run, and took the
            #  give-up with it. What ends the round for this bidder is a bid leaving (`_bid`)
            #  or the give-up firing, and nothing else.
            reviser.wake_for(self.agent, stake)

    @contributes(SENSING_URGENCY)
    def urgency(self, subject_uri: str, observed_property: str,
                value: float | None) -> float | None:
        """A HELD claim is urgency (#132): the dose is coming the moment my watch is live,
        and the watch becomes live by exactly this answer reaching the board. Read off the
        ledger — a standing Apply on this property, younger than my patience — so a claim
        the bounded wait will redeem blind anyway cannot hold the fast cadence forever. The
        keeper used to answer this by naming Apply; it is this package's word and this
        module's hold, so the answer moved here, through the same choir hook."""
        if subject_uri != self.me.acts_for or observed_property != self.about:
            return None
        keeper = self._keeper()
        if keeper is None:
            return None
        now = clock.now()
        if any(s.age_s(now) <= keeper.beliefs.patience_s
               for s in keeper.standing(action=PRESENTING, want=self._stake_uri())):
            return 1.0
        return None

    @contributes(PRESENTING)
    def present(self, act, desire, intention: str) -> bool:
        """The second step of Acquiring's method (#523): present the claim I hold on this
        venue and open the watch on the end. Reached only when the keeper released the step
        — my watch is live, or the sensor's horizon passed and a dose delayed forever is
        worse than a dose unobserved — since the step's readiness is the action's to declare
        and the keeper's to hold."""
        claim = self._claim_on(act.via)
        if claim is None:
            return False
        market = next((m for m in self.markets if m.uri == act.via), None)
        if claim["presented"]:
            self.log.info("claim %s was redeemed by the host — nothing to present, a watch to open",
                          claim["id"])
        else:
            self.log.info("presenting claim %s: released by the keeper — my watch is live, or "
                          "the bound passed", claim["id"])
            if market is not None and market.redeem_topic:
                self.publish(f"{market.redeem_topic}/{self.me.agent_id}",
                             self._signed({"jti": claim["id"], "sub": self.me.agent_id}))
            self.agent.beliefs.update(f"""
INSERT DATA {{ GRAPH <{claim_graph(self.agent.id, claim["id"])}> {{
  <{claim["uri"]}> <{PRESENTED_AT}> "{clock.now().isoformat()}"^^xsd:dateTime }} }}""")
        if keeper := self._keeper():
            #  Held to the band the step predicted (#579); what I add is the number I aimed
            #  the lot at, for the residual review to read against what the world shows.
            sensing = self.agent.provider(SENSING)
            keeper.expect(intention,
                          f"presented {claim['id']} for {claim['litres']}L — the graph says "
                          f"this moves what I am short of, so show me",
                          baseline=self._baseline(),
                          sized=sensing.aim(self.about) if sensing is not None else None,
                          seeing_s=self._seeing_s())
        if (sensing := self.agent.provider(SENSING)) is not None:
            sensing.sense_now()
        return True

    def _claim_on(self, venue_uri: str | None) -> dict | None:
        """The newest claim I hold on this venue, and whether it is presented already."""
        #  A CLAIM IS A GRAPH HOLDING DURING ITS WINDOW (#645): the door hands back only one
        #  still usable, so a claim left over past its window is not held, and nothing here
        #  sweeps it.
        rows = bindings(self.agent.beliefs.query_at(f"""
SELECT ?c ?id ?l ?at ?p WHERE {{
  <{self.me.uri}> <{HOLDS_CLAIM}> ?c . ?c <{CLAIM_ID}> ?id ; <{CLAIM_L}> ?l ; <{ON_VENUE}> <{venue_uri}> ;
     <{CLAIMED_AT}> ?at . OPTIONAL {{ ?c <{PRESENTED_AT}> ?p }} }} ORDER BY DESC(?at) LIMIT 1"""))
        if not rows:
            return None
        return {"uri": rows[0]["c"], "id": rows[0]["id"], "litres": float(rows[0]["l"]),
                "presented": bool(rows[0].get("p"))}

    def _presenting_instant(self, holds_at, market, litres: float):
        """The instant to present so the water has landed by `holds_at`: the instant less the
        pour — Acquiring's landing for these litres, less the venue's redeem window, which is
        the part of that landing that is the valve's."""
        from datetime import timedelta
        from orexis_agent_deliberation import effects
        pour = 0.0
        try:
            lands = effects.lands_after(
                self.agent.beliefs, ACQUIRING, me=f"<{self.me.uri}>",
                subject=f"<{self.me.acts_for}>", about=f"<{self.about}>", via=f"<{market.uri}>",
                litres=str(float(litres)), beliefs=f"<{beliefs_graph(self.agent.id)}>")
            if lands is not None:
                pour = max(0.0, float(lands) - float(market.redeem_window_s or 0.0))
        except Exception as exc:                        # a rule's refusal is not the bid's problem
            self.log.warning("could not size the pour for the wanted instant: %s", exc)
        return holds_at - timedelta(seconds=pour)

    @contributes(TENDERING)
    def tender(self, act, desire, intention: str) -> bool:
        """The first step of Acquiring's method (#523): bid into the round that is open, if
        one is. No round open is "not now": the intention stands, and the next offer runs
        `submit`, which finds the tender standing and comes back here — a bid adopted on the
        keeper's tick is answered by the market's knock without a second search. The reading
        is the one in hand: `on_offer` looked first, and a stale one is never bid on. Done
        when a claim arrives (`orexis:doneWhen`), lapsed at the round's close.
        """
        if act.about != self.about:
            return False
        #  A CLAIM HELD on this venue and not yet presented (#627) — granted on my ask, with
        #  no round — is what this tender is done by: there is nothing to bid, the step is
        #  taken, and the keeper's hold on `doneWhen` answers at once from the fact.
        if (held := self._claim_on(act.via)) is not None and not held["presented"]:
            self.log.info("holding claim %s on this venue already — nothing to tender", held["id"])
            return True
        #  THE ROUND IS THE FACT, read off the row's own lever (#358): the row exists only
        #  while one is open on that venue, so this is a lookup and never a wait. `pending`
        #  survives only as "I asked for a look for this round" — the actor's own bookkeeping,
        #  not a second statement of whether a round is open.
        open_ = [r for r in rounds.rounds_of(self.agent, act.via) if r.is_open()]
        if not open_:
            return False
        #  THE NEWEST OFFER where several stand — the one closing last — rather than the
        #  first row the store lists: a claim that named no round leaves the old one
        #  standing until its period ends, and a bid into it is a bid into the past.
        newest = max(open_, key=lambda r: r.closes_at)
        #  THE WINDOW IS THE ACT'S, written where the act is TAKEN: a bid is worth nothing
        #  after the round closes, and the round row says when that is. It moved here from
        #  `on_offer` with #392, which no longer learns which intention was adopted.
        if (keeper := self._keeper()) is not None:
            keeper.window(intention, newest.closes_at)
        sensing = self.agent.provider(SENSING)
        reading = (sensing.fresh_reading(self.me.acts_for, self.about)
                   if sensing is not None else None)
        if reading is None:
            return False
        market = next((m for m in self.markets if m.uri == act.via), None)
        if market is None:
            return False
        return self._bid(reading.value, market, newest.auction_id,
                         not_after=newest.closes_at,
                         wanted_at=getattr(desire, "holds_at", None))

    def _bid(self, moisture: float, market, auction_id: str, not_after=None,
             wanted_at=None) -> bool:
        """Size and publish one bid into the round that is open. True if one left.

        `not_after` is the round's own close, where the caller knows it: a bid is worth
        nothing after it, so it is refused rather than queued when the link is down, and the
        Acquire stands instead — which is the outbox's whole property, obtained from the act
        that was already there (#396)."""
        #  `pending` is "I asked for a look for this round", and it is cleared when the round
        #  is DONE for me — ceded, or bid. It used to be cleared here, before anyone knew
        #  whether the bid left; a bid the link could not carry then took the give-up with it,
        #  and the Acquire outlived the round it was for (#396).
        mine = bool(self.pending and self.pending.get("auction_id") == auction_id)

        def done():
            if mine:
                self.pending = None

        aim = self._my_aim()
        if aim is None:
            self.log.info("auction %s: I hold no aim in %s — sitting out",
                          auction_id, self.about)
            done()
            return False
        bid = value_bid(moisture, aim, self.beliefs, self.balance,
                        litres_per_unit=self.conversion)
        if bid is None:
            self.log.info("auction %s: moisture %.3f, aim %.2f — cede",
                          auction_id, moisture, aim)
            done()
            return False
        self.log.info("auction %s: moisture %.3f -> bid %.3f L @ €%.3f",
                      auction_id, moisture, bid.max_qty_l, bid.max_price_per_l)
        payload = {
            "auction_id": auction_id,
            "agent": self.me.agent_id,
            "max_qty_l": bid.max_qty_l,
            "max_price_per_l": bid.max_price_per_l,
            "balance": round(self.balance, 4),
        }
        #  WHEN I WANT IT (#625): the instant I intend to present, where the want I serve
        #  holds at one — the instant less the pour the host's valve takes for these litres,
        #  read off Acquiring's own landing so the two never fork (#238). A want unmet now
        #  wants it now, and says nothing.
        if wanted_at is not None:
            payload["wanted_at"] = self._presenting_instant(wanted_at, market, bid.max_qty_l).isoformat()
        sent = self.publish(f"{market.bid_topic}/{self.me.agent_id}", payload, not_after=not_after)
        if sent:
            done()
        return sent

    # --- what came back ---

    def on_claim(self, market, claim: dict) -> None:
        """A round cleared to me: pay, and WRITE THE CLAIM as a fact in my own graph (#523).
        Nothing is adopted here — the tender standing on this venue is done when the fact
        appears (`market:Tendering`'s `orexis:doneWhen`), the keeper advances to Presenting
        and holds it until my watch is live, and `present` takes it. A market with no redeem
        channel has already redeemed; the claim is written all the same, so the same road
        presents nothing and opens the watch."""
        if claim.get("auction_id"):
            rounds.close_round(self.agent, claim["auction_id"])   # over for me: I won
        amount = float(claim.get("amount_l", 0.0))
        debit = float(claim.get("debit", 0.0))
        left = wallet.debit(self.agent, debit)
        self.won_l += amount
        self.log.info("won %.3f L for €%.2f — balance €%.2f", amount, debit, left)
        if (sensing := self.agent.provider(SENSING)) is not None:
            sensing.sense_now()   # the freshest before on record — and the watch it makes live
        now = clock.now().isoformat()
        jti = claim.get("jti") or f"unredeemable-{uuid.uuid4().hex[:8]}"
        #  A VENUE WITH NO REDEEM CHANNEL, or a claim with no id, is one the host redeemed
        #  for me: written as presented, so Presenting has nothing to send and opens the watch.
        redeemed = (f'\n      <{PRESENTED_AT}> "{now}"^^xsd:dateTime ;'
                    if not market.redeem_topic or not claim.get("jti") else "")
        #  WATER AT A TIME (#625): the window the host granted rides onto the fact, and the
        #  Presenting step is placed by it (`orexis:readyAt`).
        window = "".join(
            f'\n      <{term}> "{claim[key]}"^^xsd:dateTime ;'
            for key, term in (("usable_from", USABLE_FROM), ("usable_until", USABLE_UNTIL))
            if claim.get(key))
        #  A GRAPH HOLDING DURING THE CLAIM'S WINDOW (#645): from now to `usable_until`, open
        #  where the host named none, so the door hands a lapsed claim to nobody and the one
        #  sweep drops it — this module keeps no sweep, and lets nothing go by hand.
        graph = claim_graph(self.agent.id, jti)
        ends = (f'\n      orexis:end "{claim["usable_until"]}"^^xsd:dateTime ;' if claim.get("usable_until") else "")
        self.agent.beliefs.drop_graph(graph)
        self.agent.beliefs.update(f"""
INSERT DATA {{
  GRAPH <{graph}> {{
  <{self.me.uri}> <{HOLDS_CLAIM}> <{NS}claim_{jti}> .
  <{NS}claim_{jti}> a <{CLAIM}> ; <{CLAIM_ID}> "{jti}" ; <{CLAIMED_AT}> "{now}"^^xsd:dateTime ;{redeemed}{window}
      <{CLAIM_L}> "{amount}"^^xsd:decimal ; <{CLAIM_DEBIT}> "{debit}"^^xsd:decimal ;
      <{ON_VENUE}> <{market.uri}> . }}
  GRAPH <{CLASSIFICATION_GRAPH}> {{ <{graph}> a orexis:BeliefGraph ; orexis:arrivedBy <{rounds.RECEIVED}> . }}
  GRAPH <{PERIODS_GRAPH}> {{
    <{graph}> dcterms:temporal [ a dcterms:PeriodOfTime ;{ends}
      orexis:start "{now}"^^xsd:dateTime ] . }}
}}""")
        #  GRANTED ON MY ASK, with nothing standing for the want (#627): nothing is waiting on
        #  this fact, so the mind is woken — buying is available while I hold a claim, and
        #  the pass plans the presenting, placed by the claim's window. A plan standing is
        #  left to the keeper, which advances its tender on the fact as it always has.
        from orexis_agent_deliberation import reviser

        keeper = self._keeper()
        stake = self._stake()
        if (not redeemed and stake is not None
                and not (keeper is not None and keeper.standing(want=stake.uri))):
            reviser.wake_for(self.agent, stake)
