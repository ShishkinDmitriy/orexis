"""The self (knowledge/domain/kernel/self.md): the one agent a store is this agent's, AUTHORED by
the world in a self graph of that agent's own and CHECKED by the boot against the id the process
was told — and held to one at every door an instance could come through. A text asks
`?me a orexis:Self` and is bound nothing, so a second self would answer every such text for two
agents without a word; the gate stands at the boot, and here.

And whose a graph is, is what it says: a world's graph of an agent's own states its owner, a self
graph is its self's, and the boot keeps as its own exactly those naming it — never asking a file's
name. The loader's and speech's doors are held where those doors are (`test_document.py`,
`speech/tests/`); this holds the boot, and a world read whole, which holds no self."""

from __future__ import annotations

from pathlib import Path

import pyoxigraph as ox
import pytest

from agent.ontology import BELIEF, OREXIS, PUBLIC, SELF, SELF_GRAPH
from agent.runtime import MIND, SENSING, boot, packages_of, selves, world_of
from agent.store import DocumentRefused, forget_graph, graphs_of, rows, update

T = "http://example.org/test#"
ANN, BOB = T + "ann", T + "bob"
DESIRE_GRAPH = "http://example.org/orexis/planning#DesireGraph"

_HEAD = """@prefix : <http://example.org/test#> .
@prefix orexis: <http://example.org/orexis#> .
@prefix planning: <http://example.org/orexis/planning#> .
@prefix sosa: <http://www.w3.org/ns/sosa/> .
"""
#  TWO AGENTS OF ONE WORLD, and a sensor of bob's alone: ann loads no sensing, bob does.
_WORLD = (_HEAD + "<> a orexis:WorldGraph .\n"
          ':ann a orexis:Agent ; orexis:localId "ann" ; orexis:actsFor :pot .\n'
          ':bob a orexis:Agent ; orexis:localId "bob" ; orexis:actsFor :fern .\n'
          ":probe a sosa:Sensor ; sosa:isHostedBy :fern .\n")
#  EACH AGENT'S SELF GRAPH AND DESIRES, under names that say nothing of whose they are: the content
#  says, and a boot reading the names would take the wrong one.
_SELF = _HEAD + "<> a orexis:SelfGraph .\n:{who} a orexis:Self .\n"
_DESIRES = _HEAD + "<> a planning:DesireGraph ; orexis:beliefsOf :{who} .\n:{who} planning:holds :{who}_wish .\n"

_ROW_Q = """SELECT ?arrival ?owner WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph .
  $g orexis:arrivedBy ?arrival ; orexis:beliefsOf ?owner } }"""
_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"


@pytest.fixture
def world(tmp_path: Path) -> Path:
    (tmp_path / "world.ttl").write_text(_WORLD)
    (tmp_path / "beliefs").mkdir()
    (tmp_path / "beliefs" / "one.ttl").write_text(_SELF.format(who="bob"))
    (tmp_path / "beliefs" / "two.ttl").write_text(_SELF.format(who="ann"))
    (tmp_path / "beliefs" / "ann.ttl").write_text(_DESIRES.format(who="bob"))
    (tmp_path / "beliefs" / "bob.ttl").write_text(_DESIRES.format(who="ann"))
    return tmp_path


def _uri(world: Path, name: str) -> str:
    return (world / "beliefs" / name).resolve().as_uri()


def _self_rows(store) -> list[tuple[str, str]]:
    return sorted((q.subject.value, q.graph_name.value)
                  for q in store.quads_for_pattern(None, ox.NamedNode(_TYPE), ox.NamedNode(SELF), None))


def test_the_boot_puts_in_the_self_graph_the_world_authored_for_the_agent_it_was_told_to_be(world):
    store = boot(world, "ann")
    assert graphs_of(store, SELF_GRAPH) == [_uri(world, "two.ttl")], "ann's, found by what it says"
    assert _self_rows(store) == [(ANN, _uri(world, "two.ttl"))], "one row, in the self graph, and nowhere else"
    assert rows(store, _ROW_Q, (), g=_uri(world, "two.ttl")) == [{"arrival": OREXIS + "Asserted", "owner": ANN}], \
        "authored by the world and the agent's own"
    graph = _uri(world, "two.ttl")
    assert graph in graphs_of(store, BELIEF) and graph not in graphs_of(store, PUBLIC), \
        "a belief, read by every text answered over what is known — and nobody else's to read"


def test_the_boot_keeps_the_graphs_whose_content_names_it_whatever_they_are_called(world):
    """`beliefs/ann.ttl` is bob's by what it says, and `beliefs/bob.ttl` ann's: each agent holds the
    one naming it, and passes the other over without refusing it."""
    assert graphs_of(boot(world, "ann"), DESIRE_GRAPH) == [_uri(world, "bob.ttl")]
    assert graphs_of(boot(world, "bob"), DESIRE_GRAPH) == [_uri(world, "ann.ttl")]


def test_every_premise_asks_the_self_and_not_every_agent_the_world_states(world):
    """The sensor is bob's: booted as ann, no premise of sensing's holds, though the world holds a
    sensor of an agent's; booted as bob, it does."""
    assert packages_of(boot(world, "ann")) == MIND
    assert packages_of(boot(world, "bob")) == (*MIND, SENSING)


def test_an_agent_its_world_authored_no_self_graph_for_refuses_to_boot(world):
    (world / "beliefs" / "two.ttl").unlink()
    with pytest.raises(RuntimeError, match="no self graph of the world says who 'ann' is"):
        boot(world, "ann")


def test_an_agent_its_world_authored_two_self_graphs_for_refuses_to_boot(world):
    """Two documents saying the same agent is the self is still two homes for it: neither is picked."""
    (world / "beliefs" / "three.ttl").write_text(_SELF.format(who="ann"))
    with pytest.raises(RuntimeError, match="2 self graphs of the world say who 'ann' is"):
        boot(world, "ann")


def test_a_graph_of_an_agents_own_that_says_nobodys_is_refused(world):
    """Kept by its owner and owned by nobody, it would be in no agent's store, silently."""
    (world / "beliefs" / "stray.ttl").write_text(_HEAD + "<> a planning:DesireGraph .\n")
    with pytest.raises(DocumentRefused, match="says nobody's"):
        boot(world, "ann")
    with pytest.raises(DocumentRefused, match="says nobody's"):
        world_of(world)


def test_a_graph_of_an_agents_own_that_names_no_agent_of_the_world_is_refused(world):
    (world / "beliefs" / "typo.ttl").write_text(_DESIRES.format(who="anne"))
    with pytest.raises(DocumentRefused, match="the world states no such agent"):
        boot(world, "ann")


def test_a_public_graph_that_says_whose_it_is_is_refused(world):
    """A public graph is everyone's: owned, it would not be read again at a volume's next boot."""
    (world / "world.ttl").write_text(_WORLD.replace("<> a orexis:WorldGraph .", "<> a orexis:WorldGraph ; orexis:beliefsOf :ann ."))
    with pytest.raises(DocumentRefused, match="is public"):
        boot(world, "ann")


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
    graph the boot did not put in is a self to every text that asks, and is counted."""
    store = boot(world, "ann")
    update(store, f"INSERT DATA {{ GRAPH <urn:test:smuggled> {{ <{BOB}> a orexis:Self }} }}")
    with pytest.raises(RuntimeError, match="2 agents are the self"):
        boot(world, "ann", store)


def test_a_volume_lived_in_before_the_self_was_authored_is_given_the_world_s(world):
    """A volume from before its world authored a self graph holds none: the boot puts the authored
    one in — checked, never written from the id."""
    store = boot(world, "ann")
    forget_graph(store, _uri(world, "two.ttl"))
    assert selves(store) == []
    boot(world, "ann", store)
    assert selves(store) == [ANN] and graphs_of(store, SELF_GRAPH) == [_uri(world, "two.ttl")]


def test_a_world_document_of_a_public_kind_saying_who_the_self_is_is_refused_at_the_loader(world):
    (world / "imposter.ttl").write_text(_HEAD + "<> a orexis:WorldGraph .\n:bob a orexis:Self .\n")
    with pytest.raises(DocumentRefused, match="no self graph"):
        boot(world, "ann")


def test_a_private_document_of_another_kind_saying_who_the_self_is_is_refused_at_the_loader(world):
    """The self has one home: a desire graph stating it would be a second place to look."""
    (world / "beliefs" / "bob.ttl").write_text(_DESIRES.format(who="ann") + ":ann a orexis:Self .\n")
    with pytest.raises(DocumentRefused, match="no self graph"):
        boot(world, "ann")


def test_a_world_read_whole_holds_no_self_though_its_documents_state_two(world):
    """What the operator's tools and the simulator read: no agent's store, so every graph of an
    agent's own is passed over, the self graphs among them — a text asking for the self there
    answers nothing, and a premise is asked of every `orexis:Agent` instead (`dashboards`)."""
    store = world_of(world)
    assert selves(store) == [] and graphs_of(store, SELF_GRAPH) == [] and graphs_of(store, DESIRE_GRAPH) == []
    assert packages_of(store) == MIND, "the self asked where none is: nothing holds"
    assert SENSING in packages_of(store, OREXIS + "Agent"), "some agent of the world loads sensing"
