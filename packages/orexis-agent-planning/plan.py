"""What one pass of the search returns for one want: its steps, and why it ended.

Apart from the search because a reader of a plan needs only THIS. Reaching the whole of
`planner` for a record and a word is rdflib, pyoxigraph, a heap and the imagining of worlds;
a record of what was found is not part of the finding of it.

See knowledge/domain/plan.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

#  Why a pass ended, and they are not interchangeable. The two failures in particular: NOTHING
#  proposed anything (equip me), against EXHAUSTED, where levers exist and no bounded sequence
#  of them lands inside the region (my doses are too coarse, or my region is too tight).
SATISFIED = "satisfied"      # a world where the want is met
NOTHING = "no candidate"     # no lever this agent holds points at this want
EXHAUSTED = "exhausted"      # levers exist; none reaches the want within the budget allowed
#  THREE, AND THE PREDECESSOR HAD SEVEN. `improved` and `not better` were a GRADED answer —
#  nearer than doing nothing — which nothing measures since a want is judged by its met-test
#  and nothing scores a world by degree; `refused` was the legality check the judge made, and
#  the judge is the gates'; `remembered` was a plan adopted without a search. Each comes back
#  with the thing that could return it (an-agent-is-four-things).



@dataclass(frozen=True)
class Plan:
    """What the search found: the steps, why it stopped, and what it would cost to be wrong.

    A plan with no steps is an ANSWER — `outcome` says which of the four silences it is, and the
    difference is the whole reason this returns a record rather than a means or None.
    """

    outcome: str
    steps: tuple = ()                 # of `act.Step`, in order
    #  WHAT IT WAS SCORED TO SPEND, summed from each step's own `orexis:costs`. The unit is
    #  the domain's and the kernel interprets no literal.
    cost: float | None = None
    #  NO DEGREE OF UNMET-NESS, and there were two fields of it. A want is judged by its
    #  met-test and nothing scores a world by degree, so "how unmet before" and "how unmet
    #  after" could only ever read 1 and 0 — which is `outcome` said twice
    #  (a-want-is-judged-by-its-met-test-and-nothing-else).
    landing: float | None = None      # seconds from the pass's root to its last landing (#619): its duration
    #  THE INSTANT THE PASS STOOD AT when it found this plan (#625), where that was not now: a
    #  plan is placed at the instant of the root it was found from, never by subtraction from a
    #  deadline. None for a plan found from the present, which is taken now.
    placed_at: datetime | None = None
    #  WHICH CANDIDATE of the root's menu this plan came through: its first step's action for
    #  a plan the search chained, the remembered plan's own node for a route walked as one
    #  candidate (#469) — what the trace's `planning:chose` names, so a reader sees the
    #  route was taken as a route and not as the first of its steps.
    origin: str | None = None

    @property
    def first(self) -> str | None:
        """The one move to commit. A plan is re-derived every pass, so only its head is acted
        on: the world moves, and a committed tail is a promise about a future nobody can see."""
        return self.steps[0].action if self.steps else None
