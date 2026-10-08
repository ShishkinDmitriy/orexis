"""A stance (knowledge/domain/kernel/stance.md): a figure the agent states of itself in its self graph,
read there and nowhere else, and the package's constant where it states none.

Held over a world BOOTED as an agent boots it, so the self graph is the one the world authored and
the boot put in: what the self graph states is read; what the world states of the same agent in a
public graph, or a graph of the agent's own desires states, is not the agent's word about itself and
is not read. The kernel names no package's figure, so neither does this: the terms are the test's."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent.ontology import SELF_GRAPH
from agent.runtime import boot
from agent.stance import stance
from agent.store import Memo, graphs_of, update

T = "http://example.org/test#"
PATIENCE, LIMIT, WISH, UNSTATED = T + "patience", T + "limit", T + "wish", T + "unstated"

_HEAD = """@prefix : <http://example.org/test#> .
@prefix orexis: <http://example.org/orexis#> .
@prefix planning: <http://example.org/orexis/planning#> .
"""
#  THE WORLD STATES A FIGURE OF THE AGENT, publicly — beside who it is.
_WORLD = _HEAD + '<> a orexis:WorldGraph .\n:ann a orexis:Agent ; orexis:localId "ann" ; :limit 9 .\n'
#  THE SELF GRAPH STATES ONE, and the agent's desires another.
_SELF = _HEAD + "<> a orexis:SelfGraph .\n:ann a orexis:Self ; :patience 5 .\n"
_DESIRES = _HEAD + "<> a planning:DesireGraph ; orexis:beliefsOf :ann .\n:ann :wish 4 .\n"


@pytest.fixture
def ann(tmp_path: Path):
    (tmp_path / "world.ttl").write_text(_WORLD)
    (tmp_path / "beliefs").mkdir()
    (tmp_path / "beliefs" / "ann.self.ttl").write_text(_SELF)
    (tmp_path / "beliefs" / "ann.ttl").write_text(_DESIRES)
    return boot(tmp_path, "ann")


def test_a_figure_the_self_graph_states_is_read_in_the_defaults_type(ann):
    assert stance(ann, PATIENCE, 60.0) == 5.0 and isinstance(stance(ann, PATIENCE, 60.0), float)
    assert stance(ann, PATIENCE, 60) == 5 and isinstance(stance(ann, PATIENCE, 60), int)


def test_a_figure_the_self_graph_does_not_state_is_the_default(ann):
    assert stance(ann, UNSTATED, 7) == 7


def test_a_figure_stated_of_the_agent_anywhere_but_its_self_graph_is_not_its_stance(ann):
    """The world says `:ann :limit 9` in its public graph and ann's desires say `:ann :wish 4`: both
    are in ann's store and about ann, and neither is ann's word about itself."""
    assert stance(ann, LIMIT, 3) == 3, "a public graph's figure is the world's, not the self's"
    assert stance(ann, WISH, 1) == 1, "a desire graph is the agent's own, and not where it states itself"


def test_two_figures_or_one_that_is_no_number_is_the_default_said_in_the_log(ann, caplog):
    (graph,) = graphs_of(ann, SELF_GRAPH)
    update(ann, f'INSERT DATA {{ GRAPH <{graph}> {{ <{T}ann> <{PATIENCE}> 6 ; <{UNSTATED}> "soon" }} }}')
    with caplog.at_level("WARNING", logger="stance"):
        assert stance(ann, PATIENCE, 60.0) == 60.0
        assert stance(ann, UNSTATED, 7) == 7
    assert "states 2 figures for patience" in caplog.text and "which is no number" in caplog.text


def test_a_store_holding_no_self_answers_every_stance_with_the_default(tmp_path):
    """A store with no self — no catalogue at all here — has no one to state anything: a package
    reading a stance over it gets its own constant."""
    import pyoxigraph as ox
    assert stance(ox.Store(), PATIENCE, 60.0) == 60.0


def test_a_stance_is_remembered_for_as_long_as_the_memo_is_kept(ann):
    memo = Memo()
    assert stance(ann, PATIENCE, 60.0, memo) == 5.0
    (graph,) = graphs_of(ann, SELF_GRAPH)
    update(ann, f"DELETE DATA {{ GRAPH <{graph}> {{ <{T}ann> <{PATIENCE}> 5 }} }}")
    assert stance(ann, PATIENCE, 60.0, memo) == 5.0, "kept for the pass"
    assert stance(ann, PATIENCE, 60.0) == 60.0, "asked afresh, the self graph says nothing now"
