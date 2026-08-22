"""market:Hosting — run auctions in a market: announce, collect, match, clear, issue.

This module exists in this shape *because* each agent is its own process. The host cannot
compute anyone's bid — the valuation is private and lives in another process entirely — so an
auction is a conversation rather than a calculation:

    participant announces it is in trouble (its own judgment, voluntarily disclosed)
        -> host announces an offer with a deadline          [market:offerTopic]
        -> each bidder answers with a number only it can compute   [market:bidTopic/<agent>]
        -> host matches, clearing validates, claims go back  [market:claimTopic/<agent>]
        -> each HOLDER presents its claim when its watch is live [market:redeemTopic/<agent>]
        -> actuation redeems the presented claim against the hardware

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

import json

from agent import signing
from agent.auction import run_auction
from agent.market import EPS, Bid, Limits, MarketState, Offer
from agent.module import Module, Timer
from agent.ontology import WORLD_GRAPH
from agent.store import bindings
from agent.world import allocation_ceilings, participants

from .beliefs import HOSTING_BLOCK
from .terms import (ACTUATION, DELIBERATION, HOSTING, BID_MATCHING,
                    INTENTION, OFFER, OWING)


def _event_topics_q(market_uri: str) -> str:
    """Where my participants announce what they notice. Public, like the rest of the wiring."""
    return f"""
SELECT ?agentId ?eventTopic WHERE {{
  ?agent market:bidsIn <{market_uri}> ; ag:localId ?agentId ; mqtt:eventTopic ?eventTopic  }}"""


# Which properties being in trouble are a reason to open a round HERE. Asked through THE
# VENUE AND ITS PARTICIPANTS' STAKES (#198), per hosted market: the venue is for a source,
# the source's class states its good, the good's valuations each carry a property, and the
# ones THIS venue convenes on are those some participant's subject states a need in — the
# same premises the participation rule derived that bidsIn from, read from the host's side.
# Both joins are load-bearing, and a set rather than one property, because one venue may
# serve two kinds of recipient: the barrel's venue waters pots (SoilMoisture) while the
# city's fills barrels (StoredLitres), and the same good backs both.
#
# This became load-bearing twice. First when an agent could want more than one thing: a fern
# announces a temperature band too, and nothing relieves a hot afternoon by dispensing water.
# Then again when a second denomination existed: asked of the T-Box at large (as this was),
# the host would have filtered on whichever property the store returned first — opening
# rounds on the wrong scarcity, or never, silently, by ORDER BY luck.
_ABOUT_Q = """
SELECT DISTINCT ?property WHERE {
  <%s> market:marketFor ?src . ?src market:supplies ?good .
  ?buyer market:bidsIn <%s> ; ag:actsFor ?subject .
  ?subject <http://www.w3.org/ns/ssn/systems/hasOperatingRange> ?range .
  ?range <http://www.w3.org/ns/ssn/systems/inCondition> ?cond .
  ?cond <http://www.w3.org/ns/ssn/forProperty> ?property .
  ?term market:ofGood ?good ; market:aboutProperty ?property }"""

# The attested roster (#144, #145): each agent's published public keys, from keys.ttl swept
# into the world graph. Absence is the pre-key era and stays legal — a world onboarded before
# keygen learned agents has no rows here and behaves exactly as it always did.
_KEY_Q = """
SELECT ?key WHERE { ?a ag:localId "%s" ; ag:%s ?key } LIMIT 1"""


class HostingModule(Module):
    CAPABILITY = HOSTING
    name = "hosting"

    def __init__(self, agent):
        super().__init__(agent)
        self.beliefs = agent.beliefs.read(HOSTING_BLOCK)
        self.markets = self.me.hosted_markets
        self.participants = {
            m.uri: participants(agent.beliefs.query, m) for m in self.markets
        }
        # Derived at genesis from the world, so it is read once rather than per round. A
        # participant absent from this map has no stated ceiling and is not checked; see #270.
        self.ceilings = {
            m.uri: allocation_ceilings(agent.beliefs.query, m) for m in self.markets
        }
        self.event_topics = {}  # topic -> market
        for market in self.markets:
            for row in bindings(agent.beliefs.query(_event_topics_q(market.uri))):
                self.event_topics[row["eventTopic"]] = market

        # Empty when no valuation of the venue's good meets any participant's stake — a
        # market in something no instrument measures, which `market:aboutProperty` exists to
        # keep expressible. Such a host takes any band it is sent, which is the behaviour
        # every host had before there was more than one kind of band to send. Per MARKET
        # (#198), because a host of two venues convenes each on its own scarcities — the
        # dealer hosting water-for-pots while bidding for refill litres must not confuse
        # the two.
        self.about = {}
        for market in self.markets:
            rows = bindings(agent.beliefs.query(_ABOUT_Q % (market.uri, market.uri)))
            self.about[market.uri] = {r["property"] for r in rows}

        # My witness on each venue's source, where I have one (#the-planner): the sensor I
        # poll that monitors the resource, and the property it observes. A host with a witness
        # sizes its rounds by what the vessel actually holds; a host without one sells blind —
        # honest for the mains, whose pressure is always there and whose 1000 L is a
        # constitutional ceiling rather than a stock anyone watches.
        self.stock_property = {}
        for market in self.markets:
            rows = bindings(agent.beliefs.query(f"""
SELECT ?p WHERE {{
  <{self.me.uri}> sensing:polls ?s .
  ?s sensing:monitors <{market.resource}> ; sosa:observes ?p }} LIMIT 1"""))
            self.stock_property[market.uri] = rows[0]["p"] if rows else None
        # A LOW I could not serve, per market: the refill-then-sell dependency, held until the
        # stock arrives. The deferred round is the plan's second step made observable — see
        # knowledge/decisions/a-plan-is-a-path-of-graph-diffs.md, "the first honest customer".
        self.deferred: dict[str, str] = {}

        self.open_auction: dict | None = None
        self.last_auction_at = 0.0
        self._timer: Timer | None = None
        # Issued and not yet presented, by jti (#132). Winning stopped implying actuation: the
        # holder redeems when its watch is live, so the host keeps the claim until it is
        # presented — single-use, popped on redemption. In-memory, like the round itself: a
        # host that restarts forgets unpresented claims, which is the claim-ledger seam the
        # roadmap already records, not a new one.
        self.held: dict[str, object] = {}

    def _keeper(self):
        """Whoever keeps my commitments, or None — and None keeps the old behaviour whole."""
        return self.agent.provider(INTENTION)

    def subscriptions(self) -> list[str]:
        topics = list(self.event_topics)
        for market in self.markets:
            topics.append(f"{market.bid_topic}/+")
            if market.redeem_topic:
                topics.append(f"{market.redeem_topic}/+")
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
            if m.redeem_topic and topic.startswith(m.redeem_topic + "/"):
                self.on_redeem(topic.rsplit("/", 1)[-1], self.parse(payload) or {})
                return True
        return False

    def on_participant_event(self, market, event: dict) -> None:
        """A participant said it is in trouble. Scarcity is what condenses an auction.

        In trouble ABOUT THE RIGHT THING. An announcement names the property it is about — it has
        since a subject with two sensors started announcing two values on one topic — and a
        participant that is too cold is not a participant this market can help.
        """
        if event.get("band") != "LOW":
            return
        about = self.about.get(market.uri)
        if about and event.get("property") not in about:
            return
        now = time.monotonic()
        if now - self.last_auction_at < self.beliefs.cooldown_s:
            return  # a flapping participant must not be able to spam the market
        if self.open_auction is not None:
            return
        self.announce(market, trigger=event.get("agent", "?"))

    def on_reading_recorded(self, subject_uri: str, observed_property: str, value: float) -> None:
        """The refill landed — the deferred sell reopens. The two-step's second step.

        A LOW nobody could serve was held in `deferred` instead of being sold as phantom
        water; the moment my own witness reports the vessel holding anything again, the
        round it owed opens. The cooldown still applies — a refill is not a licence to spam —
        and an open round absorbs it exactly as a fresh LOW would.
        """
        for market in self.markets:
            if subject_uri != market.resource or observed_property != self.stock_property.get(market.uri):
                continue
            # My own vessel just said what it holds, which is the one moment the answer to
            # "can I serve what I owe" can have changed without anybody speaking to me. A debt
            # refused for want of stock is not lost and is not retried on a clock: it waits
            # here, on the reading, exactly as the deferred round does. The two are the same
            # shape — a commitment held until the world can honour it — and it is worth
            # noticing that the duty case needed no new machinery, only a want to point at.
            if (ledger := self.agent.provider(OWING)) is not None:
                for desire in ledger.duties():
                    if desire.pursuable and desire.claim in self.held:
                        self._pursue(desire.claim,
                                     f"my vessel reports {value:.3f} — trying again")
            if market.uri not in self.deferred:
                # An owed round survives the process that owed it (#206): the deferral used
                # to live in module memory alone, so a restart forgot a commitment the
                # ledger never saw. A standing Offer for this vessel's stock IS the owed
                # round, recovered here — at the reading, where the debt becomes payable —
                # rather than at any lifecycle moment a test or a crash could miss.
                keeper = self._keeper()
                if keeper is None or not any(
                        s.observed_property == observed_property and s.means == OFFER
                        for s in keeper.standing()):
                    continue
                self.deferred[market.uri] = \
                    "a round owed before this process started — the ledger kept it"
            if value <= EPS:
                continue
            if self.open_auction is not None:
                continue
            if time.monotonic() - self.last_auction_at < self.beliefs.cooldown_s:
                continue
            trigger = self.deferred.pop(market.uri)
            if keeper := self._keeper():
                keeper.satisfy(OFFER, self.stock_property[market.uri],
                               "the refill landed — the owed round opens", desire=market.uri)
            self.log.info("the refill landed (%.3f) — opening the round deferred for %s: "
                          "step two of acquire-then-offer", value, trigger)
            self.announce(market, trigger=trigger)

    def matcher(self):
        """Whichever of my capabilities can turn bids into an allocation, or None.

        Asked for by family, so this package does not know that pay-as-bid is implemented in
        Python at all — the same way `redeem` asks for whoever can actuate. A host that names
        a way of matching nothing implements gets None here, which is the honest outcome of
        declaring a member ahead of its module.
        """
        return self.agent.provider(BID_MATCHING)

    def _stock_of(self, market) -> float | None:
        """What my venue's vessel holds, by my own freshest reading — None when I am blind.

        The freshest I have, however old: a stale level is still my best knowledge of my own
        stock, and a push sensor updates it on its own clock. What this exists to end is the
        phantom dose: a barrel at 0.000 kept selling 2 L lots, the sim valve poured water
        from nothing, and conservation was violated live on the bench while every module
        behaved exactly as written.
        """
        prop = self.stock_property.get(market.uri)
        if prop is None:
            return None
        reading = self.agent.beliefs.current_reading(market.resource, prop)
        return reading.value if reading is not None else None

    def announce(self, market, trigger: str) -> None:
        quantity_l = self.beliefs.quantity_l
        stock = self._stock_of(market)
        if stock is not None:
            if stock <= EPS:
                # The dry vessel is the dependency the planning record names: "water fern"
                # dead-ends here, and the true plan is refill, then sell. The refill is the
                # stake's own business (the reflex is already pursuing the stock's aim); the
                # SELL is deferred, and reopens the moment my witness reports the refill —
                # the two-step, held by the market instead of sold as phantom water.
                self.deferred[market.uri] = trigger
                # The owed round is a COMMITMENT, and commitments live in the ledger (#206):
                # crossing the "host keeps no gap ledger" line knowingly, because a deferral
                # held only in module memory was a promise a restart forgot and no ask could
                # see. Deciding is still nobody's here — physics deferred the round, and the
                # keeper only remembers that it is owed.
                if keeper := self._keeper():
                    #  The venue IS the desire here: a host of two venues owes two rounds, and
                    #  keying by property alone would make paying one look like paying both.
                    keeper.adopt(OFFER, self.stock_property[market.uri],
                                 f"{trigger} is LOW and my vessel is dry — a round is owed "
                                 f"on {market.local_id} the moment the refill lands",
                                 desire=market.uri)
                self.log.info("%s is LOW but my vessel is dry — deferring the round: "
                              "acquire upstream, then offer (the depth-2 plan, distributed)",
                              trigger)
                return
            quantity_l = min(quantity_l, stock)
        auction_id = uuid.uuid4().hex[:8]
        self.last_auction_at = time.monotonic()
        self.open_auction = {"auction_id": auction_id, "market": market, "bids": {},
                             "quantity_l": quantity_l}
        matcher = self.matcher()
        self.log.info("auction %s opened on %s (%s is LOW) — %.2f L, reserve €%.2f, %ss to bid",
                      auction_id, market.local_id, trigger, quantity_l,
                      self.beliefs.reserve_price_per_l, self.beliefs.bid_window_s)
        self.publish(market.offer_topic, {
            "auction_id": auction_id,
            "host": self.me.agent_id,
            "quantity_l": quantity_l,
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
            limits=Limits(tank_capacity_l=market.capacity_l,
                          allocation_ceiling_l=self.ceilings[market.uri]),
        )
        offer = Offer(
            supplier=self.me.agent_id,
            # The round's own quantity, not the belief: the announce may have sized this
            # round down to what the vessel actually held, and matching against the full
            # lot would allocate the phantom litres the sizing exists to refuse.
            quantity_l=rnd.get("quantity_l", self.beliefs.quantity_l),
            reserve_price_per_l=self.beliefs.reserve_price_per_l,
        )

        matcher = self.matcher()
        if matcher is None:
            # Nothing to allocate the bids with. Checked here as well as by the shape, because a
            # world can be amended between validation and an auction, and losing its bids in
            # silence is worse than saying so — every bidder is waiting on a claim.
            self.log.error("auction %s cannot be matched — this host has no matching capability, "
                           "so the bids are discarded. Check its market:matchesBy.", auction_id)
            return

        result = run_auction(offer, bids, state, auction_id=auction_id,
                             match=matcher.propose_match,
                             redeem_window_s=market.redeem_window_s)
        if not result.validation.ok:
            self.log.warning("auction %s RED — clearing rejected: %s",
                             auction_id, result.validation.violations)
            return
        if not result.claims:
            self.log.info("auction %s closed — nothing cleared the reserve", auction_id)
            return

        self.log.info("auction %s GREEN — %.3f L allocated to %d",
                      auction_id, result.trade.total_qty_l, len(result.claims))
        for claim in result.claims:
            self._issue(market, auction_id, claim)
        # Issued is not actuated (#132). The host used to redeem every claim itself, here,
        # the moment it published them — which spent the dose before the winner's sensor could
        # possibly be watching it land. The claims are HELD now, and the holder presents each
        # when its watch is live; a market authored without a redeem channel keeps the old
        # reflex, so a pre-#132 world behaves exactly as it always did.
        if market.redeem_topic:
            for claim in result.claims:
                self.held[claim.jti] = claim
        else:
            self.redeem(result.claims)
        # The debt is a WANT now (#218 remade): the society allocated, so this agent owes —
        # raised as an obligation in its own desire ledger, with the counterparty and the
        # claim that sourced it, whether or not the holder ever presents. What it buys
        # immediately is durability: `held` above dies with the process, and a restarted host
        # used to forget every claim it had issued.
        #  Asked for by OWING and no longer by DESIRE (#233). A host with no stake of its
        #  own — the city, acting for a mains that states no ranges — used to reach this line,
        #  find no desire module, and record nothing at all while issuing claims all day.
        if (ledger := self.agent.provider(OWING)) is not None:
            for claim in result.claims:
                ledger.owe(claim.sub, claim.jti, expires_at=claim.exp)

    def on_redeem(self, presenter: str, claim: dict) -> None:
        """A holder presented its claim: verify it is theirs, then actuate. Single-use.

        Three refusals, each logged with its reason, none answered on the wire — a redeem
        channel is not a conversation, and a forged claim deserves a log line for the operator,
        not an error message for the forger: an unknown or already-spent jti, a claim presented
        by someone other than the winner it was issued to, and a payload with no jti at all.
        """
        jti = claim.get("jti")
        if not jti:
            self.log.warning("redeem from %s carries no jti — ignored", presenter)
            return
        # The winner's own hand (#144). Where the roster publishes a signing key for the
        # presenter, the presentation must carry a signature over its canonical form and the
        # signature must verify — the durable identity exercising the ephemeral grant, which
        # takes the BROKER out of the trust boundary: the ACL becomes defence in depth, not
        # the proof. No published key means the pre-#144 era, and the ACL stands alone as it
        # always did.
        rows = bindings(self.agent.beliefs.query(_KEY_Q % (presenter, "signingKey")))
        if rows:
            sig = claim.get("sig", "")
            payload = {k: v for k, v in claim.items() if k != "sig"}
            pub = signing.signing_public_from_b64(rows[0]["key"])
            if not sig or not signing.verify(pub, signing.canonical(payload), sig):
                self.log.warning("redeem from %s fails its own signature — ignored", presenter)
                return
        claim = self.held.get(jti)
        if claim is None:
            self.log.warning("redeem from %s for unknown or already-spent jti %s — ignored",
                             presenter, jti)
            return
        if claim.sub != presenter:
            self.log.warning("%s presented %s's claim %s — ignored",
                             presenter, claim.sub, jti)
            return
        # A window that closed (#step 9). The venue held this claim for exactly as long as it
        # said it would, and afterwards the good is the venue's again — a holder that never
        # presented has forfeited, and dosing now would put water where nobody is watching for
        # it. The debt stays on the books, undischarged, with a deadline in the past: that is
        # the evidence, and it reads differently from a debt paid and differently again from a
        # debt nobody ever demanded.
        if claim.exp is not None and time.time() > claim.exp:
            del self.held[jti]
            self.log.warning("%s presented claim %s after its window closed — refused, and the "
                             "debt stands unserved", presenter, jti)
            return
        # Asked for: the obligation steps from owed to demanded. What happens next is a
        # DECISION and not a handler any more — the whole of step 9. See below.
        ledger = self.agent.provider(OWING)
        if ledger is not None:
            ledger.demanded(jti)
        self._pursue(jti, f"{presenter} presented it")

    def _pursue(self, jti: str, why: str) -> None:
        """Serve a debt because this agent WANTS to, or leave it standing and hot.

        The step-9 turn, and it is small on the page because the design had been laid for it:
        an obligation is a want (an-obligation-is-a-desire-someone-else-sourced), so the host
        does not redeem *on presentation* — it asks its deliberator about a GOAL, exactly as it
        would about a pot drying, and acts on the answer. A society where a claim is honoured
        by a handler cannot express a host that is out of stock; one where it is honoured by a
        decision reports that as a hot unpursued desire, which is the posture this project takes
        towards everything it cannot prevent.

        The guarantee that was never deliberation's is untouched: the dose still opens against
        a claim the pump's firmware verifies, clearing still validated the trade, and the ACL
        still bounds who may speak. What moved is only whether this agent TRIES — see "why a
        deliberating host is not a defecting host" in that record.

        No deliberator means the old arrangement, whole: a build without one redeems on
        presentation as it always did, because refusing to act for want of an opinion would be
        a worse failure than the one this replaces.
        """
        claim = self.held.get(jti)
        if claim is None:
            return
        ledger = self.agent.provider(OWING)
        deliberator = self.agent.provider(DELIBERATION)
        if ledger is not None and deliberator is not None:
            desire = next((g for g in ledger.duties() if g.claim == jti), None)
            if desire is None:
                return
            if deliberator.propose_for(desire) is None:
                # Hot, owed, and unpursued. It stays in `held`, so the moment the answer
                # changes — stock arrives, a lever comes back — the sweep below serves it.
                self.log.warning(
                    "claim %s stands unserved (urgency %.2f, owed to %s): %s proposed no move",
                    jti, desire.urgency, desire.owed_to.rsplit("#", 1)[-1], deliberator.name)
                return
        del self.held[jti]
        self.log.info("serving claim %s (%.3f L) — %s", jti, claim.amount_l, why)
        self.redeem([claim])
        if ledger is not None:
            ledger.discharge(jti)

    def _issue(self, market, auction_id: str, claim) -> None:
        """Publish one winner's claim — sealed to it, where the roster says it can open one.

        The seal (#145) is what takes the BUS out of the confidentiality boundary: the ACL
        already keeps other agents off this topic, but the broker, a port mirror or an operator
        on the wire read every payload — and this one has money in it. Sealed, they carry an
        envelope only the winner can open. A winner with no published sealing key receives
        plaintext: the pre-#145 era, legal, exactly as the missing signing key is for #144.
        """
        payload = {"auction_id": auction_id, "jti": claim.jti, "sub": claim.sub,
                   "scope": claim.scope, "amount_l": claim.amount_l,
                   "debit": claim.debit}
        rows = bindings(self.agent.beliefs.query(_KEY_Q % (claim.sub, "sealingKey")))
        if rows:
            sealed = signing.seal(signing.sealing_public_from_b64(rows[0]["key"]),
                                  signing.canonical(payload))
            payload = {"sealed": sealed}
        self.publish(f"{market.claim_topic}/{claim.sub}", payload)

    def redeem(self, claims) -> None:
        """Hand the claims to whichever of my capabilities can touch the hardware.

        Winning is not the same as being able to open a valve: the resource owner redeems.
        Asked for by term, so this package does not know that actuation is implemented in
        Python at all — a host in a build without it simply issues paper.
        """
        actuation = self.agent.provider(ACTUATION)
        if actuation is None:
            self.log.info("no actuation capability — claims issued but not redeemed")
            return
        actuation.redeem_all(claims)
