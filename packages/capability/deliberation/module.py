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

from agent.module import Module

from .terms import REFLEX

# What this package asks OF others, by family — their namespaces, never their Python.
_DESIRE = "http://example.org/agora/desire#DesireCapability"

# The moves. The intention package's individuals, referenced by IRI: a move IS what the keeper
# records when the actor carries it out, so naming anything else would put a translation table
# between deciding and remembering.
_INTENTION_NS = "http://example.org/agora/intention#"
OBSERVE = _INTENTION_NS + "Observe"
ACQUIRE = _INTENTION_NS + "Acquire"


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

        None twice over is deliberate: no aim means nothing to pursue toward (an agent that
        picked no point has decided not to steer this property), and at-or-above the aim means
        no need. Both are the reflex saying *do nothing*, which an actor must treat exactly as
        it treats its own cooldowns — a decision, not an absence of one.
        """
        if value is None:
            return OBSERVE
        desire = self.agent.provider(_DESIRE)
        if desire is None:
            return None
        aim = desire.aim(observed_property)
        if aim is None or value >= aim:
            return None
        return ACQUIRE
