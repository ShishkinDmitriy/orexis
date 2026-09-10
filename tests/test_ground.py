"""A possible world is what it holds AND what it is predicted on (#587).

Where a plan stands used to be its facts alone, and for as long as the agent's own present is
the only thing any imagined world is grounded on, that is exactly right. It stops being right
when the world predicts: a bed vented onto a warm afternoon and the same bed vented onto a cold
night are two worlds, because what happens next differs — and neither the facts nor a clock
separates them. The PREDICTION does. See
knowledge/decisions/planning-branches-on-action-forecasting-on-belief.md, item 1.

So a node carries its GROUND: which of the world's own branches it sits under, the happening
edges taken to reach it, where a step is a chosen one. Empty is the present, observed, and it is
every node's ground until something predicts (#589) — which is why every claim below about a
shipped world is that nothing changed.
"""

from __future__ import annotations

import pytest

from orexis_agent_deliberation import signature
from orexis_agent_deliberation.planner import Planner
from test_hanoi import _goal, _mover

ACTIONS = "http://example.org/orexis/graph/actions"
MOVE = "http://example.org/orexis/hanoi#Move"
LANDS = "http://example.org/orexis#landsAfter"
PRESENT = ()
RAINED = ("http://example.org/orexis/world#it_rained",)


def _lands_after(agent, seconds: int) -> None:
    """Declare what a move costs in TIME. A hanoi move lands at once, and nothing in that
    puzzle moves while a clock runs — which is the whole of why this must change nothing."""
    agent.beliefs.update(f"""INSERT DATA {{ GRAPH <{ACTIONS}> {{
        <{MOVE}> <{LANDS}> "SELECT ({seconds} AS ?seconds) WHERE {{ }}" }} }}""")


def _solve(agent, budget=None, forks=None):
    planner = Planner(agent, agent.me)
    planner.budget = budget or Planner.BUDGET
    return planner, planner.plan(_goal(agent))


def _counting(monkeypatch):
    from orexis_agent_deliberation import imaginarium
    forks = []
    reached = imaginarium.Imaginarium.reached
    monkeypatch.setattr(imaginarium.Imaginarium, "reached",
                        lambda self, *a, **k: (forks.append(1), reached(self, *a, **k))[1])
    return forks


def test_a_world_is_what_it_holds_and_what_it_stands_on():
    """The key itself: the same facts on two predictions are two worlds, and on one they are
    one. Nothing else is in it — an instant is not, because a later world differs only where
    something says the world moved, and saying that is the ground's job."""
    world = (frozenset({("a", "b", "c")}), frozenset())
    assert signature.where(world, PRESENT) != signature.where(world, RAINED), \
        "the same bed under two forecasts is two worlds"
    assert signature.where(world, RAINED) == signature.where(world, RAINED), \
        "and under one forecast it is one"
    assert signature.where(world, PRESENT) != signature.where(signature.EMPTY, PRESENT), \
        "the facts still decide, on one ground"


def test_every_world_of_a_pass_stands_on_the_present(monkeypatch):
    """One ground, until something predicts. A step is a CHOSEN edge, so taking a lever never
    changes which of the world's own branches the agent is in; only a happening edge does, and
    nothing draws one yet. So every world this pass imagines stands where the agent does."""
    agent = _mover(monkeypatch, ["disk_1", "disk_2"])
    planner, plan = _solve(agent)

    assert plan.outcome == "satisfied", plan.outcome
    assert {m.ground for m in planner._nodes} == {PRESENT}, \
        "a world was predicted on something, and nothing predicts yet"
    assert {g for _, g in planner._seen} == {PRESENT}


def test_a_move_that_takes_a_minute_makes_no_second_world(monkeypatch):
    """The measurement, pinned. Give a hanoi move a minute and nothing about the puzzle
    changes: the same forks, the same three moves, and the pose the puzzle started in is still
    the pose it started in when a path doubles back to it.

    This is what keying on the INSTANT got wrong for a day. Two disks went from 14 forks to 17
    and three from 50 to a whole 128-world budget, no longer solved at that world's own 64 —
    distinctions with no content, since a hanoi world holds still while the clock runs. A clock
    alone separates nothing; a prediction does.
    """
    plain = _counting(monkeypatch)
    agent = _mover(monkeypatch, ["disk_1", "disk_2"])
    _, without = _solve(agent)
    forked_plain = len(plain)

    timed = _counting(monkeypatch)
    agent = _mover(monkeypatch, ["disk_1", "disk_2"])
    _lands_after(agent, 60)
    planner, with_a_clock = _solve(agent)

    assert [s.action for s in with_a_clock.steps] == [s.action for s in without.steps], \
        "the plan changed because its moves take time"
    assert len(timed) == forked_plain, \
        f"a clock split a world: {len(timed)} forks against {forked_plain}"
    returned = [m for m in planner._nodes if m.diff == signature.EMPTY and m is not planner._root]
    assert returned, "no path doubled back, so this pins nothing"
    assert len([k for k in planner._seen if k[0] == signature.EMPTY]) == 1, \
        "the pose the puzzle started in became a second world because two minutes had passed"


def test_the_puzzle_is_still_solved_when_its_moves_take_time(monkeypatch):
    """And the answer is the answer, three minutes out rather than at once — a landing still
    says WHEN a plan's last change completes, which is what a Within want's room reads."""
    agent = _mover(monkeypatch, ["disk_1", "disk_2"])
    _lands_after(agent, 60)
    planner, plan = _solve(agent, budget=128)

    assert plan.outcome == "satisfied", plan.outcome
    assert len(plan.steps) == 3, [s.action.rsplit("#", 1)[-1] for s in plan.steps]
    won = min((m for m in planner._nodes if m.met), key=lambda m: m.cost)
    assert won.landing == pytest.approx(180.0), \
        "three moves of a minute each complete three minutes out"
