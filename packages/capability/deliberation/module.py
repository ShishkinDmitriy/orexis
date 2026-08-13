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

from .terms import REFLEX

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
_RAISES = "http://example.org/agora/market#Raises"
_LOWERS = "http://example.org/agora/market#Lowers"
_DIRECTION_Q = """
SELECT ?direction WHERE {
  ?term market:aboutProperty <%s> ; market:direction ?direction
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
        """Which way the lever I could pull moves this property — the domain's statement.

        Per call rather than cached, like the aim: the T-Box is replaced on restart, not under
        a running agent, but a query this small is not worth a second copy of the truth.
        """
        rows = bindings(self.agent.store.query(_DIRECTION_Q % observed_property))
        return rows[0]["direction"] if rows else None
