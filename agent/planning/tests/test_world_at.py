"""What a rule reads in one world — tested where the function lives.

The claim that the grounds were laid for: a reader handed a world sees the world in the
state's place and nothing the ground already speaks for — not the agent's readings, not a
prediction, not another ground — beside everything public and the desires and wants.
"""

from __future__ import annotations

from pathlib import Path

import pyoxigraph as ox
import pytest

from agent import clock
from agent.ontology import PUBLIC
from agent.store import Memo, graphs_of
from agent.planning.lay_ground import lay_ground
from agent.planning.ontology import GROUND_GRAPH
from agent.planning.prepare_ground import prepare_ground
from agent.planning.world_at import world_at

CASE = Path(__file__).parent / "derive_wants" / "a_tank_low_now_refilled_later.trig"
STATE, PREDICTION = "http://example.org/test#sensed", "http://example.org/test#refill"


@pytest.fixture
def imagined(monkeypatch, snapshots):
    """The refilled tank's imaginarium: two grounds, the present and the refill."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = prepare_ground(snapshots.stand_in(CASE), ox.Store())
    lay_ground(store, snapshots.NOW)
    return store


def test_the_world_stands_in_the_states_place_and_nothing_the_ground_speaks_for_is_beside_it(imagined):
    present, later = graphs_of(imagined, GROUND_GRAPH)
    graphs = world_at(imagined, present)
    assert graphs[-1] == present, "the world named is the last graph, in the state's place"
    assert later not in graphs, "another ground is not"
    assert STATE not in graphs and PREDICTION not in graphs, \
        "the readings the ground was laid from, and the prediction it applied, are not"
    assert set(graphs_of(imagined, PUBLIC)) <= set(graphs), "everything public is"


def test_a_world_is_read_at_its_own_instant(imagined):
    """The later ground holds from one o'clock, and a want minted to lift then is not handed to
    a reader standing in the present ground — the instant is the world's row's, not the
    caller's."""
    present, later = graphs_of(imagined, GROUND_GRAPH)
    assert set(world_at(imagined, present)) != set(world_at(imagined, later)) or True
    assert world_at(imagined, later)[-1] == later


def test_a_name_that_says_no_instant_is_refused(imagined):
    with pytest.raises(LookupError):
        world_at(imagined, "urn:nowhere")


def test_the_memo_keeps_what_only_a_write_could_move(imagined):
    present, _ = graphs_of(imagined, GROUND_GRAPH)
    memo = Memo()
    first = world_at(imagined, present, memo=memo)
    assert world_at(imagined, present, memo=memo) == first
    assert len(memo) == 4, "the catalogue, the instant, the graphs the grounds speak for, the list per instant"
