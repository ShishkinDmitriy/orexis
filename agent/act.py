"""An act: an action filled in — and a step: an act at its place in a plan.

An `ag:Action` is a template (a precondition, an effect, a taker). What gets committed, taken
and promised is a FILLED one — the lever it goes through, the want it serves and what that
want is about, how much, for whom where it is a duty's, and WHEN — and until this file it had
no name: an affordance row carried some of it, an intention some, a commitment some, and the
timing lived in actors' timers. An act is execution's word for that thing; a step is
planning's word for an act at a position in a plan with what the search predicted. The two
words keep the two scopes apart: a step is a hypothesis that must not outlive its pass, an act
is what survives it. See knowledge/domain/act.md, knowledge/domain/step.md and
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
    about: str | None = None          # what that want is about (`ag:about`), opaque here
    quantity: float | None = None     # how much, sized by the taker — nothing, for a look
    direction: str | None = None      # which way it moves what it is about, where it moves
    for_agent: str | None = None      # whom it serves, where it is a duty's
    #  The window: when taking it counts. Not-after is what every hand-kept timer was saying
    #  (a bid not after the round closes, a serve not after the claim's expiry); not-before is
    #  the half nothing writes yet — where a held claim spent later would arrive.
    not_before: datetime | None = None
    not_after: datetime | None = None

    @classmethod
    def from_row(cls, row, quantity: float | None = None, not_after: datetime | None = None):
        """An affordance row, filled: sized, and windowed where the caller knows when. Handed
        a step or an act already, it fills that one again — a search re-sizes a step it takes
        from a different world."""
        row = getattr(row, "act", row)
        return cls(action=row.action, via=row.via, want=row.want, about=row.about,
                   quantity=quantity, direction=row.direction, for_agent=row.for_agent,
                   not_after=not_after)


@dataclass(frozen=True)
class Step:
    """An act at its place in a plan, with what the search predicted taking it would reach."""

    act: Act
    urgency_after: float | None = None   # the want's urgency in the world this step reaches

    #  The act's identity, read through: a plan reads as a sequence of acts.
    @property
    def action(self) -> str:
        return self.act.action

    @property
    def via(self) -> str:
        return self.act.via

    @property
    def want(self) -> str | None:
        return self.act.want

    @property
    def about(self) -> str | None:
        return self.act.about
