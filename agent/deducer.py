"""The deducer: the kernel's own module in the desire modality — the AIM, and nothing else.

`desire:Deducing`'s body, with the grant gone and, since the-stake-is-sensings-want, with the
REGION gone too. It used to hold every region this agent deduced and answer the choir about
readings — the band, the urgency, the bounds a board should watch, the gaps. Every one of
those is a sentence about an observation, and the module that owns observations answers them
now (`packages/capability/sensing/module.py`). What is left is the one thing about a want
that is the agent's own belief rather than a fact about its equipment: the point it steers
for inside the room it was given, and that a review may move it.
"""

from __future__ import annotations

from .aims import aims_of
from .module import Module


class Deducer(Module):
    """The agent's picks: where, inside each region it holds, it has chosen to steer."""

    name = "desire"

    def __init__(self, agent):
        super().__init__(agent)
        self._aims = aims_of(agent.desires.query_union, agent.id, self.me.uri)
        self.log.info("aims %s", ", ".join(
            f"{p.rsplit('#', 1)[-1]} at {v:g}" for p, v in sorted(self._aims.items()))
            or "nowhere yet")

    def aim(self, observed_property: str) -> float | None:
        """The point I am steering this property toward, or None if I picked none.

        A consumer that requires one (a bidder pricing a deficit) treats None as its own
        refusal; nothing here defaults to the region's centre, because a fabricated preference
        is still a fabricated belief.
        """
        return self._aims.get(observed_property)

    def on_belief_revised(self, belief_term: str, value) -> None:
        """An aim is a belief, so a review may move it — within the region, which is the same
        check boot makes. Re-read rather than patched, because the revision names a term and an
        aim is a structure: simplest correct answer is to ask the graph again."""
        self._aims = aims_of(self.agent.desires.query_union, self.agent.id, self.me.uri)
