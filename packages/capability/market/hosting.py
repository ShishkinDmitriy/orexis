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
from .auction import run_auction
from .trade import EPS, Bid, Limits, MarketState, Offer
from agent.desire import Desire
from agent.module import Module, Timer
from agent.ontology import WORLD_GRAPH
from agent.store import bindings

from . import calls, rounds
from .wiring import allocation_ceilings, hosted_markets_of, participants
from .beliefs import HOSTING_PICKS

#  The serving action, spelled rather than imported: the kernel owns the term and market's own
#  honoured.rq binds it, and `intention/terms.py` holds the same string for the same reason —
#  a package may not import another's Python.
from .terms import (ACTUATION, SENSING, SERVING, HOSTING, BID_MATCHING,
                    OFFERING)


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
        self.beliefs = agent.desires.read(HOSTING_PICKS)
        self.markets = hosted_markets_of(agent.beliefs.query, self.me.uri)
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
        #  `deferred` and `last_auction_at` WERE HERE. A LOW nobody could serve was held in a
        #  dict and reopened on the next reading; the cooldown was a monotonic clock. Both are
        #  facts now — a `market:Call` and `market:mayConveneAt` in my own graph — and the
        #  Offering action's precondition reads them, so a dry vessel is a plan the search
        #  finds (acquire upstream, then offer) rather than a handler (#359).
        self.open_auction: dict | None = None
        self._timer: Timer | None = None
        # Issued and not yet presented, by jti (#132). Winning stopped implying actuation: the
        # holder redeems when its watch is live, so the host keeps the claim until it is
        # presented — single-use, popped on redemption. In-memory, like the round itself: a
        # host that restarts forgets unpresented claims, which is the claim-ledger seam the
        # roadmap already records, not a new one.
        self.held: dict[str, object] = {}

    def _keeper(self):
        """Whoever keeps my commitments, or None — and None keeps the old behaviour whole."""
        return self.agent.keeper

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
        """A participant said it is in trouble. That makes a round WANTED — a call (#359).

        In trouble ABOUT THE RIGHT THING. An announcement names the property it is about — it has
        since a subject with two sensors started announcing two values on one topic — and a
        participant that is too cold is not a participant this market can help.

        Nothing is decided here. The call is written into my own graph as a want the search
        ranges over, and execution plans it: Offer where the vessel holds something and my
        cooldown has run out, acquire upstream then Offer where it is dry, nothing where neither
        is possible yet — and then the call stays hot, and the next reading or tick tries again.
        The cooldown, the open round and the dry vessel are the Offering action's premises
        now, not checks here.
        """
        if event.get("band") != "LOW":
            return
        about = self.about.get(market.uri)
        if about and event.get("property") not in about:
            return
        calls.call(self.agent, market.uri, event.get("agent", "?"))
        self._pursue_calls(market)

    def _pursue_calls(self, market=None) -> None:
        """Every call I hold — on one venue, or all — through execution."""
        from agent import execution

        for desire in self.desires():
            if market is None or desire.uri == calls.uri_for(market.uri):
                execution.pursue(self.agent, desire)

    def desires(self, now=None) -> list[Desire]:
        """My contribution to what this agent pursues: the calls on the venues I host.

        A call is a want somebody else sourced, like a debt (owing contributes those); it is
        met exactly when a round stands on its venue, and since a round that opens answers the
        call by retracting it, every call I hold is unmet. Maximal urgency, and deliberately:
        a call has no clock running it down, and a host with a stake of its own (the dealer's
        barrel) ranks its downstream's trouble beside it rather than below it — the strategic
        question of whether it would RATHER sell is the strategic-supplier seam, not a number
        invented here.
        """
        return [Desire(uri=c.uri, urgency=1.0) for c in calls.calls_of(self.agent)]

    def desire_urgency(self, desire, query, sensed: str, value=None) -> float | None:
        """How badly a CALL is unmet, in the world `query` answers about: 0 where a round
        stands on its venue, 1 where none does. Reads both the graph I hold rounds in and
        the graph a plan imagines them into, because an Offer's effect lands in the latter.
        None for anything that is not a call."""
        if not desire.uri.startswith(f"{calls.NS}call_"):
            return None
        from agent.ontology import beliefs_graph

        rows = bindings(query(f"""
SELECT ?r WHERE {{
  GRAPH <{beliefs_graph(self.agent.id)}> {{ <{desire.uri}> market:calledOn ?via }}
  {{ GRAPH <{beliefs_graph(self.agent.id)}> {{ ?via market:hasRound ?r . ?r market:closesAt ?c }}
    FILTER(?c > NOW()) }}
  UNION {{ GRAPH <{sensed}> {{ ?via market:hasRound ?r }} }}
}} LIMIT 1"""))
        return 0.0 if rows else 1.0

    def on_reading_recorded(self, subject_uri: str, observed_property: str, value: float) -> None:
        """My witness reported the vessel: every held claim and every call is tried again.

        The refill landing is the reading that changes the answer — for a claim held because
        the vessel was too low, and for a call the search could not plan an Offer for. Neither
        is decided here; both go through execution, which finds what the new stock allows.
        """
        for market in self.markets:
            if subject_uri != market.resource or observed_property != self.stock_property.get(market.uri):
                continue
            if (ledger := self.agent.owing) is not None:
                for desire in ledger.duties():
                    if desire.pursuable and desire.claim in self.held:
                        self._pursue(desire.claim,
                                     f"my vessel reports {value:.3f} — trying again")
            self._pursue_calls(market)

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
        sensing = self.agent.provider(SENSING)
        reading = sensing.current_reading(market.resource, prop) if sensing else None
        return reading.value if reading is not None else None

    def announce(self, market, trigger: str) -> bool:
        quantity_l = self.beliefs.quantity_l
        stock = self._stock_of(market)
        if stock is not None:
            if stock <= EPS:
                #  Unreachable through execution — Offering's premise is stock > 0 — and kept
                #  as the boundary for anyone who calls this directly: a dry vessel announces
                #  no lot it cannot pour, and the call it would have answered stays standing.
                self.log.info("%s is LOW but my vessel is dry — no round; the call stands "
                              "until the refill lands", trigger)
                return False
            quantity_l = min(quantity_l, stock)
        auction_id = uuid.uuid4().hex[:8]
        self.open_auction = {"auction_id": auction_id, "market": market, "bids": {},
                             "quantity_l": quantity_l}
        calls.answer(self.agent, market.uri)   # the round is what the call wanted
        #  THE ROUND AS A FACT, in my own graph: what I announced, as I announced it — the lot,
        #  the reserve and the instant bidding closes. Never the window or the cooldown.
        from datetime import datetime, timedelta, timezone

        rounds.open_round(self.agent, market.uri, auction_id, quantity_l,
                          self.beliefs.reserve_price_per_l,
                          datetime.now(timezone.utc)
                          + timedelta(seconds=float(self.beliefs.bid_window_s)))
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
        return True

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
        rounds.close_round(self.agent, auction_id)   # over, whatever the bids say below
        rounds.convened(self.agent, market.uri, self.beliefs.cooldown_s)   # the next may open then

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
        #  The LEDGER OF DEBTS and not the deducer (#233). A host with no stake of its
        #  own — the city, acting for a mains that states no ranges — used to reach this line,
        #  find no desire module, and record nothing at all while issuing claims all day.
        if (ledger := self.agent.owing) is not None:
            for claim in result.claims:
                ledger.owe(claim.sub, claim.jti, expires_at=claim.exp, amount_l=claim.amount_l)

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
        ledger = self.agent.owing
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
        ledger = self.agent.owing
        if ledger is None:
            self._serve(jti, why)
            return
        desire = next((g for g in ledger.duties() if g.claim == jti), None)
        if desire is None:
            return
        #  THROUGH EXECUTION: the search sees the honoured row AND this agent's own levers,
        #  so a host owing water it does not hold plans the refill — an Acquire, committed and
        #  handed to bidding, which stands until the upstream round — and the claim stays held
        #  for the sweep that re-runs this when stock arrives. A serve is the plan's head only
        #  when the vessel can honour it, and `take` below is handed exactly that row.
        from agent import execution

        if execution.pursue(self.agent, desire) is None and jti in self.held:
            # Hot, owed, and unpursued — or absorbed within patience. It stays in `held`, so
            # the moment the answer changes the sweep serves it.
            self.log.warning(
                "claim %s stands unserved (urgency %.2f, owed to %s): nothing was committed",
                jti, desire.urgency, desire.owed_to.rsplit("#", 1)[-1])

    def take(self, row, desire, intention: str) -> bool:
        """Carry out a committed serve: pour the claim this duty names.

        The actor for `market:Apply` on the duty's row (knowledge/domain/actor.md). A plan
        whose head is the refill hands that row to bidding, not here; this answers only a
        serve, and only for a claim still held — a duty whose claim was never presented is
        not this module's to invent.
        """
        if row.action == OFFERING:
            #  THE HOST'S MOVE, taken: announce on the venue the row names, for the call the
            #  plan served. `announce` sizes the lot by the vessel and writes the round; the
            #  call is answered by the round existing. Satisfied at once — the round is the
            #  end, and it is there by construction.
            market = next((m for m in self.markets if m.uri == row.via), None)
            if market is None:
                return False
            by = next((c.called_by for c in calls.calls_of(self.agent, market.uri)), "?")
            if not self.announce(market, trigger=by):
                return False
            if (keeper := self._keeper()) is not None:
                keeper.satisfy(OFFERING, row.observed_property, "the round opened", desire=desire.uri)
            return True
        if row.action != SERVING or not desire.claim or desire.claim not in self.held:
            return False
        #  A VESSEL I KNOW IS TOO LOW IS NOT POURED FROM. The search used to keep this claim
        #  held by planning the refill first; since a round is a fact (#358) there may be no
        #  upstream round to plan into, the search finds no path, and the duty's own row is
        #  what reaches here. The actor is the boundary then: what I know of my stock says the
        #  claim cannot be honoured, so it stays held for the reading that changes that. A
        #  vessel I have never read keeps the old arrangement and is judged by the pour.
        claim = self.held[desire.claim]
        market = next((m for m in self.markets if m.uri == row.via or
                       self.stock_property.get(m.uri)), None)
        stock = self._stock_of(market) if market is not None else None
        if stock is not None and stock + EPS < claim.amount_l:
            self.log.info("claim %s waits — my vessel holds %.3f L and it asks %.3f L",
                          desire.claim, stock, claim.amount_l)
            return False
        self._serve(desire.claim, "the plan's head — a duty's row")
        if (keeper := self._keeper()) is not None:
            keeper.satisfy(SERVING, row.observed_property, "served", desire=desire.uri)
        return True

    def _serve(self, jti: str, why: str) -> None:
        claim = self.held.pop(jti)
        self.log.info("serving claim %s (%.3f L) — %s", jti, claim.amount_l, why)
        self.redeem([claim])
        if (ledger := self.agent.owing) is not None:
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
