"""What one pass of the search returns for one want: its steps, and why it ended.

Apart from the search because most of the readers need only THIS. `pursuit` asks whether an
outcome was SATISFIED and `deliberator` both constructs a plan and reads its outcome; neither
searches, and reaching the whole of `planner` for a record and a word is rdflib, pyoxigraph,
the heap and nineteen hundred lines of imagining worlds. A record of what was found is not
part of the finding of it.

The outcomes live here rather than beside the trace's verdicts because they are what
`Plan.outcome` holds — the plan's own vocabulary, not the pass's. What the PASS records about
why the world differed is the trace's, and `SURPRISE_WITHHELD` and `SURPRISE_EXOGENOUS` sit
there beside the verdicts.

See knowledge/domain/plan.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import NamedTuple

#  Why a pass ended, and they are not interchangeable. The two failures in particular: NOTHING
#  proposed anything (equip me), against EXHAUSTED, where levers exist and no bounded sequence
#  of them lands inside the region (my doses are too coarse, or my region is too tight for them).
SATISFIED = "satisfied"      # a world where the desire is met
IMPROVED = "improved"        # not met, but nearer than doing nothing
NOTHING = "no candidate"     # no lever this agent holds points at this want
EXHAUSTED = "exhausted"      # levers exist; none reaches the desire within the budget allowed
NOT_BETTER = "not better"    # every world reachable is as bad as this one, or worse
REFUSED = "refused"          # the world it would reach is one the society would not accept
REMEMBERED = "remembered"    # a plan that worked here before, adopted without a search (#469)



class Weighed(NamedTuple):
    """One candidate the search weighed, and what it made of it.

    A NAMED shape rather than a tuple, because it grew: it was four fields, then five where a
    remembered plan's precondition was the finding, then six when a candidate came to be named
    from the world it was weighed IN (#747). Each widening broke every positional unpack that
    had not been widened with it, silently in a reader that used `entry[:4]` and loudly in one
    that did not.
    """

    depth: int
    row: object                 # the filled action — a `Step`, not yet picked
    urgency: float | None       # what the want would read in the world it reached, where it reached one
    verdict: str                # why it was taken or passed over, in `trace`'s words
    missing: object = None      # the fact a remembered plan's precondition wanted (#551)
    world: str = ""             # the world it was weighed IN, which is what names it

@dataclass(frozen=True)
class Plan:
    """What the search found: the steps, why it stopped, and what it would cost to be wrong.

    A plan with no steps is an ANSWER — `outcome` says which of the four silences it is, and the
    difference is the whole reason this returns a record rather than a means or None.
    """

    outcome: str
    steps: tuple = ()                 # of `act.Step`: each with what it was predicted to reach
    urgency_now: float | None = None
    urgency_after: float | None = None
    cost: float | None = None         # what the plan was scored to spend — a remembered plan's measure (#469)
    landing: float | None = None      # seconds from the pass's root to its last landing (#619): its duration
    #  THE INSTANT THE PASS STOOD AT when it found this plan (#625), where that was not now: a
    #  plan is placed at the instant of the root it was found from, never by subtraction from a
    #  deadline. None for a plan found from the present, which is taken now.
    placed_at: datetime | None = None
    #  WHICH CANDIDATE of the root's menu this plan came through: its first step's action for
    #  a plan the search chained, the remembered plan's own node for a route walked as one
    #  candidate (#469) — what the trace's `deliberation:chose` names, so a reader sees the
    #  route was taken as a route and not as the first of its steps.
    origin: str | None = None

    @property
    def first(self) -> str | None:
        """The one move to commit. A plan is re-derived every pass, so only its head is acted
        on: the world moves, and a committed tail is a promise about a future nobody can see."""
        return self.steps[0].action if self.steps else None
