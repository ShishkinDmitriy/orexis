"""A step: a planned instance of an action. An act: the record that a step was taken.

An `orexis:Action` is a template (a precondition, an effect, a taker). A STEP is one filling of
it, planned and not yet done — the lever it goes through, the want it serves and what that want
is about, how much, for whom where it is an obligation's, its window, what the search predicted
taking it would reach, what it waits for, what follows. A plan is steps; an intention commits to
steps; a claim promises one. Nothing has happened yet. An ACT is the record that something did:
which step, when, whether anyone took it, and in time the verdict — history, and only history
(the sovereign's ruling, 2026-09-02: a plan is not executed, so its elements are not acts).
One step may be attempted more than once; each attempt is an act. See knowledge/domain/step.md,
knowledge/domain/act.md and knowledge/decisions/an-act-is-a-filled-action-and-a-step-is-its-place-in-a-plan.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Step:
    """One action, filled in and planned. Every step is an instance and no code names one."""

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
    urgency_after: float | None = None  # the want's urgency in the world this step was predicted to reach
    predicts: tuple | None = None     # (adds, retracts): the canonical facts the search said this
                                      # step makes true and false — what the world is held to (#510)
    relies_on: str | None = None      # which outcome it was planned through, where the action
                                      # states several (`orexis:reliesOn`, #522)

    @classmethod
    def from_row(cls, row, quantity: float | None = None, not_after: datetime | None = None):
        """An affordance row, filled: sized, and windowed where the caller knows when. Handed
        a step already, it fills that one again — a search re-sizes a step it takes from a
        different world."""
        return cls(action=row.action, via=row.via, want=row.want, about=row.about,
                   quantity=quantity, direction=row.direction, for_agent=row.for_agent,
                   not_after=not_after)


@dataclass(frozen=True)
class Act:
    """The record that a step was taken: which step, when, and whether anyone took it. Written
    by execution into the ledger the moment the actors have been asked; the verdict on what
    the world made of it lands beside it when the world answers."""

    step: str                         # the ledger's step node, by IRI
    taken_at: datetime
    took: bool                        # some actor took it, or none could now — standing


def predicts_json(predicts) -> str:
    """The step's predicted diff as one literal for the ledger: two lists of canonical facts,
    exactly as `signature.facts` states them, so a step read back from the ledger can be
    checked against the world without an imaginarium."""
    import json
    adds, retracts = predicts
    return json.dumps({"adds": sorted(map(list, adds), key=repr),
                       "retracts": sorted(map(list, retracts), key=repr)})


def predicts_from_json(text: str) -> tuple:
    import json

    def tup(x):
        return tuple(tup(y) for y in x) if isinstance(x, list) else x
    d = json.loads(text)
    return (frozenset(tup(f) for f in d["adds"]), frozenset(tup(f) for f in d["retracts"]))
