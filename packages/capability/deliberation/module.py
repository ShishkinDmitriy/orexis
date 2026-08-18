"""deliberation:Reflex — the welded chain, extracted unchanged into the seam a model will use.

**This module is the old bidder's whether, and nothing else.** Pursue what sits below the aim;
look when you cannot see; otherwise, nothing. It decides no quantity, no price, no cadence and
no announcement — the HOW stays with the actors, and the bid number in particular stays
deterministic wherever the whether comes from (knowledge/decisions/deterministic-bid.md).

Why extracting a three-line reflex was worth a package: the caller now asks
`agent.provider(DELIBERATION)` and cannot tell WHO answered. `deliberation:Consulting` — one
model call over the beliefs, the T-Box, the gap and the standing intentions, emitting a move
from the vocabulary's menu — drops into this seam without touching a line of any actor, which
is the property the whole roadmap was run to buy. The proof the seam is load-bearing is in the
tests: silence the deliberator and a thirsty bidder with a fresh reading in hand submits
nothing, because the whether genuinely is not the bidder's any more.

Vocabulary: packages/capability/deliberation/ontology.ttl. Derivation: its rules.ru. No beliefs
and no shapes, and both omissions are statements: a reflex holds no opinion a shape could check —
the aim it steers by is desire's, already shaped — and a member with parameters to hold would
bring its own block. See knowledge/decisions/an-intention-is-an-amortised-deliberation.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agent.module import Module
from agent.store import bindings

from .terms import PLANNING, REFLEX

# The affordance menu, shipped as SPARQL — see the file's own header. Read at import, so a
# malformed query fails when the package loads rather than when a model first asks.
MENU_QUERY = (Path(__file__).parent / "menu.rq").read_text()

# What this package asks OF others, by family — their namespaces, never their Python.
_DESIRE = "http://example.org/agora/desire#DesireCapability"

# The moves. The intention package's individuals, referenced by IRI: a move IS what the keeper
# records when the actor carries it out, so naming anything else would put a translation table
# between deciding and remembering.
_INTENTION_NS = "http://example.org/agora/intention#"
OBSERVE = _INTENTION_NS + "Observe"
ACQUIRE = _INTENTION_NS + "Acquire"

# Which way the lot moves what it is priced in — the market vocabulary's terms, read off the
# T-Box rather than known. Issue #127: the sign used to be hardcoded here as `value < aim`,
# which was the one piece of "buy water to raise moisture" written nowhere in any graph.
#
# Joined THROUGH A VENUE I BID IN (#198), never over the T-Box at large: the direction is a
# fact about a lever, and the lever I hold is a market. Asked bare, "which way does moisture
# move" has no answer the moment a fan market lowers what a water market raises — whichever
# term the store returned first would steer the reflex, silently. Asked through my venue, the
# answer is which way MY lever moves it, which is the only question a reflex ever had.
_RAISES = "http://example.org/agora/market#Raises"
_LOWERS = "http://example.org/agora/market#Lowers"
_DIRECTION_Q = """
SELECT ?direction WHERE {
  <%s> market:bidsIn ?m .
  ?m market:marketFor ?src .
  ?src market:supplies ?good .
  ?term market:ofGood ?good ; market:aboutProperty <%s> ; market:direction ?direction
} LIMIT 1"""


@dataclass(frozen=True)
class Affordance:
    """One row of the menu: a means, the property it is about, the lever, and — for a means
    that moves anything — which way it moves it."""

    means: str
    observed_property: str
    via: str
    direction: str | None = None


def menu_of(query, agent_uri: str) -> list[Affordance]:
    """What one agent could do, about what, through which lever — derived, never written.

    The Consulting member's prompt substrate and the reflex's worldview as data: a move with no
    row here is a move nothing should propose. Free function for the same reason `gaps_of` is —
    a test about what a world implies should not have to build an agent to ask.
    """
    return [Affordance(means=r["means"], observed_property=r["property"], via=r["via"],
                       direction=r.get("direction"))
            for r in bindings(query(MENU_QUERY.replace("$me", f"<{agent_uri}>")))]


class ReflexModule(Module):
    """The decider. Speaks to no topic; its callers are its siblings, through the agent."""

    CAPABILITY = REFLEX
    name = "deliberation"

    def propose(self, observed_property: str, value: float | None) -> str | None:
        """Given where this property stands, the next move — or None, which is a decision.

        `value` is the freshest reading the caller trusts, and None means it holds none it
        does: the reflex answer to not seeing is to look, which is the boot-order fact the
        decision record is built on — at birth there is a desired state, no observations, and
        the first intention is always Observe.

        With a reading in hand, the whole reflex is the gap's sign against the AIM — the pick,
        not the region's edge, because pursuing only past the band edge would leave the agent
        permanently short of where it decided to sit. Asked of desire at every call rather
        than cached: the aim is a belief, and a review may move it under a running agent.

        WHICH sign means pursue is read off the T-Box, not known (#127): the domain states that
        applying the lot raises or lowers the property its bids are priced in, and the reflex
        steers by that — below the aim with a lever that Raises, or above it with one that
        Lowers, is the move. `value < aim` used to be hardcoded here, which was the one piece
        of "buy water to raise moisture" written nowhere in any graph; a heater against a cold
        snap is now the same rule with no code change, which is what stating it bought.

        None three times over, and each is a decision: no aim means nothing to pursue toward
        (an agent that picked no point has decided not to steer this property); a gap on the
        side no lever moves means no move helps; and no stated direction means the reflex
        cannot know which way — refusing is honest where guessing would be the hardcoded sign
        sneaking back in as a default.
        """
        if value is None:
            return OBSERVE
        desire = self.agent.provider(_DESIRE)
        if desire is None:
            return None
        aim = desire.aim(observed_property)
        if aim is None:
            return None
        direction = self._direction_of(observed_property)
        if direction == _RAISES and value < aim:
            return ACQUIRE
        if direction == _LOWERS and value > aim:
            return ACQUIRE
        return None

    def _direction_of(self, observed_property: str) -> str | None:
        """Which way the lever I could pull moves this property — through a venue I bid in.

        Per call rather than cached, like the aim: the T-Box is replaced on restart, not under
        a running agent, but a query this small is not worth a second copy of the truth.
        An agent bidding in no market gets None here and proposes nothing, which was already
        true — a direction with no venue behind it was the menu offering a move with no lever.
        """
        rows = bindings(self.agent.store.query(
            _DIRECTION_Q % (self.me.uri, observed_property)))
        return rows[0]["direction"] if rows else None


# The dealer's shop, asked from inside: the lot my downstream venue owes, IF the property in
# hand is my own vessel's stock. Both joins are the Planning grant's premises re-asked —
# I act for a vessel I offer, the property is one its stated ranges name — plus my own
# offerQuantityL belief, read from my private graph exactly as the bidder reads its
# conversion: a lot is a HOSTING belief, and this package may name the term's IRI but never
# import the market's Python.
_SHOP_Q = """
SELECT ?q WHERE {
  <%s> ag:actsFor ?vessel .
  ?vessel market:offeredBy <%s> .
  ?vessel <http://www.w3.org/ns/ssn/systems/hasOperatingRange> ?range .
  ?range <http://www.w3.org/ns/ssn/systems/inCondition> ?cond .
  ?cond <http://www.w3.org/ns/ssn/forProperty> <%s> .
  GRAPH <%s> { <%s> <http://example.org/agora/market#offerQuantityL> ?q }
} LIMIT 1"""

# The two steps of the dealer's plan, as menu-row-shaped rows: my Acquire on the upstream
# venue (the same walk the menu's Acquire branch closes), then Offer on the venue I host for
# my vessel. Recomputed from given-level facts, never read from bidsIn/hosts conclusions.
_PLAN_Q = """
SELECT ?upSrcId ?downSrcId WHERE {
  <%s> ag:actsFor ?vessel .
  ?vessel market:offeredBy <%s> ; ag:localId ?downSrcId .
  ?pipe <http://example.org/agora/actuation#drawsFrom> ?upstream ;
        <http://example.org/agora/actuation#actuates> ?vessel .
  ?upstream market:offeredBy ?owner ; ag:localId ?upSrcId .
  FILTER(<%s> != ?owner)
} LIMIT 1"""

OFFER = _INTENTION_NS + "Offer"


class PlanningModule(ReflexModule):
    """The dealer's member: the reflex plus one deduced goal, and the plan said out loud.

    Depth 2 and no deeper, by construction: the search space is the two venues the grant's
    premise names, not open-ended STRIPS. What it adds to the reflex is exactly one goal past
    the region — MY HOSTED LOT MUST BE SERVEABLE. Every downstream buyer's Acquire silently
    preconditions stock >= lot ("refilling makes lotCapacity > 0 true" is the planning
    record's own sentence), and the reflex would only pursue the vessel's aim; a dealer whose
    aim sat below its lot would honestly keep a vessel too empty to trade from. The plan
    itself — acquire upstream, then offer downstream — is exposed as data (`plan_for`) for
    the same reason the menu is: the Consulting member's prompt substrate, and the
    sovereign's inspection, without a line of prose maintained anywhere.
    """

    CAPABILITY = PLANNING
    name = "planning"

    def propose(self, observed_property: str, value: float | None) -> str | None:
        move = super().propose(observed_property, value)
        if move is not None:
            return move
        if value is None:
            return None
        needed = self._my_shop_needs(observed_property)
        if needed is not None and value < needed                 and self._direction_of(observed_property) == _RAISES:
            return ACQUIRE
        return None

    def _my_shop_needs(self, observed_property: str) -> float | None:
        """The lot my downstream venue owes — None when this property is not my shop's stock."""
        rows = bindings(self.agent.store.query(_SHOP_Q % (
            self.me.uri, self.me.uri, observed_property,
            self.agent.beliefs.graph, self.me.uri)))
        return float(rows[0]["q"]) if rows else None

    def plan_for(self, observed_property: str) -> list[Affordance]:
        """The dealer's two-step, as rows: acquire upstream, then offer downstream.

        Empty when the property is not the vessel's stock — a planner asked about somebody
        else's gap has no chain to offer, and says so rather than inventing one.
        """
        if self._my_shop_needs(observed_property) is None:
            return []
        rows = bindings(self.agent.store.query(
            _PLAN_Q % (self.me.uri, self.me.uri, self.me.uri)))
        if not rows:
            return []
        up, down = rows[0]["upSrcId"], rows[0]["downSrcId"]
        mint = "http://example.org/agora#market."
        return [
            Affordance(means=ACQUIRE, observed_property=observed_property,
                       via=mint + up, direction=_RAISES),
            Affordance(means=OFFER, observed_property=observed_property,
                       via=mint + down, direction=_LOWERS),
        ]
