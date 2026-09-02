"""An act: an action filled in, and the record of that instance through its life.

An `orexis:Action` is a template (a precondition, an effect, a taker). What gets committed,
taken and promised is a FILLED one — the lever it goes through, the want it serves and what
that want is about, how much, for whom where it is an obligation's, WHEN — and, since the fold
of the step into it (the sovereign's ruling, 2026-09-02), what the search predicted taking it
would reach. One node, three moments: planned, taken, answered. Its place in a plan is a LINK,
not a thing — `orexis:step` from the intention to each act, `orexis:then` from an act to the
one that follows — because every act is minted for the place it fills, so a step node was a
distinction without a difference. Two nouns, action and act, and both are needed: one template,
many fillings. See knowledge/domain/act.md and
knowledge/decisions/an-act-is-a-filled-action-and-a-step-is-its-place-in-a-plan.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Act:
    """One action, filled in. Every act is an instance and no code names one."""

    action: str                       # which template — `market:Acquiring`, `actuation:Dosing`
    via: str                          # the lever it goes through — this venue, this valve
    want: str | None = None           # the desire it serves, by node
    about: str | None = None          # what that want is about (`orexis:about`), opaque here
    quantity: float | None = None     # how much, sized by the taker — nothing, for a look
    direction: str | None = None      # which way it moves what it is about, where it moves
    for_agent: str | None = None      # whom it serves, where it is an obligation's
    #  The window: when taking it counts. Not-after is what every hand-kept timer was saying
    #  (a bid not after the round closes, a serve not after the claim's expiry); not-before is
    #  the half nothing writes yet — where a held claim spent later would arrive.
    not_before: datetime | None = None
    not_after: datetime | None = None
    urgency_after: float | None = None  # the want's urgency in the world this act was predicted to reach

    @classmethod
    def from_row(cls, row, quantity: float | None = None, not_after: datetime | None = None):
        """An affordance row, filled: sized, and windowed where the caller knows when. Handed
        an act already, it fills that one again — a search re-sizes an act it takes from a
        different world."""
        return cls(action=row.action, via=row.via, want=row.want, about=row.about,
                   quantity=quantity, direction=row.direction, for_agent=row.for_agent,
                   not_after=not_after)
