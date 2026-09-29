"""What the Planner says happened — every event its signals carry, and what of each is reported.

An event is said whole, so a handler asks nobody: the executor adopts from `PlanPublished` and ends
from `WantReached` and `StepBlocked`, and the metrics part tallies what a class marks
(`agent.metrics`). An event nobody but metrics hears — a search ended, a pass, a re-root, what an
imaginarium holds — is made only where its signal is heard, so nothing is read or timed for it
where no metrics sink is loaded.

A want's name is on no metric: a want is minted per instance and a tag of unbounded values breaks
the series store's index, so what a want reports is tagged by the DESIRE it was derived under,
which reads across worlds and agents; the log, and history, name the want.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent.metrics import Flag, Level, Tag, Value


@dataclass(frozen=True)
class PlanPublished:
    """A plan published into the beliefs for `want`, from the imaginarium of `scope`: in how many
    passes its want was searched and what was weighed for it in all, the real seconds since it was
    first searched, the estimate at the present ground against what the plan spent — how honest the
    estimate is — and whether an intention pursued the want before, a replan."""
    metric = "published"
    plan: str
    want: str
    desire: Tag = None
    scope: Tag = None
    passes: Value = None
    weighed: Value = None
    wall_s: Value = None
    estimate: Value = None
    cost: Value = None
    replan: Flag = False


@dataclass(frozen=True)
class WantReached:
    """A want an intention walks that the present meets."""
    want: str


@dataclass(frozen=True)
class StepBlocked:
    """A step an intention stands at, fallen due, that the present no longer admits."""
    step: str


@dataclass(frozen=True)
class WantUnreachable:
    """A want standing, walked by nothing, no search cut short: nothing this agent holds reaches it."""
    metric = "unreachable"
    want: str
    desire: Tag = None


@dataclass(frozen=True)
class SearchEnded:
    """One want's search in one pass, as it ends: its real seconds, the budget it had and the
    candidates it weighed, by the desire, the scope and how it ended."""
    metric = "search"
    want: str
    desire: Tag = None
    scope: Tag = None
    outcome: Tag = None
    duration_s: Value = None
    budget: Value = None
    weighed: Value = None


@dataclass(frozen=True)
class Planned:
    """A pass of the Planner, in real seconds per part — laying the ground and finding the present in
    it, weighing the desires, deriving and withdrawing the wants, searching, publishing — and how many
    wants it searched."""
    metric = "planner"
    wants: Value = None
    ground_s: Value = None
    weigh_s: Value = None
    derive_s: Value = None
    search_s: Value = None
    publish_s: Value = None


@dataclass(frozen=True)
class Rerooted:
    """Which world the present was found to be in `scope` — first, ground, child or surprise — and
    what of the cone was kept and dropped. A surprise is the one a pass names."""
    metric = "reroot"
    scope: Tag
    present: Tag
    kept: Value = None
    dropped: Value = None


@dataclass(frozen=True)
class Imagined:
    """What the imaginarium of `scope` holds at the end of a pass: its possible worlds and the
    weighings of them — of those how many are on a frontier and how many met their want — and its
    plans, by why each search ended. `exhausted` is the one to watch: a budget that keeps cutting
    searches short is a budget too small for the problem, and `no_candidate` is a want nothing this
    agent holds points at."""
    metric = "imaginarium"
    scope: Tag
    worlds: Level = None
    weighings: Level = None
    open: Level = None
    met: Level = None
    satisfied: Level = None
    exhausted: Level = None
    no_candidate: Level = None
