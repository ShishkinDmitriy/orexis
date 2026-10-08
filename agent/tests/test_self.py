"""The self (knowledge/domain/kernel/self.md): the one agent a store is this agent's, written by the
boot alone, once, in a graph of the agent's own — and held to one at every door an instance could
come through. A text asks `?me a orexis:Self` and is bound nothing, so a second self would answer
every such text for two agents without a word; the gate stands at the boot, and here.

The loader's and speech's doors are held where those doors are (`test_document.py`,
`speech/tests/`); this holds the boot, and a world read whole, which holds none."""

from __future__ import annotations

from pathlib import Path

import pyoxigraph as ox
import pytest

from agent.ontology import BELIEF, OREXIS, PUBLIC, SELF, SELF_GRAPH
from agent.runtime import MIND, SENSING, boot, packages_of, selves, world_of
from agent.store import DocumentRefused, forget_graph, graphs_of, rows, update

T = "http://example.org/test#"
ANN, BOB = T + "ann", T + "bob"

_HEAD = """@prefix : <http://example.org/test#> .
@prefix orexis: <http://example.org/orexis#> .
@prefix sosa: <http://www.w3.org/ns/sosa/> .
"""
#  TWO AGENTS OF ONE WORLD, and a sensor of bob's alone: ann loads no sensing, bob does.
_WORLD = (_HEAD + "<> a orexis:WorldGraph .\n"
          ':ann a orexis:Agent ; orexis:localId "ann" ; orexis:actsFor :pot .\n'
          ':bob a orexis:Agent ; orexis:localId "bob" ; orexis:actsFor :fern .\n'
          ":probe a sosa:Sensor ; sosa:isHostedBy :fern .\n")

_ROW_Q = """SELECT ?arrival ?owner WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph .
  $g orexis:arrivedBy ?arrival ; orexis:beliefsOf ?owner } }"""
_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"


@pytest.fixture
def world(tmp_path: Path) -> Path:
    (tmp_path / "world.ttl").write_text(_WORLD)
    return tmp_path


def _self_rows(store) -> list[tuple[str, str]]:
    return sorted((q.subject.value, q.graph_name.value)
                  for q in store.quads_for_pattern(None, ox.NamedNode(_TYPE), ox.NamedNode(SELF), None))


def test_the_boot_writes_the_agent_it_was_told_to_be_as_the_self_in_a_graph_of_its_own(world):
    store = boot(world, "ann")
    (graph,) = graphs_of(store, SELF_GRAPH)
    assert _self_rows(store) == [(ANN, graph)], "one row, in the self graph, and nowhere else"
    assert rows(store, _ROW_Q, (), g=graph) == [{"arrival": OREXIS + "Recorded", "owner": ANN}], \
        "the agent's own word about itself"
    assert graph in graphs_of(store, BELIEF) and graph not in graphs_of(store, PUBLIC), \
        "a belief, read by every text answered over what is known — and nobody else's to read"


def test_every_premise_asks_the_self_and_not_every_agent_the_world_states(world):
    """The sensor is bob's: booted as ann, no premise of sensing's holds, though the world holds a
    sensor of an agent's; booted as bob, it does."""
    assert packages_of(boot(world, "ann")) == MIND
    assert packages_of(boot(world, "bob")) == (*MIND, SENSING)


def test_a_volume_lived_in_keeps_the_one_self_it_has(world):
    store = boot(world, "ann")
    boot(world, "ann", store)
    assert selves(store) == [ANN] and len(graphs_of(store, SELF_GRAPH)) == 1


def test_a_volume_whose_self_is_another_agent_refuses_to_boot(world):
    """The right id handed the wrong volume: bob's process is not to live in ann's beliefs."""
    store = boot(world, "ann")
    with pytest.raises(RuntimeError, match=f"self is {ANN}, and the process was told to be 'bob'"):
        boot(world, "bob", store)
    assert selves(store) == [ANN], "refused, and nothing written"


def test_a_store_saying_two_agents_are_the_self_refuses_to_boot_and_picks_neither(world):
    """No door this side of the boot admits a second self, so one is put in by hand: a self in a
    graph the boot did not write is a self to every text that asks, and is counted."""
    store = boot(world, "ann")
    update(store, f"INSERT DATA {{ GRAPH <urn:test:smuggled> {{ <{BOB}> a orexis:Self }} }}")
    with pytest.raises(RuntimeError, match="2 agents are the self"):
        boot(world, "ann", store)


def test_a_volume_lived_in_before_the_self_was_written_is_given_one(world):
    """A volume from before `orexis:Self` holds none: the boot writes it, for the id it was told."""
    store = boot(world, "ann")
    (graph,) = graphs_of(store, SELF_GRAPH)
    forget_graph(store, graph)
    assert selves(store) == []
    boot(world, "ann", store)
    assert selves(store) == [ANN]


def test_a_world_document_saying_who_the_self_is_is_refused_at_the_loader(world):
    (world / "imposter.ttl").write_text(_HEAD + "<> a orexis:WorldGraph .\n:bob a orexis:Self .\n")
    with pytest.raises(DocumentRefused, match="only the boot says"):
        boot(world, "ann")


def test_a_world_read_whole_holds_no_self_and_asks_its_premises_of_every_agent(world):
    """What the operator's tools read: no agent's store, so no self — a text asking for one there
    answers nothing, and a premise is asked of every `orexis:Agent` instead (`dashboards`)."""
    store = world_of(world)
    assert selves(store) == [] and graphs_of(store, SELF_GRAPH) == []
    assert packages_of(store) == MIND, "the self asked where none is: nothing holds"
    assert SENSING in packages_of(store, OREXIS + "Agent"), "some agent of the world loads sensing"
