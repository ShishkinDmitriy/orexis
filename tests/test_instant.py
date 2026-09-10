"""A node is a world AND an instant (#587).

Where a plan stands used to be its facts alone, which says that two nodes holding the same
facts are the same node however far apart they stand. That is true of a world nothing moves
but the agent — a puzzle, a grid — and false of every world that keeps going on its own. So
the instant joins the facts, and cycle detection stops collapsing two instants into one world.
See knowledge/decisions/planning-branches-on-action-forecasting-on-belief.md, item 1.

The instant is the path's own: each step's `orexis:landsAfter`, summed, which the search
already carried for holding a candidate to a Within want's room. Every node of a pass counts
from one root, so seconds-after-the-root ARE the instant and nothing reads a wall clock.
"""

from __future__ import annotations

import pytest

from orexis_agent_deliberation import signature
from orexis_agent_deliberation.planner import Planner
from test_hanoi import _goal, _mover

ACTIONS = "http://example.org/orexis/graph/actions"
MOVE = "http://example.org/orexis/hanoi#Move"
LANDS = "http://example.org/orexis#landsAfter"


def _lands_after(agent, seconds: int) -> None:
    """Declare what a move costs in TIME — a hanoi move lands at once, and a world whose
    steps all land at once is the timeless world the search assumed before this."""
    agent.beliefs.update(f"""INSERT DATA {{ GRAPH <{ACTIONS}> {{
        <{MOVE}> <{LANDS}> "SELECT ({seconds} AS ?seconds) WHERE {{ }}" }} }}""")


def _instants_of(planner) -> dict:
    """Every world the pass settled, by its facts, with the instants it was reached at."""
    out: dict = {}
    for node in planner._nodes:
        out.setdefault(node.diff, set()).add(round(node.landing, 6))
    return out


def test_a_world_is_where_it_stands_and_when_it_stands_there():
    """The key itself: the same facts at two instants are two keys, and one instant is one."""
    world = (frozenset({("a", "b", "c")}), frozenset())
    assert signature.where(world, 0.0) != signature.where(world, 60.0), \
        "the same facts a minute later are somewhere else"
    assert signature.where(world, 60.0) == signature.where(world, 60.0000000001), \
        "and a float's last places are not a difference the search may fork on"
    assert signature.where(world, 0.0) != signature.where(signature.EMPTY, 0.0), \
        "the facts still decide, at one instant"


def test_a_hanoi_move_lands_at_once_so_its_puzzle_is_timeless(monkeypatch):
    """The world that declares no landing is the world the search always had: every node of
    the pass stands at the root's own instant, so the key is its facts and nothing else."""
    agent = _mover(monkeypatch, ["disk_1", "disk_2"])
    planner = Planner(agent, agent.me)
    planner.budget = Planner.BUDGET
    plan = planner.plan(_goal(agent))

    assert plan.outcome == "satisfied" and len(plan.steps) == 3, plan.outcome
    assert {i for instants in _instants_of(planner).values() for i in instants} == {0.0}, \
        "a move declares no landing, so nothing in this puzzle is later than anything else"


def test_the_world_a_path_returns_to_later_is_not_the_world_it_left(monkeypatch):
    """The change, in the case that shows it. Give a move a minute and the puzzle acquires a
    clock: moving a disk out and back reaches the pose it started from, which cycle detection
    discarded as somewhere already seen — and still would, if a world were its facts alone.
    It is two minutes later now, so it is another world, and the pass keeps it."""
    agent = _mover(monkeypatch, ["disk_1", "disk_2"])
    _lands_after(agent, 60)
    planner = Planner(agent, agent.me)
    planner.budget = Planner.BUDGET
    planner.plan(_goal(agent))

    returned = [instants for instants in _instants_of(planner).values() if len(instants) > 1]
    assert returned, "no world was reached at two instants: the pass never doubled back"
    #  THE ROOT'S OWN POSE, LEFT AND RETURNED TO: the empty diff at a later instant is a node
    #  of its own, where before it was the root a second time and pruned.
    root_again = _instants_of(planner).get(signature.EMPTY, set())
    assert root_again - {0.0}, \
        f"the pose the puzzle started in was reached again and folded into the root: {root_again}"


def test_the_puzzle_is_still_solved_when_its_moves_take_time(monkeypatch):
    """And the widening is not a loss of the answer: the same three moves, from a cone that
    now holds the worlds a doubling-back reaches. What it costs is forks, measured in
    knowledge/runbooks/measure-the-search.md."""
    agent = _mover(monkeypatch, ["disk_1", "disk_2"])
    _lands_after(agent, 60)
    planner = Planner(agent, agent.me)
    planner.budget = 128
    plan = planner.plan(_goal(agent))

    assert plan.outcome == "satisfied", plan.outcome
    assert len(plan.steps) == 3, [s.action.rsplit("#", 1)[-1] for s in plan.steps]
    won = min((m for m in planner._nodes if m.met), key=lambda m: m.cost)
    assert won.landing == pytest.approx(180.0), \
        "three moves of a minute each stand three minutes out from the present"


def test_a_look_that_takes_a_minute_is_still_nowhere_new(monkeypatch):
    """The instant separates two worlds; it does not separate a world from itself.

    A look predicts the value it found, so its diff is its parent's and the search discards it
    as somewhere already reached — the constraint that keeps a plan from chaining past a
    sensing act, held by no guard but that one. Give the look a minute and the clock is the
    only thing between the two worlds, which is a difference only a world that changes on its
    own could make. Nothing declares one yet (#592), so the look is still nowhere new.

    Found by the market host rather than reasoned out: with the instant alone deciding, a host
    owing water it does not hold served from a barrel too low instead of planning the refill,
    because a serve whose premise cannot bind predicts nothing and had stopped colliding.
    """
    from orexis_agent_deliberation import trace
    from test_planning import OBSERVING, _thirsty_with_a_nearly_empty_butt

    agent, planner, desire = _thirsty_with_a_nearly_empty_butt(monkeypatch)
    agent.beliefs.update(f"""DELETE {{ GRAPH <{ACTIONS}> {{ <{OBSERVING}> <{LANDS}> ?text }} }}
        INSERT {{ GRAPH <{ACTIONS}> {{ <{OBSERVING}> <{LANDS}> "SELECT (60 AS ?seconds) WHERE {{ }}" }} }}
        WHERE {{ GRAPH <{ACTIONS}> {{ <{OBSERVING}> <{LANDS}> ?text }} }}""")

    planner.plan(desire)

    looks = [verdict for _, row, _, verdict in planner._weighed if row.action == OBSERVING]
    assert looks, "the gardener polls a probe, so looking is on its menu"
    assert set(looks) == {trace.SEEN}, \
        f"a look that changed nothing was somewhere new because it took time: {looks}"
