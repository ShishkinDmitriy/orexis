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
from dataclasses import replace
from datetime import datetime, timezone

import json

from agent import signing
from .auction import run_auction
from .trade import EPS, Bid, Limits, MarketState, Offer
from orexis_agent_deliberation.want import Want

from .ower import Ower
from agent.module import Module, contributes
from orexis_agent_progression.timer import Timer
from orexis_agent_progression.ontology import HANDLE, OUTDATED, SUBSCRIPTIONS

READING_RECORDED = "http://example.org/orexis/sensing#readingRecorded"   # sensing's hook, spelled
from orexis_agent_progression.act import Step
from orexis_agent_progression.ontology import WORLD_GRAPH, obligations_graph
from orexis_agent_progression.store import bindings
from assembly.contribute import contributes

from . import calls, rounds
from .wiring import allocation_ceilings, hosted_markets_of, node_of, participants
from .beliefs import HOSTING_PICKS

#  The serving action, spelled rather than imported: the kernel owns the term and market's own
#  honoured.rq binds it, and `intention/terms.py` holds the same string for the same reason —
#  a package may not import another's Python.
from .terms import (ACTUATION, SENSING, SERVING, HOSTING, BID_MATCHING, VENUE,
                    OFFERING)
from orexis_agent_progression import clock
from orexis_agent_progression.ontology import PUBLIC
from orexis_agent_progression.ontology import KNOWN


def _event_topics_q(market_uri: str) -> str:
    """Where my participants announce what they notice. Public, like the rest of the wiring."""
    return f"""
SELECT ?agentId ?eventTopic WHERE {{
  ?agent market:bidsIn <{market_uri}> ; orexis:localId ?agentId ; mqtt:eventTopic ?eventTopic  }}"""


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
  ?buyer market:bidsIn <%s> ; orexis:actsFor ?subject .
  ?subject <http://www.w3.org/ns/ssn/systems/hasOperatingRange> ?range .
  ?range <http://www.w3.org/ns/ssn/systems/inCondition> ?cond .
  ?cond <http://www.w3.org/ns/ssn/forProperty> ?property .
  ?term market:ofGood ?good ; market:aboutProperty ?property }"""

# The attested roster (#144, #145): each agent's published public keys, from keys.ttl swept
# into the world graph. Absence is the pre-key era and stays legal — a world onboarded before
# keygen learned agents has no rows here and behaves exactly as it always did.
_KEY_Q = """
SELECT ?key WHERE { ?a orexis:localId "%s" ; orexis:%s ?key } LIMIT 1"""


class HostingModule(Module):
    CAPABILITY = HOSTING
    name = "hosting"

    def __init__(self, agent):
        super().__init__(agent)
        self.beliefs = agent.desires.read(HOSTING_PICKS)
        #  THE LEDGER OF DEBTS IS MINE, since #448's neighbour: only a host owes, because a
        #  debt arises from a claim this agent ISSUED. It writes the graph the kernel declares
        #  — the same arrangement sensing has with `graph/sensed` — so the obligation modality
        #  stays the mind's while incurring one is the market's.
        self.ledger = Ower(agent)
        self.markets = hosted_markets_of(agent.beliefs.reader(PUBLIC), self.me.uri)
        self.participants = {
            m.uri: participants(agent.beliefs.reader(PUBLIC), m) for m in self.markets
        }
        # Derived at genesis from the world, so it is read once rather than per round. A
        # participant absent from this map has no stated ceiling and is not checked; see #270.
        self.ceilings = {
            m.uri: allocation_ceilings(agent.beliefs.reader(PUBLIC), m) for m in self.markets
        }
        self.event_topics = {}  # topic -> market
        for market in self.markets:
            for row in bindings(agent.beliefs.query(_event_topics_q(market.uri), agent.beliefs.graphs_of(PUBLIC))):
                self.event_topics[row["eventTopic"]] = market

        # Empty when no valuation of the venue's good meets any participant's region want — a
        # market in something no instrument measures, which `market:aboutProperty` exists to
        # keep expressible. Such a host takes any band it is sent, which is the behaviour
        # every host had before there was more than one kind of band to send. Per MARKET
        # (#198), because a host of two venues convenes each on its own scarcities — the
        # dealer hosting water-for-pots while bidding for refill litres must not confuse
        # the two.
        self.about = {}
        for market in self.markets:
            rows = bindings(agent.beliefs.query(_ABOUT_Q % (market.uri, market.uri), agent.beliefs.graphs_of(PUBLIC)))
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
  ?s sensing:monitors <{market.resource}> ; sosa:observes ?p }} LIMIT 1""", agent.beliefs.graphs_of(PUBLIC)))
            self.stock_property[market.uri] = rows[0]["p"] if rows else None
        self.open_auction: dict | None = None
        self._timer: Timer | None = None
        #  THE COOLDOWN'S OWN DEADLINE WAS A TIMER HERE (#598), with a sweep at boot for a row
        #  that outlived the process. The cooling row is a graph holding during its period
        #  now (#645): the door hands it to nobody past the horizon, and the one sweep drops it.
        # Issued and not yet presented, by jti (#132). Winning stopped implying actuation: the
        # holder redeems when its watch is live, so the host keeps the claim until it is
        # presented — single-use, popped on redemption. In-memory, like the round itself: a
        # host that restarts forgets unpresented claims, which is the claim-ledger seam the
        # roadmap already records, not a new one.
        self.held: dict[str, object] = {}

    def _keeper(self):
        """Whoever keeps my commitments, or None — and None keeps the old behaviour whole."""
        return self.agent.keeper

    @contributes(OUTDATED)
    def outdated(self, graph: str) -> None:
        """A graph of this agent's own has ended and is about to be dropped (#645): the ledger
        of debts is mine to keep and no module of its own, so the word reaches it through me —
        a debt whose window closed leaves its verdict in the record before its graph goes."""
        self.ledger.outdated(graph)

    @contributes(SUBSCRIPTIONS)
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

    @contributes(HANDLE)
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

    def start(self) -> None:
        #  THE LEDGER IS MINE TO START (#635): a debt written before the record carried its
        #  met-test is endowed with one, as an amendment endows what it grants.
        if self.ledger is not None:
            self.ledger.endow()

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
        if event.get("asks") is not None and event.get("wanted_at"):
            self.on_ask(market, event)
            return
        if event.get("band") != "LOW":
            return
        about = self.about.get(market.uri)
        if about and event.get("property") not in about:
            return
        calls.call(self.agent, market.uri, event.get("agent", "?"))
        self._pursue_calls(market)

    def on_ask(self, market, ask: dict) -> None:
        """A participant asked for a dose AT an instant (#627): grant it where my stock covers
        the ask at that instant — what I hold, less what I already owe to holders whose
        windows open by then, less the ask, still inside my vessel's region — and convene a
        round where it does not. The auction is the allocation under scarcity, not the only
        path to water; a claim granted is water at a time, a debt in my ledger, and an
        arrival my vessel's drift reads."""
        who = ask.get("agent")
        if who not in self.participants[market.uri]:
            self.log.warning("ask from %s, who does not bid in this market — ignored", who)
            return
        about = self.about.get(market.uri)
        if about and ask.get("property") not in about:
            return
        try:
            litres = float(ask["asks"])
            wanted_at = datetime.fromisoformat(ask["wanted_at"])
        except (TypeError, ValueError, KeyError):
            self.log.warning("ask from %s is unreadable: %r — ignored", who, ask)
            return
        if litres <= 0:
            return
        if self._covers(market, litres, wanted_at):
            self._grant(market, who, litres, wanted_at)
            return
        self.log.info("%s asks %.3f L at %s and my stock will not cover it — a round",
                      who, litres, wanted_at.isoformat(timespec="seconds"))
        calls.call(self.agent, market.uri, who)
        self._pursue_calls(market)

    def _covers(self, market, litres: float, wanted_at: datetime) -> bool:
        """Whether my vessel, less what I owe by `wanted_at`, less `litres`, stays inside its
        region — the same arithmetic the vessel's drift runs, asked of the ledger now."""
        stock = self._stock_of(market)
        if stock is None:
            return False
        #  THROUGH THE DOOR (#645): every debt standing now, each a graph of its own.
        rows = bindings(self.agent.beliefs.query(f"""
SELECT (SUM(?a) AS ?owed) WHERE {{
  ?debt market:forClaim ?jti ; market:amountL ?a ; market:owedAt ?issued .
  OPTIONAL {{ ?debt market:owedFrom ?from }}
  FILTER NOT EXISTS {{ ?debt market:dischargedAt ?d }}
  FILTER(COALESCE(?from, ?issued) <= \"{wanted_at.isoformat()}\"^^xsd:dateTime) }}""",
            self.agent.beliefs.graphs_of(*KNOWN, at=clock.now())))
        owed = float(rows[0]["owed"]) if rows and rows[0].get("owed") else 0.0
        floor = 0.0
        sensing = self.agent.provider(SENSING)
        prop = self.stock_property.get(market.uri)
        region = sensing.regions.get(prop) if sensing is not None and prop else None
        if region is not None and region.low is not None:
            floor = float(region.low)
        return stock - owed - litres >= floor - EPS

    def _grant(self, market, who: str, litres: float, wanted_at: datetime) -> None:
        """Issue a claim on an ask, no round: usable from the instant asked for, for the venue's
        window, at the reserve price; held for presenting, owed in the ledger with its window."""
        from .clearing import Claim
        jti = uuid.uuid4().hex
        opens = wanted_at.timestamp()
        expires = opens + float(market.redeem_window_s) if market.redeem_window_s else None
        claim = Claim(sub=who, permits=f"actuate:valve/{who}", amount_l=litres,
                      debit=round(litres * float(self.beliefs.reserve_price_per_l), 4),
                      auction_id=f"ask-{jti[:8]}", jti=jti, exp=expires, usable_from=opens,
                      step=Step(action=SERVING, binding=((VENUE, market.uri),), quantity=litres,
                                for_agent=node_of(self.agent.beliefs.reader(PUBLIC), who),
                                not_after=(datetime.fromtimestamp(expires, tz=timezone.utc)
                                           if expires is not None else None)))
        self.log.info("granting %s %.3f L usable from %s on its ask — no round", who, litres,
                      wanted_at.isoformat(timespec="seconds"))
        self._issue(market, claim.auction_id, claim)
        if market.redeem_topic:
            self.held[jti] = claim
        else:
            self.redeem([claim])
        if (ledger := self.ledger) is not None:
            ledger.owe(who, jti, expires_at=claim.exp, amount_l=litres, usable_from=opens)

    def _pursue_calls(self, market=None) -> None:
        """Every call I hold — on one venue, or all — through execution.

        ASKED OF THE WANTS, under the standing desire they are derived from. It read
        `self.desires()` and compared each row's uri to the call's, which worked while a call
        WAS the want this module built; a call is the instance now and the want is the
        derivation's, named after the desire and about the call — so the criterion is the
        desire it came under, and the venue is read off what it is about.
        """
        from orexis_agent_deliberation import reviser
        from orexis_agent_deliberation.wants import find_wants

        wanted = calls.uri_for(market.uri) if market is not None else None
        for want in find_wants(self.agent.beliefs, desire=self._calls_desire(), derived=True):
            if wanted is None or wanted in want.about:
                reviser.wake_for(self.agent, want)

    def _calls_desire(self) -> str:
        """The standing desire a call's want is derived under — `desires.ru` mints it at
        genesis, one per host, and spells it exactly this way."""
        return f"{self.me.uri}.no_unanswered_calls"

    def desires(self, now=None) -> list[Want]:
        """My contribution to what this agent pursues: the debts, delegated to the ledger that
        holds them.

        IT LIFTED THE CALLS TOO, and they were the one want in this repo that no derivation
        minted — built here per call and handed to the choir, with no provenance, no graph and
        no period. A host holds a standing desire over its venues now (`desires.ru`), the call
        is the instance it is about, and the want is the derivation's like every other. What
        is left here is the ledger's half, which is a delegation rather than a lift: the
        ledger is no longer a module in its own right, so what it contributes to the choir
        arrives through the module that holds it.
        """
        return self.ledger.desires(now)

    def series(self) -> list[tuple[str, dict, dict]]:
        """What I owe, as figures — the ledger's, through the module that holds it."""
        return self.ledger.series()

    @contributes(READING_RECORDED)
    def on_reading_recorded(self, subject_uri: str, observed_property: str, value: float) -> None:
        """My witness reported the vessel: every held claim and every call is tried again.

        The refill landing is the reading that changes the answer — for a claim held because
        the vessel was too low, and for a call the search could not plan an Offer for. Neither
        is decided here; both go through execution, which finds what the new stock allows.
        """
        for market in self.markets:
            if subject_uri != market.resource or observed_property != self.stock_property.get(market.uri):
                continue
            if (ledger := self.ledger) is not None:
                for judgment in ledger.obligations():
                    if judgment.pursuable and judgment.claim in self.held:
                        self._pursue(judgment.claim,
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
        if self.open_auction is not None:
            #  ONE OPEN ROUND, and `self.open_auction` being singular has always said so. What
            #  it did not do is refuse: an overlapping announce overwrote the round AND the
            #  timer, leaving the old timer pending on a round nobody could close, whose `fn`
            #  closes whichever round is open when it lands. Refusing here is the fix; the
            #  one-shot deadline below is what stops a leaked one from becoming permanent.
            self.log.warning("%s is LOW but auction %s is still open — no second round",
                             trigger, self.open_auction["auction_id"])
            return False
        auction_id = uuid.uuid4().hex[:8]
        self.open_auction = {"auction_id": auction_id, "market": market, "bids": {},
                             "quantity_l": quantity_l}
        calls.answer(self.agent, market.uri)   # the round is what the call wanted
        #  THE ROUND AS A FACT, in my own graph: what I announced, as I announced it — the lot,
        #  the reserve and the instant bidding closes. Never the window or the cooldown.
        from datetime import datetime, timedelta, timezone

        rounds.open_round(self.agent, market.uri, auction_id, quantity_l,
                          self.beliefs.reserve_price_per_l,
                          clock.now()
                          + timedelta(seconds=float(self.beliefs.bid_window_s)),
                          arrival=rounds.RECORDED)
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
        #  A DEADLINE, not a cadence: it closes this round and is spent. See Timer.
        if self._timer:
            self._timer.stop()
        self._timer = Timer(self.beliefs.bid_window_s, self.close, repeat=False)
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
        #  DECLARED, as the opening was (#599). A round exists because the host announced it,
        #  and it ends the same way: on the topic every bidder already subscribes to, naming
        #  the round that is over and nothing else about it. Before this, a bidder that lost
        #  was told nothing and ended the round by its own arithmetic against `closesAt` —
        #  which made a fact about the venue something each bidder computed privately, with
        #  its own clock, and put a NOW() in the premise of every buy.
        #
        #  WHAT IT DOES NOT SAY is who won or what anything cleared at. That is the claim's,
        #  sealed to its winner; this is the venue's own fact, public by construction and
        #  already implied by the offer that opened it.
        self.publish(market.offer_topic, {"auction_id": auction_id,
                                          "host": self.me.agent_id,
                                          "closed": True})
        #  AND THE VENUE COOLS — a graph holding during the cooldown (#645), handed to nobody
        #  once it ran out: no deadline of its own lands here any more.

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

        #  Every claim is a commitment to MY Serving STEP: this venue, so many litres, for
        #  this buyer, not after the window closes — planned, not done; the buyer's
        #  presentation is what asks me to take it, and the taking is the act.
        def serving(line, expires):
            return Step(action=SERVING, binding=((VENUE, market.uri),), quantity=line.qty_l,
                       for_agent=node_of(self.agent.beliefs.reader(PUBLIC), line.agent),
                       not_after=(datetime.fromtimestamp(expires, tz=timezone.utc)
                                  if expires is not None else None))

        #  WHEN each bidder wants its water (#625): the instant its bid asked for, as an
        #  epoch second, handed to clearing so the claim's window runs from it.
        wanted = {}
        for a, b in rnd["bids"].items():
            if b.get("wanted_at"):
                try:
                    wanted[a] = datetime.fromisoformat(b["wanted_at"]).timestamp()
                except (TypeError, ValueError):
                    self.log.warning("bid from %s carries an unreadable wanted_at %r — ignored", a, b["wanted_at"])
        result = run_auction(offer, bids, state, auction_id=auction_id,
                             match=matcher.propose_match,
                             redeem_window_s=market.redeem_window_s, act_for=serving,
                             wanted_at=wanted)
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
        #  The LEDGER OF DEBTS and not the regions (#233). A host with no region want of its
        #  own — the city, acting for a mains that states no ranges — used to reach this line,
        #  find no desire module, and record nothing at all while issuing claims all day.
        if (ledger := self.ledger) is not None:
            for claim in result.claims:
                ledger.owe(claim.sub, claim.jti, expires_at=claim.exp, amount_l=claim.amount_l,
                           usable_from=claim.usable_from)

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
        rows = bindings(self.agent.beliefs.query(_KEY_Q % (presenter, "signingKey"), self.agent.beliefs.graphs_of(PUBLIC)))
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
        #  THE WINDOW IS THE ACT'S: `exp` is its `not_after` on the wire, and a claim that
        #  came back over the wire carries only that; the act it embodies is the one I issued.
        if claim.usable_from is not None and clock.now().timestamp() < claim.usable_from:
            self.log.warning("%s presented claim %s before its window opens — refused; the "
                             "claim stands until then", presenter, jti)
            return
        if claim.exp is not None and clock.now().timestamp() > claim.exp:
            del self.held[jti]
            self.log.warning("%s presented claim %s after its window closed — refused, and the "
                             "debt stands unserved", presenter, jti)
            return
        # Asked for: the obligation steps from owed to demanded. What happens next is a
        # DECISION and not a handler any more — the whole of step 9. See below.
        ledger = self.ledger
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
        ledger = self.ledger
        if ledger is None:
            self._serve(jti, why)
            return
        judgment = next((g for g in ledger.obligations() if g.claim == jti), None)
        if judgment is None:
            return
        #  THROUGH EXECUTION: the search sees the honoured row AND this agent's own levers,
        #  so a host owing water it does not hold plans the refill — an Acquire, committed and
        #  handed to bidding, which stands until the upstream round — and the claim stays held
        #  for the sweep that re-runs this when stock arrives. A serve is the plan's head only
        #  when the vessel can honour it, and `take` below is handed exactly that row.
        from orexis_agent_deliberation import reviser

        #  MARKED, not asked (#392): a claim presented is a message, and what the search makes
        #  of it is not this handler's to wait for. The claim stays in `held` until it is
        #  served — which is what happened anyway when nothing was committed — so the moment
        #  the answer changes, the sweep serves it.
        reviser.wake_for(self.agent, judgment)

    @contributes(OFFERING)
    def offer(self, act, judgment, intention: str) -> bool:
        """THE HOST'S MOVE, taken: announce on the venue the row names, for the call the plan
        served. `announce` sizes the lot by the vessel and writes the round; the call is
        answered by the round existing. Satisfied at once — the round is the end, and it is
        there by construction."""
        market = next((m for m in self.markets if m.uri == act.value_of(VENUE)), None)
        if market is None:
            return False
        by = next((c.called_by for c in calls.calls_of(self.agent, market.uri)), "?")
        if not self.announce(market, trigger=by):
            return False
        if (keeper := self._keeper()) is not None:
            keeper.satisfy(OFFERING, judgment.uri, "the round opened")
        return True

    @contributes(SERVING)
    def serve(self, act, judgment, intention: str) -> bool:
        """Carry out a committed serve: pour the claim this obligation names.

        The actor for `market:Serving` on the obligation's row (knowledge/domain/actor.md). A
        plan whose head is the refill hands that row to bidding, not here; this answers only a
        serve, and only for a claim still held — an obligation whose claim was never presented
        is not this module's to invent.
        """
        #  THE MARKET'S OWN JUDGMENT carries the claim (`OwedWant`); a judgment of any other kind
        #  names none, and a serve is not this module's to invent for it.
        jti = getattr(judgment, "claim", None)
        if not jti or jti not in self.held:
            return False
        #  A VESSEL I KNOW IS TOO LOW IS NOT POURED FROM. The search used to keep this claim
        #  held by planning the refill first; since a round is a fact (#358) there may be no
        #  upstream round to plan into, the search finds no path, and the obligation's own row is
        #  what reaches here. The actor is the boundary then: what I know of my stock says the
        #  claim cannot be honoured, so it stays held for the reading that changes that. A
        #  vessel I have never read keeps the old arrangement and is judged by the pour.
        claim = self.held[jti]
        market = next((m for m in self.markets if m.uri == act.value_of(VENUE) or
                       self.stock_property.get(m.uri)), None)
        stock = self._stock_of(market) if market is not None else None
        if stock is not None and stock + EPS < claim.amount_l:
            self.log.info("claim %s waits — my vessel holds %.3f L and it asks %.3f L",
                          jti, stock, claim.amount_l)
            return False
        self._serve(jti, "the plan's head — an obligation's row")
        if (keeper := self._keeper()) is not None:
            keeper.satisfy(SERVING, judgment.uri, "served")
        return True

    def _serve(self, jti: str, why: str) -> None:
        claim = self.held.pop(jti)
        self.log.info("serving claim %s (%.3f L) — %s", jti, claim.amount_l, why)
        self.redeem([claim])
        if (ledger := self.ledger) is not None:
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
                   "permits": claim.permits, "amount_l": claim.amount_l,
                   "debit": claim.debit}
        #  WATER AT A TIME (#625): from when the claim may be presented, and until when.
        if claim.usable_from is not None:
            payload["usable_from"] = datetime.fromtimestamp(claim.usable_from, tz=timezone.utc).isoformat()
        if claim.exp is not None:
            payload["usable_until"] = datetime.fromtimestamp(claim.exp, tz=timezone.utc).isoformat()
        rows = bindings(self.agent.beliefs.query(_KEY_Q % (claim.sub, "sealingKey"), self.agent.beliefs.graphs_of(PUBLIC)))
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
